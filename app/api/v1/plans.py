"""
app/api/v1/plans.py
────────────────────
Public endpoint to list available gym plans.
No authentication required — needed for the registration form plan selector.
"""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Annotated, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_db
from app.models.gym_plan import GymPlan

router = APIRouter(prefix="/plans", tags=["Plans"])


class PlanOut(BaseModel):
    id: uuid.UUID
    name: str
    price: Decimal
    duration_days: Optional[int]
    description: Optional[str]

    model_config = {"from_attributes": True}


class PlansListResponse(BaseModel):
    plans: list[PlanOut]
    total: int


@router.get(
    "",
    response_model=PlansListResponse,
    summary="List all active gym plans (public)",
    description=(
        "Returns all active gym plans. No authentication required. "
        "Used by the registration form to display plan options."
    ),
)
async def list_plans(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PlansListResponse:
    result = await db.execute(
        select(GymPlan)
        .where(GymPlan.is_active == True)  # noqa: E712
        .order_by(GymPlan.price)
    )
    plans = result.scalars().all()
    return PlansListResponse(plans=list(plans), total=len(plans))
