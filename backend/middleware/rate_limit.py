"""
middleware/rate_limit.py — Rate limiting with SlowAPI

Phase 2: Uses Redis as the storage backend for distributed rate limiting.
In development, falls back to in-memory if REDIS_URL is not reachable.
"""
from __future__ import annotations

from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from starlette.requests import Request
from starlette.responses import JSONResponse

from core.config import get_settings

settings = get_settings()

storage_uri = settings.REDIS_URL if settings.REDIS_URL.startswith("redis") else "memory://"

# In dev/test environments without a running Redis container, fall back to memory://
try:
    if storage_uri.startswith("redis"):
        import redis as py_redis
        r = py_redis.from_url(storage_uri, socket_connect_timeout=1)
        r.ping()
except Exception:
    storage_uri = "memory://"

limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],
    storage_uri=storage_uri,
)


async def rate_limit_exceeded_handler(
    request: Request, exc: RateLimitExceeded,
) -> JSONResponse:
    """Custom 429 response for rate-limited requests."""
    return JSONResponse(
        status_code=429,
        content={
            "success": False,
            "error": {
                "code": "RATE_LIMIT_EXCEEDED",
                "message": "Too many requests. Please slow down and try again.",
                "retry_after": str(exc.detail),
            },
        },
    )
