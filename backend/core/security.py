"""
core/security.py — JWT token creation/verification and password hashing

Cryptographic primitives used by the auth service.
Does NOT touch the database — that's the repository's job.
"""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from jose import JWTError, jwt
import bcrypt

from core.config import get_settings

settings = get_settings()


def hash_password(plain: str) -> str:
    """Hash a plaintext password with bcrypt."""
    pw_bytes = plain.encode("utf-8")
    if len(pw_bytes) > 72:
        pw_bytes = pw_bytes[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(pw_bytes, salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plaintext password against a bcrypt hash."""
    pw_bytes = plain.encode("utf-8")
    if len(pw_bytes) > 72:
        pw_bytes = pw_bytes[:72]
    try:
        return bcrypt.checkpw(pw_bytes, hashed.encode("utf-8"))
    except Exception:
        return False


def create_access_token(
    user_id: str,
    role: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    now = datetime.now(timezone.utc)
    expire = now + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "iss": "ai-website-generator",
        "nbf": now,
        "iat": now,
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(
        payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Raises jose.JWTError on invalid/expired tokens.
    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM],
    )
    if payload.get("type") != "access":
        raise JWTError("Invalid token type")
    return payload


def generate_token(nbytes: int = 32) -> str:
    """Generate a cryptographically secure random token (URL-safe)."""
    return secrets.token_urlsafe(nbytes)


def hash_token(token: str) -> str:
    """SHA-256 hash a token for safe database storage."""
    return hashlib.sha256(token.encode()).hexdigest()
