"""Devices, events, overview and simulation controls."""
from __future__ import annotations

from collections import OrderedDict
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, Request

from ..schemas import Device, Event, EventPage, Overview, SimStart, SimStep, SimulationState, StatusPatch
from ..services.simulator import DEVICES

router = APIRouter(prefix="/api")
BUCKET_SECONDS = 15


def _devices(request: Request) -> List[Dict[str, Any]]:
    stats = request.app.state.store.device_stats()
    out = []
    for d in DEVICES:
        s = stats.get(d["id"])
        status = "idle" if not s else ("alert" if s["open_alerts"] else "normal")
        out.append({**d, "status": status, "last_activity": s["last_activity"] if s else None,
                    "open_alerts": s["open_alerts"] if s else 0, "total_events": s["total_events"] if s else 0,
                    "is_simulated": True})
    return out


def _timeline(rows) -> List[Dict[str, Any]]:
    buckets: "OrderedDict[int, Dict[str, Any]]" = OrderedDict()
    for ts, label in rows:
        epoch = int(datetime.fromisoformat(ts).timestamp()) // BUCKET_SECONDS * BUCKET_SECONDS
        b = buckets.setdefault(epoch, {"t": datetime.fromtimestamp(epoch).astimezone().strftime("%H:%M:%S"),
                                       "normal": 0, "suspicious": 0})
        b["normal" if label == "normal" else "suspicious"] += 1
    return list(buckets.values())[-24:]


@router.get("/devices", response_model=List[Device], tags=["devices"])
def list_devices(request: Request):
    return _devices(request)


@router.get("/devices/{device_id}/events", response_model=EventPage, tags=["devices"])
def device_events(device_id: str, request: Request, limit: int = Query(50, ge=1, le=200), offset: int = Query(0, ge=0)):
    if device_id not in {d["id"] for d in DEVICES}:
        raise HTTPException(status_code=404, detail="Unknown device.")
    total, items = request.app.state.store.query(device_id=device_id, limit=limit, offset=offset)
    return {"total": total, "limit": limit, "offset": offset, "items": items}


@router.get("/events", response_model=EventPage, tags=["events"])
def list_events(request: Request, q: Optional[str] = None, device_id: Optional[str] = None,
                event_type: Optional[str] = None, label: Optional[str] = None, severity: Optional[str] = None,
                status: Optional[str] = None, since: Optional[str] = None, until: Optional[str] = None,
                limit: int = Query(25, ge=1, le=200), offset: int = Query(0, ge=0)):
    total, items = request.app.state.store.query(q=q, device_id=device_id, event_type=event_type, label=label,
                                                 severity=severity, status=status, since=since, until=until,
                                                 limit=limit, offset=offset)
    return {"total": total, "limit": limit, "offset": offset, "items": items}


@router.get("/events/{event_id}", response_model=Event, tags=["events"])
def get_event(event_id: int, request: Request):
    ev = request.app.state.store.get(event_id)
    if ev is None:
        raise HTTPException(status_code=404, detail="Event not found.")
    return ev


@router.patch("/events/{event_id}/status", response_model=Event, tags=["events"])
def patch_status(event_id: int, body: StatusPatch, request: Request):
    ev = request.app.state.store.set_status(event_id, body.status)
    if ev is None:
        raise HTTPException(status_code=404, detail="Event not found.")
    return ev


@router.get("/overview", response_model=Overview, tags=["events"])
def overview(request: Request):
    st = request.app.state
    c = st.store.counts()
    _, recent = st.store.query(limit=8)
    status = st.model.status()
    model: Dict[str, Any] = {"available": status["available"], "mode": status["mode"],
                             "model_version": status.get("model_version"), "is_synthetic": status.get("is_synthetic", False),
                             "headline": None}
    if status["available"]:
        mt = st.model.metrics().get("metrics")
        if mt and "test" in mt:
            model["headline"] = {k: mt["test"].get(k) for k in ("accuracy", "macro_precision", "macro_recall", "macro_f1")}
            model["selected_model"] = mt.get("selected_model")
    return {"devices_monitored": len(DEVICES), "total_events": c["total"], "suspicious_events": c["suspicious"],
            "high_priority_open": c["high_open"], "threat_distribution": c["distribution"],
            "timeline": _timeline(st.store.timeline_rows()), "device_health": _devices(request),
            "recent_events": recent, "simulation": st.simulation.snapshot(), "model": model,
            "data_origin": "simulated"}


@router.get("/simulation", response_model=SimulationState, tags=["simulation"])
def sim_state(request: Request):
    return request.app.state.simulation.snapshot()


@router.post("/simulation/start", response_model=SimulationState, tags=["simulation"])
def sim_start(request: Request, body: Optional[SimStart] = None):
    return request.app.state.simulation.start(body.seed if body else None)


@router.post("/simulation/pause", response_model=SimulationState, tags=["simulation"])
def sim_pause(request: Request):
    return request.app.state.simulation.pause()


@router.post("/simulation/resume", response_model=SimulationState, tags=["simulation"])
def sim_resume(request: Request):
    return request.app.state.simulation.resume()


@router.post("/simulation/stop", response_model=SimulationState, tags=["simulation"])
def sim_stop(request: Request):
    """Alias of pause: stops event generation but keeps history."""
    return request.app.state.simulation.pause()


@router.post("/simulation/reset", response_model=SimulationState, tags=["simulation"])
def sim_reset(request: Request):
    return request.app.state.simulation.reset()


@router.post("/simulation/step", response_model=SimulationState, tags=["simulation"])
def sim_step(request: Request, body: Optional[SimStep] = None):
    sim = request.app.state.simulation
    sim.step(body.ticks if body else 1)
    return sim.snapshot()
