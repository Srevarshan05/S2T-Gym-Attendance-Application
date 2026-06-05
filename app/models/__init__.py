"""
app/models/__init__.py
───────────────────────
Import ALL ORM models here.

This file serves two critical purposes:
1. Alembic autogenerate: When env.py does `import app.models`, all
   model classes are registered with Base.metadata, so Alembic can
   detect schema changes and generate accurate migrations.

2. Relationship resolution: SQLAlchemy resolves string-based
   relationship targets (e.g., relationship("MemberProfile")) by
   scanning all classes registered with the same Base. Importing
   everything here ensures all classes are registered before any
   relationship is resolved.

Add every new model file to this list as new phases are implemented.
"""

from app.models.attendance_log import AttendanceLog
from app.models.gym_plan import GymPlan
from app.models.member_profile import MemberProfile
from app.models.payment_request import PaymentRequest
from app.models.refresh_token import RefreshToken
from app.models.revenue_log import RevenueLog
from app.models.user import User

__all__ = [
    "AttendanceLog",
    "User",
    "MemberProfile",
    "GymPlan",
    "RefreshToken",
    "PaymentRequest",
    "RevenueLog",
]
