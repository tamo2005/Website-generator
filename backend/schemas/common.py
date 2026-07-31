"""
schemas/common.py — Shared Pydantic schemas
"""
from pydantic import BaseModel


class MessageResponse(BaseModel):
    """Generic success/error message response."""

    message: str
