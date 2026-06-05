"""
app/repositories/member_repo.py
─────────────────────────────────
Data Access Object for member profile queries.

All queries JOIN across: users ↔ members_profile ↔ gym_plans.
Returns Row objects (namedtuple-like) that the service layer maps
to Pydantic schemas.

No business logic here — only query construction and execution.
"""

from __future__ import annotations

import math
import uuid
from typing import Optional

from sqlalchemy import func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gym_plan import GymPlan
from app.models.member_profile import MemberProfile
from app.models.user import User


# ── Column Projection ──────────────────────────────────────────────────────
# Define once — used in both list and single-fetch queries.
# Returning explicit columns (not full ORM objects) avoids loading unused data.
_MEMBER_COLUMNS = (
    User.id,
    User.member_id,
    User.email,
    User.is_active,
    User.created_at.label("joined_on"),
    MemberProfile.full_name,
    MemberProfile.age,
    MemberProfile.gender,
    MemberProfile.phone,
    MemberProfile.address,
    MemberProfile.membership_status,
    MemberProfile.membership_start_date,
    MemberProfile.membership_end_date,
    MemberProfile.plan_id,
    GymPlan.name.label("plan_name"),
)


def _base_member_query():
    """
    Base SELECT … JOIN query shared between list and count operations.
    Filters: role='member', is_active=True (shows only registered members).
    """
    return (
        select(*_MEMBER_COLUMNS)
        .join(MemberProfile, MemberProfile.user_id == User.id)
        .join(GymPlan, GymPlan.id == MemberProfile.plan_id)
        .where(User.role == "member")
    )


# ── List Members ───────────────────────────────────────────────────────────

async def list_all_members(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 20,
    search_term: Optional[str] = None,
    include_inactive: bool = False,
) -> tuple[list, int]:
    """
    Return a paginated list of members with their profile and plan data.

    Args:
        db            — async database session
        skip          — number of records to skip (offset)
        limit         — number of records to return
        search_term   — optional free-text search on full_name and member_id (case-insensitive)
        include_inactive — if True, includes soft-deleted (is_active=False) members

    Returns:
        (rows, total_count)
        rows       — list of Row objects with all _MEMBER_COLUMNS fields
        total_count — total matching records (for pagination metadata)

    Query strategy:
        1. Build the base JOIN query.
        2. Apply optional search filter with ILIKE (PostgreSQL case-insensitive LIKE).
        3. Execute a COUNT(*) subquery for total (single DB round-trip per call).
        4. Execute the data query with ORDER BY + LIMIT/OFFSET.
    """
    query = _base_member_query()

    # Filter active status
    if not include_inactive:
        query = query.where(User.is_active == True)  # noqa: E712

    # Optional search: ILIKE on full_name OR member_id
    if search_term and search_term.strip():
        pattern = f"%{search_term.strip()}%"
        query = query.where(
            or_(
                MemberProfile.full_name.ilike(pattern),
                User.member_id.ilike(pattern),
            )
        )

    # ── Count query (wrap filtered query in a subquery for accurate count) ─
    count_subq = query.subquery()
    count_query = select(func.count()).select_from(count_subq)
    total_result = await db.execute(count_query)
    total = total_result.scalar_one() or 0

    # ── Data query with ordering and pagination ────────────────────────────
    paginated_query = (
        query
        .order_by(MemberProfile.full_name.asc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(paginated_query)
    rows = result.all()

    return rows, total


# ── Single Member Fetch ────────────────────────────────────────────────────

async def get_member_by_member_id(
    db: AsyncSession,
    member_id: str,
) -> Optional[object]:
    """
    Fetch full member profile by human-readable member_id (e.g., "S2T101").
    Used by:
      - GET /members/{member_id} (admin or self-access)
      - Internal lookup during payment approval
    Returns None if member not found.
    """
    query = (
        _base_member_query()
        .where(User.member_id == member_id)
    )
    result = await db.execute(query)
    return result.one_or_none()


async def get_member_by_user_id(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> Optional[object]:
    """
    Fetch full member profile by internal UUID (user.id).
    Used when we already have the UUID from JWT claims.
    """
    query = (
        _base_member_query()
        .where(User.id == user_id)
    )
    result = await db.execute(query)
    return result.one_or_none()


# ── Update Operations ──────────────────────────────────────────────────────

async def update_member_profile(
    db: AsyncSession,
    user_id: uuid.UUID,
    update_data: dict,
) -> None:
    """
    Update mutable fields in members_profile for a given user_id.

    Args:
        update_data — dict of {column_name: new_value} for fields to update.
                      Only non-None values should be passed in (filtering done in service).

    Uses a targeted UPDATE — does not read the row first (no ORM fetch overhead).
    The keys must match MemberProfile column names exactly.
    """
    if not update_data:
        return

    await db.execute(
        update(MemberProfile)
        .where(MemberProfile.user_id == user_id)
        .values(**update_data)
    )


async def update_member_status(
    db: AsyncSession,
    user_id: uuid.UUID,
    status: str,
) -> None:
    """
    Update only the membership_status for a member.
    Convenience wrapper around update_member_profile for status-only changes.
    Used by the payment approval flow (Phase 5 Payments) and admin overrides.
    """
    await db.execute(
        update(MemberProfile)
        .where(MemberProfile.user_id == user_id)
        .values(membership_status=status)
    )


async def activate_membership(
    db: AsyncSession,
    user_id: uuid.UUID,
    start_date,
    end_date,
) -> None:
    """
    Activate a member's membership by setting dates and status to ACTIVE.
    Called by the payment approval service after admin approves payment.
    """
    await db.execute(
        update(MemberProfile)
        .where(MemberProfile.user_id == user_id)
        .values(
            membership_status="ACTIVE",
            membership_start_date=start_date,
            membership_end_date=end_date,
        )
    )
