"""
models/__init__.py — Import all models so Alembic can discover them.

Every model must be imported here for autogenerate to detect tables.
"""
from models.user import User, UserRole  # noqa: F401
from models.settings import UserSettings  # noqa: F401
from models.project import Project, ProjectVersion  # noqa: F401
from models.conversation import Conversation, Message  # noqa: F401
from models.generation import Generation  # noqa: F401
from models.export import Export  # noqa: F401
from models.token import (  # noqa: F401
    RefreshToken,
    PasswordResetToken,
    EmailVerificationToken,
)
from models.audit import AuditLog  # noqa: F401
from models.usage import UsageDaily  # noqa: F401

__all__ = [
    "User",
    "UserRole",
    "UserSettings",
    "Project",
    "ProjectVersion",
    "Conversation",
    "Message",
    "Generation",
    "Export",
    "RefreshToken",
    "PasswordResetToken",
    "EmailVerificationToken",
    "AuditLog",
    "UsageDaily",
]
