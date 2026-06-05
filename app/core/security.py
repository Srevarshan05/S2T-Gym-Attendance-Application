"""
app/core/security.py
─────────────────────
Pure cryptographic utility functions.
No DB access. No HTTP. No side effects.
Independently unit-testable with zero fixtures.

Note on bcrypt library:
  We use the `bcrypt` library directly (not passlib) because passlib is
  unmaintained and incompatible with bcrypt >= 4.1 on Python 3.13.
  Direct bcrypt usage is simpler and fully supported.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

# bcrypt work factor — 12 rounds ≈ 300ms per hash on modern hardware.
# Slow enough to resist brute-force; fast enough to not degrade UX.
_BCRYPT_ROUNDS = 12


# ── Password Utilities ─────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password using bcrypt (rounds=12).
    Returns a bcrypt hash string safe to store in the DB.
    """
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return bcrypt.hashpw(plain_password.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Constant-time comparison of plain password against bcrypt hash.
    bcrypt.checkpw() uses a constant-time comparison internally.
    """
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


# ── JWT Utilities ──────────────────────────────────────────────────────────

def create_access_token(
    user_id: str,
    role: str,
    member_id: str | None = None,
) -> str:
    """
    Create a signed HS256 JWT access token.

    Payload claims:
        sub        — user UUID (subject)
        role       — "admin" | "member"
        member_id  — "S2T101" | None (None for admin accounts)
        exp        — expiry timestamp (UTC)
        iat        — issued-at timestamp (UTC)

    TTL: settings.JWT_ACCESS_TOKEN_TTL (default 15 minutes).
    """
    now = datetime.now(timezone.utc)
    expire = now + timedelta(seconds=settings.JWT_ACCESS_TOKEN_TTL)

    payload: dict = {
        "sub": str(user_id),
        "role": role,
        "member_id": member_id,
        "exp": expire,
        "iat": now,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> dict:
    """
    Decode and validate a JWT access token.

    Raises:
        jose.JWTError — if signature is invalid, token is expired,
                        or any claim is malformed.

    The caller (dependencies.py) is responsible for catching JWTError
    and converting it to HTTP 401.
    """
    return jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )


# ── Refresh Token Utilities ────────────────────────────────────────────────

def generate_refresh_token() -> str:
    """
    Generate a cryptographically secure random refresh token.

    Uses secrets.token_urlsafe(48) → 64-character URL-safe base64 string.
    This is the RAW value returned to the client in the response body.
    The DB stores only its SHA-256 hash (see hash_refresh_token).
    """
    return secrets.token_urlsafe(48)


def hash_refresh_token(raw_token: str) -> str:
    """
    SHA-256 hex digest of the raw refresh token.

    Only the hash is persisted in the `refresh_tokens` table.
    Even if the table is compromised, the attacker cannot use hashes
    directly as tokens — they would need to reverse SHA-256 first.
    """
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
