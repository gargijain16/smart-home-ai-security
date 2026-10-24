"""Health, model, metrics and dataset endpoints."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from ..config import APP_VERSION
from ..schemas import DatasetInfo, HealthResponse, MetricsResponse, ModelStatus
from ..services.ml_service import REPORT_IMAGES

router = APIRouter(prefix="/api")
MANIFEST = Path(__file__).resolve().parents[1] / "resources" / "dataset_manifest.json"


@router.get("/health", response_model=HealthResponse, tags=["system"])
def health(request: Request):
    st = request.app.state
    return {"status": "ok", "version": APP_VERSION, "time": datetime.now(timezone.utc).isoformat(),
            "mode": "ml" if st.model.loaded else "demo", "model_loaded": st.model.loaded,
            "simulation_state": st.simulation.state}


@router.get("/model/status", response_model=ModelStatus, tags=["model"])
def model_status(request: Request):
    return request.app.state.model.status()


@router.post("/model/reload", response_model=ModelStatus, tags=["model"])
def model_reload(request: Request):
    """Re-read model artefacts from disk (after copying new files into models/)."""
    request.app.state.model.load()
    return request.app.state.model.status()


@router.get("/model/metrics", response_model=MetricsResponse, tags=["model"])
def model_metrics(request: Request):
    return request.app.state.model.metrics()


@router.get("/reports/{name}", tags=["model"])
def report_image(name: str, request: Request):
    if name not in REPORT_IMAGES:
        raise HTTPException(status_code=404, detail="Unknown report image.")
    path = request.app.state.settings.reports_dir / name
    if not path.exists():
        raise HTTPException(status_code=404, detail="Report image not generated yet.")
    return FileResponse(path, media_type="image/png")


@router.get("/dataset/info", response_model=DatasetInfo, tags=["dataset"])
def dataset_info(request: Request):
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    model = request.app.state.model
    if not model.loaded:
        return {"manifest": manifest}
    m = model.metadata
    return {"manifest": manifest, "trained_on": m.get("dataset"), "feature_schema": m["features"],
            "label_distribution": m.get("label_distribution"),
            "model": {"model_version": m["model_version"], "model_type": m.get("model_type"),
                      "trained_at": m.get("trained_at"), "evaluation": m.get("evaluation"),
                      "is_synthetic": m.get("is_synthetic", False), "environment": m.get("environment")}}
