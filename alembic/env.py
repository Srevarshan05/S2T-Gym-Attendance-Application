"""
alembic/env.py
───────────────
Async-compatible Alembic environment.

This file tells Alembic:
  1. Which database to connect to (reads DATABASE_URL from settings).
  2. Which metadata to compare against (Base.metadata from all models).
  3. How to run migrations asynchronously (using asyncio.run).
"""

from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import settings
from app.database.base import Base

# Import all models so Alembic autogenerate detects them
import app.models  # noqa: F401

# Alembic Config object (access to alembic.ini values)
config = context.config

# Override sqlalchemy.url from environment — never hardcode credentials in alembic.ini
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL.replace("%", "%%"))

# Set up logging from alembic.ini [loggers] section
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# The metadata Alembic uses for autogenerate comparison
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode (no live DB connection).
    Useful for generating SQL scripts to review before applying.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """
    Run migrations against the live Supabase database using asyncpg.
    NullPool is used here — Alembic runs once then exits, no pooling needed.
    """
    connectable = create_async_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
        connect_args={"statement_cache_size": 0},
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Entry point for online migration mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
