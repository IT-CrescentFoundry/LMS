"""Linking LMS login accounts to employee records (ADR-040).

The employee record and the login account stay separate. An employee has at most one
non-disabled linked account (enforced by the generated unique column
``user_account.linked_employee_active``); disabled accounts may keep their link as
history. Link history is read back from the audit trail.

Provisional policies (Q-50): separating an employee never suspends the linked
account, and the employee code is never forced as the login ID. Mismatches are only
flagged.
"""

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.context import RequestMeta
from app.core.errors import AppError
from app.models.audit import AuditEvent
from app.models.employees import Employee
from app.models.identity import AccountStatus, UserAccount
from app.services.audit_service import AuditEventType, TargetType
from app.services.employees.common import is_separated, lock_employee, locking
from app.services.identity.access_control import ensure_can_manage_account
from app.services.identity.context import Actor
from app.services.organisation.support import audit

_LINK_EVENTS = (
    AuditEventType.EMPLOYEE_ACCOUNT_LINKED.value,
    AuditEventType.EMPLOYEE_ACCOUNT_UNLINKED.value,
)


def _active_account_error() -> AppError:
    return AppError(
        409,
        "employee_has_active_account",
        "This employee already has a linked account that is not disabled.",
    )


def _lock_account(db: Session, public_id: uuid.UUID) -> UserAccount:
    account = (
        db.scalars(
            select(UserAccount)
            .where(UserAccount.public_id == public_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        .unique()
        .one_or_none()
    )
    if account is None:
        raise AppError(404, "user_not_found", "User account not found.")
    return account


def _audit_link(
    db: Session,
    actor: Actor,
    meta: RequestMeta,
    event: AuditEventType,
    employee: Employee,
    account: UserAccount,
    reason: str | None,
) -> None:
    audit(
        db,
        actor,
        meta,
        event,
        TargetType.EMPLOYEE,
        employee.public_id,
        {
            "employee_code": employee.employee_code,
            "account": str(account.public_id),
            "login_id": account.login_id,
            "account_status": account.status,
            "reason": reason,
        },
    )


def link_account(
    db: Session,
    employee_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    user_public_id: uuid.UUID,
    reason: str | None,
) -> UserAccount:
    employee = lock_employee(db, employee_id)
    account = _lock_account(db, user_public_id)
    ensure_can_manage_account(db, actor, account)
    if account.employee_id == employee.id:
        raise AppError(422, "no_change", "This account is already linked to the employee.")
    if account.employee_id is not None:
        raise AppError(409, "account_already_linked", "This account is linked to another employee.")
    if account.status != AccountStatus.DISABLED.value:
        other = db.scalar(
            locking(
                select(UserAccount.id).where(
                    UserAccount.employee_id == employee.id,
                    UserAccount.status != AccountStatus.DISABLED.value,
                )
            ).limit(1)
        )
        if other is not None:
            raise _active_account_error()
    account.employee_id = employee.id
    account.updated_by_user_id = actor.user_id
    try:
        db.flush()
    except IntegrityError as exc:  # concurrent link (unique linked_employee_active)
        raise _active_account_error() from exc
    _audit_link(db, actor, meta, AuditEventType.EMPLOYEE_ACCOUNT_LINKED, employee, account, reason)
    return account


def unlink_account(
    db: Session,
    employee_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    user_public_id: uuid.UUID,
    reason: str | None,
) -> UserAccount:
    """Remove the link; the account itself (status, sessions, roles) is untouched."""
    employee = lock_employee(db, employee_id)
    account = _lock_account(db, user_public_id)
    if account.employee_id != employee.id:
        raise AppError(409, "account_not_linked", "This account is not linked to the employee.")
    ensure_can_manage_account(db, actor, account)
    account.employee_id = None
    account.updated_by_user_id = actor.user_id
    db.flush()
    _audit_link(
        db, actor, meta, AuditEventType.EMPLOYEE_ACCOUNT_UNLINKED, employee, account, reason
    )
    return account


# ------------------------------------------------------------------- reads


@dataclass
class AccountSummary:
    accounts: list[UserAccount]
    history: list[AuditEvent]
    flags: list[str] = field(default_factory=list)


def account_flags(employee: Employee, accounts: list[UserAccount]) -> list[str]:
    """Mismatches worth a human look; nothing is changed automatically."""
    active = [a for a in accounts if a.status != AccountStatus.DISABLED.value]
    flags = []
    if is_separated(employee) and active:
        flags.append("separated_with_active_account")
    if employee.work_email and any(
        a.email and a.email.casefold() != employee.work_email.casefold() for a in active
    ):
        flags.append("email_mismatch")
    return flags


def linked_accounts(db: Session, employee: Employee) -> list[UserAccount]:
    return list(
        db.scalars(
            select(UserAccount)
            .where(UserAccount.employee_id == employee.id)
            .order_by(UserAccount.id)
        ).unique()
    )


def account_summary(db: Session, employee: Employee) -> AccountSummary:
    accounts = linked_accounts(db, employee)
    history = list(
        db.scalars(
            select(AuditEvent)
            .where(
                AuditEvent.target_type == TargetType.EMPLOYEE.value,
                AuditEvent.target_id == str(employee.public_id),
                AuditEvent.event_type.in_(_LINK_EVENTS),
            )
            .order_by(AuditEvent.occurred_at.desc(), AuditEvent.id.desc())
        )
    )
    return AccountSummary(accounts, history, account_flags(employee, accounts))
