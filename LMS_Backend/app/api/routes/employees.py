"""Employee master, assignments, functional roles, responsibilities, reporting lines
and account links (Stage C3).

Interim permissions (global only, Q-51; scoped access is C4):
* reads: ``employees.view``; assignment timeline and history: ``employees.history.view``;
* changes: ``employees.manage``; reporting lines: ``reporting_lines.manage``;
* account link/unlink: ``employees.manage`` and ``user_accounts.manage``.
Being a manager in a reporting line grants no access. Every change is audited.
"""

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.admin_support import audit_denials
from app.api.deps import DbSessionDep, RequestMetaDep, SettingsDep, require_permission
from app.api.employee_presenters import (
    assignment_out,
    effective_role_out,
    employee_account_out,
    employee_events_out,
    employee_out,
    employee_summaries,
    reporting_record_out,
    reporting_type_out,
    responsibility_out,
    role_record_out,
    separation_preview_out,
)
from app.api.org_presenters import warnings_out
from app.models.employees import AssignmentType, Employee, EmploymentStatus, FunctionalRoleKind
from app.models.occupation import Designation
from app.models.organisation import Location
from app.schemas.audit import AuditEventOut
from app.schemas.employees import (
    AccountLink,
    AccountUnlink,
    AssignmentChange,
    AssignmentCorrect,
    AssignmentCreate,
    AssignmentEnd,
    AssignmentOut,
    AssignmentWriteOut,
    DataQualityOut,
    EmployeeAccountOut,
    EmployeeCorrect,
    EmployeeCreate,
    EmployeeOut,
    EmployeeSummary,
    EmploymentStatusChange,
    FunctionalRolesOut,
    ManagerSet,
    RecordEnd,
    ReportingOut,
    ReportingRecordOut,
    ReportingTypeOut,
    ResponsibilityAssign,
    ResponsibilityRecordOut,
    RoleAssign,
    RoleRecordOut,
    SeparationPreviewOut,
    StatusFilter,
)
from app.schemas.errors import ErrorResponse
from app.schemas.pagination import Page
from app.services.employees import (
    accounts,
    assignments,
    employees,
    history,
    quality,
    reporting,
    responsibilities,
    roles,
)
from app.services.employees.common import decode_employee_cursor, encode_text_cursor, get_employee
from app.services.identity.accounts import decode_cursor, encode_cursor
from app.services.identity.context import AuthContext
from app.services.identity.permissions import Permission
from app.services.organisation.support import business_today, get_or_404

router = APIRouter(
    prefix="/employees",
    tags=["employees"],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
    },
)

ViewEmployees = Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYEES_VIEW))]
ViewHistory = Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYEES_HISTORY_VIEW))]
ManageEmployees = Annotated[AuthContext, Depends(require_permission(Permission.EMPLOYEES_MANAGE))]
ManageReporting = Annotated[
    AuthContext, Depends(require_permission(Permission.REPORTING_LINES_MANAGE))
]
ManageLinks = Annotated[
    AuthContext,
    Depends(require_permission(Permission.EMPLOYEES_MANAGE, Permission.USER_ACCOUNTS_MANAGE)),
]
AsOf = Annotated[
    date | None, Query(description="Business date to view; defaults to today (business date).")
]
Limit = Annotated[int, Query(ge=1, le=200)]
Cursor = Annotated[str | None, Query(max_length=80)]


def _page_cursor(rows: list[Employee], limit: int) -> str | None:
    return encode_text_cursor(rows[limit - 1].employee_code) if len(rows) > limit else None


# ---------------------------------------------------------------- static routes


@router.get(
    "/reporting-types", response_model=list[ReportingTypeOut], summary="List reporting types"
)
def list_reporting_types(_auth: ViewEmployees, db: DbSessionDep) -> list[ReportingTypeOut]:
    return [reporting_type_out(item) for item in reporting.list_types(db)]


@router.get(
    "/data-quality",
    response_model=DataQualityOut,
    summary="Data-quality counts, and the employees failing one check",
)
def data_quality(
    _auth: ManageEmployees,
    db: DbSessionDep,
    settings: SettingsDep,
    as_of: AsOf = None,
    check: Annotated[str | None, Query(max_length=50)] = None,
    limit: Limit = 50,
    cursor: Cursor = None,
) -> DataQualityOut:
    day = as_of or business_today(settings)
    items: list[EmployeeSummary] = []
    next_cursor = None
    if check is not None:
        rows = quality.quality_list(
            db, check=check, as_of=day, after_code=decode_employee_cursor(cursor), limit=limit + 1
        )
        next_cursor = _page_cursor(rows, limit)
        items = employee_summaries(db, rows[:limit], day)
    return DataQualityOut(
        as_of=day,
        counts=quality.quality_counts(db, day),
        check=check,
        items=items,
        next_cursor=next_cursor,
    )


# -------------------------------------------------------------------- employees


@router.get("", response_model=Page[EmployeeSummary], summary="Employee directory")
def list_employees(
    _auth: ViewEmployees,
    db: DbSessionDep,
    settings: SettingsDep,
    as_of: AsOf = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    status_filter: Annotated[
        StatusFilter | None,
        Query(alias="status", description="'unknown' = status not recorded"),
    ] = None,
    unit: Annotated[uuid.UUID | None, Query(description="Organisation unit public_id")] = None,
    include_descendants: bool = False,
    location: Annotated[uuid.UUID | None, Query(description="Location public_id")] = None,
    designation: Annotated[uuid.UUID | None, Query(description="Designation public_id")] = None,
    has_account: Annotated[
        bool | None, Query(description="Has a linked account that is not disabled")
    ] = None,
    limit: Limit = 50,
    cursor: Cursor = None,
) -> Page[EmployeeSummary]:
    day = as_of or business_today(settings)
    location_id = (
        get_or_404(db, Location, location, "location_not_found", "Location not found.").id
        if location
        else None
    )
    designation_id = (
        get_or_404(
            db, Designation, designation, "designation_not_found", "Designation not found."
        ).id
        if designation
        else None
    )
    rows = employees.list_employees(
        db,
        as_of=day,
        q=q,
        status=status_filter,
        unit_id=unit,
        include_descendants=include_descendants,
        location_id=location_id,
        designation_id=designation_id,
        has_account=has_account,
        after_code=decode_employee_cursor(cursor),
        limit=limit + 1,
    )
    return Page[EmployeeSummary](
        items=employee_summaries(db, rows[:limit], day), next_cursor=_page_cursor(rows, limit)
    )


@router.post(
    "",
    response_model=EmployeeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create an employee record",
)
def create_employee(
    body: EmployeeCreate,
    auth: ManageEmployees,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> EmployeeOut:
    employee = employees.create_employee(db, actor=auth.actor, meta=meta, values=body.model_dump())
    db.commit()
    return employee_out(db, employee, business_today(settings))


@router.get("/{public_id}", response_model=EmployeeOut, summary="Get an employee")
def get_employee_detail(
    public_id: uuid.UUID,
    _auth: ViewEmployees,
    db: DbSessionDep,
    settings: SettingsDep,
    as_of: AsOf = None,
) -> EmployeeOut:
    return employee_out(
        db, employees.employee_detail(db, public_id), as_of or business_today(settings)
    )


@router.patch(
    "/{public_id}", response_model=EmployeeOut, summary="Correct an employee's recorded data"
)
def correct_employee(
    public_id: uuid.UUID,
    body: EmployeeCorrect,
    auth: ManageEmployees,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> EmployeeOut:
    employee = employees.correct_employee(
        db,
        public_id,
        actor=auth.actor,
        meta=meta,
        version=body.version,
        reason=body.reason,
        changes=body.changes(),
    )
    db.commit()
    return employee_out(db, employee, business_today(settings))


@router.post(
    "/{public_id}/employment-status",
    response_model=EmployeeOut,
    summary="Change employment status (separation can end open records)",
)
def change_employment_status(
    public_id: uuid.UUID,
    body: EmploymentStatusChange,
    auth: ManageEmployees,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> EmployeeOut:
    employee = employees.change_employment_status(
        db,
        public_id,
        actor=auth.actor,
        meta=meta,
        version=body.version,
        status=EmploymentStatus(body.status),
        separation_date=body.separation_date,
        end_open_records=body.end_open_records,
        end_direct_reports=body.end_direct_reports,
        reason=body.reason,
    )
    db.commit()
    return employee_out(db, employee, business_today(settings))


@router.get(
    "/{public_id}/separation-preview",
    response_model=SeparationPreviewOut,
    summary="Preview what a separation would end (read-only; nothing is changed)",
)
def separation_preview(
    public_id: uuid.UUID,
    _auth: ManageEmployees,
    db: DbSessionDep,
    separation_date: Annotated[date, Query(description="Last working day (YYYY-MM-DD).")],
) -> SeparationPreviewOut:
    return separation_preview_out(employees.separation_preview(db, public_id, separation_date))


@router.get(
    "/{public_id}/history",
    response_model=Page[AuditEventOut],
    summary="Audit history of an employee (newest first; no network details)",
)
def employee_history(
    public_id: uuid.UUID,
    _auth: ViewHistory,
    db: DbSessionDep,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    cursor: Annotated[str | None, Query(max_length=40)] = None,
) -> Page[AuditEventOut]:
    employee = get_employee(db, public_id)
    rows = history.employee_history(db, employee, before_id=decode_cursor(cursor), limit=limit + 1)
    next_cursor = encode_cursor(rows[limit - 1].id) if len(rows) > limit else None
    return Page[AuditEventOut](items=employee_events_out(db, rows[:limit]), next_cursor=next_cursor)


# ------------------------------------------------------------------ assignments


@router.get(
    "/{public_id}/assignments",
    response_model=list[AssignmentOut],
    summary="Assignment timeline",
)
def list_assignments(
    public_id: uuid.UUID,
    _auth: ViewHistory,
    db: DbSessionDep,
    include_ended: bool = True,
) -> list[AssignmentOut]:
    employee = get_employee(db, public_id)
    return [
        assignment_out(row)
        for row in assignments.list_assignments(db, employee, include_ended=include_ended)
    ]


@router.post(
    "/{public_id}/assignments",
    response_model=AssignmentWriteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add an assignment",
)
def create_assignment(
    public_id: uuid.UUID,
    body: AssignmentCreate,
    auth: ManageEmployees,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> AssignmentWriteOut:
    row, warnings = assignments.create_assignment(
        db,
        public_id,
        actor=auth.actor,
        meta=meta,
        assignment_type=AssignmentType(body.assignment_type),
        raw=body.model_dump(
            include={"org_unit_id", "designation_id", "grade_id", "job_level_id", "location_id"}
        ),
        effective_from=body.effective_from,
        effective_to=body.effective_to,
        reason=body.reason,
    )
    db.commit()
    return AssignmentWriteOut(assignment=assignment_out(row), warnings=warnings_out(warnings))


@router.post(
    "/{public_id}/assignments/{assignment_id}/change",
    response_model=AssignmentWriteOut,
    status_code=status.HTTP_201_CREATED,
    summary="Change an assignment from a date (transfer, designation, grade, level, location)",
)
def change_assignment(
    public_id: uuid.UUID,
    assignment_id: uuid.UUID,
    body: AssignmentChange,
    auth: ManageEmployees,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> AssignmentWriteOut:
    row, warnings = assignments.change_assignment(
        db,
        public_id,
        assignment_id,
        actor=auth.actor,
        meta=meta,
        version=body.version,
        effective_date=body.effective_date,
        raw=body.changes("effective_date"),
        reason=body.reason,
    )
    db.commit()
    return AssignmentWriteOut(assignment=assignment_out(row), warnings=warnings_out(warnings))


@router.post(
    "/{public_id}/assignments/{assignment_id}/end",
    response_model=AssignmentOut,
    summary="End an assignment",
)
def end_assignment(
    public_id: uuid.UUID,
    assignment_id: uuid.UUID,
    body: AssignmentEnd,
    auth: ManageEmployees,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> AssignmentOut:
    row = assignments.end_assignment(
        db,
        public_id,
        assignment_id,
        actor=auth.actor,
        meta=meta,
        version=body.version,
        effective_to=body.effective_to,
        reason=body.reason,
    )
    db.commit()
    return assignment_out(row)


@router.patch(
    "/{public_id}/assignments/{assignment_id}",
    response_model=AssignmentWriteOut,
    summary="Correct an assignment (back-dated fix, audited before/after)",
)
def correct_assignment(
    public_id: uuid.UUID,
    assignment_id: uuid.UUID,
    body: AssignmentCorrect,
    auth: ManageEmployees,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> AssignmentWriteOut:
    row, warnings = assignments.correct_assignment(
        db,
        public_id,
        assignment_id,
        actor=auth.actor,
        meta=meta,
        version=body.version,
        reason=body.reason,
        changes=body.changes(),
    )
    db.commit()
    return AssignmentWriteOut(assignment=assignment_out(row), warnings=warnings_out(warnings))


# ------------------------------------------------------------- functional roles


@router.get(
    "/{public_id}/functional-roles",
    response_model=FunctionalRolesOut,
    summary="Effective functional roles (derived, manual, excluded) on a date",
)
def list_functional_roles(
    public_id: uuid.UUID,
    _auth: ViewEmployees,
    db: DbSessionDep,
    settings: SettingsDep,
    as_of: AsOf = None,
    include_ended: bool = False,
) -> FunctionalRolesOut:
    day = as_of or business_today(settings)
    employee = get_employee(db, public_id)
    return FunctionalRolesOut(
        as_of=day,
        roles=[effective_role_out(item) for item in roles.effective_roles(db, employee, day)],
        records=[
            role_record_out(record)
            for record in roles.list_role_records(db, employee, include_ended=include_ended)
        ],
    )


@router.post(
    "/{public_id}/functional-roles",
    response_model=RoleRecordOut,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a functional role manually, or exclude a derived one",
)
def assign_functional_role(
    public_id: uuid.UUID,
    body: RoleAssign,
    auth: ManageEmployees,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> RoleRecordOut:
    record = roles.assign_role(
        db,
        public_id,
        actor=auth.actor,
        meta=meta,
        functional_role_id=body.functional_role_id,
        kind=FunctionalRoleKind(body.kind),
        effective_from=body.effective_from,
        effective_to=body.effective_to,
        reason=body.reason,
    )
    db.commit()
    return role_record_out(record)


@router.post(
    "/{public_id}/functional-roles/{record_id}/end",
    response_model=RoleRecordOut,
    summary="End a manual role or an exclusion",
)
def end_functional_role(
    public_id: uuid.UUID,
    record_id: uuid.UUID,
    body: RecordEnd,
    auth: ManageEmployees,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> RoleRecordOut:
    record = roles.end_role(
        db,
        public_id,
        record_id,
        actor=auth.actor,
        meta=meta,
        effective_to=body.effective_to,
        reason=body.reason,
    )
    db.commit()
    return role_record_out(record)


# ------------------------------------------------------------- responsibilities


@router.get(
    "/{public_id}/responsibilities",
    response_model=list[ResponsibilityRecordOut],
    summary="Responsibilities",
)
def list_responsibilities(
    public_id: uuid.UUID,
    _auth: ViewEmployees,
    db: DbSessionDep,
    include_ended: bool = False,
) -> list[ResponsibilityRecordOut]:
    employee = get_employee(db, public_id)
    return [
        responsibility_out(record)
        for record in responsibilities.list_responsibilities(
            db, employee, include_ended=include_ended
        )
    ]


@router.post(
    "/{public_id}/responsibilities",
    response_model=ResponsibilityRecordOut,
    status_code=status.HTTP_201_CREATED,
    summary="Assign a responsibility (optionally for a unit or location)",
)
def assign_responsibility(
    public_id: uuid.UUID,
    body: ResponsibilityAssign,
    auth: ManageEmployees,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> ResponsibilityRecordOut:
    record = responsibilities.assign_responsibility(
        db,
        public_id,
        actor=auth.actor,
        meta=meta,
        responsibility_id=body.responsibility_id,
        context_unit_id=body.context_unit_id,
        context_location_id=body.context_location_id,
        effective_from=body.effective_from,
        effective_to=body.effective_to,
        reason=body.reason,
    )
    db.commit()
    return responsibility_out(record)


@router.post(
    "/{public_id}/responsibilities/{record_id}/end",
    response_model=ResponsibilityRecordOut,
    summary="End a responsibility",
)
def end_responsibility(
    public_id: uuid.UUID,
    record_id: uuid.UUID,
    body: RecordEnd,
    auth: ManageEmployees,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> ResponsibilityRecordOut:
    record = responsibilities.end_responsibility(
        db,
        public_id,
        record_id,
        actor=auth.actor,
        meta=meta,
        effective_to=body.effective_to,
        reason=body.reason,
    )
    db.commit()
    return responsibility_out(record)


# -------------------------------------------------------------------- reporting


@router.get(
    "/{public_id}/reporting",
    response_model=ReportingOut,
    summary="Managers, reporting history and direct reports",
)
def get_reporting(
    public_id: uuid.UUID,
    _auth: ViewEmployees,
    db: DbSessionDep,
    settings: SettingsDep,
    as_of: AsOf = None,
) -> ReportingOut:
    day = as_of or business_today(settings)
    employee = get_employee(db, public_id)
    return ReportingOut(
        as_of=day,
        managers=[reporting_record_out(r) for r in reporting.current_managers(db, employee, day)],
        history=[reporting_record_out(r) for r in reporting.reporting_history(db, employee)],
        direct_reports=[
            reporting_record_out(r) for r in reporting.direct_reports(db, employee, day)
        ],
    )


@router.post(
    "/{public_id}/reporting",
    response_model=ReportingRecordOut,
    status_code=status.HTTP_201_CREATED,
    summary="Set a manager from a date (replaces the current line manager)",
)
def set_manager(
    public_id: uuid.UUID,
    body: ManagerSet,
    auth: ManageReporting,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> ReportingRecordOut:
    record = reporting.set_manager(
        db,
        public_id,
        actor=auth.actor,
        meta=meta,
        manager_id=body.manager_id,
        relationship_type_id=body.relationship_type_id,
        effective_from=body.effective_from,
        reason=body.reason,
    )
    db.commit()
    return reporting_record_out(record)


@router.post(
    "/{public_id}/reporting/{record_id}/end",
    response_model=ReportingRecordOut,
    summary="End a reporting relationship",
)
def end_reporting(
    public_id: uuid.UUID,
    record_id: uuid.UUID,
    body: RecordEnd,
    auth: ManageReporting,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> ReportingRecordOut:
    record = reporting.end_relationship(
        db,
        public_id,
        record_id,
        actor=auth.actor,
        meta=meta,
        effective_to=body.effective_to,
        reason=body.reason,
    )
    db.commit()
    return reporting_record_out(record)


# ---------------------------------------------------------------------- account


@router.get(
    "/{public_id}/account",
    response_model=EmployeeAccountOut,
    summary="Linked login accounts, mismatch flags and link history",
)
def get_account(public_id: uuid.UUID, _auth: ViewEmployees, db: DbSessionDep) -> EmployeeAccountOut:
    employee = get_employee(db, public_id)
    return employee_account_out(db, accounts.account_summary(db, employee))


@router.put(
    "/{public_id}/account",
    response_model=EmployeeAccountOut,
    summary="Link a login account to the employee",
)
def link_account(
    public_id: uuid.UUID,
    body: AccountLink,
    auth: ManageLinks,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> EmployeeAccountOut:
    with audit_denials(db, auth, meta, "employee_account.link"):
        accounts.link_account(
            db,
            public_id,
            actor=auth.actor,
            meta=meta,
            user_public_id=body.user_public_id,
            reason=body.reason,
        )
    db.commit()
    employee = get_employee(db, public_id)
    return employee_account_out(db, accounts.account_summary(db, employee))


@router.post(
    "/{public_id}/account/unlink",
    response_model=EmployeeAccountOut,
    summary="Unlink a login account (the account itself is unchanged)",
)
def unlink_account(
    public_id: uuid.UUID,
    body: AccountUnlink,
    auth: ManageLinks,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> EmployeeAccountOut:
    with audit_denials(db, auth, meta, "employee_account.unlink"):
        accounts.unlink_account(
            db,
            public_id,
            actor=auth.actor,
            meta=meta,
            user_public_id=body.user_public_id,
            reason=body.reason,
        )
    db.commit()
    employee = get_employee(db, public_id)
    return employee_account_out(db, accounts.account_summary(db, employee))
