"""Access roles and permissions (view: HR Admin / Super Admin; edit: Super Admin)."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.api.admin_support import audit_denials
from app.api.deps import DbSessionDep, RequestMetaDep, require_permission
from app.api.presenters import permission_out, role_out
from app.db.types import utcnow
from app.schemas.access import AccessRoleOut, PermissionOut
from app.schemas.errors import ErrorResponse
from app.services.identity import access_control
from app.services.identity.context import AuthContext
from app.services.identity.permissions import Permission

router = APIRouter(
    prefix="/admin",
    tags=["administration: access control"],
    responses={401: {"model": ErrorResponse}, 403: {"model": ErrorResponse}},
)

ViewRoles = Annotated[AuthContext, Depends(require_permission(Permission.ACCESS_ROLES_VIEW))]
ManageRoles = Annotated[AuthContext, Depends(require_permission(Permission.ACCESS_ROLES_MANAGE))]


@router.get("/access-roles", response_model=list[AccessRoleOut], summary="List access roles")
def list_roles(_auth: ViewRoles, db: DbSessionDep) -> list[AccessRoleOut]:
    return [role_out(role) for role in access_control.list_roles(db)]


@router.get("/access-permissions", response_model=list[PermissionOut], summary="List permissions")
def list_permissions(_auth: ViewRoles, db: DbSessionDep) -> list[PermissionOut]:
    return [
        permission_out(p.code, p.description, p.is_privileged)
        for p in access_control.list_permissions(db)
    ]


@router.put(
    "/access-roles/{role_code}/permissions/{permission_code}",
    response_model=AccessRoleOut,
    summary="Add a permission to an access role (Super Admin)",
)
def add_permission(
    role_code: str,
    permission_code: str,
    auth: ManageRoles,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> AccessRoleOut:
    with audit_denials(db, auth, meta, "access_role.permission_grant"):
        role = access_control.get_role(db, role_code)
        access_control.add_permission_to_role(
            db,
            actor=auth.actor,
            role=role,
            permission=access_control.get_permission(db, permission_code),
            meta=meta,
            now=utcnow(),
        )
        db.commit()
    return role_out(role)


@router.delete(
    "/access-roles/{role_code}/permissions/{permission_code}",
    response_model=AccessRoleOut,
    summary="Remove a permission from an access role (Super Admin)",
)
def remove_permission(
    role_code: str,
    permission_code: str,
    auth: ManageRoles,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> AccessRoleOut:
    with audit_denials(db, auth, meta, "access_role.permission_revoke"):
        role = access_control.get_role(db, role_code)
        access_control.remove_permission_from_role(
            db,
            actor=auth.actor,
            role=role,
            permission=access_control.get_permission(db, permission_code),
            meta=meta,
        )
        db.commit()
    return role_out(role)
