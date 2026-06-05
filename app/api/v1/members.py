"""
app/api/v1/members.py
──────────────────────
FastAPI router for the Member Management module.

Endpoints:
  GET    /members                    Admin only — paginated member list with search
  GET    /members/{member_id}        Admin OR Self — full member profile
  PUT    /members/{member_id}        Admin only — partial profile/status update
  DELETE /members/{member_id}        Admin only — soft-deactivate member

Access control pattern:
  - Admin-only routes use `require_admin` dependency (raises 403 for members).
  - The GET detail endpoint uses `get_current_user` and delegates the
    admin-vs-self check to the service layer, keeping the router thin.

URL parameter note:
  {member_id} in all paths refers to the HUMAN-READABLE member ID (e.g., "S2T101"),
  NOT the internal UUID. This is intentional — it matches what members see
  on their dashboard and what admins use in the table.
"""

from __future__ import annotations

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, require_admin
from app.models.user import User
from app.schemas.auth import MessageResponse
from app.schemas.member import MemberListResponse, MemberOut, MemberUpdate
from app.services import member_service

router = APIRouter(prefix="/members", tags=["Members"])


# ── GET /members ───────────────────────────────────────────────────────────

@router.get(
    "",
    response_model=MemberListResponse,
    status_code=status.HTTP_200_OK,
    summary="List all members (Admin only)",
    description=(
        "Returns a paginated list of all registered members with their "
        "profile details, membership status, and plan. "
        "Supports free-text search on member name and member ID."
    ),
)
async def list_members(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
    page: int = Query(default=1, ge=1, description="Page number (1-indexed)."),
    per_page: int = Query(default=20, ge=1, le=100, description="Items per page."),
    search: Optional[str] = Query(
        default=None,
        max_length=100,
        description="Search by member name or member ID (case-insensitive).",
        alias="q",
    ),
) -> MemberListResponse:
    return await member_service.get_paginated_members(
        db,
        page=page,
        per_page=per_page,
        search_term=search,
    )


# ── GET /members/{member_id} ───────────────────────────────────────────────

@router.get(
    "/{member_id}",
    response_model=MemberOut,
    status_code=status.HTTP_200_OK,
    summary="Get member profile (Admin or Self)",
    description=(
        "Returns the full profile of a specific member by their Member ID (e.g., S2T101). "
        "Admins can view any member's profile. "
        "Members can only view their own profile — a 403 is returned otherwise."
    ),
)
async def get_member(
    member_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> MemberOut:
    # Access control (admin OR self) is enforced inside the service
    return await member_service.get_member_profile(
        db,
        member_id=member_id,
        requesting_user=current_user,
    )


# ── PUT /members/{member_id} ───────────────────────────────────────────────

@router.put(
    "/{member_id}",
    response_model=MemberOut,
    status_code=status.HTTP_200_OK,
    summary="Update member profile (Admin only)",
    description=(
        "Partially update a member's profile fields or membership status. "
        "All fields are optional — only supplied fields are changed. "
        "To change membership_status, use values: ACTIVE, EXPIRED, SUSPENDED, PENDING."
    ),
)
async def update_member(
    member_id: str,
    payload: MemberUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> MemberOut:
    return await member_service.update_member(db, member_id=member_id, payload=payload)


# ── DELETE /members/{member_id} ────────────────────────────────────────────

@router.delete(
    "/{member_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Deactivate member (Admin only)",
    description=(
        "Soft-deletes a member by setting is_active=False. "
        "The member cannot log in after this operation. "
        "All historical attendance, payment, and revenue records are preserved. "
        "This action is reversible by an admin via PUT /members/{member_id} "
        "or directly in Supabase."
    ),
)
async def deactivate_member(
    member_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> MessageResponse:
    await member_service.deactivate_member(db, member_id=member_id)
    return MessageResponse(
        message=f"Member {member_id} has been deactivated successfully."
    )
