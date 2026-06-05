"""
app/services/member_service.py
───────────────────────────────
Business logic for the Member Management module.

Orchestrates:
  - member_repo   → DB queries (JOIN across users + members_profile + gym_plans)
  - user_repo     → User-level operations (deactivate)

Responsibilities:
  - Map raw DB Row objects to Pydantic schemas.
  - Compute derived fields (days_remaining, total_pages).
  - Enforce self-access vs admin-access rules.
  - Raise typed BusinessErrors for not-found, forbidden, etc.

Does NOT touch HTTP (no Request/Response objects).
Does NOT execute raw SQL (all DB access goes through repositories).
"""

from __future__ import annotations

import math
import uuid
from datetime import date
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import ResourceNotFoundError
from app.models.user import User
from app.repositories import member_repo, user_repo
from app.schemas.member import (
    MemberListItem,
    MemberListResponse,
    MemberOut,
    MemberUpdate,
)


# ── Internal Helper ────────────────────────────────────────────────────────

def _compute_days_remaining(end_date: Optional[date], status: str) -> Optional[int]:
    """
    Calculate days remaining on an active membership.
    Returns None for non-ACTIVE memberships or when end_date is unset.
    Returns 0 if today is the expiry date.
    Negative values indicate past expiry (shouldn't happen for ACTIVE, but safe).
    """
    if status != "ACTIVE" or end_date is None:
        return None
    delta = (end_date - date.today()).days
    return max(delta, 0)


def _row_to_member_list_item(row) -> MemberListItem:
    """Map a DB Row (from member_repo._MEMBER_COLUMNS) to MemberListItem schema."""
    return MemberListItem(
        id=row.id,
        member_id=row.member_id,
        full_name=row.full_name,
        age=row.age,
        gender=row.gender,
        phone=row.phone,
        membership_status=row.membership_status,
        membership_end_date=row.membership_end_date,
        days_remaining=_compute_days_remaining(
            row.membership_end_date, row.membership_status
        ),
        plan_name=row.plan_name,
        is_active=row.is_active,
    )


def _row_to_member_out(row) -> MemberOut:
    """Map a DB Row (from member_repo._MEMBER_COLUMNS) to full MemberOut schema."""
    return MemberOut(
        id=row.id,
        member_id=row.member_id,
        email=row.email,
        full_name=row.full_name,
        age=row.age,
        gender=row.gender,
        phone=row.phone,
        address=row.address,
        membership_status=row.membership_status,
        membership_start_date=row.membership_start_date,
        membership_end_date=row.membership_end_date,
        days_remaining=_compute_days_remaining(
            row.membership_end_date, row.membership_status
        ),
        plan_id=row.plan_id,
        plan_name=row.plan_name,
        is_active=row.is_active,
        joined_on=row.joined_on,
    )


# ── Public Service Functions ───────────────────────────────────────────────

async def get_paginated_members(
    db: AsyncSession,
    page: int = 1,
    per_page: int = 20,
    search_term: Optional[str] = None,
) -> MemberListResponse:
    """
    Return a paginated list of members for the Admin dashboard table.

    Pagination strategy:
      - Page is 1-indexed (page=1 → skip=0).
      - skip = (page - 1) * per_page.
      - total_pages = ceil(total / per_page).

    Args:
        page       — current page (1-indexed, min=1)
        per_page   — items per page (1–100)
        search_term — optional free-text search on full_name / member_id
    """
    page = max(1, page)
    per_page = min(max(1, per_page), 100)  # Clamp between 1 and 100
    skip = (page - 1) * per_page

    rows, total = await member_repo.list_all_members(
        db,
        skip=skip,
        limit=per_page,
        search_term=search_term,
    )

    total_pages = math.ceil(total / per_page) if total > 0 else 1

    return MemberListResponse(
        members=[_row_to_member_list_item(row) for row in rows],
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
        search_term=search_term or None,
    )


async def get_member_profile(
    db: AsyncSession,
    member_id: str,
    requesting_user: User,
) -> MemberOut:
    """
    Return the full profile for a given member_id.

    Access control:
      - Admin: can fetch any member's profile.
      - Member: can only fetch their OWN profile.
        → Raises HTTP 403 if requesting another member's profile.

    Args:
        member_id       — human-readable ID from URL path (e.g., "S2T101")
        requesting_user — the authenticated user making the request
    """
    # Self-access guard for members
    if requesting_user.role == "member":
        if requesting_user.member_id != member_id:
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only view your own profile.",
            )

    row = await member_repo.get_member_by_member_id(db, member_id)
    if row is None:
        raise ResourceNotFoundError(f"Member {member_id}")

    return _row_to_member_out(row)


async def update_member(
    db: AsyncSession,
    member_id: str,
    payload: MemberUpdate,
) -> MemberOut:
    """
    Apply partial updates to a member's profile. Admin only.

    Strategy:
      1. Look up the member to verify they exist.
      2. Build a dict of only the supplied (non-None) fields.
      3. Pass the dict to the repo for a targeted SQL UPDATE.
      4. Re-fetch the updated row and return it.

    This avoids the read-modify-write ORM pattern, which would require
    loading the full profile ORM object into memory before saving.
    """
    # Verify member exists
    row = await member_repo.get_member_by_member_id(db, member_id)
    if row is None:
        raise ResourceNotFoundError(f"Member {member_id}")

    # Build update dict — only fields explicitly set in the request
    update_data: dict = {}
    if payload.full_name is not None:
        update_data["full_name"] = payload.full_name
    if payload.age is not None:
        update_data["age"] = payload.age
    if payload.phone is not None:
        update_data["phone"] = payload.phone
    if payload.address is not None:
        update_data["address"] = payload.address
    if payload.membership_status is not None:
        update_data["membership_status"] = payload.membership_status

    if update_data:
        await member_repo.update_member_profile(db, row.id, update_data)

    # Re-fetch the updated record to return accurate state
    updated_row = await member_repo.get_member_by_member_id(db, member_id)
    return _row_to_member_out(updated_row)  # type: ignore[arg-type]


async def deactivate_member(
    db: AsyncSession,
    member_id: str,
) -> None:
    """
    Soft-delete a member by setting is_active=False in the users table.
    Admin only. The member account is preserved for audit/history purposes.

    The member cannot log in after this operation (get_current_user checks is_active).
    All historical attendance and payment records remain intact.

    Raises ResourceNotFoundError if the member_id doesn't exist.
    """
    # Verify member exists using the users table directly
    user = await user_repo.get_by_member_id(db, member_id)
    if user is None:
        raise ResourceNotFoundError(f"Member {member_id}")

    await user_repo.deactivate_user(db, user.id)
