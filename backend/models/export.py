"""
models/export.py — Export tracking model
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class Export(Base):
    """Tracks a ZIP / HTML export event."""

    __tablename__ = "exports"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
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
    format: Mapped[str] = mapped_column(
        String(20), nullable=False, default="zip",
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    def __repr__(self) -> str:
        return f"<Export id={self.id} format={self.format}>"
