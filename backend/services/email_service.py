"""
services/email_service.py — Email sending via Resend + Jinja2 templates

Falls back to console logging when RESEND_API_KEY is not configured,
which is the default for local development.
"""
from __future__ import annotations

import logging
from pathlib import Path

from jinja2 import Environment, FileSystemLoader

from core.config import get_settings

logger = logging.getLogger("ai-site-gen")

# Jinja2 template environment
_template_dir = Path(__file__).resolve().parent.parent / "templates"
_jinja_env = Environment(
    loader=FileSystemLoader(str(_template_dir)),
    autoescape=True,
)

settings = get_settings()


def _render_template(template_name: str, **context) -> str:
    """Render a Jinja2 template with the given context."""
    template = _jinja_env.get_template(template_name)
    return template.render(**context)


async def send_email(to: str, subject: str, html: str) -> None:
    """
    Send an email via Resend, or log to console if no API key is configured.
    """
    if not settings.RESEND_API_KEY:
        logger.info(
            f"\n📧 [EMAIL — console mode]\n"
            f"   To: {to}\n"
            f"   Subject: {subject}\n"
            f"   Body:\n{html[:500]}{'...' if len(html) > 500 else ''}\n"
        )
        return

    import resend

    resend.api_key = settings.RESEND_API_KEY
    try:
        resend.Emails.send(
            {
                "from": settings.RESEND_FROM_EMAIL,
                "to": [to],
                "subject": subject,
                "html": html,
            }
        )
        logger.info(f"📧 Email sent to {to}: {subject}")
    except Exception as exc:
        logger.error(f"📧 Failed to send email to {to}: {exc}")
        # Don't raise — email failure shouldn't block auth flows


async def send_verification_email(to: str, username: str, token: str) -> None:
    """Send an email verification link."""
    action_url = f"{settings.FRONTEND_URL}/auth/verify-email?token={token}"
    html = _render_template(
        "verify_email.html",
        username=username,
        action_url=action_url,
        app_name="AI Website Generator",
    )
    await send_email(to, "Verify your email address", html)


async def send_password_reset_email(to: str, username: str, token: str) -> None:
    """Send a password reset link."""
    action_url = f"{settings.FRONTEND_URL}/auth/reset-password?token={token}"
    html = _render_template(
        "reset_password.html",
        username=username,
        action_url=action_url,
        app_name="AI Website Generator",
    )
    await send_email(to, "Reset your password", html)


async def send_welcome_email(to: str, username: str) -> None:
    """Send a welcome email after verification."""
    html = _render_template(
        "welcome.html",
        username=username,
        app_url=settings.FRONTEND_URL,
        app_name="AI Website Generator",
    )
    await send_email(to, "Welcome to AI Website Generator!", html)
