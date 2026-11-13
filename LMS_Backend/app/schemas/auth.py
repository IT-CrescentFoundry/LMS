"""Authentication request/response schemas.

Passwords are ``SecretStr`` so they are masked in any repr, log or error.
Responses never contain password hashes or session tokens; the session token is
sent only in the HttpOnly cookie.
"""

import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, Field, SecretStr

LoginIdField = Annotated[str, Field(min_length=1, max_length=128)]
PasswordField = Annotated[SecretStr, Field(min_length=1, max_length=1024)]


class LoginRequest(BaseModel):
    login_id: LoginIdField
    password: PasswordField


class ChangePasswordRequest(BaseModel):
    current_password: PasswordField
    new_password: PasswordField


class CurrentUser(BaseModel):
    public_id: uuid.UUID
    login_id: str
    display_name: str
    email: str | None
    status: str
    password_must_change: bool
    roles: list[str]
    permissions: list[str]


class SessionResponse(BaseModel):
    authenticated: bool
    user: CurrentUser | None = None
    csrf_token: str | None = Field(
        default=None,
        description="Send in the X-CSRF-Token header on state-changing requests.",
    )
    idle_expires_at: datetime | None = None
    absolute_expires_at: datetime | None = None
