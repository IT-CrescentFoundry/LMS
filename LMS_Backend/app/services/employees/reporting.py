"""Reporting relationships (C3 seeds only LINE_MANAGER).

Every write takes the ``graph_lock`` row ``reporting`` first, so hierarchical edge
writes are serialised (separation takes it too, because it can end reporting lines);
then the employee rows in ascending internal id order; the rows checked afterwards
are read with locking reads (see ``common`` for the lock order). Edges are
``(employee, manager)`` pairs; a new edge is refused when it would close a cycle with
any edge of the same type that overlaps its period.

Being a manager grants nothing: no access role and no data access (scoped access is
C4).
"""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import RequestMeta
from app.core.errors import AppError
from app.db.types import utcnow
from app.models.employees import (
    LINE_MANAGER,
    Employee,
    ReportingRelationship,
    ReportingRelationshipType,
)
from app.services.audit_service import AuditEventType, TargetType
from app.services.employees.common import (
    covers_day,
    ensure_within_employment,
    is_separated,
    lock_employee,
    lock_employees,
    lock_reporting,
    locking,
    make_period,
    overlap_conditions,
)
from app.services.identity.context import Actor
from app.services.organisation.graph import creates_cycle
from app.services.organisation.support import audit, flush_unique

# ------------------------------------------------------------------- reads


def list_types(db: Session, *, include_inactive: bool = False) -> list[ReportingRelationshipType]:
    statement = select(ReportingRelationshipType).order_by(ReportingRelationshipType.code)
    if not include_inactive:
        statement = statement.where(ReportingRelationshipType.is_active.is_(True))
    return list(db.scalars(statement).unique())


def _type(db: Session, public_id: uuid.UUID | None) -> ReportingRelationshipType:
    statement = select(ReportingRelationshipType)
    statement = (
        statement.where(ReportingRelationshipType.code == LINE_MANAGER)
        if public_id is None
        else statement.where(ReportingRelationshipType.public_id == public_id)
    )
    relationship_type = db.scalars(statement).unique().one_or_none()
    if relationship_type is None:
        raise AppError(404, "reporting_type_not_found", "Reporting relationship type not found.")
    return relationship_type


def current_managers(db: Session, employee: Employee, as_of: date) -> list[ReportingRelationship]:
    return list(
        db.scalars(
            select(ReportingRelationship)
            .where(
                ReportingRelationship.employee_id == employee.id,
                *covers_day(ReportingRelationship, as_of),
            )
            .order_by(ReportingRelationship.id)
        ).unique()
    )


def reporting_history(db: Session, employee: Employee) -> list[ReportingRelationship]:
    return list(
        db.scalars(
            select(ReportingRelationship)
            .where(ReportingRelationship.employee_id == employee.id)
            .order_by(
                ReportingRelationship.effective_from.is_(None).desc(),
                ReportingRelationship.effective_from,
                ReportingRelationship.id,
            )
        ).unique()
    )


def direct_reports(db: Session, employee: Employee, as_of: date) -> list[ReportingRelationship]:
    return list(
        db.scalars(
            select(ReportingRelationship)
            .join(Employee, Employee.id == ReportingRelationship.employee_id)
            .where(
                ReportingRelationship.manager_employee_id == employee.id,
                *covers_day(ReportingRelationship, as_of),
            )
            .order_by(Employee.employee_code)
        ).unique()
    )


# ------------------------------------------------------------------- writes


def set_manager(
    db: Session,
    employee_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    manager_id: uuid.UUID,
    relationship_type_id: uuid.UUID | None,
    effective_from: date | None,
    reason: str | None,
) -> ReportingRelationship:
    """Open a relationship from ``effective_from``.

    For a single-valued type the current relationship (if any) is closed on that
    date, keeping history; a relationship starting on or after it must be ended or
    corrected first (``later_change_exists``).
    """
    # Lock order (see ``common``): reporting graph lock, then both employee rows in
    # ascending internal id order - never "employee first, then manager".
    lock_reporting(db)
    locked = lock_employees(db, [employee_id, manager_id])
    employee = locked.get(employee_id)
    if employee is None:
        raise AppError(404, "employee_not_found", "Employee not found.")
    if manager_id == employee_id:
        raise AppError(422, "self_reporting", "An employee cannot report to themselves.")
    manager = locked.get(manager_id)
    if manager is None:
        raise AppError(404, "manager_not_found", "Manager not found.")
    relationship_type = _type(db, relationship_type_id)
    if not relationship_type.is_active:
        raise AppError(
            422, "reporting_type_inactive", "This reporting relationship type is inactive."
        )
    if is_separated(manager):
        raise AppError(422, "manager_separated", "The selected manager has separated.")
    period = make_period(effective_from, None)
    ensure_within_employment(employee, period)

    existing = list(
        db.scalars(
            locking(
                select(ReportingRelationship).where(
                    ReportingRelationship.employee_id == employee.id,
                    ReportingRelationship.relationship_type_id == relationship_type.id,
                    *overlap_conditions(ReportingRelationship, period),
                )
            )
        ).unique()
    )
    # A relationship starting on or after the new start must be ended or corrected first.
    if any(
        effective_from is None
        or (record.effective_from is not None and record.effective_from >= effective_from)
        for record in existing
    ):
        raise AppError(
            409,
            "later_change_exists",
            "A reporting relationship already starts on or after this date.",
        )
    replaced: ReportingRelationship | None = None
    for record in existing:
        if record.manager_employee_id == manager.id:
            if record.effective_to is None:
                raise AppError(422, "no_change", "The employee already reports to this manager.")
            raise AppError(
                409,
                "manager_overlap",
                "The employee already reports to this manager for part of this period.",
            )
        if relationship_type.allows_multiple:
            continue
        if record.effective_to is not None or replaced is not None:
            raise AppError(
                409,
                "manager_overlap",
                "Another manager relationship covers part of this period. End or correct it first.",
            )
        replaced = record

    if relationship_type.is_hierarchical:
        edges = [
            (child, parent)
            for record_id, child, parent in db.execute(
                locking(
                    select(
                        ReportingRelationship.id,
                        ReportingRelationship.employee_id,
                        ReportingRelationship.manager_employee_id,
                    ).where(
                        ReportingRelationship.relationship_type_id == relationship_type.id,
                        *overlap_conditions(ReportingRelationship, period),
                    )
                )
            )
            if replaced is None or record_id != replaced.id
        ]
        if creates_cycle(edges, employee.id, manager.id):
            raise AppError(
                409,
                "reporting_cycle",
                "This manager reports, directly or indirectly, to the employee.",
            )

    # ``replaced`` is only set when a start date was given (a NULL start raised above).
    if replaced is not None and effective_from is not None:
        replaced.effective_to = effective_from
        replaced.ended_at = utcnow()
        replaced.ended_by_user_id = actor.user_id
        db.flush()
    record = ReportingRelationship(
        employee_id=employee.id,
        manager_employee_id=manager.id,
        relationship_type_id=relationship_type.id,
        effective_from=effective_from,
        reason=reason,
        created_by_user_id=actor.user_id,
    )
    db.add(record)
    flush_unique(db, "manager_overlap", "The employee already reports to this manager.")
    db.refresh(record)
    audit(
        db,
        actor,
        meta,
        AuditEventType.REPORTING_CREATED,
        TargetType.EMPLOYEE,
        employee.public_id,
        {
            "employee_code": employee.employee_code,
            "record": str(record.public_id),
            "relationship_type": relationship_type.code,
            "manager": str(manager.public_id),
            "manager_code": manager.employee_code,
            "from": effective_from,
            "replaced_record": str(replaced.public_id) if replaced else None,
            "previous_manager_code": replaced.manager.employee_code if replaced else None,
            "reason": reason,
        },
    )
    return record


def end_relationship(
    db: Session,
    employee_id: uuid.UUID,
    record_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    effective_to: date,
    reason: str | None,
) -> ReportingRelationship:
    lock_reporting(db)
    employee = lock_employee(db, employee_id)
    record = (
        db.scalars(
            locking(
                select(ReportingRelationship).where(
                    ReportingRelationship.public_id == record_id,
                    ReportingRelationship.employee_id == employee.id,
                )
            )
        )
        .unique()
        .one_or_none()
    )
    if record is None:
        raise AppError(404, "reporting_relationship_not_found", "Reporting relationship not found.")
    if record.effective_from is not None and effective_to <= record.effective_from:
        raise AppError(422, "invalid_period", "The end date must be after the start date.")
    if record.effective_to is not None and effective_to >= record.effective_to:
        raise AppError(409, "record_already_ended", "The record already ends by that date.")
    record.effective_to = effective_to
    record.ended_at = utcnow()
    record.ended_by_user_id = actor.user_id
    db.flush()
    audit(
        db,
        actor,
        meta,
        AuditEventType.REPORTING_ENDED,
        TargetType.EMPLOYEE,
        employee.public_id,
        {
            "employee_code": employee.employee_code,
            "record": str(record.public_id),
            "relationship_type": record.relationship_type.code,
            "manager_code": record.manager.employee_code,
            "to": effective_to,
            "reason": reason,
        },
    )
    return record
