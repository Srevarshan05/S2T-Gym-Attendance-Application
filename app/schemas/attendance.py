"""
app/schemas/attendance.py
──────────────────────────
Pydantic v2 schemas for the Attendance module.

CheckinRequest    — Member's session selection (FN or AN) after QR scan.
CheckinResponse   — Confirmation with streak and monthly stats.
CalendarDay       — Single day's attendance status (for calendar heatmap).
CalendarResponse  — Full month calendar with aggregates.
"""

from __future__ import annotations

from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ── Enums ──────────────────────────────────────────────────────────────────

class SessionType(str, Enum):
    """
    Strict two-value enum for gym session.
    Using str Enum so FastAPI serializes it as "FN"/"AN" strings in JSON,
    not as {"value": "FN", ...} — keeping the API response clean.
    """
    FN = "FN"   # Forenoon (morning session)
    AN = "AN"   # Afternoon / Evening session


# ── Check-in ───────────────────────────────────────────────────────────────

class CheckinRequest(BaseModel):
    """
    Payload sent when a member scans the QR code and selects their session.

    The QR code itself carries no data — it just opens the check-in page.
    The session selection (FN/AN) is the only input from the member.
    FastAPI validates that `session` is exactly "FN" or "AN" before the
    request reaches the service layer — any other value returns HTTP 422.
    """

    session: SessionType = Field(
        ...,
        description="Gym session: 'FN' (Forenoon/Morning) or 'AN' (Afternoon/Evening).",
        examples=["FN"],
    )


class CheckinResponse(BaseModel):
    """
    Confirmation returned after a successful check-in.

    Includes real-time stats so the member's dashboard can update
    without an extra API call after check-in:
      - streak        → consecutive calendar days attended (≥1 session)
      - total_this_month → total sessions logged this calendar month
    """

    # Identity
    member_id: str = Field(examples=["S2T101"])
    full_name: str = Field(examples=["Rahul Sharma"])

    # What was logged
    attendance_date: date = Field(description="IST calendar date of this check-in.")
    session: SessionType
    message: str = Field(
        examples=["FN check-in recorded successfully!"],
        description="Human-readable confirmation message.",
    )

    # Live stats
    streak: int = Field(
        description="Consecutive days attended (including today). Resets if a day is missed.",
        examples=[7],
    )
    total_this_month: int = Field(
        description="Total sessions (FN + AN combined) logged this calendar month.",
        examples=[14],
    )
    can_checkin_an: bool = Field(
        description=(
            "True if the member has NOT yet checked in for AN today. "
            "Lets the UI decide whether to show the 'Check in AN' button."
        ),
    )


# ── Calendar ───────────────────────────────────────────────────────────────

class CalendarDay(BaseModel):
    """
    Attendance state for a single calendar date.
    Designed to drive a heatmap/dot-calendar UI directly from the API response.
    """

    attendance_date: date
    has_fn: bool = Field(description="True if Forenoon session was attended.")
    has_an: bool = Field(description="True if Afternoon/Evening session was attended.")
    sessions: list[str] = Field(
        description="List of sessions attended. e.g. ['FN', 'AN'] or ['FN'] or [].",
        examples=[["FN", "AN"]],
    )
    is_full_day: bool = Field(
        description="True when both FN and AN were attended — full day at gym.",
        default=False,
    )


class CalendarResponse(BaseModel):
    """
    Full monthly attendance calendar for a member.
    Only days with at least one session appear in `days` — absent days are omitted.
    The frontend renders the full month grid and uses the `days` list to mark
    attended dates.
    """

    year: int
    month: int
    member_id: str = Field(examples=["S2T101"])

    # Only attended days (absent days omitted for bandwidth efficiency)
    days: list[CalendarDay] = Field(
        description=(
            "Attendance records for this month, one entry per attended date. "
            "Sorted ascending by date. Dates with no attendance are NOT included."
        )
    )

    # Monthly aggregates
    total_days_attended: int = Field(
        description="Count of distinct calendar days attended this month."
    )
    total_sessions: int = Field(
        description="Total individual sessions (FN + AN) logged this month."
    )
    streak: int = Field(
        description=(
            "Current consecutive-day streak as of today. "
            "Calculated from today backwards — not from start of month."
        )
    )
