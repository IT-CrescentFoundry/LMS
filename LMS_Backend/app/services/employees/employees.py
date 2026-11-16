"""Employee records: create, correct, employment status, directory and context.

Rules:
* ``employment_status`` NULL means "not recorded" and is never treated as active;
  directory filters expose it as the explicit ``unknown`` bucket.
* ``date_of_separation`` is the last day of employment; records must end no later
  than the following day (half-open periods). Provisional convention [V].
* Separation never changes a linked LMS account (Q-50) and never ends records
  silently: the employee's open records block it unless ``end_open_records`` is
  requested, and direct reports' reporting lines block it unless
  ``end_direct_reports`` is requested (each ending is audited on the subordinate).
"""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import ColumnElement, exists, or_, select
from sqlalchemy.orm import Session

from app.core.context import RequestMeta
from app.core.errors import AppError
from app.db.types import utcnow
from app.models.employees import (
    LINE_MANAGER,
    Employee,
    EmployeeAssignment,
    EmployeeFunctionalRole,
    EmployeeResponsibility,
    EmploymentStatus,
    ReportingRelationship,
    ReportingRelationshipType,
)
from app.models.identity import AccountStatus, UserAccount
from app.models.organisation import OrgUnit
from app.schemas.errors import ValidationIssue
from app.services.audit_service import AuditEventType, TargetType
from app.services.employees.common import (
    covers_day,
    get_employee,
    lock_employee,
    lock_reporting,
    locking,
    normalise_employee_code,
)
from app.services.identity.context import Actor
from app.services.organisation.graph import ancestor_path, descendants
from app.services.organisation.support import (
    apply_changes,
    audit,
    clean_text,
    ensure_absent,
    ensure_version,
    flush_unique,
    like_pattern,
    touch,
)
from app.services.organisation.units import get_unit, parents_on

_CODE_TAKEN = ("employee_code_taken", "Another employee already uses this employee code.")
_CORRECTABLE = (
    "employee_code",
    "full_name",
    "display_name",
    "preferred_language",
    "work_email",
    "date_of_joining",
    "external_ref",
)


def _check_dates(joining: date | None, separation: date | None) -> None:
    if joining is not None and separation is not None and separation < joining:
        raise AppError(
            422,
            "invalid_employment_dates",
            "The separation date cannot be before the joining date.",
        )


def create_employee(
    db: Session,
    *,
    actor: Actor,
    meta: RequestMeta,
    values: Mapping[str, Any],
) -> Employee:
    code = normalise_employee_code(values["employee_code"])
    status = values.get("employment_status")
    separation = values.get("date_of_separation")
    if status == EmploymentStatus.SEPARATED.value and separation is None:
        raise AppError(
            422, "separation_date_required", "A separated employee needs a separation date."
        )
    if separation is not None and status != EmploymentStatus.SEPARATED.value:
        raise AppError(
            422,
            "separation_date_not_allowed",
            "A separation date can only be recorded for a separated employee.",
        )
    _check_dates(values.get("date_of_joining"), separation)
    ensure_absent(db, select(Employee.id).where(Employee.employee_code == code), *_CODE_TAKEN)
    employee = Employee(
        employee_code=code,
        full_name=values["full_name"].strip(),
        display_name=clean_text(values.get("display_name")),
        preferred_language=values.get("preferred_language"),
        work_email=clean_text(values.get("work_email")),
        employment_status=status,
        date_of_joining=values.get("date_of_joining"),
        date_of_separation=separation,
        external_ref=clean_text(values.get("external_ref")),
        created_by_user_id=actor.user_id,
        updated_by_user_id=actor.user_id,
    )
    db.add(employee)
    flush_unique(db, *_CODE_TAKEN)
    audit(
        db,
        actor,
        meta,
        AuditEventType.EMPLOYEE_CREATED,
        TargetType.EMPLOYEE,
        employee.public_id,
        {"employee_code": code, "employment_status": status},
    )
    return employee


def _records_starting_before(db: Session, employee: Employee, day: date) -> bool:
    """Any of the employee's records starting before ``day`` (or with no start)?"""
    for model in (EmployeeAssignment, EmployeeFunctionalRole, EmployeeResponsibility):
        hit = db.scalar(
            locking(
                select(model.id).where(
                    model.employee_id == employee.id,
                    (model.effective_from.is_(None)) | (model.effective_from < day),
                )
            ).limit(1)
        )
        if hit is not None:
            return True
    hit = db.scalar(
        locking(
            select(ReportingRelationship.id).where(
                ReportingRelationship.employee_id == employee.id,
                (ReportingRelationship.effective_from.is_(None))
                | (ReportingRelationship.effective_from < day),
            )
        ).limit(1)
    )
    return hit is not None


def correct_employee(
    db: Session,
    public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    reason: str | None,
    changes: Mapping[str, Any],
) -> Employee:
    """Fix wrongly recorded data in place (audited before/after). Status has its own path."""
    employee = lock_employee(db, public_id)
    ensure_version(employee, version)
    values: dict[str, Any] = {}
    for key, raw in changes.items():
        if key not in _CORRECTABLE:
            continue
        if key == "employee_code":
            values[key] = normalise_employee_code(raw)
        elif key == "full_name":
            values[key] = raw.strip()
        elif key in ("display_name", "work_email", "external_ref"):
            values[key] = clean_text(raw)
        else:
            values[key] = raw
    if values.get("employee_code", employee.employee_code) != employee.employee_code:
        ensure_absent(
            db,
            select(Employee.id).where(
                Employee.employee_code == values["employee_code"], Employee.id != employee.id
            ),
            *_CODE_TAKEN,
        )
    if "date_of_joining" in values and values["date_of_joining"] != employee.date_of_joining:
        joining = values["date_of_joining"]
        _check_dates(joining, employee.date_of_separation)
        if joining is not None and _records_starting_before(db, employee, joining):
            raise AppError(
                422,
                "outside_employment_period",
                "Records start before the new joining date. Correct them first.",
            )
    diff = apply_changes(employee, values)
    if diff:
        touch(employee, actor)
        flush_unique(db, *_CODE_TAKEN)
        audit(
            db,
            actor,
            meta,
            AuditEventType.EMPLOYEE_CORRECTED,
            TargetType.EMPLOYEE,
            employee.public_id,
            {"employee_code": employee.employee_code, "reason": reason, "changes": diff},
        )
    return employee


# ------------------------------------------------------------ employment status


@dataclass
class _OpenRecord:
    kind: str
    public_id: uuid.UUID
    label: str
    name: str
    row: Any
    starts_after: bool


def _read(statement: Any, lock: bool) -> Any:
    # Writes use locking reads (see ``common``); the read-only preview uses plain reads.
    return locking(statement) if lock else statement


def _still_running(model: Any, end: date) -> ColumnElement[bool]:
    return (model.effective_to.is_(None)) | (model.effective_to > end)  # type: ignore[no-any-return]


def _open_records(
    db: Session, employee: Employee, end: date, *, lock: bool = True
) -> list[_OpenRecord]:
    """The employee's own records still running on or after ``end`` (exclusive end),
    including reporting lines in which the employee is the subordinate."""
    found: list[_OpenRecord] = []
    sources: list[tuple[str, Any, Any]] = [
        ("assignment", EmployeeAssignment, lambda row: (row.org_unit.code, row.org_unit.name)),
        (
            "functional_role",
            EmployeeFunctionalRole,
            lambda row: (row.functional_role.code, row.functional_role.name),
        ),
        (
            "responsibility",
            EmployeeResponsibility,
            lambda row: (row.responsibility.code, row.responsibility.name),
        ),
        (
            "reporting_line",
            ReportingRelationship,
            lambda row: (row.manager.employee_code, row.manager.full_name),
        ),
    ]
    for kind, model, describe in sources:
        rows = db.scalars(
            _read(
                select(model)
                .where(model.employee_id == employee.id, _still_running(model, end))
                .order_by(model.id),
                lock,
            )
        ).unique()
        for row in rows:
            code, name = describe(row)
            starts_after = row.effective_from is not None and row.effective_from >= end
            found.append(_OpenRecord(kind, row.public_id, code, name, row, starts_after))
    return found


def _direct_reports(
    db: Session, employee: Employee, end: date, *, lock: bool = True
) -> list[_OpenRecord]:
    """Reporting lines in which the employee is the MANAGER, running on or after ``end``.

    These belong to other employees, so they are never ended as a side effect: they
    are listed (labelled with the subordinate's code) and only ended on an explicit
    ``end_direct_reports`` request, with an audit event on each subordinate.
    """
    rows = db.scalars(
        _read(
            select(ReportingRelationship)
            .where(
                ReportingRelationship.manager_employee_id == employee.id,
                _still_running(ReportingRelationship, end),
            )
            .order_by(ReportingRelationship.id),
            lock,
        )
    ).unique()
    return [
        _OpenRecord(
            "direct_report",
            row.public_id,
            row.employee.employee_code,
            row.employee.full_name,
            row,
            row.effective_from is not None and row.effective_from >= end,
        )
        for row in rows
    ]


@dataclass
class SeparationImpact:
    """What a separation on ``separation_date`` would end (read-only preview)."""

    employee: Employee
    separation_date: date
    records_end_on: date
    own_records: list[_OpenRecord]
    direct_reports: list[_OpenRecord]

    @property
    def blocked(self) -> bool:
        """Records starting after the last working day cannot be ended by separation."""
        return any(r.starts_after for r in [*self.own_records, *self.direct_reports])


def separation_preview(
    db: Session, public_id: uuid.UUID, separation_date: date
) -> SeparationImpact:
    """Read-only: list everything a separation on ``separation_date`` would affect.

    Uses the same collectors as ``change_employment_status`` with plain reads; nothing
    is written or audited. The real separation re-checks everything under locks, so
    a preview can become stale and the POST may still answer 409.
    """
    employee = get_employee(db, public_id)
    _check_dates(employee.date_of_joining, separation_date)
    end = separation_date + timedelta(days=1)  # exclusive end of employment
    return SeparationImpact(
        employee=employee,
        separation_date=separation_date,
        records_end_on=end,
        own_records=_open_records(db, employee, end, lock=False),
        direct_reports=_direct_reports(db, employee, end, lock=False),
    )


def _end_record(record: _OpenRecord, end: date, actor: Actor, now: datetime) -> None:
    """End a record on the separation; row-level attribution to the acting admin."""
    row = record.row
    row.effective_to = end
    row.ended_at = now
    row.ended_by_user_id = actor.user_id
    if hasattr(row, "updated_by_user_id"):  # tracked rows (assignments) also record it
        touch(row, actor)


def change_employment_status(
    db: Session,
    public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    status: EmploymentStatus,
    separation_date: date | None,
    end_open_records: bool,
    reason: str | None,
    end_direct_reports: bool = False,
) -> Employee:
    """Change the current employment status.

    Separation ends nothing silently. It is refused (409, every affected record
    listed) while records continue after the separation date:

    * the employee's own assignments, roles, responsibilities and reporting lines
      (as subordinate) - ended only with ``end_open_records``;
    * reporting lines of the employee's direct reports (the employee as manager) -
      ended only with ``end_direct_reports``, each with its own audit event on the
      subordinate.

    Lock order (``common``): reporting graph lock (separation only), employee row.
    """
    if status is EmploymentStatus.SEPARATED:
        lock_reporting(db)  # it may end reporting lines: same order as reporting writes
    employee = lock_employee(db, public_id)
    ensure_version(employee, version)
    previous = {"status": employee.employment_status, "separation": employee.date_of_separation}
    ended: dict[str, list[str]] = {}

    if status is EmploymentStatus.SEPARATED:
        if separation_date is None:
            raise AppError(
                422, "separation_date_required", "A separated employee needs a separation date."
            )
        _check_dates(employee.date_of_joining, separation_date)
        if (employee.employment_status, employee.date_of_separation) == (
            status.value,
            separation_date,
        ):
            raise AppError(422, "no_change", "The employee already has this status.")
        end = separation_date + timedelta(days=1)  # exclusive end of employment
        own = _open_records(db, employee, end)
        reports = _direct_reports(db, employee, end)
        blockers = [r for r in [*own, *reports] if r.starts_after]
        if not end_open_records:
            blockers += [r for r in own if not r.starts_after]
        if not end_direct_reports:
            blockers += [r for r in reports if not r.starts_after]
        if blockers:
            raise AppError(
                409,
                "open_records_on_separation",
                "Records continue after the separation date. End them first, or explicitly "
                "choose to end them on the separation date (own records and direct reports "
                "are confirmed separately).",
                details=[
                    ValidationIssue(
                        location=[record.kind, record.label],
                        message="Record starts after the separation date"
                        if record.starts_after
                        else "Record continues after the separation date",
                        type="starts_after_separation"
                        if record.starts_after
                        else f"open_{record.kind}",
                    )
                    for record in blockers
                ],
            )
        employee.date_of_separation = separation_date
        now = utcnow()
        for record in [*own, *reports]:
            _end_record(record, end, actor, now)
            ended.setdefault(record.kind, []).append(str(record.public_id))
        db.flush()
        for record in reports:  # the subordinate's own history shows the change
            subordinate = record.row.employee
            audit(
                db,
                actor,
                meta,
                AuditEventType.REPORTING_ENDED,
                TargetType.EMPLOYEE,
                subordinate.public_id,
                {
                    "employee_code": subordinate.employee_code,
                    "record": str(record.public_id),
                    "relationship_type": record.row.relationship_type.code,
                    "manager_code": employee.employee_code,
                    "to": end,
                    "cause": "manager_separated",
                    "reason": reason,
                },
            )
    else:
        if separation_date is not None:
            raise AppError(
                422,
                "separation_date_not_allowed",
                "A separation date can only be recorded for a separated employee.",
            )
        if employee.employment_status == status.value:
            raise AppError(422, "no_change", "The employee already has this status.")
        employee.date_of_separation = None  # re-joining clears the previous separation date

    employee.employment_status = status.value
    touch(employee, actor)
    db.flush()
    audit(
        db,
        actor,
        meta,
        AuditEventType.EMPLOYEE_STATUS_CHANGED,
        TargetType.EMPLOYEE,
        employee.public_id,
        {
            "employee_code": employee.employee_code,
            "from_status": previous["status"],
            "to_status": status.value,
            "from_separation_date": previous["separation"],
            "separation_date": employee.date_of_separation,
            "ended_records": ended,
            "reason": reason,
        },
    )
    return employee


# -------------------------------------------------------------- directory/context


@dataclass
class EmployeeContext:
    """Where an employee sits on a date (derived, never stored)."""

    primary: EmployeeAssignment | None = None
    path: list[OrgUnit] = field(default_factory=list)
    line_manager: Employee | None = None
    accounts: list[UserAccount] = field(default_factory=list)


def load_context(db: Session, employees: list[Employee], as_of: date) -> dict[int, EmployeeContext]:
    ids = [employee.id for employee in employees]
    result = {employee_id: EmployeeContext() for employee_id in ids}
    if not ids:
        return result
    for assignment in db.scalars(
        select(EmployeeAssignment)
        .where(
            EmployeeAssignment.employee_id.in_(ids),
            EmployeeAssignment.assignment_type == "primary",
            *covers_day(EmployeeAssignment, as_of),
        )
        .order_by(EmployeeAssignment.id)
    ).unique():
        result[assignment.employee_id].primary = assignment
    parent_of = parents_on(db, as_of)
    paths = {
        employee_id: ancestor_path(context.primary.org_unit_id, parent_of)
        for employee_id, context in result.items()
        if context.primary is not None
    }
    unit_ids = {unit_id for path in paths.values() for unit_id in path}
    units = (
        {
            unit.id: unit
            for unit in db.scalars(select(OrgUnit).where(OrgUnit.id.in_(unit_ids))).unique()
        }
        if unit_ids
        else {}
    )
    for employee_id, path in paths.items():
        result[employee_id].path = [units[unit_id] for unit_id in path if unit_id in units]
    for relationship in db.scalars(
        select(ReportingRelationship)
        .join(ReportingRelationshipType)
        .where(
            ReportingRelationship.employee_id.in_(ids),
            ReportingRelationshipType.code == LINE_MANAGER,
            *covers_day(ReportingRelationship, as_of),
        )
    ).unique():
        result[relationship.employee_id].line_manager = relationship.manager
    for account in db.scalars(
        select(UserAccount).where(UserAccount.employee_id.in_(ids)).order_by(UserAccount.id)
    ):
        if account.employee_id is not None:
            result[account.employee_id].accounts.append(account)
    for context in result.values():
        context.accounts.sort(key=lambda account: account.status == AccountStatus.DISABLED.value)
    return result


STATUS_FILTERS = ("active", "on_leave", "separated", "unknown")


def list_employees(
    db: Session,
    *,
    as_of: date,
    q: str | None,
    status: str | None,
    unit_id: uuid.UUID | None,
    include_descendants: bool,
    location_id: int | None,
    designation_id: int | None,
    has_account: bool | None,
    after_code: str | None,
    limit: int,
) -> list[Employee]:
    statement = select(Employee).order_by(Employee.employee_code).limit(limit)
    if q and q.strip():
        pattern = like_pattern(q)
        statement = statement.where(
            or_(
                Employee.employee_code.like(pattern, escape="\\"),
                Employee.full_name.like(pattern, escape="\\"),
                Employee.display_name.like(pattern, escape="\\"),
            )
        )
    if status == "unknown":
        statement = statement.where(Employee.employment_status.is_(None))
    elif status is not None:
        statement = statement.where(Employee.employment_status == status)
    if has_account is not None:
        linked = exists().where(
            UserAccount.employee_id == Employee.id,
            UserAccount.status != AccountStatus.DISABLED.value,
        )
        statement = statement.where(linked if has_account else ~linked)
    assignment_filters: list[ColumnElement[bool]] = []
    if unit_id is not None:
        unit = get_unit(db, unit_id)
        unit_ids = {unit.id}
        if include_descendants:
            unit_ids |= descendants(unit.id, parents_on(db, as_of))
        assignment_filters.append(EmployeeAssignment.org_unit_id.in_(unit_ids))
    if location_id is not None:
        assignment_filters.append(EmployeeAssignment.location_id == location_id)
    if designation_id is not None:
        assignment_filters.append(EmployeeAssignment.designation_id == designation_id)
    if assignment_filters:
        statement = statement.where(
            exists().where(
                EmployeeAssignment.employee_id == Employee.id,
                *covers_day(EmployeeAssignment, as_of),
                *assignment_filters,
            )
        )
    if after_code is not None:
        statement = statement.where(Employee.employee_code > after_code)
    return list(db.scalars(statement))


def employee_detail(db: Session, public_id: uuid.UUID) -> Employee:
    return get_employee(db, public_id)
