"""
models/user.py — User model and UserRole enum
"""
from __future__ import annotations

import enum
import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Enum, String, Text
import sqlalchemy as sa
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from models.project import Project
    from models.settings import UserSettings
    from models.token import RefreshToken


class UserRole(str, enum.Enum):
    """User role enum for role-based access control."""

    ADMIN = "admin"
    USER = "user"
    MODERATOR = "moderator"


class User(Base, TimestampMixin, SoftDeleteMixin):
    """User account."""

    __tablename__ = "users"
    __table_args__ = (
        sa.UniqueConstraint(
            "oauth_provider", "oauth_id",
            name="uq_users_oauth_provider_id",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False,
    )
    username: Mapped[str] = mapped_column(
        String(50), unique=True, index=True, nullable=False,
    )
    hashed_password: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True,
    )  # None for OAuth-only users
    role: Mapped[UserRole] = mapped_column(
        Enum(UserRole, name="user_role", create_constraint=True),
        default=UserRole.USER,
        nullable=False,
    )
    avatar_url: Mapped[Optional[str]] = mapped_column(
        String(500), nullable=True,
    )
    bio: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
    )
    is_verified: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False,
    )
    oauth_provider: Mapped[Optional[str]] = mapped_column(
        String(20), nullable=True,
    )
    oauth_id: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True,
    )

    # ── Relationships ────────────────────────────────────────
    settings: Mapped[Optional[UserSettings]] = relationship(
        "UserSettings", back_populates="user", uselist=False, lazy="noload",
    )
    refresh_tokens: Mapped[list[RefreshToken]] = relationship(
        "RefreshToken", back_populates="user", lazy="noload",
    )
    projects: Mapped[list[Project]] = relationship(
        "Project", back_populates="user", lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<User id={self.id} email={self.email}>"
