"""
app/schemas/reports.py
───────────────────────
Pydantic v2 schemas for the Reporting & Exports module.
"""

from datetime import date
from typing import Optional
from pydantic import BaseModel, Field


class ReportFilterRequest(BaseModel):
    """
    Schema for date ranges and member/plan filters.
    Used to validate query parameters for attendance and revenue reports.
    """
    start_date: Optional[date] = Field(
        default=None,
        description="Filter logs from this start date (inclusive)."
    )
    end_date: Optional[date] = Field(
        default=None,
        description="Filter logs up to this end date (inclusive)."
    )
    member_id: Optional[str] = Field(
        default=None,
        description="Filter by member's sequential ID (e.g., 'S2T101')."
    )
    plan_name: Optional[str] = Field(
        default=None,
        description="Filter by gym plan name (e.g., 'Monthly')."
    )
