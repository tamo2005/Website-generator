"""
workers/cleanup_tasks.py — Periodic cleanup tasks (run via Celery Beat)
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from workers.celery_app import celery_app

logger = logging.getLogger("ai-site-gen")


@celery_app.task(
    name="workers.cleanup_tasks.purge_expired_tokens",
    queue="default",
)
def purge_expired_tokens() -> dict:
    """
    Delete expired refresh tokens, password reset tokens, and email
    verification tokens from the database. Runs every hour via Beat.
    """
    async def _purge():
        from sqlalchemy import delete, select
        from db.session import AsyncSessionLocal
        from models.token import RefreshToken, PasswordResetToken, EmailVerificationToken

        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as session:
            # Refresh tokens: expired or revoked
            rt_result = await session.execute(
                delete(RefreshToken).where(RefreshToken.expires_at < now)
            )
            # Password reset tokens: expired or used
            prt_result = await session.execute(
                delete(PasswordResetToken).where(
                    (PasswordResetToken.expires_at < now) | (PasswordResetToken.used == True)  # noqa
                )
            )
            # Email verification tokens: expired or used
            evt_result = await session.execute(
                delete(EmailVerificationToken).where(
                    (EmailVerificationToken.expires_at < now) | (EmailVerificationToken.used == True)  # noqa
                )
            )
            await session.commit()

        return {
            "refresh_tokens_deleted": rt_result.rowcount,
            "reset_tokens_deleted": prt_result.rowcount,
            "verify_tokens_deleted": evt_result.rowcount,
        }

    result = asyncio.run(_purge())
    logger.info(f"Token cleanup complete: {result}")
    return result
