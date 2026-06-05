"""
app/schemas/member.py
──────────────────────
Pydantic v2 request/response schemas for the Member Management module.

MemberOut       — Full member profile (admin view or self-view)
MemberListItem  — Compact row for paginated admin list
MemberListResponse — Paginated wrapper
MemberUpdate    — Admin update payload (all fields optional)
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── Full Member Profile ────────────────────────────────────────────────────

class MemberOut(BaseModel):
    """
    Full profile view of a single member.
    Returned by GET /members/{member_id} for both admin and self-access.
    Aggregates data from: users + members_profile + gym_plans.
    """

    # Identity
    id: uuid.UUID = Field(description="Internal UUID. Not shown to members.")
    member_id: str = Field(examples=["S2T101"])
    email: str

    # Personal details
    full_name: str
    age: int
    gender: str
    phone: str
    address: str

    # Membership state
    membership_status: str = Field(
        description="ACTIVE | EXPIRED | PENDING | SUSPENDED",
        examples=["ACTIVE"],
    )
    membership_start_date: Optional[date] = None
    membership_end_date: Optional[date] = None
    days_remaining: Optional[int] = Field(
        default=None,
        description="Days until expiry for ACTIVE memberships. None if not ACTIVE.",
    )

    # Plan info
    plan_id: uuid.UUID
    plan_name: str = Field(examples=["Monthly"])

    # Account state
    is_active: bool
    joined_on: datetime = Field(description="Account creation timestamp.")

    model_config = {"from_attributes": True}


# ── Compact List Item ──────────────────────────────────────────────────────

class MemberListItem(BaseModel):
    """
    Compact member representation for the admin members table.
    One row = one item. Contains only the fields visible in the table UI.
    """

    id: uuid.UUID
    member_id: str = Field(examples=["S2T101"])
    full_name: str
    age: int
    gender: str
    phone: str
    membership_status: str
    membership_end_date: Optional[date] = None
    days_remaining: Optional[int] = None
    plan_name: str
    is_active: bool

    model_config = {"from_attributes": True}


# ── Paginated List Response ────────────────────────────────────────────────

class MemberListResponse(BaseModel):
    """Paginated list of members returned by GET /members."""

    members: list[MemberListItem]
    total: int = Field(description="Total members matching the current filter/search.")
    page: int
    per_page: int
    total_pages: int
    search_term: Optional[str] = Field(
        default=None,
        description="The search query applied, if any.",
    )


# ── Admin Update Payload ───────────────────────────────────────────────────

class MemberUpdate(BaseModel):
    """
    Admin-only update payload.
    All fields are optional — only supplied fields are updated (PATCH semantics).
    """

    full_name: Optional[str] = Field(
        default=None,
        min_length=2,
        max_length=255,
        examples=["Rahul Sharma"],
    )
    age: Optional[int] = Field(
        default=None,
        ge=10,
        le=100,
        examples=[29],
    )
    phone: Optional[str] = Field(
        default=None,
        pattern=r"^\d{10}$",
        examples=["9876543210"],
    )
    address: Optional[str] = Field(
        default=None,
        min_length=5,
        max_length=500,
    )
    membership_status: Optional[str] = Field(
        default=None,
        description="Admin can set: ACTIVE, EXPIRED, SUSPENDED, PENDING.",
    )

    @field_validator("membership_status")
    @classmethod
    def validate_status(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        allowed = {"ACTIVE", "EXPIRED", "SUSPENDED", "PENDING"}
        if v.upper() not in allowed:
            raise ValueError(
                f"membership_status must be one of: {', '.join(sorted(allowed))}"
            )
        return v.upper()
