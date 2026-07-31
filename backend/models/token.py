"""
models/token.py — Auth token models (refresh, password reset, email verification)
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base

if TYPE_CHECKING:
    from models.user import User


class RefreshToken(Base):
    """Opaque refresh token stored as a SHA-256 hash. Supports mandatory rotation."""

    __tablename__ = "refresh_tokens"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    revoked: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ────────────────────────────────────────
    user: Mapped[User] = relationship(
        "User", back_populates="refresh_tokens",
    )

    def __repr__(self) -> str:
        return f"<RefreshToken id={self.id} revoked={self.revoked}>"


class PasswordResetToken(Base):
    """One-time password reset token stored as a hash."""

    __tablename__ = "password_reset_tokens"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    used: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<PasswordResetToken id={self.id} used={self.used}>"


class EmailVerificationToken(Base):
    """One-time email verification token stored as a hash."""

    __tablename__ = "email_verification_tokens"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(
        String(64), nullable=False, index=True,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False,
    )
    used: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<EmailVerificationToken id={self.id} used={self.used}>"
