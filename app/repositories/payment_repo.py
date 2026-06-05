"""
app/repositories/payment_repo.py
──────────────────────────────────
Data Access Object for the `payment_requests` and `revenue_logs` tables.

All functions accept an AsyncSession. No business logic — only queries.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional

from sqlalchemy import and_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.gym_plan import GymPlan
from app.models.member_profile import MemberProfile
from app.models.payment_request import PaymentRequest
from app.models.revenue_log import RevenueLog
from app.models.user import User


# ── Column projection for payment list queries ─────────────────────────────
_PAYMENT_COLUMNS = (
    PaymentRequest.id,
    PaymentRequest.user_id,
    PaymentRequest.plan_id,
    PaymentRequest.amount,
    PaymentRequest.status,
    PaymentRequest.rejection_reason,
    PaymentRequest.reviewed_by,
    PaymentRequest.reviewed_at,
    PaymentRequest.month_bucket,
    PaymentRequest.created_at.label("submitted_at"),
    User.member_id,
    MemberProfile.full_name,
    GymPlan.name.label("plan_name"),
    MemberProfile.membership_start_date,
    MemberProfile.membership_end_date,
)


def _base_payment_query():
    """
    Base SELECT with JOINs across payment_requests → users → members_profile → gym_plans.
    Used for both the admin pending list and individual lookup.
    """
    return (
        select(*_PAYMENT_COLUMNS)
        .join(User, User.id == PaymentRequest.user_id)
        .join(MemberProfile, MemberProfile.user_id == PaymentRequest.user_id)
        .join(GymPlan, GymPlan.id == PaymentRequest.plan_id)
    )


# ── Create ─────────────────────────────────────────────────────────────────

async def create_payment_request(
    db: AsyncSession,
    user_id: uuid.UUID,
    plan_id: uuid.UUID,
    amount: Decimal,
) -> PaymentRequest:
    """
    Insert a new PENDING_APPROVAL payment request.

    The amount is passed in by the caller (payment_service) after looking up
    the gym_plan.price — it's snapshotted here, not computed from plan_id,
    because we want to capture the price at submission time.

    The DB partial unique index on (user_id WHERE status='PENDING_APPROVAL')
    provides the final safety net against duplicate concurrent submissions,
    but the service layer performs an application-level check first for a
    cleaner error message.
    """
    pr = PaymentRequest(
        user_id=user_id,
        plan_id=plan_id,
        amount=amount,
        status="PENDING_APPROVAL",
    )
    db.add(pr)
    await db.flush()
    await db.refresh(pr)
    return pr


# ── Read ───────────────────────────────────────────────────────────────────

async def get_by_id(
    db: AsyncSession,
    payment_id: uuid.UUID,
) -> Optional[object]:
    """
    Fetch a single payment request with full profile join.
    Returns None if not found.
    """
    query = _base_payment_query().where(PaymentRequest.id == payment_id)
    result = await db.execute(query)
    return result.one_or_none()


async def get_pending_by_user(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> Optional[PaymentRequest]:
    """
    Check if a user already has a PENDING_APPROVAL request.
    Returns the raw ORM object (not joined Row) for status checking.
    """
    result = await db.execute(
        select(PaymentRequest).where(
            PaymentRequest.user_id == user_id,
            PaymentRequest.status == "PENDING_APPROVAL",
        )
    )
    return result.scalar_one_or_none()


async def get_all_pending_requests(db: AsyncSession) -> list:
    """
    Fetch all PENDING_APPROVAL requests for the admin approval dashboard.
    Ordered by submission date — oldest first (FIFO approval queue).
    """
    query = (
        _base_payment_query()
        .where(PaymentRequest.status == "PENDING_APPROVAL")
        .order_by(PaymentRequest.created_at.asc())
    )
    result = await db.execute(query)
    return result.all()


async def get_all_by_user(
    db: AsyncSession,
    user_id: uuid.UUID,
) -> list:
    """
    Fetch full payment history for a single member (all statuses).
    Used for the member's payment history view.
    """
    query = (
        _base_payment_query()
        .where(PaymentRequest.user_id == user_id)
        .order_by(PaymentRequest.created_at.desc())
    )
    result = await db.execute(query)
    return result.all()


# ── Update ─────────────────────────────────────────────────────────────────

async def update_payment_status(
    db: AsyncSession,
    payment_id: uuid.UUID,
    status: str,
    reviewed_by: uuid.UUID,
    rejection_reason: Optional[str] = None,
    month_bucket: Optional[str] = None,
) -> None:
    """
    Atomically update a payment request's status and review metadata.

    Args:
        payment_id       — the request being reviewed
        status           — 'APPROVED' or 'REJECTED'
        reviewed_by      — UUID of the admin making the decision
        rejection_reason — stored only for REJECTED requests
        month_bucket     — 'YYYY-MM' string, stored only for APPROVED requests

    This single UPDATE statement is used for BOTH approve and reject paths
    to avoid duplicating update logic. The caller provides only the relevant
    optional fields for the chosen action.
    """
    values: dict = {
        "status": status,
        "reviewed_by": reviewed_by,
        "reviewed_at": datetime.now(timezone.utc),
    }
    if rejection_reason is not None:
        values["rejection_reason"] = rejection_reason
    if month_bucket is not None:
        values["month_bucket"] = month_bucket

    await db.execute(
        update(PaymentRequest)
        .where(PaymentRequest.id == payment_id)
        .values(**values)
    )


# ── Revenue Log ────────────────────────────────────────────────────────────

async def create_revenue_log(
    db: AsyncSession,
    payment_request_id: uuid.UUID,
    user_id: uuid.UUID,
    plan_id: uuid.UUID,
    amount: Decimal,
    month_bucket: str,
) -> RevenueLog:
    """
    Insert an immutable revenue log entry after a payment is approved.

    Called exclusively by payment_service.approve_payment(), always within
    the same session transaction. If the transaction rolls back (e.g., the
    membership update fails), this INSERT is also rolled back — ensuring
    no phantom revenue entries exist without a corresponding active membership.
    """
    log = RevenueLog(
        payment_request_id=payment_request_id,
        user_id=user_id,
        plan_id=plan_id,
        amount=amount,
        month_bucket=month_bucket,
    )
    db.add(log)
    await db.flush()
    return log
