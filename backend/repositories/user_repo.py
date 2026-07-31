"""
repositories/user_repo.py — User database operations

All SQLAlchemy queries for the User model live here.
Services call this layer; they never touch SQLAlchemy directly.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User, UserRole


class UserRepository:
    """CRUD operations for the User model."""

    @staticmethod
    async def get_by_id(db: AsyncSession, user_id: uuid.UUID) -> Optional[User]:
        result = await db.execute(
            select(User).where(User.id == user_id, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_email(db: AsyncSession, email: str) -> Optional[User]:
        result = await db.execute(
            select(User).where(User.email == email, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_username(db: AsyncSession, username: str) -> Optional[User]:
        result = await db.execute(
            select(User).where(User.username == username, User.deleted_at.is_(None))
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_by_oauth(
        db: AsyncSession, provider: str, oauth_id: str,
    ) -> Optional[User]:
        result = await db.execute(
            select(User).where(
                User.oauth_provider == provider,
                User.oauth_id == oauth_id,
                User.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        email: str,
        username: str,
        hashed_password: Optional[str] = None,
        role: UserRole = UserRole.USER,
        is_verified: bool = False,
        oauth_provider: Optional[str] = None,
        oauth_id: Optional[str] = None,
        avatar_url: Optional[str] = None,
    ) -> User:
        user = User(
            email=email,
            username=username,
            hashed_password=hashed_password,
            role=role,
            is_verified=is_verified,
            oauth_provider=oauth_provider,
            oauth_id=oauth_id,
            avatar_url=avatar_url,
        )
        db.add(user)
        await db.flush()
        return user

    @staticmethod
    async def update(db: AsyncSession, user: User, **kwargs) -> User:
        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)
        await db.flush()
        return user

    @staticmethod
    async def soft_delete(db: AsyncSession, user: User) -> User:
        user.deleted_at = datetime.now(timezone.utc)
        await db.flush()
        return user


# Singleton instance for convenience
user_repo = UserRepository()
