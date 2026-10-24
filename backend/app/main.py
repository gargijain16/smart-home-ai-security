"""FastAPI application factory. Run: uvicorn app.main:app --port 8000"""
from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager, suppress
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config import APP_VERSION, Settings, load_settings
from .routes import events, predict, system
from .services.ml_service import ModelService, ModelUnavailable, SchemaError
from .services.simulation import SimulationService
from .services.store import EventStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("ids.api")


def _err(status: int, code: str, message: str, details=None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"error": {"code": code, "message": message, "details": details}})


async def _runner(app: FastAPI) -> None:
    while True:
        await asyncio.sleep(app.state.settings.sim_tick_seconds)
        if app.state.simulation.state == "running":
            try:
                app.state.simulation.step(1)
            except Exception:  # noqa: BLE001
                log.exception("simulation tick failed")


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    settings = settings or load_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        task = asyncio.create_task(_runner(app))
        yield
        task.cancel()
        with suppress(asyncio.CancelledError):
            await task
        app.state.store.close()

    app = FastAPI(title="Smart Home IDS API", version=APP_VERSION, lifespan=lifespan,
                  description="Simulated smart-home events plus real ML inference over uploaded MQTT feature CSVs.")
    app.state.settings = settings
    app.state.store = EventStore(settings.db_path)
    app.state.model = ModelService(settings.models_dir, settings.reports_dir, settings.max_upload_rows)
    app.state.simulation = SimulationService(app.state.store, settings.sim_seed, settings.sim_tick_seconds)

    app.add_middleware(CORSMiddleware, allow_origins=list(settings.cors_origins), allow_credentials=False,
                       allow_methods=["GET", "POST", "PATCH", "OPTIONS"], allow_headers=["*"])

    @app.exception_handler(SchemaError)
    async def _schema(_: Request, exc: SchemaError):
        return _err(422, "schema_mismatch", str(exc), exc.details)

    @app.exception_handler(ModelUnavailable)
    async def _unavailable(_: Request, exc: ModelUnavailable):
        return _err(503, "model_unavailable", str(exc) or "No trained model is installed.",
                    {"how_to_enable": "See GET /api/model/status"})

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        return _err(422, "invalid_request", "Request validation failed.", exc.errors())

    @app.exception_handler(HTTPException)
    async def _http(_: Request, exc: HTTPException):
        return _err(exc.status_code, "http_error", str(exc.detail))

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):
        log.exception("unhandled error")
        return _err(500, "internal_error", "Unexpected server error.")

    for r in (system.router, events.router, predict.router):
        app.include_router(r)
    return app


app = create_app()
