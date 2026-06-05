"""
app/main.py
────────────
FastAPI application factory.

This is the entry point for both uvicorn (development) and
gunicorn+uvicorn workers (production).

Run locally:
    uvicorn app.main:app --reload --port 8000

Production (via gunicorn):
    gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker --bind 0.0.0.0:8000
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.exceptions import register_exception_handlers
from app.database.connection import engine
from app.middlewares.cors import setup_cors


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Application lifespan handler.

    Startup: Connection pool is implicitly initialized by SQLAlchemy
             on first query. No explicit warmup needed for asyncpg.

    Shutdown: Gracefully dispose the connection pool — waits for all
              active connections to complete before closing.
              Critical for zero-downtime deployments.
    """
    # ── Startup ────────────────────────────────────────────────────────────
    yield
    # ── Shutdown ───────────────────────────────────────────────────────────
    await engine.dispose()


def create_app() -> FastAPI:
    """
    Application factory pattern.
    Keeps app creation testable — tests can call create_app() with
    different settings or overridden dependencies.
    """
    app = FastAPI(
        title="S2T Fitness Attendance API",
        description=(
            "Gym Attendance & Membership Management System for "
            "S2T Fitness Studio, Trichy, Tamil Nadu."
        ),
        version="1.0.0",
        # Disable docs in production for security
        docs_url="/docs" if settings.ENV != "production" else None,
        redoc_url="/redoc" if settings.ENV != "production" else None,
        openapi_url="/openapi.json" if settings.ENV != "production" else None,
        lifespan=lifespan,
    )

    # ── Middleware (order matters — outermost runs first on request) ────────
    setup_cors(app)

    # ── Exception Handlers ─────────────────────────────────────────────────
    register_exception_handlers(app)

    # ── Routers ────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix="/api/v1")

    # ── Health Check ───────────────────────────────────────────────────────
    @app.get("/health", tags=["Health"], include_in_schema=False)
    async def health_check() -> JSONResponse:
        return JSONResponse(
            content={"status": "ok", "gym": settings.GYM_NAME},
            status_code=200,
        )

    return app


# Module-level app instance for uvicorn/gunicorn
app = create_app()
