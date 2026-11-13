"""User-account administration schemas. No schema exposes password hashes or tokens."""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, SecretStr

from app.services.identity.permissions import DEFAULT_ROLE

DisplayName = Annotated[str, Field(min_length=1, max_length=200)]
# Optional contact address; a basic shape check is sufficient (it is not a login ID).
EmailAddress = Annotated[str, Field(max_length=254, pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$")]
Reason = Annotated[str, Field(max_length=500)]
TemporaryPassword = Annotated[SecretStr, Field(min_length=1, max_length=1024)]


class RoleGrantOut(BaseModel):
    role: str
    granted_at: datetime


class UserSummary(BaseModel):
    public_id: uuid.UUID
    login_id: str
    display_name: str
    email: str | None
    status: str
    roles: list[str]
    last_login_at: datetime | None
    created_at: datetime


class UserDetail(UserSummary):
    password_must_change: bool
    status_changed_at: datetime
    status_reason: str | None
    activated_at: datetime | None
    deactivated_at: datetime | None
    password_changed_at: datetime | None
    role_grants: list[RoleGrantOut]


class CreateUserRequest(BaseModel):
    login_id: Annotated[str, Field(min_length=2, max_length=64)]
    display_name: DisplayName
    email: EmailAddress | None = None
    temporary_password: TemporaryPassword
    roles: list[str] = Field(default_factory=lambda: [DEFAULT_ROLE], max_length=10)


class UpdateUserRequest(BaseModel):
    display_name: DisplayName | None = None
    email: EmailAddress | None = None


class StatusChangeRequest(BaseModel):
    reason: Reason | None = None


class PasswordResetRequest(BaseModel):
    temporary_password: TemporaryPassword


class RoleAssignmentRequest(BaseModel):
    role: Annotated[str, Field(min_length=1, max_length=50)]


class SessionOut(BaseModel):
    public_id: uuid.UUID
    created_at: datetime
    last_seen_at: datetime
    idle_expires_at: datetime
    absolute_expires_at: datetime
    ip_address: str | None
    user_agent: str | None


class RevokedCount(BaseModel):
    revoked: int
