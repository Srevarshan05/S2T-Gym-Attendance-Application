"""
app/api/v1/router.py
─────────────────────
Central v1 API router. Includes all sub-routers.
Add new routers here as each phase is implemented.
"""

from fastapi import APIRouter

from app.api.v1 import auth, members, payments, attendance, dashboard, reports, plans

api_router = APIRouter()

# Phase 4: Authentication
api_router.include_router(auth.router)

# Phase 5: Members
api_router.include_router(members.router)

# Phase 6: Payments
api_router.include_router(payments.router)

# Phase 7: Attendance
api_router.include_router(attendance.router)

# Phase 8: Dashboard
api_router.include_router(dashboard.router)

# Phase 9: Reports
api_router.include_router(reports.router)

# Phase 10: Public Plans (no auth required — for registration form)
api_router.include_router(plans.router)
