"""
app/services/report_service.py
───────────────────────────────
Business logic layer for reporting and raw query aggregation.
"""

from typing import Any, Dict, List

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models.attendance_log import AttendanceLog
from app.models.gym_plan import GymPlan
from app.models.member_profile import MemberProfile
from app.models.payment_request import PaymentRequest
from app.models.revenue_log import RevenueLog
from app.models.user import User
from app.schemas.reports import ReportFilterRequest


async def get_attendance_report(
    db: AsyncSession, filters: ReportFilterRequest
) -> List[Dict[str, Any]]:
    """
    Fetch detailed attendance logs based on given filters.
    Joins the member profile and gym plan details.
    
    Returns a list of dictionaries ready for export.
    """
    stmt = (
        select(
            AttendanceLog.attendance_date.label("Date"),
            AttendanceLog.session.label("Session"),
            User.member_id.label("Member ID"),
            MemberProfile.full_name.label("Full Name"),
            GymPlan.name.label("Gym Plan"),
            AttendanceLog.created_at.label("Check-in Time")
        )
        .join(User, User.id == AttendanceLog.user_id)
        .join(MemberProfile, MemberProfile.user_id == User.id)
        .join(GymPlan, GymPlan.id == MemberProfile.plan_id)
    )

    # Apply filters dynamically
    if filters.start_date:
        stmt = stmt.where(AttendanceLog.attendance_date >= filters.start_date)
    if filters.end_date:
        stmt = stmt.where(AttendanceLog.attendance_date <= filters.end_date)
    if filters.member_id:
        stmt = stmt.where(User.member_id == filters.member_id.strip())
    if filters.plan_name:
        stmt = stmt.where(GymPlan.name == filters.plan_name.strip())

    # Order chronologically descending
    stmt = stmt.order_by(AttendanceLog.attendance_date.desc(), AttendanceLog.created_at.desc())

    result = await db.execute(stmt)
    
    rows = []
    for row in result.mappings().all():
        row_dict = dict(row)
        if row_dict.get("Check-in Time"):
            dt = row_dict["Check-in Time"]
            row_dict["Check-in Time"] = dt.strftime("%Y-%m-%d %H:%M:%S")
        rows.append(row_dict)
        
    return rows


async def get_financial_report(
    db: AsyncSession, month: str
) -> List[Dict[str, Any]]:
    """
    Fetch a detailed breakdown of all payments approved within the given month bucket (YYYY-MM).
    Joins member profiles, gym plans, payment requests, and the admin reviewer.
    
    Returns a list of dictionaries ready for export.
    """
    AdminUser = aliased(User)

    stmt = (
        select(
            RevenueLog.month_bucket.label("Month Bucket"),
            RevenueLog.created_at.label("Approval Date"),
            User.member_id.label("Member ID"),
            MemberProfile.full_name.label("Member Name"),
            GymPlan.name.label("Gym Plan"),
            RevenueLog.amount.label("Amount (INR)"),
            AdminUser.email.label("Approved By")
        )
        .join(User, User.id == RevenueLog.user_id)
        .join(MemberProfile, MemberProfile.user_id == User.id)
        .join(GymPlan, GymPlan.id == RevenueLog.plan_id)
        .join(PaymentRequest, PaymentRequest.id == RevenueLog.payment_request_id)
        .outerjoin(AdminUser, AdminUser.id == PaymentRequest.reviewed_by)
        .where(RevenueLog.month_bucket == month)
        .order_by(RevenueLog.created_at.desc())
    )

    result = await db.execute(stmt)
    
    rows = []
    for row in result.mappings().all():
        row_dict = dict(row)
        if row_dict.get("Approval Date"):
            dt = row_dict["Approval Date"]
            row_dict["Approval Date"] = dt.strftime("%Y-%m-%d %H:%M:%S")
        # Convert Decimal to float for clean serialization and JSON/Excel writing
        if row_dict.get("Amount (INR)") is not None:
            row_dict["Amount (INR)"] = float(row_dict["Amount (INR)"])
        rows.append(row_dict)
        
    return rows
