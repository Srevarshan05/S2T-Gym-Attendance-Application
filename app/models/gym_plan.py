"""
app/models/gym_plan.py
───────────────────────
SQLAlchemy ORM model for the `gym_plans` table.

Seed data (Monthly / Annually / Special Personal Training) is inserted
via the Alembic initial migration, not here. Prices are admin-configurable.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base, TimestampMixin


class GymPlan(Base, TimestampMixin):
    __tablename__ = "gym_plans"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa.text("gen_random_uuid()"),
    )

    name: Mapped[str] = mapped_column(
        sa.String(100),
        unique=True,
        nullable=False,
        doc="Plan display name. E.g., 'Monthly', 'Annually', 'Special Personal Training'.",
    )

    duration_days: Mapped[Optional[int]] = mapped_column(
        sa.SmallInteger,
        nullable=True,
        doc=(
            "Number of days this plan extends the membership. "
            "NULL for 'Special Personal Training' — admin manually sets end date."
        ),
    )

    price: Mapped[Decimal] = mapped_column(
        sa.Numeric(10, 2),
        nullable=False,
        doc="Plan price in INR. Exact decimal arithmetic — no float rounding errors.",
    )

    is_active: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=True,
        server_default=sa.true(),
        doc="Inactive plans cannot be selected during registration.",
    )

    description: Mapped[Optional[str]] = mapped_column(
        sa.Text,
        nullable=True,
    )

    def __repr__(self) -> str:
        return f"<GymPlan name={self.name!r} price={self.price} days={self.duration_days}>"
