"""
services/audit_service.py — Audit logging service

Logs security-relevant events to the audit_logs table.
Actions use dot-notation: user.login, password.changed, security.token_reuse_detected, etc.
"""
from __future__ import annotations

import uuid
from typing import Any, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from models.audit import AuditLog


async def log_audit(
    db: AsyncSession,
    *,
    user_id: Optional[uuid.UUID] = None,
    action: str,
    resource_type: Optional[str] = None,
    resource_id: Optional[str] = None,
    request: Optional[Request] = None,
    metadata: Optional[dict[str, Any]] = None,
) -> None:
    """
    Create an audit log entry.

    Writes within the current transaction — does not create its own.
    """
    ip_address = None
    user_agent = None

    if request:
        ip_address = request.client.host if request.client else None
        user_agent = request.headers.get("user-agent")

    entry = AuditLog(
        user_id=user_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=ip_address,
        user_agent=user_agent,
        metadata_json=metadata,
    )
    db.add(entry)
    await db.flush()
