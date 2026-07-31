"""
models/conversation.py — Conversation and Message models
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db.base import Base, SoftDeleteMixin, TimestampMixin

if TYPE_CHECKING:
    from models.project import Project


class Conversation(Base, TimestampMixin, SoftDeleteMixin):
    """An AI conversation within a project."""

    __tablename__ = "conversations"

    id: Mapped[uuid.UUID] = mapped_column(
        primary_key=True, default=uuid.uuid4,
    )
    project_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True,
    )

    # ── Relationships ────────────────────────────────────────
    project: Mapped[Project] = relationship(
        "Project", back_populates="conversations",
    )
    messages: Mapped[list[Message]] = relationship(
        "Message", back_populates="conversation", lazy="noload",
        order_by="Message.created_at.asc()",
    )

    def __repr__(self) -> str:
        return f"<Conversation id={self.id} title={self.title!r}>"


class Message(Base):
    """A single message in a conversation (user, assistant, or system)."""

    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(
        String(20), nullable=False,
    )  # "user" | "assistant" | "system"
    content: Mapped[str] = mapped_column(
        Text, nullable=False,
    )
    token_count: Mapped[Optional[int]] = mapped_column(
        Integer, nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # ── Relationships ────────────────────────────────────────
    conversation: Mapped[Conversation] = relationship(
        "Conversation", back_populates="messages",
    )

    def __repr__(self) -> str:
        return f"<Message id={self.id} role={self.role}>"
