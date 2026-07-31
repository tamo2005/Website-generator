"""
main.py — FastAPI application entry point

Mounts all routers, configures middleware, and handles global exceptions.
All domain exceptions (AppError subclasses) are caught and returned in the
standard response envelope.
"""

import logging
import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from core.config import get_settings
from core.exceptions import AppError
from core.responses import api_error
from db.session import async_engine
from middleware.rate_limit import limiter, rate_limit_exceeded_handler
from middleware.request_id import RequestIDMiddleware
from middleware.security_headers import SecurityHeadersMiddleware
from utils.logging import setup_logging

# ── Setup structured logging ────────────────────────────────
setup_logging()
logger = structlog.get_logger("ai-site-gen")

settings = get_settings()

# ── CORS origins ────────────────────────────────────────────
_raw = settings.ALLOWED_ORIGIN
ALLOWED_ORIGINS = [o.strip() for o in _raw.split(",") if o.strip()]
for port in ("3000", "3001"):
    origin = f"http://localhost:{port}"
    if origin not in ALLOWED_ORIGINS:
        ALLOWED_ORIGINS.append(origin)


# ── Lifespan ────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "app.startup",
        cors=ALLOWED_ORIGINS,
    )
    yield
    await async_engine.dispose()
    logger.info("app.shutdown")


# ── Application ─────────────────────────────────────────────
app = FastAPI(
    title="AI Website Generator API",
    description="FastAPI + OpenRouter streaming HTML generator with authentication",
    version="2.0.0",
    lifespan=lifespan,
    docs_url="/api/v1/docs",
    redoc_url="/api/v1/redoc",
    openapi_url="/api/v1/openapi.json",
)


# ── Middleware (last added = outermost = first executed) ──────
# Order matters! CORSMiddleware MUST be outermost so CORS headers
# are always present — even when inner middleware or the app crashes.
app.add_middleware(RequestIDMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Authorization", "X-Request-ID"],
)


# ── Rate limiter ────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


# ── Routers ─────────────────────────────────────────────────
from api.auth.router import router as auth_router      # noqa: E402
from api.generation.router import router as gen_router  # noqa: E402

app.include_router(auth_router)
app.include_router(gen_router)


# ── Global exception handlers ───────────────────────────────


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    """
    Catch all domain exceptions and return the consistent error envelope.

    Avoids leaking internal details — only the message and code are exposed.
    """
    logger.warning(
        "domain_error",
        code=exc.code,
        message=exc.message,
        status=exc.status_code,
        path=str(request.url.path),
    )
    return api_error(
        code=exc.code,
        message=exc.message,
        request=request,
        status_code=exc.status_code,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Wrap Pydantic / FastAPI validation errors in the standard envelope."""
    errors = exc.errors()
    # Build a human-friendly summary
    messages = []
    for err in errors:
        loc = " → ".join(str(l) for l in err.get("loc", []))
        messages.append(f"{loc}: {err.get('msg', 'invalid')}")

    return api_error(
        code="VALIDATION_ERROR",
        message="; ".join(messages) if messages else "Request validation failed",
        request=request,
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Catch-all for unhandled exceptions.

    Logs the full traceback but returns a generic message to the client
    to avoid leaking internals (passwords, tokens, stack traces, etc.).
    """
    logger.error(
        "unhandled_exception",
        error=str(exc),
        path=str(request.url.path),
        exc_info=True,
    )
    return api_error(
        code="INTERNAL_ERROR",
        message="An internal server error occurred.",
        request=request,
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
    )


# ── Request logging middleware ───────────────────────────────


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """
    Log every request with method, path, status, and latency.

    Sensitive headers (Authorization, Cookie) are NOT logged.
    """
    start = time.perf_counter()
    response = await call_next(request)
    elapsed_ms = (time.perf_counter() - start) * 1000

    logger.info(
        "http_request",
        method=request.method,
        path=str(request.url.path),
        status=response.status_code,
        latency_ms=round(elapsed_ms, 1),
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent", "")[:120],
    )
    return response
