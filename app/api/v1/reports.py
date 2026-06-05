"""
app/api/v1/reports.py
──────────────────────
FastAPI router for the Reporting & Exports module.
"""

from datetime import date
from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_admin
from app.models.user import User
from app.schemas.reports import ReportFilterRequest
from app.services import report_service
from app.utils import export_helpers

router = APIRouter(prefix="/reports", tags=["Reports"])


@router.get("/attendance")
async def get_attendance_report(
    filters: ReportFilterRequest = Depends(),
    export_format: str = Query(
        "csv",
        description="Format to export: 'csv' or 'excel'",
        pattern="^(csv|excel)$"
    ),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """
    Export attendance logs as a CSV or Excel spreadsheet.
    Admin authorization required.
    
    Accepts date ranges, member ID, and plan filters (paginated-unaware).
    """
    data = await report_service.get_attendance_report(db, filters)
    filename_date = date.today().isoformat()

    if export_format == "csv":
        generator = export_helpers.generate_csv(data)
        return StreamingResponse(
            generator,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=attendance_report_{filename_date}.csv"
            }
        )
    else:
        excel_buffer = export_helpers.generate_excel(data)
        return StreamingResponse(
            excel_buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=attendance_report_{filename_date}.xlsx"
            }
        )


@router.get("/revenue")
async def get_revenue_report(
    month: str = Query(
        ...,
        description="Month bucket in YYYY-MM format (e.g. '2026-06')",
        pattern=r"^\d{4}-\d{2}$"
    ),
    export_format: str = Query(
        "csv",
        description="Format to export: 'csv' or 'excel'",
        pattern="^(csv|excel)$"
    ),
    db: AsyncSession = Depends(get_db),
    admin_user: User = Depends(require_admin),
):
    """
    Export financial / revenue logs for a specific month as a CSV or Excel spreadsheet.
    Admin authorization required.
    
    Expects a month in YYYY-MM format.
    """
    data = await report_service.get_financial_report(db, month)

    if export_format == "csv":
        generator = export_helpers.generate_csv(data)
        return StreamingResponse(
            generator,
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=revenue_report_{month}.csv"
            }
        )
    else:
        excel_buffer = export_helpers.generate_excel(data)
        return StreamingResponse(
            excel_buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": f"attachment; filename=revenue_report_{month}.xlsx"
            }
        )
