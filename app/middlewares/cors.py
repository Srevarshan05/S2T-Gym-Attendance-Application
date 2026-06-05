"""
app/middlewares/cors.py
────────────────────────
CORS middleware configuration.

Only the whitelisted frontend origins can make cross-origin requests.
This is enforced at the middleware level — before any route handler runs.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings


def setup_cors(app: FastAPI) -> None:
    """
    Register CORSMiddleware on the FastAPI app.
    Called once in main.py during app factory setup.

    allow_credentials=True is required for the browser to send
    cookies and Authorization headers in cross-origin requests.
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Authorization", "Content-Type", "Accept"],
        expose_headers=["X-Request-ID"],
    )
