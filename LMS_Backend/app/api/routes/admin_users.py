"""User-account administration (HR Admin / Super Admin).

Route-level permissions gate each endpoint; the services enforce the finer rules
(no self-administration, no managing more-privileged accounts, role-assignment
guards). Refused actions are audited.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.admin_support import audit_denials
from app.api.deps import DbSessionDep, RequestMetaDep, SettingsDep, require_permission
from app.api.presenters import session_out, user_detail, user_summaries
from app.db.types import utcnow
from app.models.identity import AccountStatus
from app.schemas.errors import ErrorResponse
from app.schemas.pagination import Page
from app.schemas.users import (
    CreateUserRequest,
    PasswordResetRequest,
    RevokedCount,
    RoleAssignmentRequest,
    SessionOut,
    StatusChangeRequest,
    UpdateUserRequest,
    UserDetail,
    UserSummary,
)
from app.services.identity import access_control, accounts
from app.services.identity.context import AuthContext
from app.services.identity.permissions import Permission

router = APIRouter(
    prefix="/admin/users",
    tags=["administration: users"],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
    },
)

ViewUsers = Annotated[AuthContext, Depends(require_permission(Permission.USER_ACCOUNTS_VIEW))]
ManageUsers = Annotated[AuthContext, Depends(require_permission(Permission.USER_ACCOUNTS_MANAGE))]
RevokeSessions = Annotated[
    AuthContext, Depends(require_permission(Permission.USER_SESSIONS_REVOKE))
]
AssignRoles = Annotated[AuthContext, Depends(require_permission(Permission.USER_ROLES_ASSIGN))]


@router.get("", response_model=Page[UserSummary], summary="List user accounts")
def list_users(
    _auth: ViewUsers,
    db: DbSessionDep,
    status_filter: Annotated[AccountStatus | None, Query(alias="status")] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
    cursor: Annotated[str | None, Query(max_length=40)] = None,
) -> Page[UserSummary]:
    rows, next_cursor = accounts.list_accounts(
        db, status=status_filter, search=q, limit=limit, cursor=cursor
    )
    return Page[UserSummary](items=user_summaries(db, rows), next_cursor=next_cursor)


@router.post(
    "",
    response_model=UserDetail,
    status_code=status.HTTP_201_CREATED,
    summary="Create a user account (pending activation, temporary password)",
)
def create_user(
    body: CreateUserRequest,
    auth: ManageUsers,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> UserDetail:
    with audit_denials(db, auth, meta, "user_account.create"):
        account = accounts.create_account(
            db,
            settings,
            actor=auth.actor,
            login_id=body.login_id,
            display_name=body.display_name,
            email=body.email,
            temporary_password=body.temporary_password.get_secret_value(),
            role_codes=body.roles,
            meta=meta,
            now=utcnow(),
        )
        db.commit()
    return user_detail(db, account)


@router.get("/{public_id}", response_model=UserDetail, summary="Get a user account")
def get_user(public_id: uuid.UUID, _auth: ViewUsers, db: DbSessionDep) -> UserDetail:
    return user_detail(db, accounts.get_account(db, public_id))


@router.patch("/{public_id}", response_model=UserDetail, summary="Update name or email")
def update_user(
    public_id: uuid.UUID,
    body: UpdateUserRequest,
    auth: ManageUsers,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> UserDetail:
    with audit_denials(db, auth, meta, "user_account.update"):
        account = accounts.update_account(
            db,
            actor=auth.actor,
            target=accounts.get_account(db, public_id),
            display_name=body.display_name,
            email=body.email,
            email_provided="email" in body.model_fields_set,
            meta=meta,
        )
        db.commit()
    return user_detail(db, account)


def _change_status(
    public_id: uuid.UUID,
    new_status: AccountStatus,
    body: StatusChangeRequest,
    auth: AuthContext,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> UserDetail:
    with audit_denials(db, auth, meta, f"user_account.status.{new_status.value}"):
        account = accounts.change_account_status(
            db,
            actor=auth.actor,
            target=accounts.get_account(db, public_id),
            new_status=new_status,
            reason=body.reason,
            meta=meta,
            now=utcnow(),
        )
        db.commit()
    return user_detail(db, account)


@router.post("/{public_id}/activate", response_model=UserDetail, summary="Activate")
def activate_user(
    public_id: uuid.UUID,
    body: StatusChangeRequest,
    auth: ManageUsers,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> UserDetail:
    return _change_status(public_id, AccountStatus.ACTIVE, body, auth, db, meta)


@router.post(
    "/{public_id}/suspend", response_model=UserDetail, summary="Suspend (revokes sessions)"
)
def suspend_user(
    public_id: uuid.UUID,
    body: StatusChangeRequest,
    auth: ManageUsers,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> UserDetail:
    return _change_status(public_id, AccountStatus.SUSPENDED, body, auth, db, meta)


@router.post(
    "/{public_id}/disable", response_model=UserDetail, summary="Disable (revokes sessions)"
)
def disable_user(
    public_id: uuid.UUID,
    body: StatusChangeRequest,
    auth: ManageUsers,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> UserDetail:
    return _change_status(public_id, AccountStatus.DISABLED, body, auth, db, meta)


@router.post(
    "/{public_id}/password-reset",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Set a temporary password (forces change, revokes sessions)",
)
def reset_password(
    public_id: uuid.UUID,
    body: PasswordResetRequest,
    auth: ManageUsers,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> Response:
    with audit_denials(db, auth, meta, "user_account.password_reset"):
        accounts.reset_password(
            db,
            settings,
            actor=auth.actor,
            target=accounts.get_account(db, public_id),
            temporary_password=body.temporary_password.get_secret_value(),
            meta=meta,
            now=utcnow(),
        )
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{public_id}/sessions", response_model=list[SessionOut], summary="Active sessions")
def list_sessions(public_id: uuid.UUID, _auth: ViewUsers, db: DbSessionDep) -> list[SessionOut]:
    account = accounts.get_account(db, public_id)
    return [session_out(record) for record in accounts.list_user_sessions(db, account, utcnow())]


@router.post(
    "/{public_id}/sessions/{session_id}/revoke",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Revoke one session",
)
def revoke_session(
    public_id: uuid.UUID,
    session_id: uuid.UUID,
    auth: RevokeSessions,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> Response:
    with audit_denials(db, auth, meta, "user_session.revoke"):
        accounts.revoke_one_session(
            db,
            actor=auth.actor,
            target=accounts.get_account(db, public_id),
            session_public_id=session_id,
            meta=meta,
            now=utcnow(),
        )
        db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/{public_id}/sessions/revoke-all", response_model=RevokedCount, summary="Revoke all sessions"
)
def revoke_all_sessions(
    public_id: uuid.UUID, auth: RevokeSessions, db: DbSessionDep, meta: RequestMetaDep
) -> RevokedCount:
    with audit_denials(db, auth, meta, "user_session.revoke_all"):
        revoked = accounts.revoke_all_sessions(
            db,
            actor=auth.actor,
            target=accounts.get_account(db, public_id),
            meta=meta,
            now=utcnow(),
        )
        db.commit()
    return RevokedCount(revoked=revoked)


@router.post("/{public_id}/roles", response_model=UserDetail, summary="Grant an access role")
def grant_role(
    public_id: uuid.UUID,
    body: RoleAssignmentRequest,
    auth: AssignRoles,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> UserDetail:
    with audit_denials(db, auth, meta, "access_role.grant"):
        account = accounts.get_account(db, public_id)
        access_control.grant_role(
            db,
            actor=auth.actor,
            target=account,
            role=access_control.get_role(db, body.role),
            meta=meta,
            now=utcnow(),
        )
        db.commit()
    return user_detail(db, account)


@router.delete(
    "/{public_id}/roles/{role_code}", response_model=UserDetail, summary="Revoke an access role"
)
def revoke_role(
    public_id: uuid.UUID,
    role_code: str,
    auth: AssignRoles,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> UserDetail:
    with audit_denials(db, auth, meta, "access_role.revoke"):
        account = accounts.get_account(db, public_id)
        access_control.revoke_role(
            db,
            actor=auth.actor,
            target=account,
            role=access_control.get_role(db, role_code),
            meta=meta,
            now=utcnow(),
        )
        db.commit()
    return user_detail(db, account)
