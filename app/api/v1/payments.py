"""
app/api/v1/payments.py
───────────────────────
FastAPI router for the Payment Approval module.

Endpoints:
  POST /payments/submit           Member only — declare a payment
  GET  /payments/pending          Admin only  — approval queue
  POST /payments/{id}/approve     Admin only  — approve and activate membership
  POST /payments/{id}/reject      Admin only  — reject with reason

Access control:
  - Members can only submit payments (for themselves).
  - All admin endpoints use `require_admin` — members get HTTP 403.

Route ordering note:
  FastAPI matches routes top-to-bottom. "/payments/submit" MUST be declared
  before "/payments/{id}/approve" to prevent "submit" being matched as an {id}.
  The same applies to "/payments/pending".
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, require_admin
from app.models.user import User
from app.schemas.payment import (
    ApprovalRequest,
    PaymentOut,
    PaymentSubmitRequest,
    PendingPaymentsResponse,
    RejectRequest,
)
from app.services import payment_service

router = APIRouter(prefix="/payments", tags=["Payments"])


# ── POST /payments/submit ──────────────────────────────────────────────────

@router.post(
    "/submit",
    response_model=PaymentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a payment declaration (Member only)",
    description=(
        "Member declares they have paid for a gym plan. "
        "Creates a PENDING_APPROVAL request that admins can review. "
        "Only one pending request is allowed at a time — subsequent submissions "
        "return HTTP 409 until the current one is approved or rejected."
    ),
)
async def submit_payment(
    payload: PaymentSubmitRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
) -> PaymentOut:
    return await payment_service.submit_payment(
        db,
        requesting_user=current_user,
        plan_id=payload.plan_id,
    )


# ── GET /payments/pending ──────────────────────────────────────────────────

@router.get(
    "/pending",
    response_model=PendingPaymentsResponse,
    status_code=status.HTTP_200_OK,
    summary="List pending payment approvals (Admin only)",
    description=(
        "Returns all payment requests with status=PENDING_APPROVAL. "
        "Ordered by submission date (oldest first — FIFO approval queue). "
        "The admin reviews each request and approves or rejects it."
    ),
)
async def get_pending_payments(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> PendingPaymentsResponse:
    return await payment_service.get_pending_requests(db)


# ── POST /payments/{id}/approve ────────────────────────────────────────────

@router.post(
    "/{payment_id}/approve",
    response_model=PaymentOut,
    status_code=status.HTTP_200_OK,
    summary="Approve a payment request (Admin only)",
    description=(
        "Approves a PENDING_APPROVAL payment request. Triggers the full "
        "membership activation lifecycle atomically:\n"
        "1. Marks payment_requests.status = APPROVED\n"
        "2. Calculates new membership expiry date\n"
        "3. Updates members_profile: status=ACTIVE, dates set\n"
        "4. Creates a revenue_logs entry for monthly reporting\n\n"
        "For **Special Personal Training** plans (no fixed duration), "
        "the `custom_end_date` field is REQUIRED in the request body. "
        "For Monthly/Annual plans, `custom_end_date` is optional — "
        "expiry is auto-calculated from the plan's duration_days."
    ),
)
async def approve_payment(
    payment_id: uuid.UUID,
    payload: ApprovalRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
) -> PaymentOut:
    return await payment_service.approve_payment(
        db,
        payment_id=payment_id,
        admin_user=admin,
        payload=payload,
    )


# ── POST /payments/{id}/reject ─────────────────────────────────────────────

@router.post(
    "/{payment_id}/reject",
    response_model=PaymentOut,
    status_code=status.HTTP_200_OK,
    summary="Reject a payment request (Admin only)",
    description=(
        "Rejects a PENDING_APPROVAL payment request with a mandatory reason. "
        "The member's membership status is NOT changed — they remain PENDING "
        "and can submit a new payment request after addressing the rejection reason. "
        "The rejection reason is stored and visible to the member."
    ),
)
async def reject_payment(
    payment_id: uuid.UUID,
    payload: RejectRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    admin: Annotated[User, Depends(require_admin)],
) -> PaymentOut:
    return await payment_service.reject_payment(
        db,
        payment_id=payment_id,
        admin_user=admin,
        payload=payload,
    )
