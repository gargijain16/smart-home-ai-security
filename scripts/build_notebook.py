"""Generates notebooks/smart_home_intrusion_detection.ipynb. Run: python scripts/build_notebook.py"""
import json
from pathlib import Path

cells = []
def md(t): cells.append(("markdown", t.strip("\n")))
def code(t): cells.append(("code", t.strip("\n")))

md("""
# AI-Powered Smart Home Intrusion Detection (MQTT)
**Manipal University Jaipur · ICS3120 AI for Cyber Security · Sector: Smart Home**

## 1. Introduction and threat model
Consumer smart homes run lock, camera, light and HVAC devices over MQTT through a broker. Weak or absent broker
authentication lets an attacker with network access flood the broker (DoS), sit between a device and the broker
(MitM) or gain unauthorised access (intrusion). This notebook trains **Decision Tree** and **Random Forest** classifiers on
labelled frame-level MQTT traffic and exports a fitted pipeline for the dashboard's inference API.

**Scope of what the model can claim:** it classifies *network-frame feature rows* of the kinds present in the training data
(normal, DoS, MitM, intrusion). It does not monitor real devices, and it has not been evaluated on credential brute force
or topic enumeration unless the dataset contains them.

### Two modes (set `MODE` in the next cell)
| MODE | Data | Result is |
|---|---|---|
| `real` | MQTT_UAD CSVs you download/upload (CC BY 4.0) | a genuine benchmark of that dataset |
| `smoke` | synthetic rows generated below | **a pipeline check only. Never a benchmark.** |
""")
code("""
# ---- Configuration ---------------------------------------------------------------------------
import os, sys, json, time, hashlib, warnings, platform, re, zipfile
from datetime import datetime, timezone
from pathlib import Path
import numpy as np, pandas as pd
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")

MODE = os.environ.get("IDS_MODE", "smoke")        # <-- "real" for MQTT_UAD, "smoke" for the synthetic pipeline check
assert MODE in ("smoke", "real"), "MODE must be 'smoke' or 'real'"
OUT_DIR  = Path(os.environ.get("IDS_OUT",  "artifacts"))
DATA_DIR = Path(os.environ.get("IDS_DATA", "data"))
RANDOM_STATE = 42
BLOCK_SIZE = 200                      # contiguous frames kept together when splitting
INSTALL_SHAP = os.environ.get("IDS_INSTALL_SHAP", "0") == "1"
LABEL_COL_OVERRIDE = None             # set if auto-detection of the label column fails (real mode)
EXTRA_DROP_COLUMNS = []               # add column names you want excluded from the features
REAL_FILES = {"DoS": "DoS.csv", "MitM": "MitM.csv", "Intrusion": "Intrusion.csv"}
PUBLISHED_COUNTS = {"DoS": (45513, 49112), "MitM": (3855, 106813), "Intrusion": (1898, 78995)}  # (attack, normal)
for sub in ("models", "reports"): (OUT_DIR / sub).mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)
IS_SYNTHETIC = MODE == "smoke"
print(f"MODE={MODE}   synthetic={IS_SYNTHETIC}   out={OUT_DIR.resolve()}")
if IS_SYNTHETIC:
    print("*** SMOKE-TEST MODE: synthetic data. Metrics below are NOT a benchmark. ***")
""")
md("## 2. Environment setup")
code("""
if INSTALL_SHAP:                       # optional, only for section 20
    import subprocess; subprocess.run([sys.executable, "-m", "pip", "install", "-q", "shap"], check=False)
import sklearn
print("python", platform.python_version(), "| sklearn", sklearn.__version__, "| pandas", pd.__version__, "| numpy", np.__version__)
IN_COLAB = "google.colab" in sys.modules
""")
md("""
## 3–4. Dataset download or upload, source and licence
**Real mode dataset:** *MQTT_UAD – MQTT Under Attack Dataset* (Aveleira-Mata et al., 2025). Licence **CC BY 4.0**.
Data: https://doi.org/10.6084/m9.figshare.24420958.v1 · Paper: https://doi.org/10.1016/j.dib.2025.112167
Files: `DoS.csv`, `MitM.csv`, `Intrusion.csv`. Download them from the DOI page in your browser and upload them in the next cell
(a stable direct-download link could not be verified, so none is hard-coded). Cite the authors if you use or share results.
""")
code("""
def have_real_files():
    return all((DATA_DIR / f).exists() for f in REAL_FILES.values())

if MODE == "real" and not have_real_files():
    if IN_COLAB:
        from google.colab import files
        print("Select DoS.csv, MitM.csv and Intrusion.csv ...")
        for name, content in files.upload().items():
            (DATA_DIR / name).write_bytes(content)
    if not have_real_files():
        raise FileNotFoundError(f"Place {list(REAL_FILES.values())} in {DATA_DIR.resolve()} (see section 3-4). "
                                "The notebook will not silently fall back to synthetic data.")
""")
md("## 5–6. Schema validation and dataset inspection")
code("""
SYN_FEATURES = ["frame_len", "tcp_window", "mqtt_msg_len", "mqtt_msgtype", "inter_arrival_ms",
                "conn_rate_per_s", "pub_rate_per_s", "failed_auth_count", "payload_entropy", "keepalive_s"]

def make_synthetic(seed=RANDOM_STATE, n=6000):
    # SYNTHETIC. Overlapping distributions on purpose so the task is not trivially separable.
    rng = np.random.default_rng(seed)
    parts = []
    for source, attack, share in (("DoS", "dos", .45), ("MitM", "mitm", .06), ("Intrusion", "intrusion", .04)):
        k = int(n * share); m = n - k
        def block(count, label, mu):
            d = {c: np.abs(rng.normal(mu[i], mu[i] * .45 + 1, count)) for i, c in enumerate(SYN_FEATURES)}
            d["__label"] = label; return pd.DataFrame(d)
        base = [300, 29000, 120, 3, 80, 4, 6, .1, 4.2, 60]
        atk = {"dos": [160, 8000, 60, 3, 4, 60, 150, .2, 3.0, 60],
               "mitm": [330, 28000, 135, 3, 95, 5, 7, .2, 4.9, 45],
               "intrusion": [310, 29000, 125, 3, 70, 6, 8, 3.5, 4.3, 60]}[attack]
        df = pd.concat([block(m, "normal", base), block(k, attack, atk)]).sample(frac=1, random_state=seed).reset_index(drop=True)
        df["__source"] = source; df["__order"] = np.arange(len(df))
        df["frame_number"] = df["__order"]; df["ip_src"] = rng.integers(1, 254, len(df))   # identifiers to prove the drop logic
        parts.append(df)
    return pd.concat(parts, ignore_index=True)

def load_real():
    LABELS = {c.lower() for c in ["label", "class", "attack", "target", "attack_type", "type"]}
    NORMAL = {"0", "normal", "benign", "legitimate", "legit", "none"}
    parts, report = [], {}
    for attack, fname in REAL_FILES.items():
        raw = pd.read_csv(DATA_DIR / fname, low_memory=False)
        raw.columns = [str(c).strip() for c in raw.columns]
        lab = LABEL_COL_OVERRIDE if LABEL_COL_OVERRIDE in raw.columns else next((c for c in raw.columns if c.lower() in LABELS), None)
        if lab is None:
            raise ValueError(f"{fname}: no label column found. Columns: {list(raw.columns)}. Set LABEL_COL_OVERRIDE.")
        vals = raw[lab].astype(str).str.strip().str.lower()
        is_norm = vals.isin(NORMAL)
        print(f"{fname}: {raw.shape[0]:,} rows x {raw.shape[1]} cols | label column '{lab}' | values: {raw[lab].value_counts().to_dict()}")
        a, nrm = int((~is_norm).sum()), int(is_norm.sum()); pa, pn = PUBLISHED_COUNTS[attack]
        ok = abs(a - pa) <= .01 * pa and abs(nrm - pn) <= .01 * pn
        print(f"   attack={a:,} normal={nrm:,}  published=({pa:,}, {pn:,})  ->  {'matches' if ok else 'MISMATCH: check label encoding!'}")
        report[attack] = {"file": fname, "label_column": lab, "rows": int(len(raw)), "attack": a, "normal": nrm, "matches_published": bool(ok)}
        df = raw.drop(columns=[lab]).copy()
        df["__label"] = np.where(is_norm, "normal", attack.lower()); df["__source"] = attack; df["__order"] = np.arange(len(df))
        parts.append(df)
    return pd.concat(parts, ignore_index=True), report

if MODE == "real":
    df, SOURCE_REPORT = load_real()
else:
    df, SOURCE_REPORT = make_synthetic(), {"synthetic": True}
print("combined:", df.shape); display_cols = [c for c in df.columns if not c.startswith("__")][:12]
print(df[display_cols + ["__label", "__source"]].head())
""")
md("## 7–8. Missing values, duplicates and cleaning (identifier columns are removed to prevent leakage)")
code("""
DROP_TOKENS = {"ip", "mac", "addr", "address", "timestamp", "epoch", "relative", "date", "id", "stream", "index",
               "number", "no", "port", "srcport", "dstport"}
def is_identifier(col):
    toks = set(re.split(r"[._\\s\\-]+", col.lower()))
    return bool(toks & DROP_TOKENS) or col in EXTRA_DROP_COLUMNS

candidates = [c for c in df.columns if not c.startswith("__")]
dropped = {"identifier_like": [c for c in candidates if is_identifier(c)]}
candidates = [c for c in candidates if c not in dropped["identifier_like"]]
numeric = df[candidates].apply(pd.to_numeric, errors="coerce")
dropped["non_numeric"] = [c for c in candidates if numeric[c].isna().mean() > .5 and df[c].notna().mean() > .5]
dropped["mostly_missing"] = [c for c in candidates if numeric[c].isna().mean() > .5 and c not in dropped["non_numeric"]]
keep = [c for c in candidates if c not in dropped["non_numeric"] + dropped["mostly_missing"]]
dropped["constant"] = [c for c in keep if numeric[c].nunique(dropna=True) <= 1]
FEATURES = [c for c in keep if c not in dropped["constant"]]
print("dropped columns:", json.dumps(dropped, indent=1)[:1500]); print("features kept:", len(FEATURES))
assert len(FEATURES) > 0, "No usable feature columns - review the drop rules."

data = numeric[FEATURES].copy()
data[["__label", "__source", "__order"]] = df[["__label", "__source", "__order"]]
n0 = len(data)
data = data.replace([np.inf, -np.inf], np.nan)
dups = int(data.duplicated(subset=FEATURES + ["__label"]).sum())
data = data.drop_duplicates(subset=FEATURES + ["__label"]).sort_values(["__source", "__order"]).reset_index(drop=True)
print(f"rows {n0:,} -> {len(data):,} after removing {dups:,} exact duplicates; missing cells: {int(data[FEATURES].isna().sum().sum()):,}")
""")
md("## 9. Exploratory data analysis")
code("""
dist = data["__label"].value_counts()
print(dist.to_string())
fig, ax = plt.subplots(1, 2, figsize=(11, 3.4))
dist.plot.bar(ax=ax[0], color="#3b82f6", title="Class distribution (after cleaning)")
top = data[FEATURES].var().sort_values(ascending=False).head(6).index
data.groupby("__label")[list(top[:3])].median().plot.bar(ax=ax[1], title="Median of 3 high-variance features")
plt.tight_layout(); plt.show()
""")
md("""
## 10. Feature engineering
No hand-made features are added: the exported pipeline must accept exactly the dataset's columns so the API can validate uploads against
the same schema. Median imputation is part of the pipeline (fitted on training rows only).

## 11. Leakage-safe splitting
Frames from one capture are strongly correlated, so a random row split would put near-identical neighbours in train and test.
Each source file is cut into **contiguous blocks of `BLOCK_SIZE` frames**; whole blocks go to train (70%), validation (15%) or test (15%)
in a repeating pattern. Duplicates were removed first and identifier/time-position columns were dropped. This is leakage-*reduced*,
not strict forward-chaining: block boundaries are the residual risk, and a model may still learn per-file capture-session
differences (see limitations).
""")
code("""
pos = data.groupby("__source").cumcount()
blk = (pos // BLOCK_SIZE) % 20
data["__split"] = np.where(blk < 14, "train", np.where(blk < 17, "val", "test"))
classes = sorted(data["__label"].unique()); NORMAL_CLASS = "normal"
tab = pd.crosstab(data["__label"], data["__split"]); print(tab.to_string())
missing_cls = [(s, c) for s in ("train", "val", "test") for c in classes if tab.loc[c, s] == 0]
assert not missing_cls, f"Split lacks classes {missing_cls}: reduce BLOCK_SIZE or review the data."
Xtr, ytr = data.loc[data.__split == "train", FEATURES], data.loc[data.__split == "train", "__label"]
Xva, yva = data.loc[data.__split == "val", FEATURES],   data.loc[data.__split == "val", "__label"]
Xte, yte = data.loc[data.__split == "test", FEATURES],  data.loc[data.__split == "test", "__label"]
""")
md("""
## 12–14. Decision Tree, Random Forest and class-imbalance handling
Imbalance is handled with `class_weight` (`balanced` / `balanced_subsample`), not by oversampling, so evaluation data stays untouched.
Both are trained on the **train** split; the winner is chosen on **validation** macro-F1; the **test** split is used once for reporting.
""")
code("""
from sklearn.pipeline import Pipeline
from sklearn.impute import SimpleImputer
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (accuracy_score, precision_recall_fscore_support, classification_report, confusion_matrix, f1_score)

def build(est): return Pipeline([("imputer", SimpleImputer(strategy="median")), ("model", est)])
CANDIDATES = {
    "decision_tree": lambda: build(DecisionTreeClassifier(max_depth=14, min_samples_leaf=3, class_weight="balanced", random_state=RANDOM_STATE)),
    "random_forest": lambda: build(RandomForestClassifier(n_estimators=150, max_depth=18, min_samples_leaf=2,
                                   class_weight="balanced_subsample", n_jobs=-1, random_state=RANDOM_STATE)),
}
fitted, val_f1 = {}, {}
for name, mk in CANDIDATES.items():
    t = time.time(); fitted[name] = mk().fit(Xtr, ytr)
    val_f1[name] = f1_score(yva, fitted[name].predict(Xva), average="macro", zero_division=0)
    print(f"{name:14s} fit {time.time()-t:5.1f}s   validation macro-F1 = {val_f1[name]:.4f}")
""")
md("## 15–18. Model comparison, metrics, confusion matrix, false-positive / false-negative analysis")
code("""
def evaluate(pipe, X, y):
    pred = pipe.predict(X)
    p, r, f, _ = precision_recall_fscore_support(y, pred, average="macro", zero_division=0)
    cm = confusion_matrix(y, pred, labels=classes); tot = cm.sum(); rates = {}
    for i, c in enumerate(classes):
        tp = cm[i, i]; fn = cm[i].sum() - tp; fp = cm[:, i].sum() - tp; tn = tot - tp - fn - fp
        rates[c] = {"fpr": float(fp / (fp + tn)) if fp + tn else None, "fnr": float(fn / (fn + tp)) if fn + tp else None, "support": int(cm[i].sum())}
    ni = classes.index(NORMAL_CLASS)       # attack-vs-normal view: an alarm is any non-normal prediction
    fa = int(cm[ni].sum() - cm[ni, ni]); tn_ = int(cm[ni, ni]); fn_ = int(cm[:, ni].sum() - cm[ni, ni]); ta = int(tot - cm[ni].sum())
    return {"accuracy": float(accuracy_score(y, pred)), "macro_precision": float(p), "macro_recall": float(r), "macro_f1": float(f),
            "weighted_f1": float(f1_score(y, pred, average="weighted", zero_division=0)), "per_class_rates": rates,
            "binary_attack_vs_normal": {"false_positive_rate": fa / (fa + tn_) if fa + tn_ else None,
                                        "false_negative_rate": fn_ / (fn_ + ta) if fn_ + ta else None}}, cm, pred

test_eval = {n: evaluate(p, Xte, yte) for n, p in fitted.items()}
SELECTED = max(val_f1, key=val_f1.get); pipe = fitted[SELECTED]
print(pd.DataFrame({n: {"val_macro_f1": val_f1[n], "test_macro_f1": e[0]["macro_f1"], "test_accuracy": e[0]["accuracy"]}
                    for n, e in test_eval.items()}).T.round(4).to_string())
print("\\nSelected on validation macro-F1:", SELECTED)
metrics_test, cm, pred_te = test_eval[SELECTED]
report = classification_report(yte, pred_te, labels=classes, output_dict=True, zero_division=0)
print(classification_report(yte, pred_te, labels=classes, zero_division=0))
print("attack-vs-normal:", metrics_test["binary_attack_vs_normal"])

fig, ax = plt.subplots(figsize=(5.4, 4.6)); im = ax.imshow(cm, cmap="Blues")
ax.set_xticks(range(len(classes)), classes, rotation=30, ha="right"); ax.set_yticks(range(len(classes)), classes)
for i in range(len(classes)):
    for j in range(len(classes)): ax.text(j, i, int(cm[i, j]), ha="center", va="center", color="white" if cm[i, j] > cm.max() / 2 else "black")
ax.set_xlabel("Predicted"); ax.set_ylabel("Actual"); ax.set_title(f"Confusion matrix - {SELECTED}" + ("  [SYNTHETIC]" if IS_SYNTHETIC else ""))
plt.tight_layout(); plt.savefig(OUT_DIR / "reports/confusion_matrix.png", dpi=140); plt.show()
""")
md("## 19–20. Feature importance and optional SHAP")
code("""
feat_imp = sorted(({"feature": f, "importance": float(v)} for f, v in zip(FEATURES, pipe.named_steps["model"].feature_importances_)),
                  key=lambda d: -d["importance"])
top = feat_imp[:20][::-1]
plt.figure(figsize=(6.4, 5)); plt.barh([d["feature"] for d in top], [d["importance"] for d in top], color="#7c3aed")
plt.title(f"Feature importance (impurity) - {SELECTED}" + ("  [SYNTHETIC]" if IS_SYNTHETIC else "")); plt.tight_layout()
plt.savefig(OUT_DIR / "reports/feature_importance.png", dpi=140); plt.show()

try:                                   # SHAP is optional: skipped cleanly if unavailable
    import shap
    Xs = pd.DataFrame(pipe.named_steps["imputer"].transform(Xte.sample(min(300, len(Xte)), random_state=RANDOM_STATE)), columns=FEATURES)
    sv = shap.TreeExplainer(pipe.named_steps["model"]).shap_values(Xs)
    shap.summary_plot(sv, Xs, show=False, class_names=classes); plt.tight_layout()
    plt.savefig(OUT_DIR / "reports/shap_summary.png", dpi=140, bbox_inches="tight"); plt.show()
except ImportError: print("SHAP not installed - skipped (set INSTALL_SHAP / pip install shap to enable).")
except Exception as e: print("SHAP failed, skipped:", type(e).__name__, e)
""")
md("## 21. New-sample inference (a row the model never saw during training)")
code("""
row = Xte.iloc[[len(Xte) // 3]]
print("actual class   :", yte.loc[row.index[0]]); print("predicted class:", pipe.predict(row)[0])
if SELECTED == "random_forest":
    print("tree vote share:", {c: round(float(v), 3) for c, v in zip(pipe.classes_, pipe.predict_proba(row)[0])})
lat1 = []
for i in range(200):
    r = Xte.iloc[[i % len(Xte)]]; t = time.perf_counter(); pipe.predict(r); lat1.append((time.perf_counter() - t) * 1000)
t = time.perf_counter(); pipe.predict(Xte.iloc[:1000]); batch_ms = (time.perf_counter() - t) * 1000
LATENCY = {"single_sample_median_ms": float(np.median(lat1)), "single_sample_p95_ms": float(np.percentile(lat1, 95)),
           "batch_1000_ms": float(batch_ms), "measured_on": platform.platform()}
print(LATENCY)
""")
md("## 22–23. Model export, metadata and evaluation report")
code("""
import joblib
MODEL_PATH = OUT_DIR / "models/smart_home_ids_pipeline.joblib"
joblib.dump(pipe, MODEL_PATH, compress=3)
digest = hashlib.sha256(MODEL_PATH.read_bytes()).hexdigest()
stamp = datetime.now(timezone.utc)
VERSION = f"{'smoke' if IS_SYNTHETIC else 'mqtt-uad'}-{SELECTED}-{stamp:%Y%m%d}-{digest[:8]}"
splits = {s: data.loc[data.__split == s, "__label"].value_counts().to_dict() for s in ("train", "val", "test")}
LIMITS = [
    "Classifies network-frame feature rows. It does not observe real devices or the simulator's events.",
    "Random Forest vote share is not a calibrated probability.",
    "Each source file contains one attack family; normal traffic differs per file, so part of the signal may be capture-session specific.",
    "Contiguous-block splitting reduces but does not eliminate temporal leakage; performance on a new testbed is unknown.",
    "Not evaluated on credential brute force or MQTT topic enumeration unless present in the data."]
if IS_SYNTHETIC: LIMITS.insert(0, "SYNTHETIC SMOKE-TEST MODEL: trained on generated data. Results are not a benchmark and mean nothing about real traffic.")
dataset_meta = ({"name": "SYNTHETIC SMOKE TEST (generated in notebook, not a real dataset)", "licence": "n/a", "mode": "smoke"} if IS_SYNTHETIC else
    {"name": "MQTT_UAD (MQTT Under Attack Dataset)", "doi": "10.6084/m9.figshare.24420958.v1", "paper_doi": "10.1016/j.dib.2025.112167",
     "licence": "CC BY 4.0", "files": list(REAL_FILES.values()), "mode": "real", "source_checks": SOURCE_REPORT})
dataset_meta.update(rows_after_cleaning=int(len(data)), duplicates_removed=dups, dropped_columns=dropped)
metadata = {
    "model_version": VERSION, "model_type": SELECTED, "trained_at": stamp.isoformat(), "normal_class": NORMAL_CLASS,
    "classes": [str(c) for c in pipe.classes_], "features": [{"name": f, "dtype": "float"} for f in FEATURES],
    "is_synthetic": IS_SYNTHETIC, "is_benchmark": not IS_SYNTHETIC,
    "probability_display": "vote_share" if SELECTED == "random_forest" else "none",
    "dataset": dataset_meta, "label_distribution": {"all": data["__label"].value_counts().to_dict(), **splits},
    "evaluation": {"split": f"contiguous blocks of {BLOCK_SIZE} frames per source file, 70/15/15 train/val/test",
                   "selection_metric": "validation macro-F1", "test_used_once_for_reporting": True, "random_state": RANDOM_STATE,
                   "imbalance_handling": "class_weight", "candidates": list(CANDIDATES), "refit_on_train_plus_val": False},
    "feature_importance": feat_imp[:30], "limitations": LIMITS, "artifact_sha256": digest,
    "environment": {"python": platform.python_version(), "sklearn": sklearn.__version__, "pandas": pd.__version__, "numpy": np.__version__},
}
(OUT_DIR / "models/model_metadata.json").write_text(json.dumps(metadata, indent=2))
model_metrics = {"mode": MODE, "is_synthetic": IS_SYNTHETIC, "selected_model": SELECTED, "generated_at": stamp.isoformat(),
    "test": metrics_test, "n_test": int(len(Xte)),
    "comparison": {n: {"validation_macro_f1": val_f1[n], "test_macro_f1": e[0]["macro_f1"], "test_accuracy": e[0]["accuracy"]} for n, e in test_eval.items()},
    "confusion_matrix": {"labels": classes, "matrix": cm.tolist()}, "latency_ms": LATENCY}
(OUT_DIR / "reports/model_metrics.json").write_text(json.dumps(model_metrics, indent=2))
(OUT_DIR / "reports/classification_report.json").write_text(json.dumps(report, indent=2))
print("exported:", VERSION); print(f"Install in the backend:  pip install scikit-learn=={sklearn.__version__}")
""")
md("## 24. Download artefacts\nUnzip into the project so that `models/` and `reports/` sit next to `backend/`, then restart the backend.")
code("""
ZIP_PATH = OUT_DIR / "smart_home_ids_artifacts.zip"
with zipfile.ZipFile(ZIP_PATH, "w", zipfile.ZIP_DEFLATED) as z:
    for f in sorted((OUT_DIR / "models").glob("*")) + sorted((OUT_DIR / "reports").glob("*")):
        if f.is_file(): z.write(f, f"{f.parent.name}/{f.name}")
print("created", ZIP_PATH, f"({ZIP_PATH.stat().st_size/1e6:.1f} MB)")
if IN_COLAB:
    from google.colab import files; files.download(str(ZIP_PATH))
""")

def to_cell(kind, text):
    lines = text.split("\n"); src = [l + "\n" for l in lines[:-1]] + [lines[-1]]
    base = {"cell_type": kind, "metadata": {}, "source": src}
    return base if kind == "markdown" else {**base, "execution_count": None, "outputs": []}

nb = {"cells": [to_cell(k, t) for k, t in cells], "metadata": {"kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
      "language_info": {"name": "python"}, "colab": {"provenance": []}}, "nbformat": 4, "nbformat_minor": 5}
out = Path(__file__).resolve().parents[1] / "notebooks" / "smart_home_intrusion_detection.ipynb"
out.write_text(json.dumps(nb, indent=1)); print("wrote", out)
