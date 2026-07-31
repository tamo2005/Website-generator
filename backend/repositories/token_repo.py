"""
repositories/token_repo.py — Token database operations

All SQLAlchemy queries for refresh, password reset, and email verification tokens.
Services call this layer; they never touch SQLAlchemy directly.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from models.token import (
    EmailVerificationToken,
    PasswordResetToken,
    RefreshToken,
)


class TokenRepository:
    """CRUD operations for auth token models."""

    # ── Refresh Tokens ──────────────────────────────────────

    @staticmethod
    async def create_refresh_token(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> RefreshToken:
        token = RefreshToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(token)
        await db.flush()
        return token

    @staticmethod
    async def get_refresh_token(
        db: AsyncSession, token_hash: str,
    ) -> Optional[RefreshToken]:
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def revoke_refresh_token(db: AsyncSession, token_hash: str) -> None:
        await db.execute(
            update(RefreshToken)
            .where(RefreshToken.token_hash == token_hash)
            .values(revoked=True)
        )
        await db.flush()

    @staticmethod
    async def revoke_all_user_tokens(db: AsyncSession, user_id: uuid.UUID) -> None:
        await db.execute(
            update(RefreshToken)
            .where(
                RefreshToken.user_id == user_id,
                RefreshToken.revoked == False,  # noqa: E712
            )
            .values(revoked=True)
        )
        await db.flush()

    # ── Password Reset Tokens ───────────────────────────────

    @staticmethod
    async def create_password_reset_token(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> PasswordResetToken:
        token = PasswordResetToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(token)
        await db.flush()
        return token

    @staticmethod
    async def get_password_reset_token(
        db: AsyncSession, token_hash: str,
    ) -> Optional[PasswordResetToken]:
        result = await db.execute(
            select(PasswordResetToken).where(
                PasswordResetToken.token_hash == token_hash
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def mark_password_reset_used(db: AsyncSession, token_hash: str) -> None:
        await db.execute(
            update(PasswordResetToken)
            .where(PasswordResetToken.token_hash == token_hash)
            .values(used=True)
        )
        await db.flush()

    # ── Email Verification Tokens ───────────────────────────

    @staticmethod
    async def create_email_verification_token(
        db: AsyncSession,
        *,
        user_id: uuid.UUID,
        token_hash: str,
        expires_at: datetime,
    ) -> EmailVerificationToken:
        token = EmailVerificationToken(
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
        )
        db.add(token)
        await db.flush()
        return token

    @staticmethod
    async def get_email_verification_token(
        db: AsyncSession, token_hash: str,
    ) -> Optional[EmailVerificationToken]:
        result = await db.execute(
            select(EmailVerificationToken).where(
                EmailVerificationToken.token_hash == token_hash
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def mark_email_verification_used(
        db: AsyncSession, token_hash: str,
    ) -> None:
        await db.execute(
            update(EmailVerificationToken)
            .where(EmailVerificationToken.token_hash == token_hash)
            .values(used=True)
        )
        await db.flush()


# Singleton instance for convenience
token_repo = TokenRepository()
