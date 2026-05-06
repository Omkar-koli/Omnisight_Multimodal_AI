from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from omnisight.api.logging_middleware import RequestLoggingMiddleware
from omnisight.api.routes import router
from omnisight.jobs.scheduler_runtime import start_scheduler, stop_scheduler
from omnisight.logging_config import configure_logging


configure_logging()


def get_cors_origins() -> list[str]:
    raw = os.getenv(
        "CORS_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).strip()

    origins = [x.strip() for x in raw.split(",") if x.strip()]
    return origins or ["http://localhost:3000", "http://127.0.0.1:3000"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.started = False
    app.state.ready = False
    app.state.scheduler_started = False
    app.state.startup_error = None

    try:
        start_scheduler()
        app.state.scheduler_started = True
    except Exception as e:
        # Keep API alive even if scheduler fails
        app.state.startup_error = f"scheduler_start_failed: {e}"

    app.state.started = True
    app.state.ready = True

    yield

    try:
        if app.state.scheduler_started:
            stop_scheduler()
    except Exception:
        pass


app = FastAPI(
    title=os.getenv("APP_NAME", "OmniSight API"),
    version=os.getenv("APP_VERSION", "0.1.0"),
    description="Multimodal decision API for e-commerce restocking",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)


@app.get("/")
def root():
    return {
        "name": os.getenv("APP_NAME", "OmniSight API"),
        "status": "ok",
        "version": os.getenv("APP_VERSION", "0.1.0"),
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "started": getattr(app.state, "started", False),
        "scheduler_started": getattr(app.state, "scheduler_started", False),
    }


@app.get("/ready")
def ready():
    is_ready = getattr(app.state, "ready", False)
    return {
        "status": "ready" if is_ready else "not_ready",
        "ready": is_ready,
        "startup_error": getattr(app.state, "startup_error", None),
    }


app.include_router(router)