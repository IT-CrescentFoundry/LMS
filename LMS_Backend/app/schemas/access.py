"""Access-role and permission schemas."""

from pydantic import BaseModel


class PermissionOut(BaseModel):
    code: str
    description: str
    is_privileged: bool


class AccessRoleOut(BaseModel):
    code: str
    name: str
    description: str
    is_system: bool
    is_api_assignable: bool
    assign_permission: str | None
    permissions: list[str]
