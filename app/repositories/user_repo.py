"""
app/repositories/user_repo.py
──────────────────────────────
Data Access Object for the `users` table.

Rules enforced here:
  - No business logic. Only DB queries.
  - All functions accept an AsyncSession and return ORM objects or None.
  - Callers (services) handle None cases and raise appropriate exceptions.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
    """Fetch an active user by their internal UUID."""
    result = await db.execute(
        select(User).where(User.id == user_id, User.is_active == True)  # noqa: E712
    )
    return result.scalar_one_or_none()


async def get_by_member_id(db: AsyncSession, member_id: str) -> Optional[User]:
    """
    Fetch a user by their human-readable member ID (e.g., "S2T101").
    Used as the primary lookup for member login.
    Does NOT filter by is_active — caller must check lock/active status.
    """
    result = await db.execute(
        select(User).where(User.member_id == member_id)
    )
    return result.scalar_one_or_none()


async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
    """
    Fetch a user by email address.
    Used for: admin login, duplicate-email check during registration.
    """
    result = await db.execute(
        select(User).where(User.email == email)
    )
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user: User) -> User:
    """
    Persist a new User to the DB.

    IMPORTANT — flush vs commit:
      db.add(user)       → stages the object in the session (no DB write yet)
      await db.flush()   → sends INSERT to DB within the current transaction
                           This fires the BEFORE INSERT trigger that assigns
                           member_id (e.g., "S2T101") via nextval(sequence).
      await db.refresh() → re-reads the row from DB into the ORM object,
                           populating trigger-assigned fields like member_id.

    The transaction is NOT committed here. The caller (service) or the
    get_db() dependency will commit the full transaction.
    """
    db.add(user)
    await db.flush()    # Trigger fires → member_id assigned in DB
    await db.refresh(user)  # Pull trigger-assigned member_id into ORM object
    return user


async def increment_failed_attempts(db: AsyncSession, user_id: uuid.UUID) -> None:
    """
    Atomically increment failed_login_attempts by 1.
    Uses SQL-level increment (not ORM read-modify-write) to be concurrency-safe.
    """
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(failed_login_attempts=User.failed_login_attempts + 1)
    )


async def lock_account(
    db: AsyncSession,
    user_id: uuid.UUID,
    locked_until: datetime,
) -> None:
    """
    Lock a user account until the given UTC timestamp.
    Also increments failed_login_attempts for audit trail.
    Called after MAX_LOGIN_ATTEMPTS consecutive failures.
    """
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(
            locked_until=locked_until,
            failed_login_attempts=User.failed_login_attempts + 1,
        )
    )


async def reset_login_attempts(db: AsyncSession, user_id: uuid.UUID) -> None:
    """
    Clear failed_login_attempts and remove any account lock.
    Called on every successful password verification.
    """
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(failed_login_attempts=0, locked_until=None)
    )


async def deactivate_user(db: AsyncSession, user_id: uuid.UUID) -> None:
    """
    Soft-delete a user by setting is_active=False.
    Called by admin — does not physically delete the row.
    """
    await db.execute(
        update(User)
        .where(User.id == user_id)
        .values(is_active=False)
    )
