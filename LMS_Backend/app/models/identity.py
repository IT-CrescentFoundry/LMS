"""Identity and access-control models (Stage B).

A ``UserAccount`` is a *system login identity*. It is deliberately not an employee
record: accounts can exist before or without employee data (ADR-040). Stage C3 adds a
nullable ``employee_id`` link; the generated ``linked_employee_active`` column makes
"at most one non-disabled account per employee" a database guarantee, while disabled
accounts keep their link as history.

``AccessRole`` / ``AccessPermission`` are *application access* concepts. They are
unrelated to functional job roles, designations or positions (organisation domain),
which never grant permissions.
"""

import uuid
from datetime import datetime
from enum import StrEnum

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    Computed,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.ids import uuid7
from app.db.base import Base
from app.db.types import BigIntKey, UTCDateTime, UUIDBinary, utcnow


class AccountStatus(StrEnum):
    PENDING_ACTIVATION = "pending_activation"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DISABLED = "disabled"


class ThrottleScope(StrEnum):
    IDENTIFIER = "identifier"
    IP = "ip"


def _sql_in(column: str, values: type[StrEnum]) -> str:
    return f"{column} IN ({', '.join(repr(member.value) for member in values)})"


class UserAccount(Base):
    __tablename__ = "user_account"
    __table_args__ = (
        CheckConstraint(_sql_in("status", AccountStatus), name="status_valid"),
        CheckConstraint(
            "status <> 'active' OR password_hash IS NOT NULL", name="active_requires_password"
        ),
        UniqueConstraint("linked_employee_active"),
        Index("ix_user_account_employee_id", "employee_id"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    public_id: Mapped[uuid.UUID] = mapped_column(UUIDBinary(), unique=True, default=uuid7)
    # Case-insensitive uniqueness comes from the utf8mb4_0900_ai_ci collation.
    login_id: Mapped[str] = mapped_column(String(64), unique=True)
    display_name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(254), unique=True)

    password_hash: Mapped[str | None] = mapped_column(String(255))
    password_created_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    password_changed_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    password_must_change: Mapped[bool] = mapped_column(Boolean, default=False)

    status: Mapped[str] = mapped_column(String(20), default=AccountStatus.PENDING_ACTIVATION.value)
    status_changed_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    status_reason: Mapped[str | None] = mapped_column(String(500))
    activated_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    deactivated_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    last_login_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("user_account.id"))
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)
    updated_by_user_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("user_account.id"))
    version: Mapped[int] = mapped_column(Integer)

    # Stage C3: link to an employee record (ADR-040). ``use_alter`` because employee
    # rows also reference user_account (created/updated by).
    employee_id: Mapped[int | None] = mapped_column(
        BigIntKey,
        ForeignKey("employee.id", use_alter=True, name="fk_user_account_employee_id_employee"),
    )
    linked_employee_active: Mapped[int | None] = mapped_column(
        BigIntKey,
        Computed(
            "IF(employee_id IS NOT NULL AND status <> 'disabled', employee_id, NULL)",
            persisted=True,
        ),
    )

    __mapper_args__ = {"version_id_col": version}  # noqa: RUF012 - SQLAlchemy mapper config

    @property
    def is_active(self) -> bool:
        return self.status == AccountStatus.ACTIVE


class AccessPermission(Base):
    __tablename__ = "access_permission"

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(100), unique=True)
    description: Mapped[str] = mapped_column(String(500))
    # Privileged permissions may only be held by roles that cannot be edited via the API.
    is_privileged: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)


class AccessRole(Base):
    __tablename__ = "access_role"

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    description: Mapped[str] = mapped_column(String(500))
    is_system: Mapped[bool] = mapped_column(Boolean, default=True)
    # False => the role can be granted/edited only through controlled CLI commands.
    is_api_assignable: Mapped[bool] = mapped_column(Boolean, default=True)
    # Permission an administrator must hold to grant or revoke this role.
    assign_permission_id: Mapped[int | None] = mapped_column(
        BigIntKey, ForeignKey("access_permission.id")
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)
    version: Mapped[int] = mapped_column(Integer)

    assign_permission: Mapped[AccessPermission | None] = relationship(lazy="joined")
    permissions: Mapped[list[AccessPermission]] = relationship(
        secondary="access_role_permission", viewonly=True, order_by=AccessPermission.code
    )

    __mapper_args__ = {"version_id_col": version}  # noqa: RUF012 - SQLAlchemy mapper config


class AccessRolePermission(Base):
    __tablename__ = "access_role_permission"
    __table_args__ = (UniqueConstraint("access_role_id", "access_permission_id"),)

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    access_role_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("access_role.id"))
    access_permission_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("access_permission.id"))
    granted_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    granted_by_user_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("user_account.id"))


class UserAccessRole(Base):
    """Grant of an access role to a user account. Revocations keep the row (history)."""

    __tablename__ = "user_access_role"
    __table_args__ = (
        # At most one *active* grant per (user, role); revoked rows have NULL here.
        UniqueConstraint("user_account_id", "access_role_id", "active_flag"),
        Index("ix_user_access_role_access_role_id", "access_role_id"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    user_account_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("user_account.id"))
    access_role_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("access_role.id"))
    granted_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    granted_by_user_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("user_account.id"))
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    revoked_by_user_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("user_account.id"))
    revoke_reason: Mapped[str | None] = mapped_column(String(500))
    active_flag: Mapped[int | None] = mapped_column(
        SmallInteger, Computed("IF(revoked_at IS NULL, 1, NULL)", persisted=True)
    )

    role: Mapped[AccessRole] = relationship(lazy="joined")


class UserSession(Base):
    """Server-side login session. Only the SHA-256 hash of the cookie token is stored."""

    __tablename__ = "user_session"
    __table_args__ = (
        Index("ix_user_session_user_account_id_revoked_at", "user_account_id", "revoked_at"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    public_id: Mapped[uuid.UUID] = mapped_column(UUIDBinary(), unique=True, default=uuid7)
    user_account_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("user_account.id"))
    token_hash: Mapped[str] = mapped_column(CHAR(64), unique=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    last_seen_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    idle_expires_at: Mapped[datetime] = mapped_column(UTCDateTime())
    absolute_expires_at: Mapped[datetime] = mapped_column(UTCDateTime())
    revoked_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    revoked_reason: Mapped[str | None] = mapped_column(String(30))
    revoked_by_user_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("user_account.id"))
    ip_address: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))

    user: Mapped[UserAccount] = relationship(foreign_keys=[user_account_id], lazy="joined")


class LoginThrottle(Base):
    """Failed-login counters (temporary lockout), separate from account status.

    ``key_hash`` is an HMAC of the submitted identifier or client IP; raw values
    are never stored.
    """

    __tablename__ = "login_throttle"
    __table_args__ = (
        UniqueConstraint("scope", "key_hash"),
        CheckConstraint(_sql_in("scope", ThrottleScope), name="scope_valid"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    scope: Mapped[str] = mapped_column(String(20))
    key_hash: Mapped[str] = mapped_column(CHAR(64))
    failure_count: Mapped[int] = mapped_column(Integer, default=0)
    window_started_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    last_failure_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    locked_until: Mapped[datetime | None] = mapped_column(UTCDateTime())
