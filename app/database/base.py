"""
app/database/base.py
─────────────────────
SQLAlchemy 2.0 Declarative Base and shared TimestampMixin.

All ORM model classes inherit from Base (required by SQLAlchemy metadata).
All 7 tables also inherit TimestampMixin to get created_at / updated_at
without repeating the column definitions in every model file.
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """
    SQLAlchemy 2.0-style declarative base.
    All ORM models must inherit this for Alembic autogenerate to discover them.
    """
    pass


class TimestampMixin:
    """
    Adds created_at and updated_at to any model that inherits it.

    - created_at: set once on INSERT via server default (DB clock, not Python clock).
    - updated_at: updated on every UPDATE via onupdate.
      NOTE: SQLAlchemy's onupdate fires only when the ORM issues an UPDATE statement.
      The PostgreSQL trigger fn_set_updated_at() provides a DB-level fallback.
    """

    created_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        nullable=False,
        doc="UTC timestamp of record creation.",
    )
    updated_at: Mapped[datetime] = mapped_column(
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        doc="UTC timestamp of last update.",
    )
