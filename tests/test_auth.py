"""
tests/test_auth.py
───────────────────
Unit tests for the Authentication module.

Security unit tests run with zero fixtures (no DB, no HTTP).
Schema validation tests use Pydantic directly.
Integration tests (requiring DB) are stubbed out.

Run with:  pytest tests/test_auth.py -v
"""

from __future__ import annotations

import os

import pytest

# ── Provide minimum env vars so settings can be instantiated ──────────────
# This runs before any app import to prevent ValidationError on settings load.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://test:test@localhost/test")
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key-that-is-at-least-32-chars-long")

from app.core.security import (  # noqa: E402
    create_access_token,
    decode_access_token,
    generate_refresh_token,
    hash_password,
    hash_refresh_token,
    verify_password,
)


# ── Security Unit Tests (no DB, no HTTP) ───────────────────────────────────

class TestSecurityUtils:
    def test_password_hash_and_verify(self):
        plain = "MyPass@123"
        hashed = hash_password(plain)
        assert hashed != plain
        assert hashed.startswith("$2b$")   # bcrypt prefix
        assert verify_password(plain, hashed) is True

    def test_wrong_password_fails(self):
        hashed = hash_password("Correct@123")
        assert verify_password("Wrong@123", hashed) is False

    def test_access_token_roundtrip(self):
        token = create_access_token(
            user_id="some-uuid",
            role="member",
            member_id="S2T101",
        )
        payload = decode_access_token(token)
        assert payload["sub"] == "some-uuid"
        assert payload["role"] == "member"
        assert payload["member_id"] == "S2T101"

    def test_refresh_token_hash_is_deterministic(self):
        raw = generate_refresh_token()
        assert hash_refresh_token(raw) == hash_refresh_token(raw)

    def test_refresh_token_hash_not_reversible(self):
        raw = generate_refresh_token()
        hashed = hash_refresh_token(raw)
        assert raw not in hashed
        assert len(hashed) == 64   # SHA-256 hex digest is always 64 chars


# ── Schema Validation Tests ────────────────────────────────────────────────

class TestRegisterRequest:
    def test_valid_payload(self):
        from app.schemas.auth import RegisterRequest
        import uuid
        req = RegisterRequest(
            full_name="Rahul Sharma",
            age=28,
            gender="Male",
            phone="9876543210",
            email="rahul@example.com",
            address="12, Anna Nagar, Trichy",
            password="MyPass@123",
            plan_id=uuid.uuid4(),
        )
        assert req.full_name == "Rahul Sharma"

    def test_weak_password_rejected(self):
        from pydantic import ValidationError
        from app.schemas.auth import RegisterRequest
        import uuid
        with pytest.raises(ValidationError) as exc_info:
            RegisterRequest(
                full_name="Test",
                age=25,
                gender="Male",
                phone="9876543210",
                email="test@test.com",
                address="Test address",
                password="weakpassword",  # No uppercase, no digit
                plan_id=uuid.uuid4(),
            )
        errors = str(exc_info.value)
        assert "uppercase" in errors or "digit" in errors

    def test_invalid_phone_rejected(self):
        from pydantic import ValidationError
        from app.schemas.auth import RegisterRequest
        import uuid
        with pytest.raises(ValidationError):
            RegisterRequest(
                full_name="Test",
                age=25,
                gender="Male",
                phone="12345",   # Only 5 digits — must be 10
                email="test@test.com",
                address="Test address",
                password="MyPass@123",
                plan_id=uuid.uuid4(),
            )

    def test_invalid_gender_rejected(self):
        from pydantic import ValidationError
        from app.schemas.auth import RegisterRequest
        import uuid
        with pytest.raises(ValidationError):
            RegisterRequest(
                full_name="Test",
                age=25,
                gender="Unknown",   # Not Male/Female/Other
                phone="9876543210",
                email="test@test.com",
                address="Test address",
                password="MyPass@123",
                plan_id=uuid.uuid4(),
            )


# ── API Integration Tests (Phase 4 — requires DB) ─────────────────────────
# Uncomment and configure conftest.py with test DB fixtures for full integration tests.

# @pytest.mark.asyncio
# async def test_register_and_login_flow():
#     async with AsyncClient(app=app, base_url="http://test") as client:
#         # Register
#         resp = await client.post("/api/v1/auth/register", json={...})
#         assert resp.status_code == 201
#         member_id = resp.json()["member_id"]
#         assert member_id.startswith("S2T")
#
#         # Login
#         resp = await client.post("/api/v1/auth/login", json={
#             "member_id": member_id, "password": "MyPass@123"
#         })
#         assert resp.status_code == 200
#         data = resp.json()
#         assert "access_token" in data
#         assert data["user"]["role"] == "member"
