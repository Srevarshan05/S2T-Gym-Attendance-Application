"""
app/services/payment_service.py
────────────────────────────────
Business logic for the Payment Approval module.

The critical function is `approve_payment()`, which performs a 4-step
membership lifecycle update. All 4 steps run inside the SAME database
session transaction — the one opened by get_db() and committed on
successful HTTP response. If any step raises an exception, get_db()
automatically rolls back the entire transaction, ensuring no partial state.

Transaction atomicity guarantee:
  Step 1: update payment_requests.status → APPROVED
  Step 2: calculate expiry_date
  Step 3: update members_profile (status, start_date, end_date)
  Step 4: insert into revenue_logs

If Step 4 fails (e.g., DB constraint violation), Steps 1, 2, and 3 are
also rolled back. The DB is always in a consistent state.

Note: We rely on the session-level transaction managed by get_db(), NOT
on nested transactions (savepoints). A savepoint approach would be needed
only if we wanted partial rollback within a larger transaction — which we
don't need here.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import (
    MembershipPendingError,
    PendingPaymentExistsError,
    ResourceNotFoundError,
)
from app.models.gym_plan import GymPlan
from app.models.user import User
from app.repositories import member_repo, payment_repo
from app.schemas.payment import (
    ApprovalRequest,
    PaymentOut,
    PendingPaymentsResponse,
    RejectRequest,
)


# ── Internal Helpers ───────────────────────────────────────────────────────

def _row_to_payment_out(row) -> PaymentOut:
    """Map a joined DB Row from payment_repo._PAYMENT_COLUMNS to PaymentOut."""
    return PaymentOut(
        id=row.id,
        member_id=row.member_id,
        full_name=row.full_name,
        plan_name=row.plan_name,
        amount=row.amount,
        status=row.status,
        rejection_reason=row.rejection_reason,
        submitted_at=row.submitted_at,
        reviewed_at=row.reviewed_at,
        reviewed_by_name=None,  # Resolved separately if needed; None for list views
        membership_start_date=row.membership_start_date,
        membership_end_date=row.membership_end_date,
    )


def _compute_month_bucket(approval_date: date) -> str:
    """
    Format a date into a 'YYYY-MM' month bucket string.
    Example: date(2026, 6, 15) → '2026-06'
    Stored at approval time — never recalculated.
    """
    return approval_date.strftime("%Y-%m")


def _calculate_expiry_date(
    current_end_date: Optional[date],
    duration_days: Optional[int],
    custom_end_date: Optional[date],
    approval_date: date,
) -> date:
    """
    Calculate the new membership expiry date on payment approval.

    Priority rules (highest to lowest):
      1. `custom_end_date` — always takes precedence if supplied by admin.
         Required for Special Personal Training plans (duration_days=NULL).
      2. `duration_days` from the gym plan — calculated from the later of:
           a. `current_end_date` if it's in the future (renewal extension)
           b. `approval_date` if the membership is already expired or new

    Renewal extension logic:
      If a member renews BEFORE their current membership expires, the new
      expiry is calculated from the existing end_date, not from today.
      This prevents members losing days for early renewal.

      Example:
        current_end_date = 2026-07-01 (still active)
        approval_date    = 2026-06-15
        duration_days    = 30
        → new end_date   = 2026-07-01 + 30 = 2026-07-31 ✓ (not 2026-07-15)

    Raises ValueError if duration_days is None AND custom_end_date is None.
    This is caught by the service and surfaced as a 422 to the admin.
    """
    if custom_end_date is not None:
        return custom_end_date

    if duration_days is None:
        raise ValueError(
            "This plan has no fixed duration (Special Personal Training). "
            "Please provide a custom_end_date in the approval request body."
        )

    # Base date: extend from existing end_date if still active, else from today
    base = (
        current_end_date
        if (current_end_date is not None and current_end_date > approval_date)
        else approval_date
    )
    return base + timedelta(days=duration_days)


# ── Public Service Functions ───────────────────────────────────────────────

async def submit_payment(
    db: AsyncSession,
    requesting_user: User,
    plan_id: uuid.UUID,
) -> PaymentOut:
    """
    Member submits a payment declaration.

    Guards:
      1. Member cannot have two PENDING_APPROVAL requests simultaneously.
         (Application-level check + DB partial index as backstop.)
      2. The selected plan must exist and be active.

    The plan's current price is snapshotted into payment_requests.amount
    so the record reflects the price at the time of submission.
    """

    # Guard 1: No duplicate pending requests
    existing_pending = await payment_repo.get_pending_by_user(
        db, requesting_user.id
    )
    if existing_pending is not None:
        raise PendingPaymentExistsError()

    # Guard 2: Plan must exist and be active
    plan_result = await db.execute(
        select(GymPlan).where(
            GymPlan.id == plan_id,
            GymPlan.is_active == True,  # noqa: E712
        )
    )
    plan = plan_result.scalar_one_or_none()
    if plan is None:
        raise ResourceNotFoundError("Gym plan")

    # Create the payment request (amount snapshotted from plan.price)
    pr = await payment_repo.create_payment_request(
        db,
        user_id=requesting_user.id,
        plan_id=plan_id,
        amount=plan.price,
    )

    # Build response — fetch profile for member_id and full_name
    profile_row = await member_repo.get_member_by_user_id(db, requesting_user.id)

    return PaymentOut(
        id=pr.id,
        member_id=requesting_user.member_id or "",
        full_name=profile_row.full_name if profile_row else "—",
        plan_name=plan.name,
        amount=pr.amount,
        status=pr.status,
        rejection_reason=None,
        submitted_at=pr.created_at,
        reviewed_at=None,
        reviewed_by_name=None,
        membership_start_date=profile_row.membership_start_date if profile_row else None,
        membership_end_date=profile_row.membership_end_date if profile_row else None,
    )


async def get_pending_requests(db: AsyncSession) -> PendingPaymentsResponse:
    """
    Fetch all PENDING_APPROVAL requests for the admin queue.
    Ordered oldest-first (FIFO) to ensure fairness.
    """
    rows = await payment_repo.get_all_pending_requests(db)
    payment_outs = [_row_to_payment_out(row) for row in rows]
    return PendingPaymentsResponse(requests=payment_outs, total=len(payment_outs))


async def approve_payment(
    db: AsyncSession,
    payment_id: uuid.UUID,
    admin_user: User,
    payload: ApprovalRequest,
) -> PaymentOut:
    """
    Admin approves a payment request.

    Four-step atomic operation (all within the same session transaction):

    Step 1 — Validate the request is PENDING_APPROVAL.
    Step 2 — Calculate the new membership expiry date.
    Step 3 — Update payment_requests: status=APPROVED, reviewed_by, reviewed_at, month_bucket.
    Step 4 — Update members_profile: status=ACTIVE, start_date=today, end_date=calculated.
    Step 5 — Insert into revenue_logs (immutable audit entry).

    Transaction guarantee:
      All 5 steps use the same AsyncSession. get_db() commits the session
      after this function returns successfully. If an exception occurs at
      any step, get_db() rolls back the entire session — no partial state.

    Raises:
      ResourceNotFoundError — payment_id not found.
      ValueError            — Special Training plan approved without custom_end_date.
      BusinessError (400)   — Request is not in PENDING_APPROVAL state.
    """
    from fastapi import HTTPException, status as http_status

    # ── Step 1: Validate request exists and is PENDING ─────────────────────
    row = await payment_repo.get_by_id(db, payment_id)
    if row is None:
        raise ResourceNotFoundError("Payment request")

    if row.status != "PENDING_APPROVAL":
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=(
                f"Cannot approve — request is already {row.status}. "
                f"Only PENDING_APPROVAL requests can be approved."
            ),
        )

    # ── Step 2: Fetch plan details and calculate expiry date ───────────────
    plan_result = await db.execute(
        select(GymPlan).where(GymPlan.id == row.plan_id)
    )
    plan = plan_result.scalar_one_or_none()
    if plan is None:
        raise ResourceNotFoundError("Gym plan linked to payment request")

    today = date.today()

    try:
        expiry_date = _calculate_expiry_date(
            current_end_date=row.membership_end_date,
            duration_days=plan.duration_days,
            custom_end_date=payload.custom_end_date,
            approval_date=today,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(exc),
        )

    month_bucket = _compute_month_bucket(today)

    # ── Step 3: Mark payment request as APPROVED ───────────────────────────
    await payment_repo.update_payment_status(
        db,
        payment_id=payment_id,
        status="APPROVED",
        reviewed_by=admin_user.id,
        month_bucket=month_bucket,
    )

    # ── Step 4: Activate membership in members_profile ────────────────────
    await member_repo.activate_membership(
        db,
        user_id=row.user_id,
        start_date=today,
        end_date=expiry_date,
    )

    # ── Step 5: Create revenue log entry ───────────────────────────────────
    await payment_repo.create_revenue_log(
        db,
        payment_request_id=payment_id,
        user_id=row.user_id,
        plan_id=row.plan_id,
        amount=row.amount,
        month_bucket=month_bucket,
    )

    # ── Return updated payment record ──────────────────────────────────────
    # Re-fetch to get accurate reviewed_at / month_bucket
    updated_row = await payment_repo.get_by_id(db, payment_id)
    return _row_to_payment_out(updated_row)  # type: ignore[arg-type]


async def reject_payment(
    db: AsyncSession,
    payment_id: uuid.UUID,
    admin_user: User,
    payload: RejectRequest,
) -> PaymentOut:
    """
    Admin rejects a payment request.

    Simpler than approval — only updates payment_requests.status to REJECTED
    with a mandatory rejection_reason. The member's membership_status is NOT
    changed — they remain PENDING until a successful approval.

    Raises:
      ResourceNotFoundError — payment_id not found.
      HTTP 409              — Request is not in PENDING_APPROVAL state.
    """
    from fastapi import HTTPException, status as http_status

    row = await payment_repo.get_by_id(db, payment_id)
    if row is None:
        raise ResourceNotFoundError("Payment request")

    if row.status != "PENDING_APPROVAL":
        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=f"Cannot reject — request is already {row.status}.",
        )

    await payment_repo.update_payment_status(
        db,
        payment_id=payment_id,
        status="REJECTED",
        reviewed_by=admin_user.id,
        rejection_reason=payload.rejection_reason,
    )

    updated_row = await payment_repo.get_by_id(db, payment_id)
    return _row_to_payment_out(updated_row)  # type: ignore[arg-type]
