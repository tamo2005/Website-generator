"""
api/auth/router.py — Authentication API endpoints

Thin handlers that delegate to services. Returns consistent API envelope.
All paths prefixed with /api/v1/auth.
"""

import secrets

from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from core.dependencies import get_current_active_user, get_current_verified_user
from core.responses import api_response
from db.session import get_db
from middleware.rate_limit import limiter
from models.user import User
from schemas.auth import (
    ForgotPasswordRequest,
    LoginRequest,
    RegisterRequest,
    ResetPasswordRequest,
    VerifyEmailRequest,
)
from schemas.user import UserResponse, UserUpdate
from services import auth_service, oauth_service

settings = get_settings()

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])

# ── Cookie settings ─────────────────────────────────────────
_COOKIE_KEY = "refresh_token"
_COOKIE_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, token: str) -> None:
    """Set the refresh token as an HttpOnly Secure cookie."""
    response.set_cookie(
        key=_COOKIE_KEY,
        value=token,
        httponly=True,
        secure=False,  # Set True in production (HTTPS only)
        samesite="lax",
        max_age=_COOKIE_MAX_AGE,
        path=_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    """Clear the refresh token cookie."""
    response.delete_cookie(key=_COOKIE_KEY, path=_COOKIE_PATH)


# ── Registration ────────────────────────────────────────────


@router.post("/register", status_code=201)
@limiter.limit("60/hour")
async def register(
    data: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Create a new user account. Sends a verification email."""
    user = await auth_service.register(
        db,
        email=data.email,
        username=data.username,
        password=data.password,
        request=request,
    )
    msg = (
        "Account created successfully. Please check your email to verify your account."
        if not user.is_verified
        else "Account created successfully! You can now log in."
    )
    return api_response(
        data=UserResponse.model_validate(user),
        message=msg,
        status_code=201,
        request=request,
    )


# ── Login ───────────────────────────────────────────────────


@router.post("/login")
@limiter.limit("5/minute")
async def login(
    data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate with email/password. Sets refresh cookie, returns access token."""
    result = await auth_service.login(
        db,
        email=data.email,
        password=data.password,
        request=request,
    )
    response = api_response(
        data={
            "access_token": result.access_token,
            "token_type": "bearer",
            "expires_in": result.expires_in,
        },
        message="Login successful",
        request=request,
    )
    _set_refresh_cookie(response, result.refresh_token)
    return response


# ── Refresh ─────────────────────────────────────────────────


@router.post("/refresh")
@limiter.limit("30/minute")
async def refresh_token(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using HttpOnly cookie. Mandatory rotation."""
    refresh_cookie = request.cookies.get(_COOKIE_KEY)
    result = await auth_service.refresh(
        db,
        refresh_token_raw=refresh_cookie,
        request=request,
    )
    response = api_response(
        data={
            "access_token": result.access_token,
            "token_type": "bearer",
            "expires_in": result.expires_in,
        },
        request=request,
    )
    _set_refresh_cookie(response, result.refresh_token)
    return response


# ── Logout ──────────────────────────────────────────────────


@router.post("/logout")
async def logout(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_active_user),
):
    """Revoke refresh token and clear cookie."""
    refresh_cookie = request.cookies.get(_COOKIE_KEY)
    await auth_service.logout(
        db,
        refresh_token_raw=refresh_cookie,
        user_id=user.id,
        request=request,
    )
    response = api_response(
        message="Logged out successfully",
        request=request,
    )
    _clear_refresh_cookie(response)
    return response


# ── Current User ────────────────────────────────────────────


@router.get("/me")
async def get_me(
    request: Request,
    user: User = Depends(get_current_verified_user),
):
    """Get the current authenticated user's profile."""
    return api_response(
        data=UserResponse.model_validate(user),
        request=request,
    )


@router.patch("/me")
async def update_me(
    data: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_verified_user),
):
    """Update the current user's profile."""
    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        from repositories.user_repo import user_repo

        user = await user_repo.update(db, user, **update_data)
    return api_response(
        data=UserResponse.model_validate(user),
        message="Profile updated",
        request=request,
    )


# ── Email Verification ─────────────────────────────────────


@router.post("/verify-email")
@limiter.limit("10/hour")
async def verify_email(
    data: VerifyEmailRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Verify email address using the verification token."""
    await auth_service.verify_email(db, token=data.token, request=request)
    return api_response(
        message="Email verified successfully",
        request=request,
    )


# ── Forgot Password ────────────────────────────────────────


@router.post("/forgot-password")
@limiter.limit("3/hour")
async def forgot_password(
    data: ForgotPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Request a password reset email. Always succeeds (prevents enumeration)."""
    await auth_service.forgot_password(db, email=data.email, request=request)
    return api_response(
        message="If an account exists with this email, a reset link has been sent.",
        request=request,
    )


# ── Reset Password ─────────────────────────────────────────


@router.post("/reset-password")
@limiter.limit("5/minute")
async def reset_password(
    data: ResetPasswordRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Reset password with a valid reset token."""
    await auth_service.reset_password(
        db,
        token=data.token,
        new_password=data.new_password,
        request=request,
    )
    return api_response(
        message="Password reset successfully. Please log in with your new password.",
        request=request,
    )


# ── OAuth: Google ───────────────────────────────────────────


@router.get("/oauth/google")
async def oauth_google():
    """Redirect to Google OAuth2 authorization page."""
    state = secrets.token_urlsafe(16)
    url = oauth_service.get_google_auth_url(state)
    return RedirectResponse(url=url)


@router.get("/oauth/google/callback")
async def oauth_google_callback(
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth2 callback."""
    user = await oauth_service.handle_google_callback(db, code)
    result = await auth_service.login_oauth_user(db, user=user, request=request)
    response = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/auth/oauth-callback?access_token={result.access_token}",
    )
    _set_refresh_cookie(response, result.refresh_token)
    return response


# ── OAuth: GitHub ───────────────────────────────────────────


@router.get("/oauth/github")
async def oauth_github():
    """Redirect to GitHub OAuth2 authorization page."""
    state = secrets.token_urlsafe(16)
    url = oauth_service.get_github_auth_url(state)
    return RedirectResponse(url=url)


@router.get("/oauth/github/callback")
async def oauth_github_callback(
    code: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Handle GitHub OAuth2 callback."""
    user = await oauth_service.handle_github_callback(db, code)
    result = await auth_service.login_oauth_user(db, user=user, request=request)
    response = RedirectResponse(
        url=f"{settings.FRONTEND_URL}/auth/oauth-callback?access_token={result.access_token}",
    )
    _set_refresh_cookie(response, result.refresh_token)
    return response
