"""Employee responsibilities (duties such as fire warden), optionally for a unit
and/or location context. A responsibility never grants LMS permissions or practical
authorisation; it is a record that later drives compliance and learning rules.
"""

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import RequestMeta
from app.core.errors import AppError
from app.db.types import utcnow
from app.models.employees import Employee, EmployeeResponsibility
from app.models.occupation import Responsibility
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
from app.services.organisation.support import audit, get_or_404
from app.services.organisation.units import lifetime


def list_responsibilities(
    db: Session, employee: Employee, *, include_ended: bool
) -> list[EmployeeResponsibility]:
    statement = select(EmployeeResponsibility).where(
        EmployeeResponsibility.employee_id == employee.id
    )
    if not include_ended:
        statement = statement.where(EmployeeResponsibility.effective_to.is_(None))
    return list(db.scalars(statement.order_by(EmployeeResponsibility.id)).unique())


def assign_responsibility(
    db: Session,
    employee_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    responsibility_id: uuid.UUID,
    context_unit_id: uuid.UUID | None,
    context_location_id: uuid.UUID | None,
    effective_from: date | None,
    effective_to: date | None,
    reason: str | None,
) -> EmployeeResponsibility:
    employee = lock_employee(db, employee_id)
    responsibility = get_or_404(
        db,
        Responsibility,
        responsibility_id,
        "responsibility_not_found",
        "Responsibility not found.",
    )
    if not responsibility.is_active:
        raise AppError(422, "responsibility_inactive", "This responsibility is inactive.")
    period = make_period(effective_from, effective_to)
    unit = None
    if context_unit_id is not None:
        unit = get_or_404(
            db,
            OrgUnit,
            context_unit_id,
            "org_unit_not_found",
            "Organisation unit not found.",
            for_update=True,
        )
        if not lifetime(unit).covers(period):
            raise AppError(
                422,
                "unit_not_active",
                "The organisation unit does not exist for the whole period.",
            )
    location = None
    if context_location_id is not None:
        location = get_or_404(
            db, Location, context_location_id, "location_not_found", "Location not found."
        )
        if not location.is_active:
            raise AppError(422, "location_inactive", "This location is inactive.")
    ensure_within_employment(employee, period)
    clash = db.scalar(
        locking(
            select(EmployeeResponsibility.id).where(
                EmployeeResponsibility.employee_id == employee.id,
                EmployeeResponsibility.responsibility_id == responsibility.id,
                EmployeeResponsibility.context_org_unit_id.is_(None)
                if unit is None
                else EmployeeResponsibility.context_org_unit_id == unit.id,
                EmployeeResponsibility.context_location_id.is_(None)
                if location is None
                else EmployeeResponsibility.context_location_id == location.id,
                *overlap_conditions(EmployeeResponsibility, period),
            )
        ).limit(1)
    )
    if clash is not None:
        raise AppError(
            409,
            "responsibility_overlap",
            "This responsibility is already held in this context for part of the period.",
        )
    record = EmployeeResponsibility(
        employee_id=employee.id,
        responsibility_id=responsibility.id,
        context_org_unit_id=unit.id if unit else None,
        context_location_id=location.id if location else None,
        effective_from=effective_from,
        effective_to=effective_to,
        reason=reason,
        created_by_user_id=actor.user_id,
    )
    db.add(record)
    db.flush()
    db.refresh(record)
    audit(
        db,
        actor,
        meta,
        AuditEventType.EMPLOYEE_RESPONSIBILITY_ASSIGNED,
        TargetType.EMPLOYEE,
        employee.public_id,
        {
            "employee_code": employee.employee_code,
            "record": str(record.public_id),
            "responsibility": responsibility.code,
            "context_unit": unit.code if unit else None,
            "context_location": location.code if location else None,
            "from": effective_from,
            "to": effective_to,
            "reason": reason,
        },
    )
    return record


def end_responsibility(
    db: Session,
    employee_id: uuid.UUID,
    record_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    effective_to: date,
    reason: str | None,
) -> EmployeeResponsibility:
    employee = lock_employee(db, employee_id)
    record = (
        db.scalars(
            locking(
                select(EmployeeResponsibility).where(
                    EmployeeResponsibility.public_id == record_id,
                    EmployeeResponsibility.employee_id == employee.id,
                )
            )
        )
        .unique()
        .one_or_none()
    )
    if record is None:
        raise AppError(404, "responsibility_record_not_found", "Responsibility record not found.")
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
        AuditEventType.EMPLOYEE_RESPONSIBILITY_ENDED,
        TargetType.EMPLOYEE,
        employee.public_id,
        {
            "employee_code": employee.employee_code,
            "record": str(record.public_id),
            "responsibility": record.responsibility.code,
            "to": effective_to,
            "reason": reason,
        },
    )
    return record
