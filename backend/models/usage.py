"""
models/usage.py — Daily usage tracking model
"""
from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from db.base import Base


class UsageDaily(Base):
    """
    Aggregated daily usage stats per user.

    The (user_id, date) pair is unique — one row per user per day.
    """

    __tablename__ = "usage_daily"
    __table_args__ = (
        UniqueConstraint("user_id", "date", name="uq_usage_daily_user_date"),
    )

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    date: Mapped[date] = mapped_column(
        Date, nullable=False, index=True,
    )
    generation_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
    )
    tokens_used: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
    )
    export_count: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False,
    )

    def __repr__(self) -> str:
        return f"<UsageDaily user_id={self.user_id} date={self.date}>"
