"""
app/database/connection.py
───────────────────────────
Async SQLAlchemy engine and session factory for Supabase PostgreSQL.

This is the ONLY file that reads DATABASE_URL or creates the engine.
Everything else receives an AsyncSession via FastAPI dependency injection.

Key async-specific settings explained:
  expire_on_commit=False  — After session.commit(), SQLAlchemy normally
                            expires all loaded attributes to force a fresh
                            DB load on next access. In async context this
                            would trigger implicit lazy loads that crash.
                            Setting False keeps attributes accessible
                            without re-querying after commit.

  pool_pre_ping=True      — Before using a connection from the pool,
                            execute a lightweight "SELECT 1" ping.
                            Recycles stale connections (e.g., after DB
                            server restart) automatically.

  pool_size / max_overflow — Supabase free tier has a 60-connection limit.
                             10 + 5 = 15 max connections per backend
                             instance leaves headroom for multiple workers.
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# ── Async Engine ───────────────────────────────────────────────────────────
# Created once at module load time (not per-request).
engine = create_async_engine(
    settings.DATABASE_URL,
    pool_size=10,
    max_overflow=5,
    pool_pre_ping=False,         # Disabled to save 150-200ms ping latency per request
    pool_recycle=1800,           # Recycle connections older than 30 minutes
    echo=settings.ENV == "development",  # Log SQL in dev, never in production
    connect_args={"statement_cache_size": 0},
)

# ── Session Factory ────────────────────────────────────────────────────────
# async_sessionmaker is the async equivalent of sessionmaker.
# get_db() in dependencies.py uses this to create one session per request.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,     # Critical — see module docstring
    autoflush=False,            # Manual flush gives us control over when
    autocommit=False,           # DB writes happen within a transaction
)
