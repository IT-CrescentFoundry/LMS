"""Organisation structure: unit types and parent rules, units, hierarchy, locations.

Reads require ``organisation.view``; changes require ``organisation.manage``. Every
change is audited. Structure is not scope-filtered (Stage C plan section 12).
"""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import DbSessionDep, RequestMetaDep, SettingsDep, require_permission
from app.api.org_presenters import (
    UnitPresenter,
    history_out,
    location_out,
    tree_out,
    unit_type_out,
    unit_types_out,
    unit_write_out,
)
from app.models.organisation import ParentRuleMode
from app.schemas.errors import ErrorResponse
from app.schemas.organisation import (
    LocationCreate,
    LocationOut,
    LocationUpdate,
    OrgTreeOut,
    OrgUnitClose,
    OrgUnitCorrect,
    OrgUnitCreate,
    OrgUnitMove,
    OrgUnitOut,
    OrgUnitReopen,
    OrgUnitTypeCreate,
    OrgUnitTypeOut,
    OrgUnitTypeUpdate,
    OrgUnitWriteOut,
    ParentRulesUpdate,
    UnitHistoryOut,
)
from app.schemas.pagination import Page
from app.services.identity.context import AuthContext
from app.services.identity.permissions import Permission
from app.services.organisation import locations, unit_types, units
from app.services.organisation.support import business_today, decode_code_cursor

router = APIRouter(
    prefix="/org",
    tags=["organisation: structure"],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)

ViewOrg = Annotated[AuthContext, Depends(require_permission(Permission.ORGANISATION_VIEW))]
ManageOrg = Annotated[AuthContext, Depends(require_permission(Permission.ORGANISATION_MANAGE))]
AsOf = Annotated[
    date | None, Query(description="Business date to view; defaults to today (business date).")
]


# ------------------------------------------------------------------------- unit types


@router.get("/unit-types", response_model=list[OrgUnitTypeOut], summary="List unit types")
def list_unit_types(_auth: ViewOrg, db: DbSessionDep) -> list[OrgUnitTypeOut]:
    return unit_types_out(db, unit_types.list_unit_types(db))


@router.post(
    "/unit-types",
    response_model=OrgUnitTypeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a unit type",
)
def create_unit_type(
    body: OrgUnitTypeCreate, auth: ManageOrg, db: DbSessionDep, meta: RequestMetaDep
) -> OrgUnitTypeOut:
    unit_type = unit_types.create_unit_type(
        db,
        actor=auth.actor,
        meta=meta,
        code=body.code,
        name=body.name,
        description=body.description,
        sort_order=body.sort_order,
        allows_employee_assignment=body.allows_employee_assignment,
        parent_rule_mode=ParentRuleMode(body.parent_rule_mode),
        translations=body.translations,
    )
    db.commit()
    return unit_type_out(db, unit_type)


@router.get("/unit-types/{public_id}", response_model=OrgUnitTypeOut, summary="Get a unit type")
def get_unit_type(public_id: uuid.UUID, _auth: ViewOrg, db: DbSessionDep) -> OrgUnitTypeOut:
    return unit_type_out(db, unit_types.get_unit_type(db, public_id))


@router.patch(
    "/unit-types/{public_id}", response_model=OrgUnitTypeOut, summary="Update a unit type"
)
def update_unit_type(
    public_id: uuid.UUID,
    body: OrgUnitTypeUpdate,
    auth: ManageOrg,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> OrgUnitTypeOut:
    unit_type = unit_types.update_unit_type(
        db,
        public_id,
        actor=auth.actor,
        meta=meta,
        version=body.version,
        changes=body.changes(),
        translations=body.translations,
    )
    db.commit()
    return unit_type_out(db, unit_type)


@router.put(
    "/unit-types/{public_id}/parent-rules",
    response_model=OrgUnitTypeOut,
    summary="Replace the allowed parent types of a unit type",
)
def set_parent_rules(
    public_id: uuid.UUID,
    body: ParentRulesUpdate,
    auth: ManageOrg,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> OrgUnitTypeOut:
    unit_type = unit_types.set_parent_rules(
        db,
        public_id,
        actor=auth.actor,
        meta=meta,
        version=body.version,
        allow_root=body.allow_root,
        parent_type_ids=body.parent_type_ids,
    )
    db.commit()
    return unit_type_out(db, unit_type)


# ------------------------------------------------------------------------------ units


@router.get("/units", response_model=Page[OrgUnitOut], summary="List organisation units")
def list_units(
    _auth: ViewOrg,
    db: DbSessionDep,
    settings: SettingsDep,
    as_of: AsOf = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    unit_type: Annotated[uuid.UUID | None, Query(description="Unit type public_id")] = None,
    parent: Annotated[
        uuid.UUID | None, Query(description="Only direct children of this unit")
    ] = None,
    roots_only: bool = False,
    include_closed: bool = False,
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    cursor: Annotated[str | None, Query(max_length=80)] = None,
) -> Page[OrgUnitOut]:
    day = as_of or business_today(settings)
    rows, next_cursor = units.list_units(
        db,
        as_of=day,
        q=q,
        unit_type_id=unit_type,
        parent_id=parent,
        roots_only=roots_only,
        include_closed=include_closed,
        limit=limit,
        after_code=decode_code_cursor(cursor),
    )
    return Page[OrgUnitOut](items=UnitPresenter(db, day).many(rows), next_cursor=next_cursor)


@router.post(
    "/units",
    response_model=OrgUnitWriteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an organisation unit",
)
def create_unit(
    body: OrgUnitCreate,
    auth: ManageOrg,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> OrgUnitWriteOut:
    unit, warnings = units.create_unit(
        db,
        actor=auth.actor,
        meta=meta,
        code=body.code,
        name=body.name,
        short_name=body.short_name,
        unit_type_id=body.unit_type_id,
        location_id=body.location_id,
        parent_id=body.parent_id,
        effective_from=body.effective_from,
        external_ref=body.external_ref,
        translations=body.translations,
    )
    db.commit()
    return unit_write_out(db, unit, _view_date(unit.effective_from, settings), warnings)


@router.get("/tree", response_model=OrgTreeOut, summary="The organisation structure on a date")
def org_tree(
    _auth: ViewOrg,
    db: DbSessionDep,
    settings: SettingsDep,
    as_of: AsOf = None,
    include_closed: bool = False,
) -> OrgTreeOut:
    day = as_of or business_today(settings)
    rows, parent_of = units.org_tree(db, as_of=day, include_closed=include_closed)
    return tree_out(rows, parent_of, day)


@router.get("/units/{public_id}", response_model=OrgUnitOut, summary="Get an organisation unit")
def get_unit(
    public_id: uuid.UUID,
    _auth: ViewOrg,
    db: DbSessionDep,
    settings: SettingsDep,
    as_of: AsOf = None,
) -> OrgUnitOut:
    return UnitPresenter(db, as_of or business_today(settings)).one(units.get_unit(db, public_id))


@router.patch(
    "/units/{public_id}",
    response_model=OrgUnitWriteOut,
    summary="Correct wrongly recorded unit data (not for reorganisations)",
)
def correct_unit(
    public_id: uuid.UUID,
    body: OrgUnitCorrect,
    auth: ManageOrg,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> OrgUnitWriteOut:
    changes = body.changes()
    if body.translations is not None:
        changes["translations"] = body.translations
    unit, warnings = units.correct_unit(
        db,
        public_id,
        actor=auth.actor,
        meta=meta,
        version=body.version,
        reason=body.reason,
        changes=changes,
    )
    db.commit()
    return unit_write_out(db, unit, business_today(settings), warnings)


@router.post(
    "/units/{public_id}/move",
    response_model=OrgUnitWriteOut,
    summary="Move a unit under a new parent from a date (history is kept)",
)
def move_unit(
    public_id: uuid.UUID,
    body: OrgUnitMove,
    auth: ManageOrg,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> OrgUnitWriteOut:
    unit, warnings = units.move_unit(
        db,
        public_id,
        actor=auth.actor,
        meta=meta,
        version=body.version,
        new_parent_id=body.new_parent_id,
        effective_date=body.effective_date,
    )
    db.commit()
    return unit_write_out(db, unit, body.effective_date, warnings)


@router.post(
    "/units/{public_id}/close",
    response_model=OrgUnitWriteOut,
    summary="Close a unit from a date (refused while it has active dependants)",
)
def close_unit(
    public_id: uuid.UUID,
    body: OrgUnitClose,
    auth: ManageOrg,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> OrgUnitWriteOut:
    unit = units.close_unit(
        db,
        public_id,
        actor=auth.actor,
        meta=meta,
        version=body.version,
        effective_date=body.effective_date,
        reason=body.reason,
    )
    db.commit()
    return unit_write_out(db, unit, business_today(settings))


@router.post(
    "/units/{public_id}/reopen",
    response_model=OrgUnitWriteOut,
    summary="Undo a unit's closure",
)
def reopen_unit(
    public_id: uuid.UUID,
    body: OrgUnitReopen,
    auth: ManageOrg,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> OrgUnitWriteOut:
    unit = units.reopen_unit(
        db, public_id, actor=auth.actor, meta=meta, version=body.version, reason=body.reason
    )
    db.commit()
    return unit_write_out(db, unit, business_today(settings))


@router.get(
    "/units/{public_id}/history",
    response_model=UnitHistoryOut,
    summary="Placement history of a unit",
)
def unit_history(public_id: uuid.UUID, _auth: ViewOrg, db: DbSessionDep) -> UnitHistoryOut:
    unit = units.get_unit(db, public_id)
    return history_out(unit, units.unit_history(db, unit))


def _view_date(effective_from: date | None, settings: SettingsDep) -> date:
    """Show a newly created unit as of its start date when that is in the future."""
    today = business_today(settings)
    return effective_from if effective_from and effective_from > today else today


# -------------------------------------------------------------------------- locations


@router.get("/locations", response_model=list[LocationOut], summary="List locations")
def list_locations(
    _auth: ViewOrg, db: DbSessionDep, include_inactive: bool = False
) -> list[LocationOut]:
    return [
        location_out(item)
        for item in locations.list_locations(db, include_inactive=include_inactive)
    ]


@router.post(
    "/locations",
    response_model=LocationOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a location",
)
def create_location(
    body: LocationCreate, auth: ManageOrg, db: DbSessionDep, meta: RequestMetaDep
) -> LocationOut:
    location = locations.create_location(
        db,
        actor=auth.actor,
        meta=meta,
        code=body.code,
        name=body.name,
        details=body.model_dump(exclude={"code", "name"}),
    )
    db.commit()
    return location_out(location)


@router.get("/locations/{public_id}", response_model=LocationOut, summary="Get a location")
def get_location(public_id: uuid.UUID, _auth: ViewOrg, db: DbSessionDep) -> LocationOut:
    return location_out(locations.get_location(db, public_id))


@router.patch("/locations/{public_id}", response_model=LocationOut, summary="Update a location")
def update_location(
    public_id: uuid.UUID,
    body: LocationUpdate,
    auth: ManageOrg,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> LocationOut:
    location = locations.update_location(
        db,
        public_id,
        actor=auth.actor,
        meta=meta,
        version=body.version,
        changes=body.changes(),
    )
    db.commit()
    return location_out(location)
