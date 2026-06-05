"""
app/schemas/payment.py
───────────────────────
Pydantic v2 request/response schemas for the Payment Approval module.

PaymentSubmitRequest — Member submits a payment declaration.
PaymentOut           — Full payment record (admin view or member history view).
ApprovalRequest      — Admin approves, optionally providing a custom end_date
                        for Special Personal Training plans (duration_days=NULL).
RejectRequest        — Admin rejection with mandatory reason.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_validator


# ── Submission ─────────────────────────────────────────────────────────────

class PaymentSubmitRequest(BaseModel):
    """
    Member submits a manual payment declaration.

    The member selects the plan they are paying for (to allow plan changes
    at renewal time without re-registering). The backend snapshots the
    plan's current price into payment_requests.amount at submission time.
    """

    plan_id: uuid.UUID = Field(
        ...,
        description="UUID of the gym plan being paid for.",
    )


# ── Output ─────────────────────────────────────────────────────────────────

class PaymentOut(BaseModel):
    """
    Represents a payment request record.
    Returned in admin's pending list and member's payment history.
    """

    id: uuid.UUID
    member_id: str = Field(examples=["S2T101"])
    full_name: str
    plan_name: str = Field(examples=["Monthly"])
    amount: Decimal = Field(examples=[1500.00])
    status: str = Field(
        examples=["PENDING_APPROVAL"],
        description="PENDING_APPROVAL | APPROVED | REJECTED",
    )
    rejection_reason: Optional[str] = None
    submitted_at: datetime = Field(description="When the member submitted the request.")
    reviewed_at: Optional[datetime] = None
    reviewed_by_name: Optional[str] = Field(
        default=None,
        description="Name/email of the admin who reviewed. None if still pending.",
    )

    # Membership dates set on approval
    membership_start_date: Optional[date] = None
    membership_end_date: Optional[date] = None

    model_config = {"from_attributes": True}


class PendingPaymentsResponse(BaseModel):
    """List of pending payment requests for admin dashboard."""

    requests: list[PaymentOut]
    total: int


# ── Admin Actions ──────────────────────────────────────────────────────────

class ApprovalRequest(BaseModel):
    """
    Admin approves a payment request.

    `custom_end_date` is REQUIRED when approving a Special Personal Training
    plan (because its gym_plans.duration_days = NULL — there is no fixed
    duration to calculate from). For Monthly and Annual plans, leave this
    field empty and the backend calculates the end_date automatically.

    If `custom_end_date` is provided for a plan that already has duration_days,
    the custom_end_date takes precedence (allows admin flexibility).
    """

    custom_end_date: Optional[date] = Field(
        default=None,
        description=(
            "Required for Special Personal Training plans (duration_days=NULL). "
            "Optional for other plans — overrides the auto-calculated expiry date."
        ),
    )

    @field_validator("custom_end_date")
    @classmethod
    def end_date_must_be_future(cls, v: Optional[date]) -> Optional[date]:
        if v is not None and v <= date.today():
            raise ValueError("custom_end_date must be a future date.")
        return v


class RejectRequest(BaseModel):
    """
    Admin rejects a payment request.
    Reason is required so the member understands what action to take.
    """

    rejection_reason: str = Field(
        ...,
        min_length=5,
        max_length=500,
        examples=["Payment proof not submitted at front desk. Please visit to complete payment."],
        description="Human-readable reason shown to the member.",
    )
