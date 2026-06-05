"""
app/services/auth_service.py
─────────────────────────────
Business logic for the Authentication module.

This layer contains ALL decisions and rules. It:
  - Orchestrates repositories (user_repo, token_repo).
  - Enforces business invariants (brute-force lock, active membership check).
  - Manages transactions across multiple tables (User + MemberProfile on register).
  - Raises typed BusinessErrors that propagate to the global exception handler.

It does NOT:
  - Touch HTTP (no Request/Response objects).
  - Execute raw SQL (all DB access goes through repositories).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import (
    AccountLockedError,
    EmailAlreadyRegisteredError,
    InvalidCredentialsError,
    InvalidRefreshTokenError,
    ResourceNotFoundError,
)
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)
from app.models.gym_plan import GymPlan
from app.models.member_profile import MemberProfile
from app.models.refresh_token import RefreshToken
from app.models.user import User
from app.repositories import token_repo, user_repo
from app.schemas.auth import (
    LoginRequest,
    MessageResponse,
    RefreshRequest,
    RegisterRequest,
    RegisterResponse,
    TokenResponse,
    UserOut,
)


# ── Internal Helper ────────────────────────────────────────────────────────

async def _build_user_out(
    db: AsyncSession,
    user: User,
) -> UserOut:
    """
    Construct a UserOut schema from a User ORM object.
    Fetches associated profile and plan in a single joined query.
    Called from login() and refresh_access_token() to build the response payload.
    """
    full_name = None
    membership_status = None
    plan_name = None
    expiry_date = None

    if user.role == "member":
        # Fetch profile and plan name in a single joined query to reduce DB round-trips
        result = await db.execute(
            select(
                MemberProfile.full_name,
                MemberProfile.membership_status,
                MemberProfile.membership_end_date,
                GymPlan.name
            )
            .outerjoin(GymPlan, GymPlan.id == MemberProfile.plan_id)
            .where(MemberProfile.user_id == user.id)
        )
        row = result.first()
        if row:
            full_name, membership_status, expiry_date, plan_name = row

    return UserOut(
        id=user.id,
        member_id=user.member_id,
        email=user.email,
        role=user.role,
        full_name=full_name,
        membership_status=membership_status,
        plan_name=plan_name,
        expiry_date=expiry_date,
    )


async def _issue_token_pair(
    db: AsyncSession,
    user: User,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> tuple[str, str]:
    """
    Generate a new access + refresh token pair and persist the refresh token.

    Returns:
        (access_token_str, raw_refresh_token_str)

    The raw refresh token is returned to the caller (and on to the client).
    Only its SHA-256 hash is stored in the DB.
    """
    # Access token (in-memory JWT, short-lived)
    access_token = create_access_token(
        user_id=str(user.id),
        role=user.role,
        member_id=user.member_id,
    )

    # Refresh token (random string, long-lived, stored as hash)
    raw_refresh = generate_refresh_token()
    refresh_token_obj = RefreshToken(
        user_id=user.id,
        token_hash=hash_refresh_token(raw_refresh),
        expires_at=datetime.now(timezone.utc)
        + timedelta(seconds=settings.JWT_REFRESH_TOKEN_TTL),
        user_agent=user_agent,
        ip_address=ip_address,
    )
    await token_repo.create_token(db, refresh_token_obj)

    return access_token, raw_refresh


# ── Public Service Functions ───────────────────────────────────────────────

async def register_member(
    db: AsyncSession,
    payload: RegisterRequest,
) -> RegisterResponse:
    """
    Register a new gym member.

    Steps:
      1. Verify email is not already registered.
      2. Verify the selected plan exists and is active.
      3. Create User row (member_id = NULL; DB trigger assigns it on flush).
      4. flush() → trigger fires → member_id set (e.g., "S2T101").
      5. refresh() → ORM object updated with trigger-assigned member_id.
      6. Create MemberProfile with status PENDING.
      7. Return RegisterResponse (transaction committed by get_db()).

    Transaction note:
      We do NOT call db.commit() here. The get_db() dependency handles
      commit/rollback for the entire request. This is intentional — if
      step 6 fails after step 3, the User row is also rolled back.
    """

    # Step 1 — Email uniqueness check
    existing_user = await user_repo.get_by_email(db, str(payload.email))
    if existing_user is not None:
        raise EmailAlreadyRegisteredError()

    # Step 2 — Validate plan
    plan_result = await db.execute(
        select(GymPlan).where(
            GymPlan.id == payload.plan_id,
            GymPlan.is_active == True,  # noqa: E712
        )
    )
    plan = plan_result.scalar_one_or_none()
    if plan is None:
        raise ResourceNotFoundError("Gym plan")

    # Step 3 — Create User (member_id is NULL at this point)
    new_user = User(
        email=str(payload.email),
        password_hash=hash_password(payload.password),
        role="member",
        is_active=True,
    )

    # Steps 4 & 5 — flush triggers the BEFORE INSERT trigger; refresh pulls member_id back
    created_user = await user_repo.create_user(db, new_user)

    # Step 6 — Create MemberProfile linked to the new user
    new_profile = MemberProfile(
        user_id=created_user.id,
        plan_id=payload.plan_id,
        full_name=payload.full_name,
        age=payload.age,
        gender=payload.gender,
        phone=payload.phone,
        address=payload.address,
        membership_status="PENDING",
    )
    db.add(new_profile)
    await db.flush()

    return RegisterResponse(
        member_id=created_user.member_id,  # type: ignore[arg-type]
        full_name=payload.full_name,
        plan_name=plan.name,
        message=(
            f"Registration successful! Your Member ID is {created_user.member_id}. "
            f"Please login and inform the front desk to process your payment."
        ),
    )


async def login(
    db: AsyncSession,
    payload: LoginRequest,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> TokenResponse:
    """
    Authenticate a member or admin and issue a token pair.

    Brute-force protection:
      - If account is locked (locked_until > now): raise AccountLockedError (423).
      - Wrong password: increment failed_login_attempts.
      - After MAX_LOGIN_ATTEMPTS failures: lock account for ACCOUNT_LOCK_MINUTES.
      - Correct password: reset failed_login_attempts to 0.

    Security note:
      We return the SAME error message for "member_id not found" and
      "wrong password" to prevent member_id enumeration attacks.
    """

    # Lookup user (member uses member_id; admin also uses member_id field but
    # we allow lookup by email too for admin convenience)
    user = await user_repo.get_by_member_id(db, payload.member_id)

    # Fallback: allow admins to log in using email in the member_id field
    if user is None:
        user = await user_repo.get_by_email(db, payload.member_id)

    if user is None:
        raise InvalidCredentialsError()

    # Check account lock
    if user.locked_until and user.locked_until > datetime.now(timezone.utc):
        locked_until_str = user.locked_until.strftime("%Y-%m-%d %H:%M")
        raise AccountLockedError(locked_until_str)

    # Verify password
    if not verify_password(payload.password, user.password_hash):
        new_attempts = user.failed_login_attempts + 1
        if new_attempts >= settings.MAX_LOGIN_ATTEMPTS:
            locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=settings.ACCOUNT_LOCK_MINUTES
            )
            await user_repo.lock_account(db, user.id, locked_until)
        else:
            await user_repo.increment_failed_attempts(db, user.id)
        raise InvalidCredentialsError()

    # Successful login — reset brute-force counters
    await user_repo.reset_login_attempts(db, user.id)

    # Issue token pair
    access_token, raw_refresh = await _issue_token_pair(
        db, user, user_agent=user_agent, ip_address=ip_address
    )

    # Build user-facing response payload
    user_out = await _build_user_out(db, user)

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_TTL,
        user=user_out,
    )


async def refresh_access_token(
    db: AsyncSession,
    payload: RefreshRequest,
) -> TokenResponse:
    """
    Validate an existing refresh token, revoke it, and issue a new pair.

    Rolling rotation strategy:
      - Old token is revoked BEFORE the new one is created.
      - If an attacker intercepts the new token but the legit user already
        rotated again, the attacker's token is already revoked.
      - Both old and new records are kept in DB (is_revoked=True) for audit.
    """

    token_hash = hash_refresh_token(payload.refresh_token)
    stored_token = await token_repo.get_active_by_hash(db, token_hash)

    if stored_token is None:
        raise InvalidRefreshTokenError()

    # Revoke old token immediately (rolling rotation)
    await token_repo.revoke_token(db, stored_token.id)

    # Fetch user
    user = await user_repo.get_by_id(db, stored_token.user_id)
    if user is None or not user.is_active:
        raise InvalidRefreshTokenError()

    # Issue new token pair (preserves device context from original login)
    access_token, raw_refresh = await _issue_token_pair(
        db,
        user,
        user_agent=stored_token.user_agent,
        ip_address=stored_token.ip_address,
    )

    user_out = await _build_user_out(db, user)

    return TokenResponse(
        access_token=access_token,
        refresh_token=raw_refresh,
        token_type="bearer",
        expires_in=settings.JWT_ACCESS_TOKEN_TTL,
        user=user_out,
    )


async def logout(
    db: AsyncSession,
    payload: RefreshRequest,
) -> MessageResponse:
    """
    Revoke the provided refresh token server-side.

    Access tokens remain valid until their 15-minute expiry.
    This is an acceptable tradeoff for this scale — the window is short.
    For immediate access token invalidation, a Redis blocklist would be needed.

    Security: We return HTTP 200 regardless of whether the token exists.
    This prevents an attacker from probing which tokens are currently valid.
    """

    token_hash = hash_refresh_token(payload.refresh_token)
    stored_token = await token_repo.get_active_by_hash(db, token_hash)

    if stored_token is not None:
        await token_repo.revoke_token(db, stored_token.id)

    return MessageResponse(message="Logged out successfully.")
