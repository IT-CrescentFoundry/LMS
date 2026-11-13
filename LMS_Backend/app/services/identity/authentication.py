"""Login, logout, password change and session resolution.

Security properties:

* Generic failure: any wrong login ID or password yields the same
  ``invalid_credentials`` error; unknown IDs are verified against a dummy hash so
  response times do not reveal whether an account exists.
* Account status is revealed (``account_inactive``) only after the correct
  password has been presented.
* Throttling is checked *before* password verification and applies to unknown IDs
  too (no enumeration through lockouts).
* Every login issues a brand-new session token and revokes the session cookie the
  browser presented, if any (no session fixation).
* A password change rotates the session and revokes all other sessions.
"""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.context import RequestMeta
from app.core.errors import AppError
from app.core.security.passwords import (
    PasswordIssue,
    hash_password,
    needs_rehash,
    verify_against_dummy,
    verify_password,
)
from app.models.audit import AuditOutcome
from app.models.identity import UserAccount, UserSession
from app.schemas.errors import ValidationIssue
from app.services.audit_service import AuditEventType, TargetType, record_audit_event
from app.services.identity import throttling
from app.services.identity.access_control import load_permission_codes, load_role_codes
from app.services.identity.accounts import ensure_password_policy
from app.services.identity.context import AuthContext
from app.services.identity.sessions import (
    NewSession,
    RevokeReason,
    find_valid_session,
    revoke_session,
    revoke_user_sessions,
    start_session,
)


def invalid_credentials() -> AppError:
    return AppError(401, "invalid_credentials", "The login ID or password is incorrect.")


@dataclass(frozen=True)
class SignedIn:
    context: AuthContext
    token: str  # raw cookie token; never serialised into a response body


def _build_context(db: Session, user: UserAccount, record: UserSession) -> AuthContext:
    return AuthContext(
        user=user,
        session=record,
        permissions=load_permission_codes(db, user.id),
        roles=load_role_codes(db, user.id),
    )


def resolve_auth_context(db: Session, token: str, now: datetime) -> AuthContext | None:
    record = find_valid_session(db, token, now)
    if record is None:
        return None
    return _build_context(db, record.user, record)


def authenticate(
    db: Session,
    settings: Settings,
    *,
    login_id: str,
    password: str,
    meta: RequestMeta,
    presented_token: str | None,
    now: datetime,
) -> SignedIn:
    keys = throttling.throttle_keys(
        settings, purpose="login", identifier=login_id, ip=meta.ip_address
    )
    user = db.scalars(
        select(UserAccount).where(UserAccount.login_id == login_id.strip())
    ).one_or_none()

    if throttling.is_throttled(db, keys, now):
        record_audit_event(
            db,
            event_type=AuditEventType.LOGIN_THROTTLED,
            outcome=AuditOutcome.DENIED,
            meta=meta,
            target_type=TargetType.USER_ACCOUNT if user else None,
            target_id=str(user.public_id) if user else None,
            metadata=None if user else {"login_id_fingerprint": keys.identifier[:16]},
        )
        db.commit()
        raise AppError(
            429, "too_many_attempts", "Too many sign-in attempts. Please try again later."
        )

    if user is not None and user.password_hash is not None:
        password_ok = verify_password(user.password_hash, password)
    else:
        verify_against_dummy(password)
        password_ok = False

    if not password_ok or user is None:
        throttling.register_failure(db, settings, keys, now)
        record_audit_event(
            db,
            event_type=AuditEventType.LOGIN_FAILED,
            outcome=AuditOutcome.FAILURE,
            meta=meta,
            target_type=TargetType.USER_ACCOUNT if user else None,
            target_id=str(user.public_id) if user else None,
            metadata={"reason": "invalid_credentials", "known_login_id": user is not None}
            | ({} if user else {"login_id_fingerprint": keys.identifier[:16]}),
        )
        db.commit()
        raise invalid_credentials()

    if not user.is_active:
        record_audit_event(
            db,
            event_type=AuditEventType.LOGIN_DENIED_INACTIVE,
            outcome=AuditOutcome.DENIED,
            meta=meta,
            target_type=TargetType.USER_ACCOUNT,
            target_id=str(user.public_id),
            metadata={"status": user.status},
        )
        db.commit()
        raise AppError(403, "account_inactive", "This account is not active. Please contact HR.")

    throttling.reset_identifier(db, keys)
    if user.password_hash is not None and needs_rehash(user.password_hash):
        user.password_hash = hash_password(password)
    if presented_token:
        previous = find_valid_session(db, presented_token, now)
        if previous is not None and previous.user_account_id == user.id:
            revoke_session(previous, reason=RevokeReason.REPLACED, actor_user_id=user.id, now=now)
    new: NewSession = start_session(db, settings, user, meta, now)
    user.last_login_at = now
    record_audit_event(
        db,
        event_type=AuditEventType.LOGIN_SUCCEEDED,
        outcome=AuditOutcome.SUCCESS,
        meta=meta,
        actor_user_id=user.id,
        target_type=TargetType.USER_SESSION,
        target_id=str(new.record.public_id),
    )
    db.commit()
    return SignedIn(context=_build_context(db, user, new.record), token=new.token)


def logout(db: Session, auth: AuthContext, meta: RequestMeta, now: datetime) -> None:
    revoke_session(auth.session, reason=RevokeReason.LOGOUT, actor_user_id=auth.user.id, now=now)
    record_audit_event(
        db,
        event_type=AuditEventType.LOGOUT,
        outcome=AuditOutcome.SUCCESS,
        meta=meta,
        actor_user_id=auth.user.id,
        target_type=TargetType.USER_SESSION,
        target_id=str(auth.session.public_id),
    )
    db.commit()


def change_password(
    db: Session,
    settings: Settings,
    *,
    auth: AuthContext,
    current_password: str,
    new_password: str,
    meta: RequestMeta,
    now: datetime,
) -> SignedIn:
    user = auth.user
    keys = throttling.throttle_keys(
        settings, purpose="password-change", identifier=str(user.public_id), ip=meta.ip_address
    )
    if throttling.is_throttled(db, keys, now):
        raise AppError(429, "too_many_attempts", "Too many attempts. Please try again later.")

    if user.password_hash is None or not verify_password(user.password_hash, current_password):
        throttling.register_failure(db, settings, keys, now)
        record_audit_event(
            db,
            event_type=AuditEventType.PASSWORD_CHANGE_FAILED,
            outcome=AuditOutcome.FAILURE,
            meta=meta,
            actor_user_id=user.id,
            target_type=TargetType.USER_ACCOUNT,
            target_id=str(user.public_id),
            metadata={"reason": "invalid_current_password"},
        )
        db.commit()
        raise AppError(400, "invalid_current_password", "The current password is incorrect.")

    ensure_password_policy(settings, new_password, login_id=user.login_id, field="new_password")
    if verify_password(user.password_hash, new_password):
        raise AppError(
            422,
            "password_policy",
            "The new password must differ from the current password.",
            details=[
                ValidationIssue(
                    location=["body", "new_password"],
                    message=PasswordIssue.SAME_AS_CURRENT,
                    type=PasswordIssue.SAME_AS_CURRENT,
                )
            ],
        )

    throttling.reset_identifier(db, keys)
    user.password_hash = hash_password(new_password)
    if user.password_created_at is None:
        user.password_created_at = now
    user.password_changed_at = now
    user.password_must_change = False
    user.updated_by_user_id = user.id
    revoked = revoke_user_sessions(
        db, user.id, reason=RevokeReason.PASSWORD_CHANGED, actor_user_id=user.id, now=now
    )
    new = start_session(db, settings, user, meta, now)
    record_audit_event(
        db,
        event_type=AuditEventType.PASSWORD_CHANGED,
        outcome=AuditOutcome.SUCCESS,
        meta=meta,
        actor_user_id=user.id,
        target_type=TargetType.USER_ACCOUNT,
        target_id=str(user.public_id),
        metadata={"sessions_revoked": revoked},
    )
    db.commit()
    return SignedIn(context=_build_context(db, user, new.record), token=new.token)
