"""
models/settings.py — User settings model
"""
from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, TimestampMixin

if TYPE_CHECKING:
    from models.user import User


class UserSettings(Base, TimestampMixin):
    """Per-user application settings."""

    __tablename__ = "user_settings"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True,
    )
    theme: Mapped[str] = mapped_column(
        String(20), default="dark", nullable=False,
    )
    preferred_model: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True,
    )
    default_export_format: Mapped[str] = mapped_column(
        String(20), default="zip", nullable=False,
    )
    notifications_enabled: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False,
    )

    # ── Relationships ────────────────────────────────────────
    user: Mapped[User] = relationship(
        "User", back_populates="settings",
    )

    def __repr__(self) -> str:
        return f"<UserSettings user_id={self.user_id} theme={self.theme}>"
