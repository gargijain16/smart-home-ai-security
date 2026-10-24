"""Pydantic response/request contracts. The frontend mirrors these in src/types/api.ts."""
from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field

Severity = Literal["info", "low", "medium", "high"]
EventStatus = Literal["open", "acknowledged", "resolved"]


class ErrorBody(BaseModel):
    code: str
    message: str
    details: Optional[Any] = None


class ErrorResponse(BaseModel):
    error: ErrorBody


class HealthResponse(BaseModel):
    status: Literal["ok"]
    version: str
    time: str
    mode: Literal["ml", "demo"]
    model_loaded: bool
    simulation_state: Literal["stopped", "running", "paused"]


class Device(BaseModel):
    id: str
    name: str
    type: str
    room: str
    protocol: str
    status: Literal["normal", "alert", "idle"]
    last_activity: Optional[str] = None
    open_alerts: int
    total_events: int
    is_simulated: bool = True


class Event(BaseModel):
    id: int
    ts: str
    device_id: str
    device_name: str
    event_type: str
    protocol: str
    topic: str
    source_ip: str
    metrics: Dict[str, Any]
    label: str
    severity: Severity
    status: EventStatus
    detection_source: str
    is_simulated: bool
    run_id: str


class EventPage(BaseModel):
    total: int
    limit: int
    offset: int
    items: List[Event]


class StatusPatch(BaseModel):
    status: EventStatus


class SimStart(BaseModel):
    seed: Optional[int] = None


class SimStep(BaseModel):
    ticks: int = Field(1, ge=1, le=200)


class SimulationState(BaseModel):
    state: Literal["stopped", "running", "paused"]
    run_id: Optional[str] = None
    seed: int
    ticks: int
    events_generated: int
    tick_seconds: float
    rules: Dict[str, Any]
    notice: str


class Overview(BaseModel):
    devices_monitored: int
    total_events: int
    suspicious_events: int
    high_priority_open: int
    threat_distribution: Dict[str, int]
    timeline: List[Dict[str, Any]]
    device_health: List[Device]
    recent_events: List[Event]
    simulation: SimulationState
    model: Dict[str, Any]
    data_origin: str


class ModelStatus(BaseModel):
    available: bool
    mode: Literal["ml", "demo"]
    reason: Optional[str] = None
    model_version: Optional[str] = None
    model_type: Optional[str] = None
    is_synthetic: bool = False
    is_benchmark: bool = False
    trained_at: Optional[str] = None
    classes: List[str] = []
    n_features: int = 0
    dataset_name: Optional[str] = None
    sklearn_version_trained: Optional[str] = None
    sklearn_version_runtime: str
    version_mismatch: bool = False
    how_to_enable: List[str] = []


class MetricsResponse(BaseModel):
    available: bool
    reason: Optional[str] = None
    metrics: Optional[Dict[str, Any]] = None
    classification_report: Optional[Dict[str, Any]] = None
    images: List[str] = []
    limitations: List[str] = []
    is_synthetic: bool = False


class DatasetInfo(BaseModel):
    manifest: Dict[str, Any]
    trained_on: Optional[Dict[str, Any]] = None
    feature_schema: List[Dict[str, Any]] = []
    label_distribution: Optional[Dict[str, Any]] = None
    model: Optional[Dict[str, Any]] = None


class PredictRecords(BaseModel):
    samples: List[Dict[str, Any]] = Field(min_length=1, max_length=5000)


class Evidence(BaseModel):
    feature: str
    value: Optional[float] = None
    global_importance: float


class RowPrediction(BaseModel):
    row: int
    predicted_class: str
    is_attack: bool
    probabilities: Optional[Dict[str, float]] = None
    evidence: List[Evidence] = []


class PredictResponse(BaseModel):
    mode: Literal["ml"]
    model_version: str
    predicted_at: str
    is_synthetic_model: bool
    validation: Dict[str, Any]
    summary: Dict[str, int]
    probability_note: Optional[str] = None
    explanation_type: str
    predictions: List[RowPrediction]
