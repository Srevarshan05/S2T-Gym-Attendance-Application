"""
app/models/member_profile.py
──────────────────────────────
SQLAlchemy ORM model for the `members_profile` table.

One-to-One with `users`. Stores personal attributes and membership state.
Only member-role users have a profile row; admin users do not.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.gym_plan import GymPlan


class MemberProfile(Base, TimestampMixin):
    __tablename__ = "members_profile"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa.text("gen_random_uuid()"),
    )

    # ── Foreign Keys ───────────────────────────────────────────────────────
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,       # Enforces 1:1 relationship at DB level
        nullable=False,
        index=True,
    )

    plan_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("gym_plans.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
        doc="Cannot delete a gym plan that has member profiles referencing it.",
    )

    # ── Personal Details (from registration form) ──────────────────────────
    full_name: Mapped[str] = mapped_column(sa.String(255), nullable=False)

    age: Mapped[int] = mapped_column(
        sa.SmallInteger,
        nullable=False,
        doc="Age must be 10–100. Enforced by DB CHECK constraint in migration.",
    )

    gender: Mapped[str] = mapped_column(
        sa.Enum("Male", "Female", "Other", name="gender_type"),
        nullable=False,
    )

    phone: Mapped[str] = mapped_column(
        sa.String(15),
        nullable=False,
        doc="10-digit phone number. Validated by Pydantic in RegisterRequest.",
    )

    address: Mapped[str] = mapped_column(sa.Text, nullable=False)

    # ── Membership Lifecycle ───────────────────────────────────────────────
    membership_status: Mapped[str] = mapped_column(
        sa.Enum("ACTIVE", "EXPIRED", "PENDING", "SUSPENDED", name="membership_status"),
        nullable=False,
        default="PENDING",
        server_default="PENDING",
        index=True,
        doc=(
            "PENDING   — Just registered; payment not yet approved.\n"
            "ACTIVE    — Admin has approved payment; can mark attendance.\n"
            "EXPIRED   — End date has passed; cannot mark attendance.\n"
            "SUSPENDED — Manually suspended by admin."
        ),
    )

    membership_start_date: Mapped[Optional[date]] = mapped_column(
        sa.Date,
        nullable=True,
        doc="Set when admin approves payment.",
    )

    membership_end_date: Mapped[Optional[date]] = mapped_column(
        sa.Date,
        nullable=True,
        index=True,
        doc="Set when admin approves payment. NULL until first approval.",
    )

    # ── Relationships ──────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(
        "User",
        back_populates="profile",
        lazy="noload",
    )

    plan: Mapped["GymPlan"] = relationship(
        "GymPlan",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<MemberProfile user_id={self.user_id} "
            f"name={self.full_name!r} status={self.membership_status!r}>"
        )
