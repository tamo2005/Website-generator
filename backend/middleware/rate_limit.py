"""
middleware/rate_limit.py — Rate limiting with SlowAPI

In-memory rate limiter (upgradeable to Redis for production).
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse

# Create the limiter — in-memory for dev, swap storage_uri to redis:// for prod
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],
    storage_uri="memory://",
)


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded,
) -> JSONResponse:
    """Custom 429 response for rate-limited requests."""
    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please try again later.",
            "retry_after": str(exc.detail),
        },
    )
