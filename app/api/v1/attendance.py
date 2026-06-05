"""
app/api/v1/attendance.py
─────────────────────────
FastAPI router for the QR Attendance module.

Endpoints:
  POST /attendance/checkin            Member only — log FN or AN session
  GET  /attendance/calendar           Member only — monthly calendar view

Security:
  Both endpoints require a valid JWT access token (member role).
  The member's user_id and member_id are read directly from the JWT
  payload (via get_current_user) — no URL parameter for member identity,
  so a member cannot spoof another member's check-in.

QR Flow context:
  The physical QR code at the gym entrance is a static image that links to
  the PWA's check-in page. When scanned, the app opens the check-in UI
  where the member selects FN or AN. The JWT in their browser session
  provides identity — no QR payload or token is needed in the QR itself.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.attendance import (
    CalendarResponse,
    CheckinRequest,
    CheckinResponse,
)
from app.services import attendance_service

router = APIRouter(prefix="/attendance", tags=["Attendance"])


# ── POST /attendance/checkin ───────────────────────────────────────────────

@router.post(
    "/checkin",
    response_model=CheckinResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Log a gym session check-in (Member only)",
    description=(
        "Record a member's attendance for today's FN (Forenoon/Morning) "
        "or AN (Afternoon/Evening) session. "
        "A member can check in at most once per session per calendar day "
        "(max 2 check-ins per day: one FN + one AN). "
        "\n\n"
        "**Errors returned:**\n"
        "- 403 `MEMBERSHIP_EXPIRED` — membership end date has passed.\n"
        "- 403 `MEMBERSHIP_PENDING` — payment not yet approved by admin.\n"
        "- 409 `ALREADY_CHECKED_IN` — this session already logged today."
    ),
)
async def checkin(
    payload: CheckinRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> CheckinResponse:
    """
    Identity is taken from the JWT (current_user), NOT from the request body.
    This makes it impossible for a member to check in on behalf of another.
    """
    return await attendance_service.process_checkin(
        db,
        user_id=current_user.id,
        member_id=current_user.member_id or "",
        session=payload.session,
    )


# ── GET /attendance/calendar ───────────────────────────────────────────────

@router.get(
    "/calendar",
    response_model=CalendarResponse,
    status_code=status.HTTP_200_OK,
    summary="Get monthly attendance calendar (Member only)",
    description=(
        "Returns the authenticated member's attendance calendar for the "
        "specified month and year. "
        "Includes per-day FN/AN status for the heatmap UI and aggregate "
        "stats (total days, total sessions, current streak). "
        "\n\n"
        "**Example:** `GET /attendance/calendar?year=2026&month=6`\n\n"
        "Only attended dates appear in the `days` array — absent dates are omitted. "
        "The `streak` reflects the current consecutive-day streak as of today, "
        "not the streak at the end of the viewed month."
    ),
)
async def get_calendar(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
    year: int = Query(
        ...,
        ge=2020,
        le=2100,
        description="4-digit year. Example: 2026",
        examples=[2026],
    ),
    month: int = Query(
        ...,
        ge=1,
        le=12,
        description="Month number (1=January, 12=December). Example: 6",
        examples=[6],
    ),
) -> CalendarResponse:
    return await attendance_service.get_calendar(
        db,
        user_id=current_user.id,
        member_id=current_user.member_id or "",
        year=year,
        month=month,
    )
