"""
app/models/revenue_log.py
──────────────────────────
SQLAlchemy ORM model for the `revenue_logs` table.

An immutable audit ledger of approved payments.
One row is created per payment approval — never updated, never deleted.

Design:
  - `month_bucket` (e.g., '2026-06') is copied from the PaymentRequest at
    the time of approval. This makes monthly aggregation a simple GROUP BY
    with an index scan instead of expensive EXTRACT(YEAR/MONTH FROM date).
  - `amount` is again snapshotted — even if the plan price changes later,
    each revenue entry permanently reflects what was actually collected.
  - The `payment_request_id` FK provides a full audit trail back to the
    original submission, reviewer, and rejection reason if needed.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.payment_request import PaymentRequest
    from app.models.user import User
    from app.models.gym_plan import GymPlan


class RevenueLog(Base, TimestampMixin):
    __tablename__ = "revenue_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa.text("gen_random_uuid()"),
    )

    # ── Traceability ───────────────────────────────────────────────────────
    payment_request_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("payment_requests.id", ondelete="RESTRICT"),
        unique=True,        # One log entry per approved payment (enforced at DB level)
        nullable=False,
        doc="Links back to the payment_request that generated this revenue entry.",
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="The member who paid. RESTRICT prevents user deletion with revenue history.",
    )

    plan_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("gym_plans.id", ondelete="RESTRICT"),
        nullable=False,
    )

    # ── Revenue data ───────────────────────────────────────────────────────
    amount: Mapped[Decimal] = mapped_column(
        sa.Numeric(10, 2),
        nullable=False,
        doc="Amount collected in INR. Snapshotted at approval time.",
    )

    month_bucket: Mapped[str] = mapped_column(
        sa.String(7),
        nullable=False,
        index=True,
        doc=(
            "'YYYY-MM' string for fast monthly aggregation. "
            "Example: '2026-06'. Copied from payment_request at approval."
        ),
    )

    # ── Relationships ──────────────────────────────────────────────────────
    payment_request: Mapped["PaymentRequest"] = relationship(
        "PaymentRequest",
        lazy="noload",
    )

    member: Mapped["User"] = relationship(
        "User",
        lazy="noload",
    )

    plan: Mapped["GymPlan"] = relationship(
        "GymPlan",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<RevenueLog id={self.id} amount={self.amount} "
            f"bucket={self.month_bucket!r} user_id={self.user_id}>"
        )
