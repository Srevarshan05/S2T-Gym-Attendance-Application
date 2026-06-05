"""
app/core/config.py
──────────────────
Single source of truth for all environment-driven configuration.
Uses Pydantic BaseSettings — reads from .env file automatically.
Never read os.environ directly anywhere else in the codebase.
"""

from __future__ import annotations

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database ───────────────────────────────────────────────────────────
    DATABASE_URL: str  # postgresql+asyncpg://user:pass@host/db

    # ── JWT ────────────────────────────────────────────────────────────────
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_TTL: int = 900          # 15 minutes (seconds)
    JWT_REFRESH_TOKEN_TTL: int = 7_776_000   # 90 days (seconds)

    # ── Application ────────────────────────────────────────────────────────
    ENV: str = "development"
    LOG_LEVEL: str = "INFO"
    GYM_NAME: str = "S2T Fitness Studio"
    ALLOWED_ORIGINS: list[str] = ["http://localhost:5173"]

    # ── Brute-force protection ─────────────────────────────────────────────
    MAX_LOGIN_ATTEMPTS: int = 5
    ACCOUNT_LOCK_MINUTES: int = 30

    # ── Admin seed account ─────────────────────────────────────────────────
    ADMIN_EMAIL: str = "admin@s2tfitness.in"
    ADMIN_PASSWORD: str = "ChangeMe@Production1"

    @field_validator("ALLOWED_ORIGINS", mode="before")
    @classmethod
    def split_origins(cls, v: str | list[str]) -> list[str]:
        """Allow comma-separated origins in .env: ALLOWED_ORIGINS=http://a.com,http://b.com"""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_secret_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters for security.")
        return v


# Module-level singleton — import this everywhere
settings = Settings()
