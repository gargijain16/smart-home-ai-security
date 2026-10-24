"""Runtime configuration, read from environment variables (see .env.example)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP_VERSION = "1.0.0"


@dataclass(frozen=True)
class Settings:
    models_dir: Path
    reports_dir: Path
    db_path: str
    cors_origins: tuple
    sim_seed: int
    sim_tick_seconds: float
    max_upload_bytes: int
    max_upload_rows: int


def load_settings() -> Settings:
    env = os.environ.get
    origins = [o.strip() for o in env("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",") if o.strip()]
    if "*" in origins:
        raise ValueError("CORS_ORIGINS must list explicit origins; '*' is not allowed.")
    return Settings(
        models_dir=Path(env("MODELS_DIR", str(ROOT / "models"))),
        reports_dir=Path(env("REPORTS_DIR", str(ROOT / "reports"))),
        db_path=env("DB_PATH", str(ROOT / "data" / "processed" / "events.db")),
        cors_origins=tuple(origins),
        sim_seed=int(env("SIM_SEED", "42")),
        sim_tick_seconds=float(env("SIM_TICK_SECONDS", "1.5")),
        max_upload_bytes=int(env("MAX_UPLOAD_MB", "25")) * 1024 * 1024,
        max_upload_rows=int(env("MAX_UPLOAD_ROWS", "50000")),
    )
