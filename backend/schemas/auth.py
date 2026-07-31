"""
schemas/auth.py — Authentication request/response Pydantic schemas
"""
from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    """User registration request."""

    email: EmailStr
    username: str = Field(min_length=3, max_length=50, pattern=r"^[a-zA-Z0-9_-]+$")
    password: str = Field(min_length=8, max_length=128)


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr
    password: str = Field(min_length=1)


class TokenResponse(BaseModel):
    """Access token response (refresh token lives in HttpOnly cookie)."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds


class ForgotPasswordRequest(BaseModel):
    """Password reset request — email only."""

    email: EmailStr


class ResetPasswordRequest(BaseModel):
    """Password reset with token."""

    token: str
    new_password: str = Field(min_length=8, max_length=128)


class VerifyEmailRequest(BaseModel):
    """Email verification with token."""

    token: str
