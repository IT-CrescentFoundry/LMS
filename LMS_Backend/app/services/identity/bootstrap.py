"""Controlled Super Admin management (used only by the ``app.cli`` commands).

* There is no default administrator, no hardcoded credential and no HTTP
  bootstrap endpoint.
* Each operation runs in one transaction that first locks the ``super_admin``
  role row, so concurrent invocations cannot both succeed.
* The first Super Admin can be created only while no active Super Admin exists.
* The last remaining Super Admin cannot be revoked.
* Every operation is audited (channel ``cli`` plus the operating-system user).
"""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.context import CLI_REQUEST
from app.core.errors import AppError
from app.core.security.passwords import hash_password
from app.models.audit import AuditOutcome
from app.models.identity import AccessRole, AccountStatus, UserAccessRole, UserAccount
from app.services.audit_service import AuditEventType, TargetType, record_audit_event
from app.services.identity.access_control import grant_role, revoke_role
from app.services.identity.accounts import ensure_password_policy, normalise_login_id
from app.services.identity.permissions import SUPER_ADMIN_ROLE


class BootstrapError(RuntimeError):
    """A Super Admin operation was refused."""


def _lock_super_admin_role(db: Session) -> AccessRole:
    role = db.scalars(
        select(AccessRole).where(AccessRole.code == SUPER_ADMIN_ROLE).with_for_update()
    ).one_or_none()
    if role is None:
        raise BootstrapError(
            "The super_admin role does not exist. Apply the database migrations first."
        )
    return role


def active_super_admin_count(db: Session, role: AccessRole) -> int:
    return int(
        db.scalar(
            select(func.count())
            .select_from(UserAccessRole)
            .where(UserAccessRole.access_role_id == role.id, UserAccessRole.revoked_at.is_(None))
        )
        or 0
    )


def _find_account(db: Session, login_id: str) -> UserAccount | None:
    return db.scalars(
        select(UserAccount).where(UserAccount.login_id == login_id.strip())
    ).one_or_none()


def create_initial_super_admin(
    db: Session,
    settings: Settings,
    *,
    login_id: str,
    display_name: str,
    email: str | None,
    password: str,
    operator: str,
    now: datetime,
) -> UserAccount:
    try:
        role = _lock_super_admin_role(db)
        if active_super_admin_count(db, role) > 0:
            raise BootstrapError(
                "A Super Admin already exists. The initial bootstrap can only run once; "
                "use 'grant-super-admin' for additional Super Admins."
            )
        try:
            login_id = normalise_login_id(login_id)
            ensure_password_policy(settings, password, login_id=login_id, field="password")
        except AppError as exc:
            detail = ", ".join(issue.type for issue in exc.details or []) or exc.code
            raise BootstrapError(f"{exc.message} ({detail})") from None
        if _find_account(db, login_id) is not None:
            raise BootstrapError("An account with this login ID already exists.")

        account = UserAccount(
            login_id=login_id,
            display_name=display_name.strip(),
            email=email,
            password_hash=hash_password(password),
            password_created_at=now,
            password_changed_at=now,
            password_must_change=False,
            status=AccountStatus.ACTIVE.value,
            status_changed_at=now,
            status_reason="Initial Super Admin bootstrap",
            activated_at=now,
        )
        db.add(account)
        db.flush()
        grant_role(
            db, actor=None, target=account, role=role, meta=CLI_REQUEST, now=now, audit=False
        )
        record_audit_event(
            db,
            event_type=AuditEventType.SUPER_ADMIN_BOOTSTRAPPED,
            outcome=AuditOutcome.SUCCESS,
            meta=CLI_REQUEST,
            target_type=TargetType.USER_ACCOUNT,
            target_id=str(account.public_id),
            metadata={"channel": "cli", "operator": operator, "login_id": account.login_id},
        )
        db.commit()
        return account
    except BaseException:
        db.rollback()
        raise


def grant_super_admin(db: Session, *, login_id: str, operator: str, now: datetime) -> UserAccount:
    try:
        role = _lock_super_admin_role(db)
        account = _find_account(db, login_id)
        if account is None or account.status != AccountStatus.ACTIVE:
            raise BootstrapError("An active account with this login ID was not found.")
        try:
            grant_role(
                db, actor=None, target=account, role=role, meta=CLI_REQUEST, now=now, audit=False
            )
        except AppError as exc:
            raise BootstrapError(exc.message) from None
        record_audit_event(
            db,
            event_type=AuditEventType.SUPER_ADMIN_GRANTED,
            outcome=AuditOutcome.SUCCESS,
            meta=CLI_REQUEST,
            target_type=TargetType.USER_ACCOUNT,
            target_id=str(account.public_id),
            metadata={"channel": "cli", "operator": operator},
        )
        db.commit()
        return account
    except BaseException:
        db.rollback()
        raise


def revoke_super_admin(db: Session, *, login_id: str, operator: str, now: datetime) -> UserAccount:
    try:
        role = _lock_super_admin_role(db)
        account = _find_account(db, login_id)
        if account is None:
            raise BootstrapError("No account with this login ID was found.")
        if active_super_admin_count(db, role) <= 1:
            raise BootstrapError("The last remaining Super Admin cannot be revoked.")
        try:
            revoke_role(
                db,
                actor=None,
                target=account,
                role=role,
                meta=CLI_REQUEST,
                now=now,
                reason="Revoked via CLI",
                audit=False,
            )
        except AppError as exc:
            raise BootstrapError(exc.message) from None
        record_audit_event(
            db,
            event_type=AuditEventType.SUPER_ADMIN_REVOKED,
            outcome=AuditOutcome.SUCCESS,
            meta=CLI_REQUEST,
            target_type=TargetType.USER_ACCOUNT,
            target_id=str(account.public_id),
            metadata={"channel": "cli", "operator": operator},
        )
        db.commit()
        return account
    except BaseException:
        db.rollback()
        raise
