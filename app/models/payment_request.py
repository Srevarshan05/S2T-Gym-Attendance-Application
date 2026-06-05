"""
app/models/payment_request.py
──────────────────────────────
SQLAlchemy ORM model for the `payment_requests` table.

Lifecycle: PENDING_APPROVAL → APPROVED | REJECTED

Design notes:
  - A partial unique index (status = 'PENDING_APPROVAL') enforced in the DB
    migration prevents a member from submitting two concurrent pending requests.
  - `amount` is snapshotted at submission time from gym_plans.price.
    This preserves historical accuracy even if the plan price later changes.
  - `month_bucket` (e.g., '2026-06') is set at APPROVAL time so revenue_logs
    can group by calendar month without expensive date arithmetic at query time.
  - `reviewed_by` is a self-referential FK back to users — the admin who approved
    or rejected the request. NULL until a decision is made.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.gym_plan import GymPlan


class PaymentRequest(Base, TimestampMixin):
    __tablename__ = "payment_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa.text("gen_random_uuid()"),
    )

    # ── Who submitted ──────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # ── What they're paying for ────────────────────────────────────────────
    plan_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("gym_plans.id", ondelete="RESTRICT"),
        nullable=False,
    )

    amount: Mapped[Decimal] = mapped_column(
        sa.Numeric(10, 2),
        nullable=False,
        doc="Plan price snapshotted at submission time. Preserved for audit history.",
    )

    # ── Approval lifecycle ─────────────────────────────────────────────────
    status: Mapped[str] = mapped_column(
        sa.Enum(
            "PENDING_APPROVAL",
            "APPROVED",
            "REJECTED",
            name="payment_status",
        ),
        nullable=False,
        default="PENDING_APPROVAL",
        server_default="PENDING_APPROVAL",
        index=True,
    )

    rejection_reason: Mapped[Optional[str]] = mapped_column(
        sa.Text,
        nullable=True,
        doc="Admin's reason for rejection. NULL for approved requests.",
    )

    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        doc="UUID of the admin who made the approval/rejection decision.",
    )

    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=True,
        doc="UTC timestamp when the admin reviewed this request.",
    )

    month_bucket: Mapped[Optional[str]] = mapped_column(
        sa.String(7),
        nullable=True,
        index=True,
        doc=(
            "Calendar month of APPROVAL in 'YYYY-MM' format (e.g., '2026-06'). "
            "NULL for pending/rejected requests. Set at approval time. "
            "Used for monthly revenue aggregation without date arithmetic."
        ),
    )

    # ── Relationships ──────────────────────────────────────────────────────
    member: Mapped["User"] = relationship(
        "User",
        foreign_keys=[user_id],
        lazy="noload",
    )

    reviewer: Mapped[Optional["User"]] = relationship(
        "User",
        foreign_keys=[reviewed_by],
        lazy="noload",
    )

    plan: Mapped["GymPlan"] = relationship(
        "GymPlan",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<PaymentRequest id={self.id} user_id={self.user_id} "
            f"status={self.status!r} amount={self.amount}>"
        )
