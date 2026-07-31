"""
models/project.py — Project and ProjectVersion models
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.types import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from models.conversation import Conversation
    from models.user import User


class Project(Base, TimestampMixin, SoftDeleteMixin):
    """A website generation project owned by a user."""

    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(
        String(255), nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True,
    )

    # ── Relationships ────────────────────────────────────────
    user: Mapped[User] = relationship(
        "User", back_populates="projects",
    )
    versions: Mapped[list[ProjectVersion]] = relationship(
        "ProjectVersion", back_populates="project", lazy="noload",
        order_by="ProjectVersion.version_number.desc()",
    )
    conversations: Mapped[list[Conversation]] = relationship(
        "Conversation", back_populates="project", lazy="noload",
    )

    def __repr__(self) -> str:
        return f"<Project id={self.id} name={self.name!r}>"


class ProjectVersion(Base):
    """An immutable snapshot of a project's generated output."""

    __tablename__ = "project_versions"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number: Mapped[int] = mapped_column(
        Integer, nullable=False,
    )
    html_content: Mapped[str] = mapped_column(
        Text, nullable=False,
    )
    css_content: Mapped[Optional[str]] = mapped_column(
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

    # ── Relationships ────────────────────────────────────────
    project: Mapped[Project] = relationship(
        "Project", back_populates="versions",
    )

    def __repr__(self) -> str:
        return f"<ProjectVersion id={self.id} v{self.version_number}>"
