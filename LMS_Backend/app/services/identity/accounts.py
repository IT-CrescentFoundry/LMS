"""User-account administration.

Lifecycle::

    pending_activation ──activate──► active ──suspend──► suspended ──activate──► active
            │                          │                     │
            └────────── disable ───────┴──── disable ────────┘──► disabled ──activate──► active

* Accounts created by administrators start ``pending_activation`` with a temporary
  password and ``password_must_change``.
* Suspending or disabling revokes every active session immediately.
* Every change is audited in the same transaction.
"""

import base64
import binascii
import re
import uuid
from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.context import RequestMeta
from app.core.errors import AppError
from app.core.security.passwords import hash_password, password_policy_issues
from app.models.audit import AuditOutcome
from app.models.identity import AccountStatus, UserAccount, UserSession
from app.schemas.errors import ValidationIssue
from app.services.audit_service import AuditEventType, TargetType, record_audit_event
from app.services.identity.access_control import (
    ensure_can_manage_account,
    grant_roles,
    manageable_by,
)
from app.services.identity.context import Actor
from app.services.identity.sessions import RevokeReason, revoke_session, revoke_user_sessions

LOGIN_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,63}$")

_ALLOWED_TRANSITIONS: dict[AccountStatus, frozenset[AccountStatus]] = {
    AccountStatus.PENDING_ACTIVATION: frozenset({AccountStatus.ACTIVE, AccountStatus.DISABLED}),
    AccountStatus.ACTIVE: frozenset({AccountStatus.SUSPENDED, AccountStatus.DISABLED}),
    AccountStatus.SUSPENDED: frozenset({AccountStatus.ACTIVE, AccountStatus.DISABLED}),
    AccountStatus.DISABLED: frozenset({AccountStatus.ACTIVE}),
}
_STATUS_EVENTS = {
    AccountStatus.ACTIVE: AuditEventType.ACCOUNT_ACTIVATED,
    AccountStatus.SUSPENDED: AuditEventType.ACCOUNT_SUSPENDED,
    AccountStatus.DISABLED: AuditEventType.ACCOUNT_DISABLED,
}
_STATUS_REVOKE_REASONS = {
    AccountStatus.SUSPENDED: RevokeReason.ACCOUNT_SUSPENDED,
    AccountStatus.DISABLED: RevokeReason.ACCOUNT_DISABLED,
}


def normalise_login_id(login_id: str) -> str:
    candidate = login_id.strip()
    if not LOGIN_ID_PATTERN.fullmatch(candidate):
        raise AppError(
            422,
            "invalid_login_id",
            "Login IDs are 2-64 characters: letters, digits, '.', '_' or '-', "
            "starting with a letter or digit.",
        )
    return candidate


def ensure_password_policy(
    settings: Settings, password: str, *, login_id: str | None, field: str
) -> None:
    issues = password_policy_issues(
        password, min_length=settings.password_min_length, login_id=login_id
    )
    if issues:
        raise AppError(
            422,
            "password_policy",
            "The password does not meet the password policy.",
            details=[
                ValidationIssue(location=["body", field], message=issue, type=issue)
                for issue in issues
            ],
        )


def _ensure_unique(
    db: Session, *, login_id: str | None, email: str | None, exclude_id: int | None
) -> None:
    conditions = []
    if login_id:
        conditions.append(UserAccount.login_id == login_id)
    if email:
        conditions.append(UserAccount.email == email)
    if not conditions:
        return
    query = select(UserAccount.login_id, UserAccount.email).where(or_(*conditions))
    if exclude_id is not None:
        query = query.where(UserAccount.id != exclude_id)
    for existing_login, existing_email in db.execute(query):
        if login_id and existing_login.casefold() == login_id.casefold():
            raise AppError(409, "login_id_taken", "This login ID is already in use.")
        if email and existing_email and existing_email.casefold() == email.casefold():
            raise AppError(409, "email_taken", "This email address is already in use.")


def _like_pattern(text: str) -> str:
    escaped = text.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def _flush_unique(db: Session) -> None:
    try:
        db.flush()
    except IntegrityError as exc:  # concurrent insert of the same login ID / email
        raise AppError(409, "conflict", "The login ID or email is already in use.") from exc


def get_account(db: Session, public_id: uuid.UUID) -> UserAccount:
    account = db.scalars(
        select(UserAccount).where(UserAccount.public_id == public_id)
    ).one_or_none()
    if account is None:
        raise AppError(404, "user_not_found", "User account not found.")
    return account


def create_account(
    db: Session,
    settings: Settings,
    *,
    actor: Actor,
    login_id: str,
    display_name: str,
    email: str | None,
    temporary_password: str,
    role_codes: Sequence[str],
    meta: RequestMeta,
    now: datetime,
) -> UserAccount:
    login_id = normalise_login_id(login_id)
    ensure_password_policy(
        settings, temporary_password, login_id=login_id, field="temporary_password"
    )
    _ensure_unique(db, login_id=login_id, email=email, exclude_id=None)
    account = UserAccount(
        login_id=login_id,
        display_name=display_name.strip(),
        email=email,
        password_hash=hash_password(temporary_password),
        password_created_at=now,
        password_changed_at=now,
        password_must_change=True,
        status=AccountStatus.PENDING_ACTIVATION.value,
        status_changed_at=now,
        created_by_user_id=actor.user_id,
        updated_by_user_id=actor.user_id,
    )
    db.add(account)
    _flush_unique(db)
    record_audit_event(
        db,
        event_type=AuditEventType.ACCOUNT_CREATED,
        outcome=AuditOutcome.SUCCESS,
        meta=meta,
        actor_user_id=actor.user_id,
        target_type=TargetType.USER_ACCOUNT,
        target_id=str(account.public_id),
        metadata={"login_id": account.login_id, "roles": list(dict.fromkeys(role_codes))},
    )
    grant_roles(db, actor=actor, target=account, role_codes=role_codes, meta=meta, now=now)
    return account


def update_account(
    db: Session,
    *,
    actor: Actor,
    target: UserAccount,
    display_name: str | None,
    email: str | None,
    email_provided: bool,
    meta: RequestMeta,
) -> UserAccount:
    ensure_can_manage_account(db, actor, target)
    changed: list[str] = []
    if display_name is not None and display_name.strip() != target.display_name:
        target.display_name = display_name.strip()
        changed.append("display_name")
    if email_provided and email != target.email:
        _ensure_unique(db, login_id=None, email=email, exclude_id=target.id)
        target.email = email
        changed.append("email")
    if changed:
        target.updated_by_user_id = actor.user_id
        _flush_unique(db)
        record_audit_event(
            db,
            event_type=AuditEventType.ACCOUNT_UPDATED,
            outcome=AuditOutcome.SUCCESS,
            meta=meta,
            actor_user_id=actor.user_id,
            target_type=TargetType.USER_ACCOUNT,
            target_id=str(target.public_id),
            metadata={"fields": changed},
        )
    return target


def _active_link_error() -> AppError:
    return AppError(
        409,
        "employee_has_active_account",
        "The linked employee already has another account that is not disabled.",
    )


def _ensure_no_other_active_link(db: Session, target: UserAccount) -> None:
    """Re-enabling a disabled account must keep one non-disabled account per employee."""
    other = db.scalar(
        select(UserAccount.id)
        .where(
            UserAccount.employee_id == target.employee_id,
            UserAccount.id != target.id,
            UserAccount.status != AccountStatus.DISABLED.value,
        )
        .with_for_update(read=True)
        .limit(1)
    )
    if other is not None:
        raise _active_link_error()


def change_account_status(
    db: Session,
    *,
    actor: Actor,
    target: UserAccount,
    new_status: AccountStatus,
    reason: str | None,
    meta: RequestMeta,
    now: datetime,
) -> UserAccount:
    ensure_can_manage_account(db, actor, target)
    current = AccountStatus(target.status)
    if new_status not in _ALLOWED_TRANSITIONS[current]:
        raise AppError(
            409,
            "invalid_status_transition",
            f"An account cannot move from {current.value} to {new_status.value}.",
        )
    if new_status is AccountStatus.ACTIVE and target.password_hash is None:
        raise AppError(409, "password_required", "Set a password before activating the account.")
    if current is AccountStatus.DISABLED and target.employee_id is not None:
        _ensure_no_other_active_link(db, target)

    target.status = new_status.value
    target.status_changed_at = now
    target.status_reason = reason
    target.updated_by_user_id = actor.user_id
    if new_status is AccountStatus.ACTIVE:
        target.activated_at = now
    if new_status is AccountStatus.DISABLED:
        target.deactivated_at = now

    revoked = 0
    if new_status in _STATUS_REVOKE_REASONS:
        revoked = revoke_user_sessions(
            db,
            target.id,
            reason=_STATUS_REVOKE_REASONS[new_status],
            actor_user_id=actor.user_id,
            now=now,
        )
    try:
        db.flush()
    except IntegrityError as exc:  # concurrent link: unique linked_employee_active (Stage C3)
        raise _active_link_error() from exc
    record_audit_event(
        db,
        event_type=_STATUS_EVENTS[new_status],
        outcome=AuditOutcome.SUCCESS,
        meta=meta,
        actor_user_id=actor.user_id,
        target_type=TargetType.USER_ACCOUNT,
        target_id=str(target.public_id),
        metadata={
            "from_status": current.value,
            "to_status": new_status.value,
            "reason": reason,
            "sessions_revoked": revoked,
        },
    )
    return target


def reset_password(
    db: Session,
    settings: Settings,
    *,
    actor: Actor,
    target: UserAccount,
    temporary_password: str,
    meta: RequestMeta,
    now: datetime,
) -> UserAccount:
    ensure_can_manage_account(db, actor, target)
    ensure_password_policy(
        settings, temporary_password, login_id=target.login_id, field="temporary_password"
    )
    target.password_hash = hash_password(temporary_password)
    if target.password_created_at is None:
        target.password_created_at = now
    target.password_changed_at = now
    target.password_must_change = True
    target.updated_by_user_id = actor.user_id
    revoked = revoke_user_sessions(
        db, target.id, reason=RevokeReason.PASSWORD_RESET, actor_user_id=actor.user_id, now=now
    )
    db.flush()
    record_audit_event(
        db,
        event_type=AuditEventType.ACCOUNT_PASSWORD_RESET,
        outcome=AuditOutcome.SUCCESS,
        meta=meta,
        actor_user_id=actor.user_id,
        target_type=TargetType.USER_ACCOUNT,
        target_id=str(target.public_id),
        metadata={"sessions_revoked": revoked},
    )
    return target


def list_user_sessions(db: Session, target: UserAccount, now: datetime) -> list[UserSession]:
    return list(
        db.scalars(
            select(UserSession)
            .where(
                UserSession.user_account_id == target.id,
                UserSession.revoked_at.is_(None),
                UserSession.absolute_expires_at > now,
            )
            .order_by(UserSession.created_at.desc())
        )
    )


def revoke_one_session(
    db: Session,
    *,
    actor: Actor,
    target: UserAccount,
    session_public_id: uuid.UUID,
    meta: RequestMeta,
    now: datetime,
) -> None:
    ensure_can_manage_account(db, actor, target)
    record = db.scalars(
        select(UserSession).where(
            UserSession.public_id == session_public_id,
            UserSession.user_account_id == target.id,
        )
    ).one_or_none()
    if record is None:
        raise AppError(404, "session_not_found", "Session not found.")
    revoke_session(record, reason=RevokeReason.ADMIN_REVOKED, actor_user_id=actor.user_id, now=now)
    db.flush()
    record_audit_event(
        db,
        event_type=AuditEventType.SESSION_REVOKED,
        outcome=AuditOutcome.SUCCESS,
        meta=meta,
        actor_user_id=actor.user_id,
        target_type=TargetType.USER_SESSION,
        target_id=str(record.public_id),
        metadata={"user": str(target.public_id)},
    )


def revoke_all_sessions(
    db: Session, *, actor: Actor, target: UserAccount, meta: RequestMeta, now: datetime
) -> int:
    ensure_can_manage_account(db, actor, target)
    revoked = revoke_user_sessions(
        db, target.id, reason=RevokeReason.ADMIN_REVOKED, actor_user_id=actor.user_id, now=now
    )
    record_audit_event(
        db,
        event_type=AuditEventType.SESSIONS_REVOKED_ALL,
        outcome=AuditOutcome.SUCCESS,
        meta=meta,
        actor_user_id=actor.user_id,
        target_type=TargetType.USER_ACCOUNT,
        target_id=str(target.public_id),
        metadata={"sessions_revoked": revoked},
    )
    return revoked


# --- Cursor pagination (keyset on the internal id, newest first) ---------------


def encode_cursor(last_id: int) -> str:
    return base64.urlsafe_b64encode(str(last_id).encode()).decode().rstrip("=")


def decode_cursor(cursor: str | None) -> int | None:
    if not cursor:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value = int(base64.urlsafe_b64decode(padded.encode()).decode())
    except (ValueError, binascii.Error, UnicodeDecodeError):
        raise AppError(422, "invalid_cursor", "The pagination cursor is invalid.") from None
    if value < 1:
        raise AppError(422, "invalid_cursor", "The pagination cursor is invalid.")
    return value


def list_accounts(
    db: Session,
    *,
    status: AccountStatus | None,
    search: str | None,
    limit: int,
    cursor: str | None,
    linked: bool | None = None,
    manageable_for: Actor | None = None,
) -> tuple[list[UserAccount], str | None]:
    query = select(UserAccount).order_by(UserAccount.id.desc()).limit(limit + 1)
    if manageable_for is not None:  # only accounts this actor may manage (pickers)
        query = query.where(manageable_by(manageable_for))
    if status is not None:
        query = query.where(UserAccount.status == status.value)
    if linked is not None:  # Stage C3: accounts with / without an employee link
        column = UserAccount.employee_id
        query = query.where(column.is_not(None) if linked else column.is_(None))
    if search and search.strip():
        pattern = _like_pattern(search)
        query = query.where(
            or_(
                UserAccount.login_id.like(pattern, escape="\\"),
                UserAccount.display_name.like(pattern, escape="\\"),
            )
        )
    before = decode_cursor(cursor)
    if before is not None:
        query = query.where(UserAccount.id < before)
    rows = list(db.scalars(query))
    next_cursor = encode_cursor(rows[limit - 1].id) if len(rows) > limit else None
    return rows[:limit], next_cursor
