"""
schemas/user.py — User-related Pydantic schemas
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from models.user import UserRole


class UserResponse(BaseModel):
    """Public user profile response."""

    id: uuid.UUID
    email: str
    username: str
    role: UserRole
    avatar_url: Optional[str] = None
    bio: Optional[str] = None
    is_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdate(BaseModel):
    """User profile update request."""

    username: Optional[str] = Field(None, min_length=3, max_length=50)
    avatar_url: Optional[str] = Field(None, max_length=500)
    bio: Optional[str] = Field(None, max_length=1000)
