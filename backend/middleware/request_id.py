"""
middleware/request_id.py — Request ID middleware

Assigns a unique ID to every request and includes it in:
- Response headers (X-Request-ID)
- Structured log context (via structlog contextvars)
- request.state.request_id
"""
from __future__ import annotations

import uuid

import structlog
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response


class RequestIDMiddleware(BaseHTTPMiddleware):
    """
    Middleware that assigns a unique request ID to every incoming request.

    If the client sends X-Request-ID, it's reused. Otherwise, one is generated.
    """

    async def dispatch(
        self, request: Request, call_next: RequestResponseEndpoint,
    ) -> Response:
        # Use client-provided ID or generate a short one
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:12]
        request.state.request_id = request_id

        # Bind to structlog context (appears in all logs for this request)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id

        return response
