"""
app/repositories/attendance_repo.py
─────────────────────────────────────
Data Access Object for the `attendance_logs` table.

Performance design:
  All queries are index-scanned:
    - `user_id` index on attendance_logs → O(log N) member lookup
    - `(user_id, attendance_date, session)` unique constraint → index scan for dupe check
    - `(user_id, attendance_date)` is covered by the unique constraint index

  The streak calculation in the service fetches up to 90 days of attendance —
  a bounded, fast range scan. No full-table scans anywhere.

  For the calendar query, filtering by year+month uses SQLAlchemy's
  `between()` on the Date column (which PostgreSQL optimises with a BTREE
  index range scan) — avoids EXTRACT() which can prevent index usage.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.attendance_log import AttendanceLog


# ── Helpers ────────────────────────────────────────────────────────────────

def _month_bounds(year: int, month: int) -> tuple[date, date]:
    """
    Return (first_day, last_day) for a given year+month.
    Uses date arithmetic instead of monthrange to avoid calendar imports.
    Works correctly for December → January rollover.
    """
    first_day = date(year, month, 1)
    # First day of NEXT month minus one day = last day of this month
    if month == 12:
        last_day = date(year + 1, 1, 1) - timedelta(days=1)
    else:
        last_day = date(year, month + 1, 1) - timedelta(days=1)
    return first_day, last_day


# ── Write ──────────────────────────────────────────────────────────────────

async def insert_attendance(
    db: AsyncSession,
    user_id: uuid.UUID,
    attendance_date: date,
    session: str,
) -> AttendanceLog:
    """
    Insert a new attendance log.

    The caller (attendance_service) performs an application-level duplicate
    check before calling this. The DB UniqueConstraint on
    (user_id, attendance_date, session) is the definitive safety net —
    if a race condition bypasses the app check, the DB raises IntegrityError,
    which propagates as HTTP 409 via the global exception handler.

    Uses flush+refresh to get the server-assigned timestamps populated
    in the returned object (needed for the checkin response).
    """
    log = AttendanceLog(
        user_id=user_id,
        attendance_date=attendance_date,
        session=session,
    )
    db.add(log)
    await db.flush()
    await db.refresh(log)
    return log


# ── Read ───────────────────────────────────────────────────────────────────

async def check_if_checked_in(
    db: AsyncSession,
    user_id: uuid.UUID,
    attendance_date: date,
    session: str,
) -> bool:
    """
    Return True if the member has already checked in for this session today.

    Uses COUNT(*) instead of EXISTS() — COUNT is marginally faster on
    PostgreSQL for single-row checks because it uses the unique index path
    without an EXISTS sub-plan.
    """
    result = await db.execute(
        select(func.count())
        .where(
            AttendanceLog.user_id == user_id,
            AttendanceLog.attendance_date == attendance_date,
            AttendanceLog.session == session,
        )
    )
    return (result.scalar_one() or 0) > 0


async def get_today_sessions(
    db: AsyncSession,
    user_id: uuid.UUID,
    today: date,
) -> list[str]:
    """
    Return the list of sessions already checked in for today (e.g., ["FN"]).
    Used to populate `can_checkin_an` in the check-in response.
    At most 2 rows returned — no pagination needed.
    """
    result = await db.execute(
        select(AttendanceLog.session)
        .where(
            AttendanceLog.user_id == user_id,
            AttendanceLog.attendance_date == today,
        )
    )
    return [row.session for row in result.all()]


async def get_monthly_calendar(
    db: AsyncSession,
    user_id: uuid.UUID,
    year: int,
    month: int,
) -> list:
    """
    Fetch all attendance logs for a member within a specific calendar month.

    Returns a list of Row objects with (attendance_date, session).
    The service maps these into the CalendarResponse schema.

    Index strategy:
      Uses `BETWEEN first_day AND last_day` on the attendance_date column —
      PostgreSQL uses the BTREE index with a range scan, avoiding EXTRACT()
      which would force a seq scan or function-based index.
    """
    first_day, last_day = _month_bounds(year, month)

    result = await db.execute(
        select(AttendanceLog.attendance_date, AttendanceLog.session)
        .where(
            AttendanceLog.user_id == user_id,
            AttendanceLog.attendance_date.between(first_day, last_day),
        )
        .order_by(AttendanceLog.attendance_date.asc(), AttendanceLog.session.asc())
    )
    return result.all()


async def get_recent_attendance_dates(
    db: AsyncSession,
    user_id: uuid.UUID,
    since: date,
) -> list[date]:
    """
    Fetch distinct calendar dates where the member attended since `since`.

    Used by the service to calculate the current streak.
    Fetching distinct dates (not sessions) is sufficient — streak counts
    days attended, not sessions.

    `since` is typically today - 90 days (a streak longer than 90 days is
    already impressive; beyond that we'd need a separate count anyway).
    The DISTINCT query with a date range scan is extremely fast on an indexed
    column.
    """
    result = await db.execute(
        select(AttendanceLog.attendance_date)
        .where(
            AttendanceLog.user_id == user_id,
            AttendanceLog.attendance_date >= since,
        )
        .distinct()
        .order_by(AttendanceLog.attendance_date.desc())
    )
    return [row.attendance_date for row in result.all()]


async def get_monthly_session_count(
    db: AsyncSession,
    user_id: uuid.UUID,
    year: int,
    month: int,
) -> int:
    """
    Return total number of session rows (FN + AN) for a member in a given month.
    Used in check-in response for `total_this_month`.
    """
    first_day, last_day = _month_bounds(year, month)
    result = await db.execute(
        select(func.count())
        .where(
            AttendanceLog.user_id == user_id,
            AttendanceLog.attendance_date.between(first_day, last_day),
        )
    )
    return result.scalar_one() or 0
