"""
app/api/v1/dashboard.py
────────────────────────
FastAPI router for the Admin Dashboard module.

Endpoints:
  GET /dashboard/overview    Admin only — all KPIs in one response

Design: Maximum thin router.
  The endpoint does nothing except:
    1. Enforce admin RBAC (require_admin).
    2. Call dashboard_service.get_overview().
    3. Return the result.

  All SQL, aggregation, and business logic live exclusively in
  dashboard_service.py — easy to unit-test without the HTTP layer.

Caching note (future):
  This endpoint is a natural candidate for short-lived server-side caching
  (e.g., 30-second TTL with fastapi-cache2 + Redis). For the current
  single-gym MVP scale, direct CTE query is fast enough without caching.
  Adding a `@cache(expire=30)` decorator here would be the upgrade path.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db, require_admin
from app.models.user import User
from app.schemas.dashboard import DashboardOverviewResponse
from app.services import dashboard_service

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get(
    "/overview",
    response_model=DashboardOverviewResponse,
    status_code=status.HTTP_200_OK,
    summary="Admin dashboard overview (Admin only)",
    description=(
        "Returns all KPIs for the Admin Dashboard in a single response. "
        "Data is fetched via a single PostgreSQL CTE — one DB round-trip. "
        "\n\n"
        "**Metrics included:**\n"
        "- Membership breakdown: total / active / expired / pending / suspended\n"
        "- Today's attendance: FN count, AN count, unique members (IST date)\n"
        "- Pending payment approvals count\n"
        "- Current month's total revenue (INR)\n"
        "- Expiring soon: ACTIVE members expiring within 7 days, sorted by urgency\n"
        "\n\n"
        "All counts default to 0 and `expiring_soon` defaults to `[]` "
        "for an empty or fresh database — the frontend never receives null values."
    ),
)
async def get_overview(
    db: Annotated[AsyncSession, Depends(get_db)],
    _: Annotated[User, Depends(require_admin)],
) -> DashboardOverviewResponse:
    return await dashboard_service.get_overview(db)
