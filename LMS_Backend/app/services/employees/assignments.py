"""Effective-dated employee assignments.

* New: a primary, additional, acting or deputation assignment from a date.
* Change from date D (transfer, designation, grade, level or location change):
  the current row is closed at D and a copy with the changes opens at D - history
  is never overwritten.
* End: the row stops at a date.
* Correction: wrongly recorded data is fixed in place with ``version`` and a reason
  (the explicit mechanism for back-dated fixes); before/after is audited.

Validation (all under the employee-row lock, with locking reads):
* half-open periods; at most one primary covering any date; no overlapping
  assignments to the same unit; other types may overlap the primary;
* the unit must exist for the whole period (closed / not-yet-started units are
  refused for new periods); referenced designation, grade, level and location must
  be active for new values;
* dates within the employee's known employment period.
"""

import uuid
from collections.abc import Mapping
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import RequestMeta
from app.core.errors import AppError
from app.db.types import utcnow
from app.models.employees import AssignmentType, Employee, EmployeeAssignment
from app.models.occupation import Designation, Grade, JobLevel
from app.models.organisation import Location, OrgUnit
from app.services.audit_service import AuditEventType, TargetType
from app.services.employees.common import (
    ensure_within_employment,
    lock_employee,
    locking,
    make_period,
    overlap_conditions,
)
from app.services.identity.context import Actor
from app.services.organisation.periods import Period
from app.services.organisation.support import audit, ensure_version, get_or_404, jsonable, touch
from app.services.organisation.unit_types import OrgWarning
from app.services.organisation.units import lifetime

REFERENCE_FIELDS = ("designation_id", "grade_id", "job_level_id", "location_id")
_REFERENCE_MODELS: dict[str, Any] = {
    "designation_id": Designation,
    "grade_id": Grade,
    "job_level_id": JobLevel,
    "location_id": Location,
}
_REFERENCE_LABELS = {
    "designation_id": "designation",
    "grade_id": "grade",
    "job_level_id": "level",
    "location_id": "location",
}


def _unit(db: Session, public_id: uuid.UUID) -> OrgUnit:
    # FOR UPDATE: serialises with a concurrent closure of the unit (C1 close_unit).
    return get_or_404(
        db,
        OrgUnit,
        public_id,
        "org_unit_not_found",
        "Organisation unit not found.",
        for_update=True,
    )


def _reference(db: Session, field: str, public_id: uuid.UUID) -> Any:
    model = _REFERENCE_MODELS[field]
    label = _REFERENCE_LABELS[field]
    return get_or_404(db, model, public_id, f"{label}_not_found", f"The {label} was not found.")


def resolve_values(db: Session, raw: Mapping[str, Any]) -> dict[str, Any]:
    """Public ids in a request -> loaded entities (``None`` clears an optional field)."""
    values: dict[str, Any] = {}
    if raw.get("org_unit_id") is not None:
        values["org_unit"] = _unit(db, raw["org_unit_id"])
    for field in REFERENCE_FIELDS:
        if field in raw:
            values[field] = _reference(db, field, raw[field]) if raw[field] is not None else None
    return values


def _new_references(
    values: Mapping[str, Any], current: EmployeeAssignment | None
) -> dict[str, int | None]:
    """Reference ids after the change. Only NEWLY chosen references must be active
    (an unchanged reference that has since been deactivated stays valid history)."""
    result: dict[str, int | None] = {}
    for field in REFERENCE_FIELDS:
        previous = getattr(current, field) if current is not None else None
        if field not in values:
            result[field] = previous
            continue
        entity = values[field]
        new_id = entity.id if entity is not None else None
        if entity is not None and new_id != previous and not entity.is_active:
            raise AppError(
                422,
                "reference_inactive",
                f"The chosen {_REFERENCE_LABELS[field]} is inactive.",
            )
        result[field] = new_id
    return result


def _validate(
    db: Session,
    employee: Employee,
    *,
    assignment_type: str,
    unit: OrgUnit,
    period: Period,
    exclude_id: int | None,
) -> list[OrgWarning]:
    if not lifetime(unit).covers(period):
        raise AppError(
            422,
            "unit_not_active",
            "The organisation unit does not exist for the whole period "
            "(closed or not yet started).",
        )
    ensure_within_employment(employee, period)
    rows = db.scalars(
        locking(
            select(EmployeeAssignment).where(
                EmployeeAssignment.employee_id == employee.id,
                *overlap_conditions(EmployeeAssignment, period),
            )
        )
    ).unique()
    for row in rows:
        if row.id == exclude_id:
            continue
        if (
            assignment_type == AssignmentType.PRIMARY.value
            and row.assignment_type == AssignmentType.PRIMARY.value
        ):
            raise AppError(
                409,
                "primary_overlap",
                "Another primary assignment covers part of this period. Change or end it first.",
            )
        if row.org_unit_id == unit.id:
            raise AppError(
                409,
                "assignment_overlap",
                "The employee is already assigned to this unit for part of this period.",
            )
    warnings = []
    if not unit.unit_type.allows_employee_assignment:
        warnings.append(
            OrgWarning(
                "unit_type_not_assignable",
                "Units of this type do not normally hold employee assignments.",
            )
        )
    return warnings


def _summary(row: EmployeeAssignment) -> dict[str, Any]:
    return {
        "assignment": str(row.public_id),
        "type": row.assignment_type,
        "unit": row.org_unit.code,
        "designation": row.designation.code if row.designation else None,
        "grade": row.grade.code if row.grade else None,
        "level": row.job_level.code if row.job_level else None,
        "location": row.location.code if row.location else None,
        "from": jsonable(row.effective_from),
        "to": jsonable(row.effective_to),
    }


def get_assignment(db: Session, employee: Employee, assignment_id: uuid.UUID) -> EmployeeAssignment:
    row = (
        db.scalars(
            select(EmployeeAssignment)
            .where(
                EmployeeAssignment.public_id == assignment_id,
                EmployeeAssignment.employee_id == employee.id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        .unique()
        .one_or_none()
    )
    if row is None:
        raise AppError(404, "assignment_not_found", "Assignment not found.")
    return row


def list_assignments(
    db: Session, employee: Employee, *, include_ended: bool
) -> list[EmployeeAssignment]:
    statement = select(EmployeeAssignment).where(EmployeeAssignment.employee_id == employee.id)
    if not include_ended:
        statement = statement.where(EmployeeAssignment.effective_to.is_(None))
    statement = statement.order_by(
        EmployeeAssignment.effective_from.is_(None).desc(),
        EmployeeAssignment.effective_from,
        EmployeeAssignment.id,
    )
    return list(db.scalars(statement).unique())


def create_assignment(
    db: Session,
    employee_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    assignment_type: AssignmentType,
    raw: Mapping[str, Any],
    effective_from: date | None,
    effective_to: date | None,
    reason: str | None,
) -> tuple[EmployeeAssignment, list[OrgWarning]]:
    employee = lock_employee(db, employee_id)
    values = resolve_values(db, raw)
    if "org_unit" not in values:
        raise AppError(422, "unit_required", "An organisation unit is required.")
    references = _new_references(values, None)
    period = make_period(effective_from, effective_to)
    warnings = _validate(
        db,
        employee,
        assignment_type=assignment_type.value,
        unit=values["org_unit"],
        period=period,
        exclude_id=None,
    )
    row = EmployeeAssignment(
        employee_id=employee.id,
        org_unit_id=values["org_unit"].id,
        assignment_type=assignment_type.value,
        effective_from=effective_from,
        effective_to=effective_to,
        reason=reason,
        created_by_user_id=actor.user_id,
        updated_by_user_id=actor.user_id,
        **references,
    )
    db.add(row)
    db.flush()
    db.refresh(row)
    audit(
        db,
        actor,
        meta,
        AuditEventType.ASSIGNMENT_CREATED,
        TargetType.EMPLOYEE,
        employee.public_id,
        {
            "employee_code": employee.employee_code,
            **_summary(row),
            "reason": reason,
            "warnings": [w.code for w in warnings],
        },
    )
    return row, warnings


def change_assignment(
    db: Session,
    employee_id: uuid.UUID,
    assignment_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    effective_date: date,
    raw: Mapping[str, Any],
    reason: str | None,
) -> tuple[EmployeeAssignment, list[OrgWarning]]:
    """Business change from ``effective_date``: close the row, open an updated copy."""
    employee = lock_employee(db, employee_id)
    current = get_assignment(db, employee, assignment_id)
    ensure_version(current, version)
    period = Period(current.effective_from, current.effective_to)
    if not period.contains(effective_date) or current.effective_from == effective_date:
        raise AppError(
            422,
            "change_date_invalid",
            "The change date must fall after the assignment's start and before its end.",
        )
    values = resolve_values(db, raw)
    unit = values.get("org_unit", current.org_unit)
    new_refs = _new_references(values, current)
    if unit.id == current.org_unit_id and all(
        new_refs[field] == getattr(current, field) for field in REFERENCE_FIELDS
    ):
        raise AppError(422, "no_change", "Nothing would change on that date.")

    new_period = Period(effective_date, current.effective_to)
    warnings = _validate(
        db,
        employee,
        assignment_type=current.assignment_type,
        unit=unit,
        period=new_period,
        exclude_id=current.id,
    )
    before = _summary(current)
    original_end = current.effective_to
    current.effective_to = effective_date
    current.ended_at = utcnow()
    current.ended_by_user_id = actor.user_id
    touch(current, actor)
    db.flush()  # frees the "one open primary / one open per unit" slots first
    row = EmployeeAssignment(
        employee_id=employee.id,
        org_unit_id=unit.id,
        assignment_type=current.assignment_type,
        effective_from=effective_date,
        effective_to=original_end,
        reason=reason,
        created_by_user_id=actor.user_id,
        updated_by_user_id=actor.user_id,
        **new_refs,
    )
    db.add(row)
    db.flush()
    db.refresh(row)
    audit(
        db,
        actor,
        meta,
        AuditEventType.ASSIGNMENT_CHANGED,
        TargetType.EMPLOYEE,
        employee.public_id,
        {
            "employee_code": employee.employee_code,
            "effective_date": effective_date,
            "from": before,
            "to": _summary(row),
            "reason": reason,
            "warnings": [w.code for w in warnings],
        },
    )
    return row, warnings


def end_assignment(
    db: Session,
    employee_id: uuid.UUID,
    assignment_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    effective_to: date,
    reason: str | None,
) -> EmployeeAssignment:
    employee = lock_employee(db, employee_id)
    row = get_assignment(db, employee, assignment_id)
    ensure_version(row, version)
    if row.effective_from is not None and effective_to <= row.effective_from:
        raise AppError(422, "invalid_period", "The end date must be after the start date.")
    if row.effective_to is not None and effective_to >= row.effective_to:
        raise AppError(409, "assignment_already_ended", "The assignment already ends by that date.")
    row.effective_to = effective_to
    row.ended_at = utcnow()
    row.ended_by_user_id = actor.user_id
    touch(row, actor)
    db.flush()
    audit(
        db,
        actor,
        meta,
        AuditEventType.ASSIGNMENT_ENDED,
        TargetType.EMPLOYEE,
        employee.public_id,
        {"employee_code": employee.employee_code, **_summary(row), "reason": reason},
    )
    return row


def correct_assignment(
    db: Session,
    employee_id: uuid.UUID,
    assignment_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    reason: str | None,
    changes: Mapping[str, Any],
) -> tuple[EmployeeAssignment, list[OrgWarning]]:
    """Fix wrongly recorded data in place (type, unit, references, dates)."""
    employee = lock_employee(db, employee_id)
    row = get_assignment(db, employee, assignment_id)
    ensure_version(row, version)
    values = resolve_values(db, changes)
    new_refs = _new_references(values, row)
    assignment_type = changes.get("assignment_type", row.assignment_type)
    if isinstance(assignment_type, AssignmentType):
        assignment_type = assignment_type.value
    start = changes.get("effective_from", row.effective_from)
    end = changes.get("effective_to", row.effective_to)
    unit = values.get("org_unit", row.org_unit)
    unchanged = (
        assignment_type == row.assignment_type
        and unit.id == row.org_unit_id
        and all(new_refs[field] == getattr(row, field) for field in REFERENCE_FIELDS)
        and (start, end) == (row.effective_from, row.effective_to)
    )
    if unchanged:
        raise AppError(422, "no_change", "Nothing has changed.")
    period = make_period(start, end)
    warnings = _validate(
        db, employee, assignment_type=assignment_type, unit=unit, period=period, exclude_id=row.id
    )
    before = _summary(row)
    row.assignment_type = assignment_type
    row.org_unit_id = unit.id
    for field, value in new_refs.items():
        setattr(row, field, value)
    row.effective_from = start
    row.effective_to = end
    touch(row, actor)
    db.flush()
    db.refresh(row)
    after = _summary(row)
    audit(
        db,
        actor,
        meta,
        AuditEventType.ASSIGNMENT_CORRECTED,
        TargetType.EMPLOYEE,
        employee.public_id,
        {
            "employee_code": employee.employee_code,
            "reason": reason,
            "from": before,
            "to": after,
            "warnings": [w.code for w in warnings],
        },
    )
    return row, warnings
