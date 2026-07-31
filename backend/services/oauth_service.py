"""
services/oauth_service.py — OAuth2 flows via Authlib

Supports Google and GitHub. Creates or links users on first OAuth login.
"""
from __future__ import annotations

import logging
from typing import Optional

from authlib.integrations.httpx_client import AsyncOAuth2Client
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.exceptions import ServiceUnavailableError, ValidationError
from repositories.user_repo import user_repo

logger = logging.getLogger("ai-site-gen")
settings = get_settings()

# ── Google OAuth ────────────────────────────────────────────

GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


def get_google_auth_url(state: str) -> str:
    """Generate the Google OAuth2 authorization URL."""
    cfg = get_settings()
    if not cfg.GOOGLE_CLIENT_ID or not cfg.GOOGLE_CLIENT_SECRET:
        raise ServiceUnavailableError(
            message="Google OAuth is not configured. Please set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in backend/.env",
            code="OAUTH_NOT_CONFIGURED",
        )
    client = AsyncOAuth2Client(
        client_id=cfg.GOOGLE_CLIENT_ID,
        client_secret=cfg.GOOGLE_CLIENT_SECRET,
        redirect_uri=cfg.GOOGLE_REDIRECT_URI,
        scope="openid email profile",
    )
    url, _ = client.create_authorization_url(GOOGLE_AUTHORIZE_URL, state=state)
    return url


async def handle_google_callback(db: AsyncSession, code: str):
    """Exchange Google auth code for user info and get/create user."""
    cfg = get_settings()
    if not cfg.GOOGLE_CLIENT_ID or not cfg.GOOGLE_CLIENT_SECRET:
        raise ServiceUnavailableError(
            message="Google OAuth is not configured",
            code="OAUTH_NOT_CONFIGURED",
        )

    client = AsyncOAuth2Client(
        client_id=cfg.GOOGLE_CLIENT_ID,
        client_secret=cfg.GOOGLE_CLIENT_SECRET,
        redirect_uri=cfg.GOOGLE_REDIRECT_URI,
    )

    try:
        await client.fetch_token(GOOGLE_TOKEN_URL, code=code)
        resp = await client.get(GOOGLE_USERINFO_URL)
        resp.raise_for_status()
        userinfo = resp.json()
    except Exception as exc:
        logger.error(f"Google OAuth error: {exc}")
        raise ServiceUnavailableError(
            message="Failed to authenticate with Google",
            code="OAUTH_GOOGLE_FAILED",
        )
    finally:
        await client.aclose()

    return await _get_or_create_oauth_user(
        db,
        provider="google",
        oauth_id=userinfo["sub"],
        email=userinfo.get("email"),
        name=userinfo.get("name"),
        avatar_url=userinfo.get("picture"),
    )


# ── GitHub OAuth ────────────────────────────────────────────

GITHUB_AUTHORIZE_URL = "https://github.com/login/oauth/authorize"
GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
GITHUB_USER_URL = "https://api.github.com/user"
GITHUB_EMAILS_URL = "https://api.github.com/user/emails"


def get_github_auth_url(state: str) -> str:
    """Generate the GitHub OAuth2 authorization URL."""
    cfg = get_settings()
    if not cfg.GITHUB_CLIENT_ID or not cfg.GITHUB_CLIENT_SECRET:
        raise ServiceUnavailableError(
            message="GitHub OAuth is not configured. Please set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in backend/.env",
            code="OAUTH_NOT_CONFIGURED",
        )
    client = AsyncOAuth2Client(
        client_id=cfg.GITHUB_CLIENT_ID,
        client_secret=cfg.GITHUB_CLIENT_SECRET,
        redirect_uri=cfg.GITHUB_REDIRECT_URI,
        scope="user:email",
    )
    url, _ = client.create_authorization_url(GITHUB_AUTHORIZE_URL, state=state)
    return url


async def handle_github_callback(db: AsyncSession, code: str):
    """Exchange GitHub auth code for user info and get/create user."""
    cfg = get_settings()
    if not cfg.GITHUB_CLIENT_ID or not cfg.GITHUB_CLIENT_SECRET:
        raise ServiceUnavailableError(
            message="GitHub OAuth is not configured",
            code="OAUTH_NOT_CONFIGURED",
        )

    client = AsyncOAuth2Client(
        client_id=cfg.GITHUB_CLIENT_ID,
        client_secret=cfg.GITHUB_CLIENT_SECRET,
        redirect_uri=cfg.GITHUB_REDIRECT_URI,
    )

    try:
        await client.fetch_token(
            GITHUB_TOKEN_URL, code=code, headers={"Accept": "application/json"},
        )
        resp = await client.get(GITHUB_USER_URL)
        resp.raise_for_status()
        userinfo = resp.json()

        # GitHub may not include email in profile
        email = userinfo.get("email")
        if not email:
            emails_resp = await client.get(GITHUB_EMAILS_URL)
            emails_resp.raise_for_status()
            emails = emails_resp.json()
            primary = next(
                (e for e in emails if e.get("primary") and e.get("verified")), None,
            )
            email = primary["email"] if primary else None

    except Exception as exc:
        logger.error(f"GitHub OAuth error: {exc}")
        raise ServiceUnavailableError(
            message="Failed to authenticate with GitHub",
            code="OAUTH_GITHUB_FAILED",
        )
    finally:
        await client.aclose()

    return await _get_or_create_oauth_user(
        db,
        provider="github",
        oauth_id=str(userinfo["id"]),
        email=email,
        name=userinfo.get("login"),
        avatar_url=userinfo.get("avatar_url"),
    )


# ── Shared Helper ───────────────────────────────────────────


async def _get_or_create_oauth_user(
    db: AsyncSession,
    *,
    provider: str,
    oauth_id: str,
    email: Optional[str],
    name: Optional[str],
    avatar_url: Optional[str] = None,
):
    """Find existing user by OAuth provider+ID, or create a new one."""

    # 1. Look up by OAuth provider + ID
    user = await user_repo.get_by_oauth(db, provider, oauth_id)
    if user:
        return user

    # 2. Look up by email → link the OAuth account
    if email:
        user = await user_repo.get_by_email(db, email)
        if user:
            await user_repo.update(
                db,
                user,
                oauth_provider=provider,
                oauth_id=oauth_id,
                is_verified=True,  # Email confirmed by provider
                avatar_url=avatar_url or user.avatar_url,
            )
            return user

    # 3. Create new user
    if not email:
        raise ValidationError(
            message="Could not retrieve email from OAuth provider",
            code="OAUTH_NO_EMAIL",
        )

    # Generate unique username from name/email
    base = (name or email.split("@")[0]).lower().replace(" ", "_")[:40]
    username = base
    counter = 1
    while await user_repo.get_by_username(db, username):
        username = f"{base}_{counter}"
        counter += 1

    user = await user_repo.create(
        db,
        email=email,
        username=username,
        oauth_provider=provider,
        oauth_id=oauth_id,
        is_verified=True,  # OAuth users are auto-verified
        avatar_url=avatar_url,
    )
    return user
