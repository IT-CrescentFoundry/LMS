"""Server-side login sessions.

* A new 256-bit random token is generated for every login (never reused, so a
  pre-set cookie cannot fixate a session); only its SHA-256 hash is stored.
* Sessions expire after an idle timeout (sliding) and an absolute timeout.
* Activity extends the idle window at most once per minute to limit writes.
* Revocation is server-side and immediate.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.context import RequestMeta
from app.core.security.tokens import generate_session_token, hash_session_token
from app.models.identity import UserAccount, UserSession

TOUCH_INTERVAL = timedelta(seconds=60)


class RevokeReason(StrEnum):
    LOGOUT = "logout"
    REPLACED = "replaced_by_login"
    PASSWORD_CHANGED = "password_changed"  # noqa: S105 - revocation reason code, not a credential
    PASSWORD_RESET = "password_reset"  # noqa: S105 - revocation reason code, not a credential
    ACCOUNT_SUSPENDED = "account_suspended"
    ACCOUNT_DISABLED = "account_disabled"
    ADMIN_REVOKED = "admin_revoked"


@dataclass(frozen=True)
class NewSession:
    token: str  # raw token: only ever placed in the Set-Cookie header
    record: UserSession


def start_session(
    db: Session, settings: Settings, user: UserAccount, meta: RequestMeta, now: datetime
) -> NewSession:
    token = generate_session_token()
    absolute = now + timedelta(hours=settings.session_absolute_timeout_hours)
    idle = min(now + timedelta(minutes=settings.session_idle_timeout_minutes), absolute)
    record = UserSession(
        user_account_id=user.id,
        token_hash=hash_session_token(token),
        created_at=now,
        last_seen_at=now,
        idle_expires_at=idle,
        absolute_expires_at=absolute,
        ip_address=meta.ip_address,
        user_agent=meta.user_agent,
    )
    db.add(record)
    db.flush()
    return NewSession(token=token, record=record)


def is_session_valid(record: UserSession, now: datetime) -> bool:
    return (
        record.revoked_at is None
        and now < record.idle_expires_at
        and now < record.absolute_expires_at
        and record.user.is_active
    )


def find_valid_session(db: Session, token: str, now: datetime) -> UserSession | None:
    record = db.scalars(
        select(UserSession).where(UserSession.token_hash == hash_session_token(token))
    ).one_or_none()
    if record is None or not is_session_valid(record, now):
        return None
    return record


def touch_session(settings: Settings, record: UserSession, now: datetime) -> bool:
    """Extend the idle window. Returns True if the record changed."""
    if now - record.last_seen_at < TOUCH_INTERVAL:
        return False
    record.last_seen_at = now
    record.idle_expires_at = min(
        now + timedelta(minutes=settings.session_idle_timeout_minutes), record.absolute_expires_at
    )
    return True


def revoke_session(
    record: UserSession, *, reason: RevokeReason, actor_user_id: int | None, now: datetime
) -> None:
    if record.revoked_at is None:
        record.revoked_at = now
        record.revoked_reason = reason.value
        record.revoked_by_user_id = actor_user_id


def revoke_user_sessions(
    db: Session,
    user_id: int,
    *,
    reason: RevokeReason,
    actor_user_id: int | None,
    now: datetime,
    except_session_id: int | None = None,
) -> int:
    """Revoke every active session of a user. Returns the number revoked."""
    statement = (
        update(UserSession)
        .where(UserSession.user_account_id == user_id, UserSession.revoked_at.is_(None))
        .values(revoked_at=now, revoked_reason=reason.value, revoked_by_user_id=actor_user_id)
        .execution_options(synchronize_session="fetch")
    )
    if except_session_id is not None:
        statement = statement.where(UserSession.id != except_session_id)
    result = db.execute(statement)
    return int(getattr(result, "rowcount", 0) or 0)
