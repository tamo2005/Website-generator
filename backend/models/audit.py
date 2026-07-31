"""
models/audit.py — Audit log model
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class AuditLog(Base):
    """
    Immutable audit trail for security-relevant events.

    Actions follow a dot-notation convention:
        user.login, user.register, password.changed, oauth.linked,
        generation.started, project.deleted, export.created,
        security.token_reuse_detected
    """

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True,
    )
    resource_type: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True,
    )
    resource_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True,
    )
    ip_address: Mapped[Optional[str]] = mapped_column(
        String(45), nullable=True,
    )
    user_agent: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
    )
    metadata_json: Mapped[Optional[dict]] = mapped_column(
        JSON, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<AuditLog id={self.id} action={self.action}>"
