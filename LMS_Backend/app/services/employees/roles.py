"""Employee functional roles: derived (computed on read) plus manual, minus exclusions.

Effective roles on date D = roles derived from EVERY assignment covering D (primary,
additional, acting, deputation) through the designation -> functional role mappings
covering D, plus manual assignments covering D, minus exclusions covering D.

A mapping applies to an assignment when the mapping has no scope, or the
assignment's unit is the scope unit, or (with ``include_descendants``) lies below it
in the hierarchy on D. Derived roles are never stored. Functional roles grant no
LMS permissions.
"""

import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import RequestMeta
from app.core.errors import AppError
from app.db.types import utcnow
from app.models.employees import (
    Employee,
    EmployeeAssignment,
    EmployeeFunctionalRole,
    FunctionalRoleKind,
)
from app.models.occupation import DesignationFunctionalRole, FunctionalRole
from app.services.audit_service import AuditEventType, TargetType
from app.services.employees.common import (
    covers_day,
    ensure_within_employment,
    lock_employee,
    locking,
    make_period,
    overlap_conditions,
)
from app.services.identity.context import Actor
from app.services.organisation.graph import ancestor_path
from app.services.organisation.support import audit, get_or_404
from app.services.organisation.units import parents_on

# ---------------------------------------------------------------- pure derivation


@dataclass(frozen=True)
class AssignmentFact:
    assignment_id: int
    org_unit_id: int
    designation_id: int | None


@dataclass(frozen=True)
class MappingFact:
    mapping_id: int
    designation_id: int
    functional_role_id: int
    scope_unit_id: int | None
    include_descendants: bool


@dataclass(frozen=True)
class Derivation:
    functional_role_id: int
    assignment_id: int
    mapping_id: int


def mapping_applies(mapping: MappingFact, unit_id: int, parent_of: Mapping[int, int]) -> bool:
    if mapping.scope_unit_id is None or mapping.scope_unit_id == unit_id:
        return True
    return mapping.include_descendants and mapping.scope_unit_id in ancestor_path(
        unit_id, parent_of
    )


def derive_roles(
    assignments: Iterable[AssignmentFact],
    mappings: Iterable[MappingFact],
    parent_of: Mapping[int, int],
) -> list[Derivation]:
    by_designation: dict[int, list[MappingFact]] = {}
    for mapping in mappings:
        by_designation.setdefault(mapping.designation_id, []).append(mapping)
    result = []
    for assignment in assignments:
        if assignment.designation_id is None:
            continue
        for mapping in by_designation.get(assignment.designation_id, []):
            if mapping_applies(mapping, assignment.org_unit_id, parent_of):
                result.append(
                    Derivation(
                        mapping.functional_role_id, assignment.assignment_id, mapping.mapping_id
                    )
                )
    return result


# ------------------------------------------------------------------ read model


@dataclass
class EffectiveRole:
    role: FunctionalRole
    derived_from: list[tuple[EmployeeAssignment, DesignationFunctionalRole]] = field(
        default_factory=list
    )
    manual: EmployeeFunctionalRole | None = None
    exclusion: EmployeeFunctionalRole | None = None

    @property
    def effective(self) -> bool:
        return (bool(self.derived_from) or self.manual is not None) and self.exclusion is None


def effective_roles(db: Session, employee: Employee, as_of: date) -> list[EffectiveRole]:
    assignments = list(
        db.scalars(
            select(EmployeeAssignment).where(
                EmployeeAssignment.employee_id == employee.id,
                *covers_day(EmployeeAssignment, as_of),
            )
        ).unique()
    )
    designation_ids = {a.designation_id for a in assignments if a.designation_id is not None}
    mappings = (
        list(
            db.scalars(
                select(DesignationFunctionalRole).where(
                    DesignationFunctionalRole.designation_id.in_(designation_ids),
                    *covers_day(DesignationFunctionalRole, as_of),
                )
            ).unique()
        )
        if designation_ids
        else []
    )
    derivations = derive_roles(
        [AssignmentFact(a.id, a.org_unit_id, a.designation_id) for a in assignments],
        [
            MappingFact(
                m.id,
                m.designation_id,
                m.functional_role_id,
                m.scope_org_unit_id,
                m.scope_include_descendants,
            )
            for m in mappings
        ],
        parents_on(db, as_of),
    )
    assignment_by_id = {a.id: a for a in assignments}
    mapping_by_id = {m.id: m for m in mappings}
    roles: dict[int, EffectiveRole] = {}
    for derivation in derivations:
        mapping = mapping_by_id[derivation.mapping_id]
        entry = roles.setdefault(mapping.functional_role_id, EffectiveRole(mapping.functional_role))
        entry.derived_from.append((assignment_by_id[derivation.assignment_id], mapping))
    for record in db.scalars(
        select(EmployeeFunctionalRole).where(
            EmployeeFunctionalRole.employee_id == employee.id,
            *covers_day(EmployeeFunctionalRole, as_of),
        )
    ).unique():
        entry = roles.setdefault(record.functional_role_id, EffectiveRole(record.functional_role))
        if record.kind == FunctionalRoleKind.EXCLUSION.value:
            entry.exclusion = record
        else:
            entry.manual = record
    return sorted(roles.values(), key=lambda item: item.role.code)


def list_role_records(
    db: Session, employee: Employee, *, include_ended: bool
) -> list[EmployeeFunctionalRole]:
    statement = select(EmployeeFunctionalRole).where(
        EmployeeFunctionalRole.employee_id == employee.id
    )
    if not include_ended:
        statement = statement.where(EmployeeFunctionalRole.effective_to.is_(None))
    return list(db.scalars(statement.order_by(EmployeeFunctionalRole.id)).unique())


# ------------------------------------------------------------------- writes


def assign_role(
    db: Session,
    employee_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    functional_role_id: uuid.UUID,
    kind: FunctionalRoleKind,
    effective_from: date | None,
    effective_to: date | None,
    reason: str | None,
) -> EmployeeFunctionalRole:
    """Manual assignment, or an exclusion that hides a derived role."""
    employee = lock_employee(db, employee_id)
    role = get_or_404(
        db,
        FunctionalRole,
        functional_role_id,
        "functional_role_not_found",
        "Functional role not found.",
    )
    if kind is FunctionalRoleKind.MANUAL and not role.is_active:
        raise AppError(422, "functional_role_inactive", "This functional role is inactive.")
    period = make_period(effective_from, effective_to)
    ensure_within_employment(employee, period)
    clash = db.scalar(
        locking(
            select(EmployeeFunctionalRole.id).where(
                EmployeeFunctionalRole.employee_id == employee.id,
                EmployeeFunctionalRole.functional_role_id == role.id,
                *overlap_conditions(EmployeeFunctionalRole, period),
            )
        ).limit(1)
    )
    if clash is not None:
        raise AppError(
            409,
            "role_assignment_overlap",
            "This role is already assigned or excluded for part of this period.",
        )
    record = EmployeeFunctionalRole(
        employee_id=employee.id,
        functional_role_id=role.id,
        kind=kind.value,
        effective_from=effective_from,
        effective_to=effective_to,
        reason=reason,
        created_by_user_id=actor.user_id,
    )
    db.add(record)
    db.flush()
    db.refresh(record)
    event = (
        AuditEventType.EMPLOYEE_ROLE_EXCLUDED
        if kind is FunctionalRoleKind.EXCLUSION
        else AuditEventType.EMPLOYEE_ROLE_ASSIGNED
    )
    audit(
        db,
        actor,
        meta,
        event,
        TargetType.EMPLOYEE,
        employee.public_id,
        {
            "employee_code": employee.employee_code,
            "record": str(record.public_id),
            "functional_role": role.code,
            "from": effective_from,
            "to": effective_to,
            "reason": reason,
        },
    )
    return record


def end_role(
    db: Session,
    employee_id: uuid.UUID,
    record_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    effective_to: date,
    reason: str | None,
) -> EmployeeFunctionalRole:
    employee = lock_employee(db, employee_id)
    record = (
        db.scalars(
            locking(
                select(EmployeeFunctionalRole).where(
                    EmployeeFunctionalRole.public_id == record_id,
                    EmployeeFunctionalRole.employee_id == employee.id,
                )
            )
        )
        .unique()
        .one_or_none()
    )
    if record is None:
        raise AppError(404, "role_assignment_not_found", "Functional role record not found.")
    _end(record, effective_to, actor)
    db.flush()
    audit(
        db,
        actor,
        meta,
        AuditEventType.EMPLOYEE_ROLE_ENDED,
        TargetType.EMPLOYEE,
        employee.public_id,
        {
            "employee_code": employee.employee_code,
            "record": str(record.public_id),
            "kind": record.kind,
            "functional_role": record.functional_role.code,
            "to": effective_to,
            "reason": reason,
        },
    )
    return record


def _end(record: EmployeeFunctionalRole, effective_to: date, actor: Actor) -> None:
    if record.effective_from is not None and effective_to <= record.effective_from:
        raise AppError(422, "invalid_period", "The end date must be after the start date.")
    if record.effective_to is not None and effective_to >= record.effective_to:
        raise AppError(409, "record_already_ended", "The record already ends by that date.")
    record.effective_to = effective_to
    record.ended_at = utcnow()
    record.ended_by_user_id = actor.user_id
