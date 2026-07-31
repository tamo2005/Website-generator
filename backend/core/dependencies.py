"""
core/dependencies.py — FastAPI dependency injection

Reusable dependencies for authentication, authorization, and ownership.
Raises domain exceptions (never HTTPException).
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from core.exceptions import (
    AuthenticationError,
    AuthorizationError,
    NotFoundError,
)
from core.security import decode_access_token
from db.session import get_db
from models.user import User, UserRole
from repositories.user_repo import user_repo

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/v1/auth/login", auto_error=False,
)


async def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract + validate JWT → return authenticated User."""
    if not token:
        raise AuthenticationError(
            message="Not authenticated",
            code="NOT_AUTHENTICATED",
        )

    try:
        payload = decode_access_token(token)
        user_id = uuid.UUID(payload["sub"])
    except (JWTError, KeyError, ValueError):
        raise AuthenticationError(
            message="Invalid or expired token",
            code="INVALID_TOKEN",
        )

    user = await user_repo.get_by_id(db, user_id)
    if not user:
        raise AuthenticationError(
            message="User not found",
            code="USER_NOT_FOUND",
        )
    if not user.is_active:
        raise AuthorizationError(
            message="Account is deactivated",
            code="ACCOUNT_DEACTIVATED",
        )

    return user


async def get_current_active_user(
    user: User = Depends(get_current_user),
) -> User:
    """Require an active (non-deleted, non-deactivated) user."""
    return user


async def get_current_verified_user(
    user: User = Depends(get_current_active_user),
) -> User:
    """Require a user with a verified email address."""
    if not user.is_verified:
        raise AuthorizationError(
            message="Email not verified. Please verify your email to continue.",
            code="EMAIL_NOT_VERIFIED",
        )
    return user


def require_role(*roles: UserRole):
    """Dependency factory: require the user to have one of the given roles."""

    async def check_role(user: User = Depends(get_current_verified_user)) -> User:
        if user.role not in roles:
            raise AuthorizationError(
                message="Insufficient permissions",
                code="INSUFFICIENT_ROLE",
            )
        return user

    return check_role


def require_owner(resource_type: str):
    """
    Dependency factory: verify the current user owns the requested resource.

    Prevents horizontal privilege escalation.
    """

    async def check_ownership(
        resource_id: uuid.UUID,
        current_user: User = Depends(get_current_verified_user),
        db: AsyncSession = Depends(get_db),
    ):
        from models.conversation import Conversation
        from models.project import Project

        model_map = {
            "project": Project,
            "conversation": Conversation,
        }

        model = model_map.get(resource_type)
        if not model:
            raise NotFoundError(
                message=f"Unknown resource type: {resource_type}",
                code="UNKNOWN_RESOURCE",
            )

        resource = await db.get(model, resource_id)
        if not resource or (
            hasattr(resource, "deleted_at") and resource.deleted_at is not None
        ):
            raise NotFoundError(
                message="Resource not found",
                code=f"{resource_type.upper()}_NOT_FOUND",
            )
        if resource.user_id != current_user.id:
            raise AuthorizationError(
                message="You don't have access to this resource",
                code="OWNERSHIP_VIOLATION",
            )
        return resource

    return check_ownership
