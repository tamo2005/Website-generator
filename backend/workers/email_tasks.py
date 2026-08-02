"""
workers/email_tasks.py — Celery tasks for email sending

Includes safe dispatch helpers: if Redis is unreachable (e.g. during tests or
local dev without Docker), falls back immediately to direct async delivery.
"""
from __future__ import annotations

import logging
from workers.celery_app import celery_app
from core.config import get_settings

logger = logging.getLogger("ai-site-gen")
settings = get_settings()

_redis_available: bool | None = None


def _is_redis_up() -> bool:
    """Check once if Redis is reachable to avoid blocking on kombu connection timeouts."""
    global _redis_available
    if _redis_available is not None:
        return _redis_available
    try:
        import redis as py_redis
        r = py_redis.from_url(settings.REDIS_URL, socket_connect_timeout=0.5)
        r.ping()
        _redis_available = True
    except Exception:
        _redis_available = False
    return _redis_available


@celery_app.task(
    name="workers.email_tasks.send_verification_email",
    queue="email",
    max_retries=3,
    default_retry_delay=30,
    bind=True,
)
def send_verification_email(self, to: str, username: str, token: str) -> None:
    """Send email verification link via Resend (or console log in dev)."""
    try:
        import asyncio
        from services.email_service import send_verification_email as _send
        asyncio.run(_send(to, username, token))
    except Exception as exc:
        logger.error(f"Email task failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(
    name="workers.email_tasks.send_password_reset_email",
    queue="email",
    max_retries=3,
    default_retry_delay=30,
    bind=True,
)
def send_password_reset_email(self, to: str, username: str, token: str) -> None:
    """Send password reset link via Resend (or console log in dev)."""
    try:
        import asyncio
        from services.email_service import send_password_reset_email as _send
        asyncio.run(_send(to, username, token))
    except Exception as exc:
        logger.error(f"Password reset email task failed: {exc}")
        raise self.retry(exc=exc)


@celery_app.task(
    name="workers.email_tasks.send_welcome_email",
    queue="email",
    max_retries=3,
    default_retry_delay=30,
    bind=True,
)
def send_welcome_email(self, to: str, username: str) -> None:
    """Send welcome email after email verification."""
    try:
        import asyncio
        from services.email_service import send_welcome_email as _send
        asyncio.run(_send(to, username))
    except Exception as exc:
        logger.error(f"Welcome email task failed: {exc}")
        raise self.retry(exc=exc)


# ── Safe Dispatchers (Instant fallback if Redis is offline) ───────────────────

def _run_email_direct(coro_fn, *args):
    """Run an async email function directly without Celery."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(coro_fn(*args))
    except RuntimeError:
        asyncio.run(coro_fn(*args))


def dispatch_verification_email(to: str, username: str, token: str) -> None:
    from services.email_service import send_verification_email as _send
    if _is_redis_up():
        try:
            send_verification_email.delay(to, username, token)
            return
        except Exception:
            pass
    _run_email_direct(_send, to, username, token)


def dispatch_password_reset_email(to: str, username: str, token: str) -> None:
    from services.email_service import send_password_reset_email as _send
    if _is_redis_up():
        try:
            send_password_reset_email.delay(to, username, token)
            return
        except Exception:
            pass
    _run_email_direct(_send, to, username, token)


def dispatch_welcome_email(to: str, username: str) -> None:
    from services.email_service import send_welcome_email as _send
    if _is_redis_up():
        try:
            send_welcome_email.delay(to, username)
            return
        except Exception:
            pass
    _run_email_direct(_send, to, username)
