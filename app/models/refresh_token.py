"""
app/models/refresh_token.py
────────────────────────────
SQLAlchemy ORM model for the `refresh_tokens` table.

Security model:
  - The RAW token (UUID-like string) is returned to the client in the
    login/refresh response body. It is NEVER persisted.
  - Only the SHA-256 hash of the token is stored here.
  - On the next /refresh call, the raw token from the client is hashed
    again and looked up in this table.
  - This means a database breach leaking `token_hash` values cannot be
    used to authenticate — an attacker would need to reverse SHA-256.

Rolling Rotation:
  - Every /refresh call revokes the old token (is_revoked=True)
    and issues a brand-new token pair.
  - If an attacker reuses a stolen refresh token, it will already be
    revoked (legit user rotated it), triggering a 401.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User


class RefreshToken(Base, TimestampMixin):
    __tablename__ = "refresh_tokens"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=sa.text("gen_random_uuid()"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        doc="Cascade delete: removing a user purges all their sessions.",
    )

    token_hash: Mapped[str] = mapped_column(
        sa.Text,
        unique=True,
        nullable=False,
        doc="SHA-256 hex digest of the raw refresh token. Never the raw token.",
    )

    expires_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        nullable=False,
        doc="UTC expiry time. Tokens older than this are rejected even if not revoked.",
    )

    is_revoked: Mapped[bool] = mapped_column(
        sa.Boolean,
        nullable=False,
        default=False,
        server_default=sa.false(),
        doc="Set to True on logout or token rotation. Never deleted — kept for audit.",
    )

    # ── Device Context (for future multi-device session management) ────────
    user_agent: Mapped[Optional[str]] = mapped_column(
        sa.Text,
        nullable=True,
        doc="Browser/device user-agent string from the login request.",
    )

    ip_address: Mapped[Optional[str]] = mapped_column(
        sa.String(45),
        nullable=True,
        doc="Client IP address (IPv4 or IPv6) from the login request.",
    )

    # ── Relationships ──────────────────────────────────────────────────────
    user: Mapped["User"] = relationship(
        "User",
        back_populates="refresh_tokens",
        lazy="noload",
    )

    def __repr__(self) -> str:
        return (
            f"<RefreshToken id={self.id} user_id={self.user_id} "
            f"revoked={self.is_revoked} expires={self.expires_at}>"
        )
