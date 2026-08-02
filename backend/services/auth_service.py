"""
services/auth_service.py — Authentication business logic

Orchestrates auth flows using repositories for database access
and core.security for cryptographic operations.
Raises domain exceptions (never HTTPException).
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ConflictError,
    NotFoundError,
    TokenReuseDetected,
    ValidationError,
)
from core.security import (
    create_access_token,
    generate_token,
    hash_password,
    hash_token,
    verify_password,
)
from models.user import User
from repositories.token_repo import token_repo
from repositories.user_repo import user_repo
from services import audit_service, email_service
from workers import email_tasks

settings = get_settings()


class AuthResult:
    """Holds the result of a login/refresh operation."""

    def __init__(self, access_token: str, refresh_token: str, expires_in: int):
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_in = expires_in


# ── Registration ────────────────────────────────────────────


async def register(
    db: AsyncSession,
    *,
    email: str,
    username: str,
    password: str,
    request: Optional[Request] = None,
) -> User:
    """
    Register a new user account.

    Raises ConflictError if email/username already exists.
    """
    if await user_repo.get_by_email(db, email):
        raise ConflictError(
            message="An account with this email already exists",
            code="EMAIL_EXISTS",
        )
    if await user_repo.get_by_username(db, username):
        raise ConflictError(
            message="This username is already taken",
            code="USERNAME_EXISTS",
        )

    # Auto-verify user in development mode if email sending (Resend) is not configured
    auto_verify = not bool(settings.RESEND_API_KEY)

    user = await user_repo.create(
        db,
        email=email,
        username=username,
        hashed_password=hash_password(password),
        is_verified=auto_verify,
    )

    # Email verification token (24 h)
    raw_token = generate_token()
    await token_repo.create_email_verification_token(
        db,
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
    )

    await audit_service.log_audit(
        db,
        user_id=user.id,
        action="user.register",
        resource_type="user",
        resource_id=str(user.id),
        request=request,
    )

    # Dispatch email to Celery (falls back to inline if Redis unavailable)
    email_tasks.dispatch_verification_email(email, username, raw_token)

    return user


# ── Login ───────────────────────────────────────────────────


async def login(
    db: AsyncSession,
    *,
    email: str,
    password: str,
    request: Optional[Request] = None,
) -> AuthResult:
    """
    Authenticate with email + password.

    Raises AuthenticationError on bad credentials.
    Raises AuthorizationError if account is deactivated.
    """
    user = await user_repo.get_by_email(db, email)
    if not user or not user.hashed_password:
        raise AuthenticationError(
            message="Invalid email or password",
            code="INVALID_CREDENTIALS",
        )

    if not verify_password(password, user.hashed_password):
        raise AuthenticationError(
            message="Invalid email or password",
            code="INVALID_CREDENTIALS",
        )

    if not user.is_active:
        raise AuthorizationError(
            message="Account is deactivated",
            code="ACCOUNT_DEACTIVATED",
        )

    access_token = create_access_token(str(user.id), user.role.value)
    refresh_raw = generate_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    await token_repo.create_refresh_token(
        db,
        user_id=user.id,
        token_hash=hash_token(refresh_raw),
        expires_at=expires_at,
    )

    await audit_service.log_audit(
        db,
        user_id=user.id,
        action="user.login",
        resource_type="user",
        resource_id=str(user.id),
        request=request,
    )

    return AuthResult(
        access_token=access_token,
        refresh_token=refresh_raw,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ── OAuth Login ─────────────────────────────────────────────


async def login_oauth_user(
    db: AsyncSession,
    *,
    user: User,
    request: Optional[Request] = None,
) -> AuthResult:
    """Issue tokens for an OAuth-authenticated user."""
    access_token = create_access_token(str(user.id), user.role.value)
    refresh_raw = generate_token()
    expires_at = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    await token_repo.create_refresh_token(
        db,
        user_id=user.id,
        token_hash=hash_token(refresh_raw),
        expires_at=expires_at,
    )

    await audit_service.log_audit(
        db,
        user_id=user.id,
        action="user.login.oauth",
        request=request,
    )

    return AuthResult(
        access_token=access_token,
        refresh_token=refresh_raw,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ── Refresh Token (mandatory rotation) ─────────────────────


async def refresh(
    db: AsyncSession,
    *,
    refresh_token_raw: Optional[str],
    request: Optional[Request] = None,
) -> AuthResult:
    """
    Refresh access token. Implements mandatory rotation + reuse detection.

    Flow: validate old → revoke old → issue new.
    If revoked token is reused → revoke ALL sessions.
    """
    if not refresh_token_raw:
        raise AuthenticationError(
            message="No refresh token provided",
            code="MISSING_REFRESH_TOKEN",
        )

    old_hash = hash_token(refresh_token_raw)
    stored = await token_repo.get_refresh_token(db, old_hash)

    if not stored:
        raise AuthenticationError(
            message="Invalid refresh token",
            code="INVALID_REFRESH_TOKEN",
        )

    # Reuse detection
    if stored.revoked:
        await token_repo.revoke_all_user_tokens(db, stored.user_id)
        await audit_service.log_audit(
            db,
            user_id=stored.user_id,
            action="security.token_reuse_detected",
            request=request,
            metadata={
                "detail": "Revoked refresh token reused. All sessions invalidated."
            },
        )
        raise TokenReuseDetected()

    # Expiry check
    token_expiry = stored.expires_at
    if token_expiry.tzinfo is None:
        token_expiry = token_expiry.replace(tzinfo=timezone.utc)
    if token_expiry < datetime.now(timezone.utc):
        raise AuthenticationError(
            message="Refresh token expired",
            code="REFRESH_TOKEN_EXPIRED",
        )

    # Rotate
    await token_repo.revoke_refresh_token(db, old_hash)

    user = await user_repo.get_by_id(db, stored.user_id)
    if not user or not user.is_active:
        raise AuthenticationError(
            message="User not found or deactivated",
            code="USER_UNAVAILABLE",
        )

    access_token = create_access_token(str(user.id), user.role.value)
    new_refresh_raw = generate_token()
    new_expires = datetime.now(timezone.utc) + timedelta(
        days=settings.REFRESH_TOKEN_EXPIRE_DAYS
    )

    await token_repo.create_refresh_token(
        db,
        user_id=user.id,
        token_hash=hash_token(new_refresh_raw),
        expires_at=new_expires,
    )

    return AuthResult(
        access_token=access_token,
        refresh_token=new_refresh_raw,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ── Logout ──────────────────────────────────────────────────


async def logout(
    db: AsyncSession,
    *,
    refresh_token_raw: Optional[str],
    user_id: uuid.UUID,
    request: Optional[Request] = None,
) -> None:
    """Revoke the refresh token."""
    if refresh_token_raw:
        await token_repo.revoke_refresh_token(db, hash_token(refresh_token_raw))

    await audit_service.log_audit(
        db, user_id=user_id, action="user.logout", request=request,
    )


# ── Email Verification ─────────────────────────────────────


async def verify_email(
    db: AsyncSession,
    *,
    token: str,
    request: Optional[Request] = None,
) -> None:
    """Verify a user's email with the verification token."""
    tok_hash = hash_token(token)
    stored = await token_repo.get_email_verification_token(db, tok_hash)

    if not stored:
        raise ValidationError(
            message="Invalid verification token",
            code="INVALID_VERIFICATION_TOKEN",
        )
    if stored.used:
        raise ValidationError(
            message="This verification link has already been used",
            code="TOKEN_ALREADY_USED",
        )

    expiry = stored.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry < datetime.now(timezone.utc):
        raise ValidationError(
            message="Verification link has expired. Please request a new one.",
            code="TOKEN_EXPIRED",
        )

    await token_repo.mark_email_verification_used(db, tok_hash)

    user = await user_repo.get_by_id(db, stored.user_id)
    if user:
        await user_repo.update(db, user, is_verified=True)
        await audit_service.log_audit(
            db,
            user_id=user.id,
            action="user.email_verified",
            resource_type="user",
            resource_id=str(user.id),
            request=request,
        )
        email_tasks.dispatch_welcome_email(user.email, user.username)


# ── Forgot Password ────────────────────────────────────────


async def forgot_password(
    db: AsyncSession,
    *,
    email: str,
    request: Optional[Request] = None,
) -> None:
    """
    Request a password reset. Always succeeds (prevents email enumeration).
    """
    user = await user_repo.get_by_email(db, email)
    if not user:
        return  # Silent — don't reveal whether email exists

    raw_token = generate_token()
    await token_repo.create_password_reset_token(
        db,
        user_id=user.id,
        token_hash=hash_token(raw_token),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    )

    await audit_service.log_audit(
        db,
        user_id=user.id,
        action="password.reset_requested",
        request=request,
    )

    email_tasks.dispatch_password_reset_email(user.email, user.username, raw_token)


# ── Reset Password ─────────────────────────────────────────


async def reset_password(
    db: AsyncSession,
    *,
    token: str,
    new_password: str,
    request: Optional[Request] = None,
) -> None:
    """Reset password with a valid reset token. Revokes all sessions."""
    tok_hash = hash_token(token)
    stored = await token_repo.get_password_reset_token(db, tok_hash)

    if not stored:
        raise ValidationError(
            message="Invalid reset token",
            code="INVALID_RESET_TOKEN",
        )
    if stored.used:
        raise ValidationError(
            message="This reset link has already been used",
            code="TOKEN_ALREADY_USED",
        )

    expiry = stored.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if expiry < datetime.now(timezone.utc):
        raise ValidationError(
            message="Reset link has expired. Please request a new one.",
            code="TOKEN_EXPIRED",
        )

    await token_repo.mark_password_reset_used(db, tok_hash)

    user = await user_repo.get_by_id(db, stored.user_id)
    if not user:
        raise NotFoundError(message="User not found", code="USER_NOT_FOUND")

    await user_repo.update(db, user, hashed_password=hash_password(new_password))
    await token_repo.revoke_all_user_tokens(db, user.id)

    await audit_service.log_audit(
        db,
        user_id=user.id,
        action="password.changed",
        resource_type="user",
        resource_id=str(user.id),
        request=request,
    )
