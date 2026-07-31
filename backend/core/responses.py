"""
core/responses.py — Standardised API response helpers

Every API response follows a consistent envelope:

    Success: { "success": true,  "data": {...}, "message": "...", "request_id": "..." }
    Error:   { "success": false, "error": { "code": "...", "message": "..." }, "request_id": "..." }

Routers call api_response(); the global exception handler calls api_error().
"""
from __future__ import annotations

from datetime import datetime, date
from typing import Any, Optional
from uuid import UUID

from fastapi import Request
from fastapi.responses import JSONResponse


def _get_request_id(request: Optional[Request]) -> Optional[str]:
    """Safely extract the request ID set by RequestIDMiddleware."""
    if request is None:
        return None
    return getattr(request.state, "request_id", None)


def _serialize(obj: Any) -> Any:
    """Make non-JSON-serializable types safe for JSONResponse."""
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if hasattr(obj, "model_dump"):          # Pydantic v2
        return obj.model_dump(mode="json")
    if hasattr(obj, "dict"):                # Pydantic v1 fallback
        return obj.dict()
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(i) for i in obj]
    return obj


def api_response(
    data: Any = None,
    message: Optional[str] = None,
    request: Optional[Request] = None,
    status_code: int = 200,
) -> JSONResponse:
    """
    Build a standardised success response.

    Usage in a router::

        return api_response(
            data=UserResponse.model_validate(user),
            message="Account created",
            request=request,
            status_code=201,
        )
    """
    body: dict[str, Any] = {
        "success": True,
        "data": _serialize(data),
        "message": message,
        "request_id": _get_request_id(request),
    }
    return JSONResponse(content=body, status_code=status_code)


def api_error(
    code: str,
    message: str,
    request: Optional[Request] = None,
    status_code: int = 400,
) -> JSONResponse:
    """
    Build a standardised error response.

    Typically called by the global exception handler, not directly by routers.
    """
    body: dict[str, Any] = {
        "success": False,
        "error": {
            "code": code,
            "message": message,
        },
        "request_id": _get_request_id(request),
    }
    return JSONResponse(content=body, status_code=status_code)
