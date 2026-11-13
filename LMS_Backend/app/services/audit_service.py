"""Central audit-event recording.

``record_audit_event`` adds the event to the caller's session, so it commits (or
rolls back) atomically with the change it describes. It never commits by itself.

Metadata must be small, structured and free of secrets: keys that suggest secrets
(password, token, secret, hash, csrf, cookie, credential) are rejected outright.
"""

from collections.abc import Mapping
from enum import StrEnum
from typing import Any

from sqlalchemy.orm import Session

from app.core.context import RequestMeta
from app.models.audit import AuditEvent, AuditOutcome


class AuditEventType(StrEnum):
    LOGIN_SUCCEEDED = "auth.login.succeeded"
    LOGIN_FAILED = "auth.login.failed"
    LOGIN_THROTTLED = "auth.login.throttled"
    LOGIN_DENIED_INACTIVE = "auth.login.denied_inactive"
    LOGOUT = "auth.logout"
    PASSWORD_CHANGED = "auth.password.changed"  # noqa: S105 - audit event code, not a credential
    PASSWORD_CHANGE_FAILED = "auth.password.change_failed"  # noqa: S105 - audit event code, not a credential
    ACCOUNT_CREATED = "user_account.created"
    ACCOUNT_UPDATED = "user_account.updated"
    ACCOUNT_ACTIVATED = "user_account.activated"
    ACCOUNT_SUSPENDED = "user_account.suspended"
    ACCOUNT_DISABLED = "user_account.disabled"
    ACCOUNT_PASSWORD_RESET = "user_account.password_reset"  # noqa: S105 - audit event code, not a credential
    SESSION_REVOKED = "user_session.revoked"
    SESSIONS_REVOKED_ALL = "user_session.revoked_all"
    ROLE_GRANTED = "access_role.granted"
    ROLE_REVOKED = "access_role.revoked"
    ROLE_PERMISSION_GRANTED = "access_role.permission_granted"
    ROLE_PERMISSION_REVOKED = "access_role.permission_revoked"
    SUPER_ADMIN_BOOTSTRAPPED = "super_admin.bootstrapped"
    SUPER_ADMIN_GRANTED = "super_admin.granted"
    SUPER_ADMIN_REVOKED = "super_admin.revoked"
    AUTHORIZATION_DENIED = "authorization.denied"
    AUDIT_VIEWED = "audit.events.viewed"


class TargetType(StrEnum):
    USER_ACCOUNT = "user_account"
    USER_SESSION = "user_session"
    ACCESS_ROLE = "access_role"


_FORBIDDEN_KEY_FRAGMENTS = ("password", "token", "secret", "hash", "csrf", "cookie", "credential")


class UnsafeAuditMetadataError(ValueError):
    """Raised when audit metadata contains a key that could hold a secret."""


def _check_metadata(value: Any, path: str = "metadata") -> None:
    if isinstance(value, Mapping):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(fragment in lowered for fragment in _FORBIDDEN_KEY_FRAGMENTS):
                raise UnsafeAuditMetadataError(f"Audit {path} may not contain key {key!r}.")
            _check_metadata(child, f"{path}.{key}")
    elif isinstance(value, list | tuple):
        for item in value:
            _check_metadata(item, path)


def record_audit_event(
    db: Session,
    *,
    event_type: AuditEventType,
    outcome: AuditOutcome,
    meta: RequestMeta,
    actor_user_id: int | None = None,
    target_type: TargetType | None = None,
    target_id: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> AuditEvent:
    if metadata is not None:
        _check_metadata(metadata)
    event = AuditEvent(
        event_type=event_type.value,
        outcome=outcome.value,
        actor_user_id=actor_user_id,
        target_type=target_type.value if target_type else None,
        target_id=target_id,
        request_id=meta.request_id,
        source_ip=meta.ip_address,
        user_agent=meta.user_agent,
        event_metadata=dict(metadata) if metadata is not None else None,
    )
    db.add(event)
    return event
