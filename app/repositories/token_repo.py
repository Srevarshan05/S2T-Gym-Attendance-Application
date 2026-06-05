"""
app/repositories/token_repo.py
────────────────────────────────
Data Access Object for the `refresh_tokens` table.

All lookups use token_hash (SHA-256 digest) — the raw token is
never passed into this layer.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import update
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.refresh_token import RefreshToken


async def create_token(db: AsyncSession, token: RefreshToken) -> RefreshToken:
    """
    Persist a new RefreshToken record.
    Uses flush+refresh so the caller gets a fully-populated ORM object
    (including server-assigned id and created_at).
    """
    db.add(token)
    await db.flush()
    await db.refresh(token)
    return token


async def get_active_by_hash(
    db: AsyncSession,
    token_hash: str,
) -> Optional[RefreshToken]:
    """
    Fetch a refresh token by its SHA-256 hash.

    Returns None if:
      - Hash not found in DB.
      - Token has been revoked (is_revoked=True).
      - Token has expired (expires_at <= now).

    The three-condition WHERE clause ensures that a single query
    enforces all three validity checks atomically.
    """
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.token_hash == token_hash,
            RefreshToken.is_revoked == False,  # noqa: E712
            RefreshToken.expires_at > datetime.now(timezone.utc),
        )
    )
    return result.scalar_one_or_none()


async def revoke_token(db: AsyncSession, token_id: uuid.UUID) -> None:
    """
    Mark a single refresh token as revoked.
    Used during token rotation — the old token is revoked before the new one is issued.
    The row is NOT deleted — kept for audit trail.
    """
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.id == token_id)
        .values(is_revoked=True)
    )


async def revoke_all_user_tokens(db: AsyncSession, user_id: uuid.UUID) -> None:
    """
    Revoke ALL active refresh tokens for a user.

    Used for:
      - Admin force-logout of a member.
      - Account deactivation.
      - "Logout from all devices" feature (future).
    """
    await db.execute(
        update(RefreshToken)
        .where(RefreshToken.user_id == user_id, RefreshToken.is_revoked == False)  # noqa: E712
        .values(is_revoked=True)
    )
