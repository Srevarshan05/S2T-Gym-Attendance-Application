"""
scripts/seed_admin.py
----------------------
One-time script to create the admin user account in Supabase.
Run this ONCE after applying alembic migrations:
    .venv\Scripts\python.exe scripts/seed_admin.py

Safe to re-run -- it checks for existing admin before inserting.
"""

from __future__ import annotations

import asyncio
import sys
import os

# Make app importable from root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession

from app.core.config import settings
from app.core.security import hash_password
from app.models.user import User
from app.models.gym_plan import GymPlan


async def seed():
    engine = create_async_engine(
        settings.DATABASE_URL,
        connect_args={"statement_cache_size": 0},
    )
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as db:
        # Check / Create Admin
        existing_admin = await db.execute(
            select(User).where(User.email == settings.ADMIN_EMAIL)
        )
        admin = existing_admin.scalar_one_or_none()

        if admin:
            print(f"[OK] Admin already exists: {settings.ADMIN_EMAIL}")
        else:
            admin = User(
                email=settings.ADMIN_EMAIL,
                password_hash=hash_password(settings.ADMIN_PASSWORD),
                role="admin",
                is_active=True,
                member_id=None,
            )
            db.add(admin)
            await db.commit()
            print(f"[OK] Admin created: {settings.ADMIN_EMAIL}")

        # Check / Create Gym Plans
        existing_plans = await db.execute(select(GymPlan))
        plans = existing_plans.scalars().all()

        if plans:
            print(f"[OK] Gym plans already seeded ({len(plans)} plans):")
            for p in plans:
                print(f"   {p.id}  |  {p.name}  |  Rs.{p.price}  |  {p.duration_days} days")
        else:
            seed_plans = [
                GymPlan(
                    name="Monthly",
                    price=1500,
                    duration_days=30,
                    description="Standard monthly membership. Includes all gym equipment access.",
                    is_active=True,
                ),
                GymPlan(
                    name="Annually",
                    price=15000,
                    duration_days=365,
                    description="Annual membership with a 17% savings over monthly plan.",
                    is_active=True,
                ),
                GymPlan(
                    name="Special Personal Training",
                    price=5000,
                    duration_days=None,
                    description="Personal training sessions. Duration set manually by admin.",
                    is_active=True,
                ),
            ]
            db.add_all(seed_plans)
            await db.commit()
            print("[OK] Gym plans seeded:")
            for p in seed_plans:
                print(f"   {p.id}  |  {p.name}  |  Rs.{p.price}  |  {p.duration_days} days")

    await engine.dispose()
    print("\n[DONE] Seed complete! You can now log in at the PWA.")
    print(f"   Admin email:    {settings.ADMIN_EMAIL}")
    print(f"   Admin password: {settings.ADMIN_PASSWORD}")


if __name__ == "__main__":
    asyncio.run(seed())
