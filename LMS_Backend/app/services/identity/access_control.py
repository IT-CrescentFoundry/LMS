"""Role-based access control: permission resolution and controlled role changes.

Rules (all data-driven; no role-name comparisons):

* A user's permissions are the union of the permissions of their *active* roles.
* Nobody may change their own roles or manage their own account via admin APIs.
* To grant or revoke a role, the actor must hold the role's ``assign_permission``
  **and** every permission the role carries (no privilege escalation).
* Roles with ``is_api_assignable = False`` (Super Admin) can never be granted,
  revoked or edited through the API — only through the controlled CLI commands.
* Privileged permissions can never be added to API-editable roles.
* An account may only be managed by an actor whose permissions include all of the
  target's permissions (an HR Admin cannot reset a Super Admin's password).
"""

from collections.abc import Sequence
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import RequestMeta
from app.core.errors import AppError
from app.models.audit import AuditOutcome
from app.models.identity import (
    AccessPermission,
    AccessRole,
    AccessRolePermission,
    UserAccessRole,
    UserAccount,
)
from app.services.audit_service import AuditEventType, TargetType, record_audit_event
from app.services.identity.context import Actor


def load_permission_codes(db: Session, user_id: int) -> frozenset[str]:
    rows = db.scalars(
        select(AccessPermission.code)
        .join(
            AccessRolePermission, AccessRolePermission.access_permission_id == AccessPermission.id
        )
        .join(UserAccessRole, UserAccessRole.access_role_id == AccessRolePermission.access_role_id)
        .where(UserAccessRole.user_account_id == user_id, UserAccessRole.revoked_at.is_(None))
        .distinct()
    )
    return frozenset(rows)


def load_role_codes(db: Session, user_id: int) -> tuple[str, ...]:
    rows = db.scalars(
        select(AccessRole.code)
        .join(UserAccessRole, UserAccessRole.access_role_id == AccessRole.id)
        .where(UserAccessRole.user_account_id == user_id, UserAccessRole.revoked_at.is_(None))
        .order_by(AccessRole.code)
    )
    return tuple(rows)


def active_grants(db: Session, user_id: int) -> list[UserAccessRole]:
    return list(
        db.scalars(
            select(UserAccessRole)
            .where(UserAccessRole.user_account_id == user_id, UserAccessRole.revoked_at.is_(None))
            .order_by(UserAccessRole.granted_at)
        )
    )


def role_permission_codes(role: AccessRole) -> frozenset[str]:
    return frozenset(permission.code for permission in role.permissions)


def list_roles(db: Session) -> list[AccessRole]:
    return list(db.scalars(select(AccessRole).order_by(AccessRole.code)))


def list_permissions(db: Session) -> list[AccessPermission]:
    return list(db.scalars(select(AccessPermission).order_by(AccessPermission.code)))


def get_role(db: Session, code: str) -> AccessRole:
    role = db.scalars(select(AccessRole).where(AccessRole.code == code)).one_or_none()
    if role is None:
        raise AppError(404, "role_not_found", "Access role not found.")
    return role


def get_permission(db: Session, code: str) -> AccessPermission:
    permission = db.scalars(
        select(AccessPermission).where(AccessPermission.code == code)
    ).one_or_none()
    if permission is None:
        raise AppError(404, "permission_not_found", "Permission not found.")
    return permission


def ensure_can_manage_account(db: Session, actor: Actor, target: UserAccount) -> None:
    if actor.user_id == target.id:
        raise AppError(
            403,
            "self_modification_forbidden",
            "You cannot perform this administrative action on your own account.",
        )
    if not load_permission_codes(db, target.id) <= actor.permissions:
        raise AppError(
            403,
            "insufficient_privilege",
            "This account has privileges you do not hold, so you cannot manage it.",
        )


def _ensure_can_change_role(actor: Actor, target: UserAccount, role: AccessRole) -> None:
    if not role.is_api_assignable:
        raise AppError(
            403,
            "role_not_assignable",
            "This role can only be changed through the controlled administration command.",
        )
    if actor.user_id == target.id:
        raise AppError(
            403, "self_modification_forbidden", "You cannot change your own access roles."
        )
    assign_code = role.assign_permission.code if role.assign_permission else None
    if assign_code is None or assign_code not in actor.permissions:
        raise AppError(403, "forbidden", "You are not permitted to assign this role.")
    if not role_permission_codes(role) <= actor.permissions:
        raise AppError(
            403,
            "privilege_escalation",
            "You cannot assign a role with permissions you do not hold yourself.",
        )


def _active_grant(db: Session, user_id: int, role_id: int) -> UserAccessRole | None:
    return db.scalars(
        select(UserAccessRole).where(
            UserAccessRole.user_account_id == user_id,
            UserAccessRole.access_role_id == role_id,
            UserAccessRole.revoked_at.is_(None),
        )
    ).one_or_none()


def grant_role(
    db: Session,
    *,
    actor: Actor | None,
    target: UserAccount,
    role: AccessRole,
    meta: RequestMeta,
    now: datetime,
    audit: bool = True,
) -> UserAccessRole:
    """Grant ``role`` to ``target``. ``actor=None`` is reserved for controlled CLI paths."""
    if actor is not None:
        _ensure_can_change_role(actor, target, role)
    if _active_grant(db, target.id, role.id) is not None:
        raise AppError(409, "role_already_granted", "The account already has this role.")
    grant = UserAccessRole(
        user_account_id=target.id,
        access_role_id=role.id,
        granted_at=now,
        granted_by_user_id=actor.user_id if actor else None,
    )
    db.add(grant)
    db.flush()
    if audit:
        record_audit_event(
            db,
            event_type=AuditEventType.ROLE_GRANTED,
            outcome=AuditOutcome.SUCCESS,
            meta=meta,
            actor_user_id=actor.user_id if actor else None,
            target_type=TargetType.USER_ACCOUNT,
            target_id=str(target.public_id),
            metadata={"role": role.code},
        )
    return grant


def revoke_role(
    db: Session,
    *,
    actor: Actor | None,
    target: UserAccount,
    role: AccessRole,
    meta: RequestMeta,
    now: datetime,
    reason: str | None = None,
    audit: bool = True,
) -> UserAccessRole:
    if actor is not None:
        _ensure_can_change_role(actor, target, role)
    grant = _active_grant(db, target.id, role.id)
    if grant is None:
        raise AppError(404, "role_not_granted", "The account does not have this role.")
    grant.revoked_at = now
    grant.revoked_by_user_id = actor.user_id if actor else None
    grant.revoke_reason = reason
    db.flush()
    if audit:
        record_audit_event(
            db,
            event_type=AuditEventType.ROLE_REVOKED,
            outcome=AuditOutcome.SUCCESS,
            meta=meta,
            actor_user_id=actor.user_id if actor else None,
            target_type=TargetType.USER_ACCOUNT,
            target_id=str(target.public_id),
            metadata={"role": role.code},
        )
    return grant


def grant_roles(
    db: Session,
    *,
    actor: Actor,
    target: UserAccount,
    role_codes: Sequence[str],
    meta: RequestMeta,
    now: datetime,
) -> None:
    for code in dict.fromkeys(role_codes):  # de-duplicate, keep order
        grant_role(db, actor=actor, target=target, role=get_role(db, code), meta=meta, now=now)


def _ensure_role_editable(role: AccessRole) -> None:
    if not role.is_api_assignable:
        raise AppError(
            403, "role_not_editable", "This role's permissions cannot be changed via the API."
        )


def add_permission_to_role(
    db: Session,
    *,
    actor: Actor,
    role: AccessRole,
    permission: AccessPermission,
    meta: RequestMeta,
    now: datetime,
) -> None:
    _ensure_role_editable(role)
    if permission.is_privileged:
        raise AppError(
            403,
            "privileged_permission",
            "Privileged permissions cannot be added to this role.",
        )
    existing = db.scalars(
        select(AccessRolePermission).where(
            AccessRolePermission.access_role_id == role.id,
            AccessRolePermission.access_permission_id == permission.id,
        )
    ).one_or_none()
    if existing is not None:
        raise AppError(409, "permission_already_granted", "The role already has this permission.")
    db.add(
        AccessRolePermission(
            access_role_id=role.id,
            access_permission_id=permission.id,
            granted_at=now,
            granted_by_user_id=actor.user_id,
        )
    )
    db.flush()
    db.expire(role, ["permissions"])
    record_audit_event(
        db,
        event_type=AuditEventType.ROLE_PERMISSION_GRANTED,
        outcome=AuditOutcome.SUCCESS,
        meta=meta,
        actor_user_id=actor.user_id,
        target_type=TargetType.ACCESS_ROLE,
        target_id=role.code,
        metadata={"permission": permission.code},
    )


def remove_permission_from_role(
    db: Session,
    *,
    actor: Actor,
    role: AccessRole,
    permission: AccessPermission,
    meta: RequestMeta,
) -> None:
    _ensure_role_editable(role)
    link = db.scalars(
        select(AccessRolePermission).where(
            AccessRolePermission.access_role_id == role.id,
            AccessRolePermission.access_permission_id == permission.id,
        )
    ).one_or_none()
    if link is None:
        raise AppError(404, "permission_not_granted", "The role does not have this permission.")
    db.delete(link)
    db.flush()
    db.expire(role, ["permissions"])
    record_audit_event(
        db,
        event_type=AuditEventType.ROLE_PERMISSION_REVOKED,
        outcome=AuditOutcome.SUCCESS,
        meta=meta,
        actor_user_id=actor.user_id,
        target_type=TargetType.ACCESS_ROLE,
        target_id=role.code,
        metadata={"permission": permission.code},
    )
