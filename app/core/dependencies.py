"""
app/core/dependencies.py
─────────────────────────
FastAPI dependency injection hub.

Three core dependencies used across the entire API:
  get_db()           — yields an AsyncSession per request
  get_current_user() — decodes JWT, returns authenticated User ORM object
  require_admin()    — enforces admin role; raises 403 for members
"""

from __future__ import annotations

import uuid
from typing import Annotated, AsyncGenerator

from fastapi import Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.database.connection import AsyncSessionLocal
from app.models.user import User
import app.repositories.user_repo as user_repo

# ── OAuth2 scheme ──────────────────────────────────────────────────────────
# tokenUrl is the endpoint that issues tokens (used by OpenAPI docs only).
# Our login endpoint accepts JSON, not form data, but this scheme still
# correctly extracts the Bearer token from Authorization headers.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


# ── Database Session ───────────────────────────────────────────────────────

async def get_db(request: Request = None) -> AsyncGenerator[AsyncSession, None]:
    """
    Yields an AsyncSession for the duration of a single HTTP request.

    Lifecycle:
      - Session opened on first yield.
      - Commits automatically on clean exit (skipped for GET/HEAD/OPTIONS to save latency).
      - Rolls back automatically on any exception.
      - Session always closed in the finally block.

    Usage in a router:
        db: Annotated[AsyncSession, Depends(get_db)]
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            # Only commit if it's a modifying request (not GET/HEAD/OPTIONS)
            if request is None or request.method not in ("GET", "HEAD", "OPTIONS"):
                await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


# ── Current User ───────────────────────────────────────────────────────────

async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> User:
    """
    Decode the JWT Bearer token and return the authenticated User.

    Raises HTTP 401 if:
      - Token is missing, malformed, or expired.
      - User ID in token doesn't exist in the DB.
      - User account is deactivated (is_active=False).

    The user object returned here is used by require_admin() and by
    any route that needs the current user's identity (e.g., member checkin).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials. Please log in again.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise credentials_exception

    user = await user_repo.get_by_id(db, user_id)
    if user is None or not user.is_active:
        raise credentials_exception

    return user


# ── Admin Guard ────────────────────────────────────────────────────────────

async def require_admin(
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    """
    Enforces that the current authenticated user has the 'admin' role.

    Raises HTTP 403 Forbidden for any non-admin user (i.e., members).

    Usage in a router — one declarative line:
        _: Annotated[User, Depends(require_admin)]

    The underscore convention signals that the user object itself isn't
    needed in the route body — we just need the authorization side-effect.
    To also USE the admin user object, name it:
        admin: Annotated[User, Depends(require_admin)]
    """
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )
    return current_user
