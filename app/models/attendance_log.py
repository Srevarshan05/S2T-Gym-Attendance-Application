"""
app/models/attendance_log.py
─────────────────────────────
SQLAlchemy ORM model for the `attendance_logs` table.

Design decisions:
  - `attendance_date` is a DATE (not TIMESTAMP). Using a date prevents
    timezone ambiguity — a member who checks in at 23:50 IST (18:20 UTC)
    should log against the Indian calendar date, not the UTC date.
    The service layer always derives the date using IST (Asia/Kolkata).

  - `session` is an ENUM('FN', 'AN') — Forenoon / Afternoon.
    A member can check in twice per day (once each session), but not
    twice in the same session. This is enforced by the DB-level
    UniqueConstraint on (user_id, attendance_date, session).

  - The UniqueConstraint is the definitive safety net. The service
    performs an application-level duplicate check first to give a cleaner
    HTTP 409 error before hitting the DB constraint.
"""

from __future__ import annotations

import uuid
from datetime import date
from typing import TYPE_CHECKING

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class AttendanceLog(Base, TimestampMixin):
    __tablename__ = "attendance_logs"

    # ── DB-level duplicate prevention ──────────────────────────────────────
    # One row per (member, date, session). FN and AN are separate rows.
    __table_args__ = (
        sa.UniqueConstraint(
            "user_id",
            "attendance_date",
            "session",
            name="uq_attendance_user_date_session",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa.text("gen_random_uuid()"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Cascade delete: removing a user also removes all their attendance records.",
    )

    attendance_date: Mapped[date] = mapped_column(
        sa.Date,
        nullable=False,
        index=True,
        doc=(
            "Calendar date of attendance in IST (Asia/Kolkata). "
            "Never derived from a UTC timestamp — always set explicitly by the service."
        ),
    )

    session: Mapped[str] = mapped_column(
        sa.Enum("FN", "AN", name="session_type"),
        nullable=False,
        doc="FN = Forenoon (morning session). AN = Afternoon/Evening session.",
    )

    # ── Relationships ──────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(
        "User",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<AttendanceLog user_id={self.user_id} "
            f"date={self.attendance_date} session={self.session!r}>"
        )
