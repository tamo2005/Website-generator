"""
core/exceptions.py — Domain exception hierarchy

Services raise these instead of HTTPException.
A global exception handler in main.py maps them to consistent JSON responses.

Hierarchy:

    AppError
    ├── AuthenticationError     (401)
    ├── AuthorizationError      (403)
    ├── ValidationError         (422)
    ├── ConflictError           (409)
    ├── NotFoundError           (404)
    ├── RateLimitError          (429)
    └── TokenReuseDetected      (401 + security event)
"""
from __future__ import annotations


class AppError(Exception):
    """Base application error. All domain exceptions inherit from this."""

    def __init__(
        self,
        message: str = "An unexpected error occurred",
        code: str = "INTERNAL_ERROR",
        status_code: int = 500,
    ):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class AuthenticationError(AppError):
    """Invalid credentials, expired/missing tokens."""

    def __init__(
        self,
        message: str = "Invalid credentials",
        code: str = "AUTHENTICATION_FAILED",
    ):
        super().__init__(message=message, code=code, status_code=401)


class AuthorizationError(AppError):
    """Insufficient permissions or ownership violation."""

    def __init__(
        self,
        message: str = "Insufficient permissions",
        code: str = "FORBIDDEN",
    ):
        super().__init__(message=message, code=code, status_code=403)


class ValidationError(AppError):
    """Business-rule validation failure (not Pydantic schema validation)."""

    def __init__(
        self,
        message: str = "Validation failed",
        code: str = "VALIDATION_ERROR",
    ):
        super().__init__(message=message, code=code, status_code=422)


class ConflictError(AppError):
    """Duplicate resource (email, username, etc.)."""

    def __init__(
        self,
        message: str = "Resource already exists",
        code: str = "CONFLICT",
    ):
        super().__init__(message=message, code=code, status_code=409)


class NotFoundError(AppError):
    """Requested resource does not exist."""

    def __init__(
        self,
        message: str = "Resource not found",
        code: str = "NOT_FOUND",
    ):
        super().__init__(message=message, code=code, status_code=404)


class RateLimitError(AppError):
    """Request rate limit exceeded."""

    def __init__(
        self,
        message: str = "Too many requests. Please try again later.",
        code: str = "RATE_LIMITED",
    ):
        super().__init__(message=message, code=code, status_code=429)


class ServiceUnavailableError(AppError):
    """External service unavailable or not configured (OAuth, email, etc.)."""

    def __init__(
        self,
        message: str = "Service temporarily unavailable",
        code: str = "SERVICE_UNAVAILABLE",
    ):
        super().__init__(message=message, code=code, status_code=503)


class TokenReuseDetected(AppError):
    """
    A revoked refresh token was reused — potential token theft.

    Triggers: revoke ALL user sessions + security audit log.
    """

    def __init__(
        self,
        message: str = "Token reuse detected. All sessions have been revoked for security.",
        code: str = "TOKEN_REUSE_DETECTED",
    ):
        super().__init__(message=message, code=code, status_code=401)
