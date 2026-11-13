"""SQLAlchemy ORM models.

Every model module must be imported here so that ``Base.metadata`` is complete
when Alembic compares it with the database (autogenerate).

The proposed schema for later stages is documented in
``docs/database/LMS_DATABASE_DESIGN.md``.
"""

from app.db.base import Base
from app.models.audit import AuditEvent, AuditOutcome
from app.models.identity import (
    AccessPermission,
    AccessRole,
    AccessRolePermission,
    AccountStatus,
    LoginThrottle,
    ThrottleScope,
    UserAccessRole,
    UserAccount,
    UserSession,
)

__all__ = [
    "AccessPermission",
    "AccessRole",
    "AccessRolePermission",
    "AccountStatus",
    "AuditEvent",
    "AuditOutcome",
    "Base",
    "LoginThrottle",
    "ThrottleScope",
    "UserAccessRole",
    "UserAccount",
    "UserSession",
]
