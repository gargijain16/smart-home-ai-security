# AI-Powered Smart Home Intrusion Detection System Using Machine Learning
*An intelligent security monitoring framework for consumer IoT environments.*
Manipal University Jaipur · ICS3120 AI for Cyber Security (VAPT, ICS3102, is planned for a later phase) · Sector: Smart Home

## What is real, what is simulated
| Part | Status |
|---|---|
| ML pipeline (Decision Tree + Random Forest, leakage-reduced split, metrics, export) | **Implemented.** Notebook executed end-to-end in synthetic smoke-test mode only. **Not yet trained on the real dataset.** |
| Inference API with strict schema validation | Implemented and unit-tested at the service level |
| Device and event data on the dashboard | **Simulated.** Labels are threshold rules, never ML output |
| CSV prediction | Real ML, available once a model is installed; otherwise a clear "no model" state |
| Model metrics shown in the UI | Read from saved `reports/*.json`. Nothing hard-coded |
| VAPT | Not implemented. Disabled "Coming later" nav item and an integration plan only |

The simulated events carry no packet-level features, so the model cannot score them. The two paths are deliberately separate.

## Quick start on Fedora (no Docker, no dataset, no broker)
```bash
sudo dnf install -y python3 python3-pip nodejs npm git
cd smart-home-ai-security
python3 -m venv .venv && source .venv/bin/activate
pip install -r backend/requirements.txt
python -m unittest discover -s tests -t . -v         # backend tests

# terminal 1: backend
cd backend && uvicorn app.main:app --host 127.0.0.1 --port 8000
# terminal 2: frontend
cd frontend && npm install && npm run dev            # http://localhost:5173
```
Stop either process with `Ctrl+C`. Frontend tests: `cd frontend && npm test`. Type check: `npm run typecheck`.
In the app press **Start** on the Overview to run the simulation (demo mode).

Optional ML-mode check without a dataset: `python scripts/make_smoke_model.py`, then restart the backend. The UI will label it a synthetic pipeline check.

Troubleshooting: `ModuleNotFoundError` means the venv is not active; port 8000 busy → `--port 8001` and set `VITE` proxy target in `frontend/vite.config.ts`; scikit-learn version warning → `pip install scikit-learn==<version in models/model_metadata.json>`; blank page with a red "Backend not reachable" card → backend is not running.

## Real training (Google Colab)
1. Open Colab → File → Upload notebook → `notebooks/smart_home_intrusion_detection.ipynb`.
2. Download `DoS.csv`, `MitM.csv`, `Intrusion.csv` from https://doi.org/10.6084/m9.figshare.24420958.v1 (CC BY 4.0).
3. In the config cell set `MODE = "real"` (or `os.environ["IDS_MODE"]="real"`), then Runtime → Run all; upload the three CSVs when asked.
4. **Check the printed label counts against the published counts** and the dropped-column list. The column names were not verified by the author of this repo, so the notebook discovers and reports them.
5. The last cell downloads `smart_home_ids_artifacts.zip`. Unzip so `models/` and `reports/` sit beside `backend/`, run the printed `pip install scikit-learn==X`, restart the backend (or `POST /api/model/reload`).

## Deployment
See `docs/DEPLOYMENT.md`. A Vercel-hosted frontend **cannot** call an API on your laptop's `localhost`; judges' browsers need a public backend URL (or a tunnel).

## Documentation
`docs/ARCHITECTURE.md` (problem, objectives, diagrams) · `DATASET_CARD.md` · `THREAT_MODEL.md` · `METHODOLOGY.md` · `TESTING_REPORT.md` · `DEPLOYMENT.md` · `VAPT_INTEGRATION.md` · `DEMO_AND_VIVA.md`

## Known limitations
- Real-dataset results do not exist yet; any number in the UI before that is labelled synthetic.
- MQTT_UAD files each contain one attack family; part of what a model learns may be capture-session specific.
- The poster's kill chain (brute force, wildcard topic enumeration) is simulated with rules; the model is not evaluated on it.
- SQLite/simulator state is in-process: run a single backend worker; data resets on ephemeral hosts.
- `joblib` artefacts are pickles: load only files you produced.
- The FastAPI layer and the React build were **not executed in the authoring sandbox** (no network to install packages); see the testing report.
