"""Occupational reference data: job families, grades, levels, designations, functional
roles (with designation mappings) and responsibilities.

Reads require ``organisation.view``. Changes require ``designations.manage`` (job
families, grades, levels, designations), ``functional_roles.manage`` (roles and
designation mappings) or ``responsibilities.manage``. None of these records grant
LMS permissions or practical authorisation.
"""

import uuid
from collections.abc import Callable, Sequence
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DbSessionDep, RequestMetaDep, SettingsDep, require_permission
from app.api.org_presenters import (
    designation_out,
    functional_role_out,
    job_families_out,
    mapping_out,
    ranked_out,
    responsibility_out,
)
from app.schemas.errors import ErrorResponse
from app.schemas.occupation import (
    DesignationCreate,
    DesignationOut,
    DesignationRoleMappingCreate,
    DesignationRoleMappingEnd,
    DesignationRoleMappingOut,
    DesignationUpdate,
    FunctionalRoleCreate,
    FunctionalRoleOut,
    FunctionalRoleUpdate,
    JobFamilyCreate,
    JobFamilyOut,
    JobFamilyUpdate,
    RankedCreate,
    RankedOut,
    RankedUpdate,
    ResponsibilityCreate,
    ResponsibilityOut,
    ResponsibilityUpdate,
)
from app.schemas.pagination import Page
from app.services.identity.context import AuthContext
from app.services.identity.permissions import Permission
from app.services.organisation import functional_roles, reference
from app.services.organisation.reference import (
    DESIGNATION,
    GRADE,
    JOB_FAMILY,
    JOB_LEVEL,
    RESPONSIBILITY,
    ReferenceKind,
)
from app.services.organisation.support import (
    business_today,
    decode_code_cursor,
    encode_code_cursor,
)

router = APIRouter(
    prefix="/org",
    tags=["organisation: reference data"],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)

ViewOrg = Annotated[AuthContext, Depends(require_permission(Permission.ORGANISATION_VIEW))]
ManageDesignations = Annotated[
    AuthContext, Depends(require_permission(Permission.DESIGNATIONS_MANAGE))
]
ManageRoles = Annotated[
    AuthContext, Depends(require_permission(Permission.FUNCTIONAL_ROLES_MANAGE))
]
ManageResponsibilities = Annotated[
    AuthContext, Depends(require_permission(Permission.RESPONSIBILITIES_MANAGE))
]
IncludeInactive = Annotated[bool, Query(description="Include deactivated entries.")]
Search = Annotated[str | None, Query(max_length=100)]
Limit = Annotated[int, Query(ge=1, le=200)]
Cursor = Annotated[str | None, Query(max_length=80)]


def _page[M, T](
    rows: Sequence[M], limit: int, code_of: Callable[[M], str], present: Callable[[M], T]
) -> tuple[list[T], str | None]:
    next_cursor = encode_code_cursor(code_of(rows[limit - 1])) if len(rows) > limit else None
    return [present(row) for row in rows[:limit]], next_cursor


# ------------------------------------------------------------------------ job families


@router.get("/job-families", response_model=list[JobFamilyOut], summary="List job families")
def list_job_families(
    _auth: ViewOrg, db: DbSessionDep, include_inactive: IncludeInactive = False
) -> list[JobFamilyOut]:
    rows = reference.list_reference(db, JOB_FAMILY, include_inactive=include_inactive)
    return job_families_out(db, rows)


@router.post(
    "/job-families",
    response_model=JobFamilyOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a job family",
)
def create_job_family(
    body: JobFamilyCreate, auth: ManageDesignations, db: DbSessionDep, meta: RequestMetaDep
) -> JobFamilyOut:
    family = reference.create_job_family(
        db,
        actor=auth.actor,
        meta=meta,
        code=body.code,
        name=body.name,
        description=body.description,
        parent_id=body.parent_id,
    )
    db.commit()
    return job_families_out(db, [family])[0]


@router.get("/job-families/{public_id}", response_model=JobFamilyOut, summary="Get a job family")
def get_job_family(public_id: uuid.UUID, _auth: ViewOrg, db: DbSessionDep) -> JobFamilyOut:
    return job_families_out(db, [reference.get_reference(db, JOB_FAMILY, public_id)])[0]


@router.patch(
    "/job-families/{public_id}", response_model=JobFamilyOut, summary="Update a job family"
)
def update_job_family(
    public_id: uuid.UUID,
    body: JobFamilyUpdate,
    auth: ManageDesignations,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> JobFamilyOut:
    family = reference.update_job_family(
        db, public_id, actor=auth.actor, meta=meta, version=body.version, changes=body.changes()
    )
    db.commit()
    return job_families_out(db, [family])[0]


# -------------------------------------------------------------------- grades and levels


def _ranked_routes(path: str, kind: ReferenceKind[Any], label: str) -> None:
    """Grades and levels share one shape; register the same four endpoints for each."""

    @router.get(
        path, response_model=list[RankedOut], summary=f"List {label}s", name=f"list_{kind.key}"
    )
    def list_items(
        _auth: ViewOrg, db: DbSessionDep, include_inactive: IncludeInactive = False
    ) -> list[RankedOut]:
        return [
            ranked_out(item)
            for item in reference.list_reference(db, kind, include_inactive=include_inactive)
        ]

    @router.post(
        path,
        response_model=RankedOut,
        status_code=status.HTTP_201_CREATED,
        summary=f"Create a {label}",
        name=f"create_{kind.key}",
    )
    def create_item(
        body: RankedCreate, auth: ManageDesignations, db: DbSessionDep, meta: RequestMetaDep
    ) -> RankedOut:
        item = reference.create_reference(
            db, kind, actor=auth.actor, meta=meta, values=body.model_dump()
        )
        db.commit()
        return ranked_out(item)

    @router.get(
        f"{path}/{{public_id}}",
        response_model=RankedOut,
        summary=f"Get a {label}",
        name=f"get_{kind.key}",
    )
    def get_item(public_id: uuid.UUID, _auth: ViewOrg, db: DbSessionDep) -> RankedOut:
        return ranked_out(reference.get_reference(db, kind, public_id))

    @router.patch(
        f"{path}/{{public_id}}",
        response_model=RankedOut,
        summary=f"Update a {label}",
        name=f"update_{kind.key}",
    )
    def update_item(
        public_id: uuid.UUID,
        body: RankedUpdate,
        auth: ManageDesignations,
        db: DbSessionDep,
        meta: RequestMetaDep,
    ) -> RankedOut:
        item = reference.update_reference(
            db,
            kind,
            reference.get_reference(db, kind, public_id, for_update=True),
            actor=auth.actor,
            meta=meta,
            version=body.version,
            changes=body.changes(),
        )
        db.commit()
        return ranked_out(item)


_ranked_routes("/grades", GRADE, "grade")
_ranked_routes("/levels", JOB_LEVEL, "level")


# ------------------------------------------------------------------------ designations


@router.get("/designations", response_model=Page[DesignationOut], summary="List designations")
def list_designations(
    _auth: ViewOrg,
    db: DbSessionDep,
    q: Search = None,
    include_inactive: IncludeInactive = False,
    limit: Limit = 100,
    cursor: Cursor = None,
) -> Page[DesignationOut]:
    rows = reference.list_reference(
        db,
        DESIGNATION,
        include_inactive=include_inactive,
        q=q,
        after_code=decode_code_cursor(cursor),
        limit=limit + 1,
    )
    items, next_cursor = _page(rows, limit, lambda item: item.code, designation_out)
    return Page[DesignationOut](items=items, next_cursor=next_cursor)


@router.post(
    "/designations",
    response_model=DesignationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a designation",
)
def create_designation(
    body: DesignationCreate, auth: ManageDesignations, db: DbSessionDep, meta: RequestMetaDep
) -> DesignationOut:
    family = reference.resolve_job_family(db, body.job_family_id)
    designation = reference.create_reference(
        db,
        DESIGNATION,
        actor=auth.actor,
        meta=meta,
        values={
            "code": body.code,
            "title": body.title,
            "job_family_id": family.id if family else None,
        },
        translations=body.translations,
    )
    db.commit()
    return designation_out(designation)


@router.get("/designations/{public_id}", response_model=DesignationOut, summary="Get a designation")
def get_designation(public_id: uuid.UUID, _auth: ViewOrg, db: DbSessionDep) -> DesignationOut:
    return designation_out(reference.get_reference(db, DESIGNATION, public_id))


@router.patch(
    "/designations/{public_id}", response_model=DesignationOut, summary="Update a designation"
)
def update_designation(
    public_id: uuid.UUID,
    body: DesignationUpdate,
    auth: ManageDesignations,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> DesignationOut:
    designation = reference.update_designation(
        db,
        public_id,
        actor=auth.actor,
        meta=meta,
        version=body.version,
        changes=body.changes(),
        translations=body.translations,
    )
    db.commit()
    return designation_out(designation)


@router.get(
    "/designations/{public_id}/functional-roles",
    response_model=list[DesignationRoleMappingOut],
    summary="Functional roles mapped to a designation",
)
def list_designation_roles(
    public_id: uuid.UUID,
    _auth: ViewOrg,
    db: DbSessionDep,
    include_ended: bool = False,
) -> list[DesignationRoleMappingOut]:
    return [
        mapping_out(mapping)
        for mapping in functional_roles.list_mappings(db, public_id, include_ended=include_ended)
    ]


@router.post(
    "/designations/{public_id}/functional-roles",
    response_model=DesignationRoleMappingOut,
    status_code=status.HTTP_201_CREATED,
    summary="Map a functional role to a designation (optionally for one unit subtree)",
)
def map_designation_role(
    public_id: uuid.UUID,
    body: DesignationRoleMappingCreate,
    auth: ManageRoles,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> DesignationRoleMappingOut:
    mapping = functional_roles.create_mapping(
        db,
        public_id,
        actor=auth.actor,
        meta=meta,
        functional_role_id=body.functional_role_id,
        scope_unit_id=body.scope_unit_id,
        include_descendants=body.include_descendants,
        effective_from=body.effective_from or business_today(settings),
    )
    db.commit()
    return mapping_out(mapping)


@router.post(
    "/designations/{public_id}/functional-roles/{mapping_id}/end",
    response_model=DesignationRoleMappingOut,
    summary="End a designation-to-role mapping from a date",
)
def end_designation_role(
    public_id: uuid.UUID,
    mapping_id: uuid.UUID,
    body: DesignationRoleMappingEnd,
    auth: ManageRoles,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> DesignationRoleMappingOut:
    mapping = functional_roles.end_mapping(
        db,
        public_id,
        mapping_id,
        actor=auth.actor,
        meta=meta,
        effective_to=body.effective_to,
        reason=body.reason,
    )
    db.commit()
    return mapping_out(mapping)


# -------------------------------------------------------------------- functional roles


@router.get(
    "/functional-roles", response_model=Page[FunctionalRoleOut], summary="List functional roles"
)
def list_functional_roles(
    _auth: ViewOrg,
    db: DbSessionDep,
    q: Search = None,
    include_inactive: IncludeInactive = False,
    owner_unit: Annotated[uuid.UUID | None, Query(description="Owner unit public_id")] = None,
    limit: Limit = 100,
    cursor: Cursor = None,
) -> Page[FunctionalRoleOut]:
    rows = functional_roles.list_roles(
        db,
        q=q,
        include_inactive=include_inactive,
        owner_unit_id=owner_unit,
        after_code=decode_code_cursor(cursor),
        limit=limit + 1,
    )
    items, next_cursor = _page(rows, limit, lambda role: role.code, functional_role_out)
    return Page[FunctionalRoleOut](items=items, next_cursor=next_cursor)


@router.post(
    "/functional-roles",
    response_model=FunctionalRoleOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a functional role",
)
def create_functional_role(
    body: FunctionalRoleCreate, auth: ManageRoles, db: DbSessionDep, meta: RequestMetaDep
) -> FunctionalRoleOut:
    role = functional_roles.create_role(
        db,
        actor=auth.actor,
        meta=meta,
        code=body.code,
        name=body.name,
        description=body.description,
        job_family_id=body.job_family_id,
        owner_unit_id=body.owner_unit_id,
        translations=body.translations,
    )
    db.commit()
    return functional_role_out(role)


@router.get(
    "/functional-roles/{public_id}",
    response_model=FunctionalRoleOut,
    summary="Get a functional role",
)
def get_functional_role(
    public_id: uuid.UUID, _auth: ViewOrg, db: DbSessionDep
) -> FunctionalRoleOut:
    return functional_role_out(functional_roles.get_role(db, public_id))


@router.patch(
    "/functional-roles/{public_id}",
    response_model=FunctionalRoleOut,
    summary="Update a functional role",
)
def update_functional_role(
    public_id: uuid.UUID,
    body: FunctionalRoleUpdate,
    auth: ManageRoles,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> FunctionalRoleOut:
    role = functional_roles.update_role(
        db,
        public_id,
        actor=auth.actor,
        meta=meta,
        version=body.version,
        changes=body.changes(),
        translations=body.translations,
    )
    db.commit()
    return functional_role_out(role)


# -------------------------------------------------------------------- responsibilities


@router.get(
    "/responsibilities",
    response_model=Page[ResponsibilityOut],
    summary="List responsibilities",
)
def list_responsibilities(
    _auth: ViewOrg,
    db: DbSessionDep,
    q: Search = None,
    include_inactive: IncludeInactive = False,
    limit: Limit = 100,
    cursor: Cursor = None,
) -> Page[ResponsibilityOut]:
    rows = reference.list_reference(
        db,
        RESPONSIBILITY,
        include_inactive=include_inactive,
        q=q,
        after_code=decode_code_cursor(cursor),
        limit=limit + 1,
    )
    items, next_cursor = _page(rows, limit, lambda item: item.code, responsibility_out)
    return Page[ResponsibilityOut](items=items, next_cursor=next_cursor)


@router.post(
    "/responsibilities",
    response_model=ResponsibilityOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a responsibility (grants no permission or authorisation)",
)
def create_responsibility(
    body: ResponsibilityCreate,
    auth: ManageResponsibilities,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> ResponsibilityOut:
    item = reference.create_reference(
        db,
        RESPONSIBILITY,
        actor=auth.actor,
        meta=meta,
        values=body.model_dump(exclude={"translations"}),
        translations=body.translations,
    )
    db.commit()
    return responsibility_out(item)


@router.get(
    "/responsibilities/{public_id}",
    response_model=ResponsibilityOut,
    summary="Get a responsibility",
)
def get_responsibility(public_id: uuid.UUID, _auth: ViewOrg, db: DbSessionDep) -> ResponsibilityOut:
    return responsibility_out(reference.get_reference(db, RESPONSIBILITY, public_id))


@router.patch(
    "/responsibilities/{public_id}",
    response_model=ResponsibilityOut,
    summary="Update a responsibility",
)
def update_responsibility(
    public_id: uuid.UUID,
    body: ResponsibilityUpdate,
    auth: ManageResponsibilities,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> ResponsibilityOut:
    item = reference.update_reference(
        db,
        RESPONSIBILITY,
        reference.get_reference(db, RESPONSIBILITY, public_id, for_update=True),
        actor=auth.actor,
        meta=meta,
        version=body.version,
        changes=body.changes(),
        translations=body.translations,
    )
    db.commit()
    return responsibility_out(item)
