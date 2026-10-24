"""Model loading, input validation and inference. Depends only on pandas/numpy/scikit-learn/joblib."""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

log = logging.getLogger("ids.ml")

PIPELINE_FILE = "smart_home_ids_pipeline.joblib"
METADATA_FILE = "model_metadata.json"
REPORT_IMAGES = ("confusion_matrix.png", "feature_importance.png", "shap_summary.png")
REQUIRED_META = ("model_version", "features", "classes", "normal_class")

HOW_TO_ENABLE = [
    "Run notebooks/smart_home_intrusion_detection.ipynb in Google Colab (MODE = 'real' for MQTT_UAD).",
    "Download the artefact ZIP the last cell produces and unzip it into this project's models/ and reports/ folders.",
    "Install the scikit-learn version printed in model_metadata.json, then restart the backend.",
    "For a synthetic pipeline check only: python scripts/make_smoke_model.py (not a benchmark).",
]


class ModelUnavailable(Exception):
    """No usable trained model is installed."""


class SchemaError(ValueError):
    """Uploaded data does not match the trained feature schema."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ModelService:
    def __init__(self, models_dir: Path, reports_dir: Path, max_rows: int = 50000):
        self.models_dir = Path(models_dir)
        self.reports_dir = Path(reports_dir)
        self.max_rows = max_rows
        self.pipeline = None
        self.metadata: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self.load()

    # ------------------------------------------------------------------ loading
    def load(self) -> bool:
        self.pipeline, self.metadata = None, None
        pipe_path = self.models_dir / PIPELINE_FILE
        meta_path = self.models_dir / METADATA_FILE
        if not pipe_path.exists() or not meta_path.exists():
            self.error = f"No trained model found in {self.models_dir} (expected {PIPELINE_FILE} and {METADATA_FILE})."
            return False
        try:
            import joblib  # joblib files are pickles: only load artefacts you produced yourself.

            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            missing = [k for k in REQUIRED_META if k not in meta]
            if missing:
                raise ValueError(f"metadata is missing keys: {missing}")
            pipeline = joblib.load(pipe_path)
            if list(pipeline.classes_) != list(meta["classes"]):
                raise ValueError("pipeline classes do not match metadata classes")
            self.pipeline, self.metadata, self.error = pipeline, meta, None
            log.info("Loaded model %s", meta["model_version"])
            return True
        except Exception as exc:  # noqa: BLE001 - report any load failure as status, not a crash
            self.pipeline, self.metadata = None, None
            self.error = f"Model failed to load: {exc}"
            log.error(self.error)
            return False

    def require(self) -> None:
        if not self.loaded:
            raise ModelUnavailable(self.error or "model not loaded")

    @property
    def loaded(self) -> bool:
        return self.pipeline is not None and self.metadata is not None

    @property
    def feature_names(self) -> List[str]:
        return [f["name"] for f in self.metadata["features"]] if self.metadata else []

    # ------------------------------------------------------------------ status
    def status(self) -> Dict[str, Any]:
        import sklearn

        runtime = sklearn.__version__
        if not self.loaded:
            return {"available": False, "mode": "demo", "reason": self.error, "sklearn_version_runtime": runtime,
                    "how_to_enable": HOW_TO_ENABLE}
        m = self.metadata
        trained_ver = (m.get("environment") or {}).get("sklearn")
        return {
            "available": True, "mode": "ml", "reason": None,
            "model_version": m["model_version"], "model_type": m.get("model_type"),
            "is_synthetic": bool(m.get("is_synthetic", False)), "is_benchmark": bool(m.get("is_benchmark", False)),
            "trained_at": m.get("trained_at"), "classes": list(m["classes"]), "n_features": len(m["features"]),
            "dataset_name": (m.get("dataset") or {}).get("name"),
            "sklearn_version_trained": trained_ver, "sklearn_version_runtime": runtime,
            "version_mismatch": bool(trained_ver and trained_ver != runtime), "how_to_enable": [],
        }

    def metrics(self) -> Dict[str, Any]:
        if not self.loaded:
            return {"available": False, "reason": self.error, "images": [], "limitations": []}
        out: Dict[str, Any] = {"available": False, "images": [], "limitations": list(self.metadata.get("limitations", [])),
                               "is_synthetic": bool(self.metadata.get("is_synthetic", False))}
        mp, cp = self.reports_dir / "model_metrics.json", self.reports_dir / "classification_report.json"
        if not mp.exists():
            out["reason"] = f"{mp.name} not found in {self.reports_dir}."
            return out
        out["metrics"] = json.loads(mp.read_text(encoding="utf-8"))
        out["classification_report"] = json.loads(cp.read_text(encoding="utf-8")) if cp.exists() else None
        out["images"] = [n for n in REPORT_IMAGES if (self.reports_dir / n).exists()]
        out["available"] = True
        return out

    # -------------------------------------------------------------- validation
    def validate_frame(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        if not self.loaded:
            raise ModelUnavailable(self.error or "model not loaded")
        if len(df) == 0:
            raise SchemaError("The input contains no rows.")
        if len(df) > self.max_rows:
            raise SchemaError(f"Too many rows: {len(df)} (limit {self.max_rows}).")
        cols = [str(c).strip() for c in df.columns]
        if len(set(cols)) != len(cols):
            raise SchemaError("Duplicate column names in input.", {"duplicates": sorted({c for c in cols if cols.count(c) > 1})})
        df = df.copy()
        df.columns = cols
        expected = self.feature_names
        missing = [c for c in expected if c not in cols]
        unexpected = [c for c in cols if c not in expected]
        if missing or unexpected:
            raise SchemaError("Columns do not match the trained feature schema.",
                              {"missing": missing[:50], "unexpected": unexpected[:50],
                               "missing_count": len(missing), "unexpected_count": len(unexpected)})
        df = df[expected]
        numeric = df.apply(pd.to_numeric, errors="coerce")
        bad = numeric.isna() & df.notna()  # a value was present but is not a number
        if bad.any().any():
            rows = sorted(set(np.where(bad.to_numpy())[0].tolist()))
            raise SchemaError("Non-numeric values found in feature columns.",
                              {"columns": [c for c in expected if bad[c].any()][:20], "example_rows": rows[:10]})
        if np.isinf(numeric.to_numpy(dtype=float)).any():
            raise SchemaError("Infinite values found in feature columns.")
        n_missing = int(numeric.isna().any(axis=1).sum())
        info = {"status": "valid", "rows": int(len(numeric)), "columns": len(expected),
                "rows_with_missing_values": n_missing,
                "note": ("Missing cells are filled by the median imputer fitted during training."
                         if n_missing else "No missing values.")}
        return numeric, info

    # --------------------------------------------------------------- inference
    def predict_frame(self, df: pd.DataFrame) -> Dict[str, Any]:
        X, info = self.validate_frame(df)
        m = self.metadata
        classes = list(m["classes"])
        preds = self.pipeline.predict(X)
        show_proba = m.get("probability_display") == "vote_share" and hasattr(self.pipeline, "predict_proba")
        proba = self.pipeline.predict_proba(X) if show_proba else None
        importance = (m.get("feature_importance") or [])[:5]
        rows: List[Dict[str, Any]] = []
        for i, p in enumerate(preds):
            ev = []
            for imp in importance:
                v = X.iloc[i][imp["feature"]]
                ev.append({"feature": imp["feature"], "value": None if pd.isna(v) else float(v),
                           "global_importance": float(imp["importance"])})
            rows.append({
                "row": i, "predicted_class": str(p), "is_attack": str(p) != m["normal_class"],
                "probabilities": {c: round(float(x), 4) for c, x in zip(classes, proba[i])} if proba is not None else None,
                "evidence": ev,
            })
        summary: Dict[str, int] = {}
        for r in rows:
            summary[r["predicted_class"]] = summary.get(r["predicted_class"], 0) + 1
        return {
            "mode": "ml", "model_version": m["model_version"], "predicted_at": _now(),
            "is_synthetic_model": bool(m.get("is_synthetic", False)), "validation": info, "summary": summary,
            "probability_note": ("Values are the share of trees voting for each class. They are not calibrated "
                                 "probabilities." if proba is not None else None),
            "explanation_type": "global_feature_importance",
            "predictions": rows,
        }
