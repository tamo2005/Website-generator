"""
models/generation.py — Generation tracking model
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Generation(Base):
    """Tracks a single AI generation event."""

    __tablename__ = "generations"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    message_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("messages.id", ondelete="SET NULL"),
        nullable=True,
    )
    project_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        ForeignKey("projects.id", ondelete="SET NULL"),
        nullable=True,
    )
    version_id: Mapped[Optional[int]] = mapped_column(
        BigInteger, ForeignKey("project_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    model_used: Mapped[str] = mapped_column(
        String(100), nullable=False,
    )
    prompt_tokens: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
    )
    completion_tokens: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
    )
    total_time_ms: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Generation id={self.id} model={self.model_used}>"
