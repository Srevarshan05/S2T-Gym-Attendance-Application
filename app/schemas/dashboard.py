"""
app/schemas/dashboard.py
─────────────────────────
Pydantic v2 schemas for the Admin Dashboard Overview.

DashboardOverviewResponse — all KPIs in one response object.
ExpiringMemberItem        — one row in the "expiring soon" alert list.

All numeric KPIs have a default of 0 / [] so an empty/new database
never causes null-reference errors in the frontend.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


# ── Expiring Soon ──────────────────────────────────────────────────────────

class ExpiringMemberItem(BaseModel):
    """
    Compact record for a member whose membership expires within 7 days.
    Surfaces only what the admin needs to take action quickly.
    """

    member_id: str = Field(examples=["S2T101"])
    full_name: str = Field(examples=["Rahul Sharma"])
    plan_name: str = Field(examples=["Monthly"])
    membership_end_date: date
    days_remaining: int = Field(
        description="0 = expires today. 1 = expires tomorrow. Max 7 in this list.",
        examples=[3],
    )


# ── Full Dashboard Overview ────────────────────────────────────────────────

class DashboardOverviewResponse(BaseModel):
    """
    All Admin Dashboard KPIs returned in a single API response.

    Sourced from a single PostgreSQL CTE — one DB round-trip, no N+1.

    Field groups:
      Membership counts  — total + breakdown by status
      Today's attendance — FN count, AN count, unique members
      Payment queue      — pending approval count
      Revenue            — current month's total in INR
      Expiring soon      — ACTIVE members expiring within 7 days
    """

    # ── Membership KPIs ────────────────────────────────────────────────────
    total_members: int = Field(
        default=0,
        description="Active (is_active=True) member accounts. Excludes soft-deleted.",
    )
    active_members: int = Field(
        default=0,
        description="Members with membership_status = 'ACTIVE'.",
    )
    expired_members: int = Field(
        default=0,
        description="Members with membership_status = 'EXPIRED'.",
    )
    pending_members: int = Field(
        default=0,
        description="Members with membership_status = 'PENDING' (payment not approved yet).",
    )
    suspended_members: int = Field(
        default=0,
        description="Members with membership_status = 'SUSPENDED'.",
    )

    # ── Today's Attendance ─────────────────────────────────────────────────
    today_fn_count: int = Field(
        default=0,
        description="Forenoon (FN) check-ins logged today (IST date).",
    )
    today_an_count: int = Field(
        default=0,
        description="Afternoon/Evening (AN) check-ins logged today (IST date).",
    )
    today_total_checkins: int = Field(
        default=0,
        description="Total check-ins today (FN + AN combined).",
    )
    today_unique_members: int = Field(
        default=0,
        description="Distinct members who attended today (regardless of session count).",
    )

    # ── Payment Queue ──────────────────────────────────────────────────────
    pending_payments_count: int = Field(
        default=0,
        description="Payment requests awaiting admin approval.",
    )

    # ── Revenue ────────────────────────────────────────────────────────────
    monthly_revenue: Decimal = Field(
        default=Decimal("0.00"),
        description="Total approved payment revenue in INR for the current calendar month (IST).",
        examples=[45000.00],
    )
    current_month_label: str = Field(
        default="",
        description="Human-readable month label for the revenue figure. E.g., 'June 2026'.",
        examples=["June 2026"],
    )

    # ── Expiring Soon ──────────────────────────────────────────────────────
    expiring_soon: list[ExpiringMemberItem] = Field(
        default_factory=list,
        description=(
            "ACTIVE members whose membership expires within the next 7 days. "
            "Sorted by expiry date ascending (most urgent first). "
            "Empty list [] if no one is expiring soon — never null."
        ),
    )

    # ── Metadata ───────────────────────────────────────────────────────────
    generated_at: datetime = Field(
        description="UTC timestamp when this dashboard data was computed."
    )
