"""Employee history: the audit events that target the employee (newest first)."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.employees import Employee
from app.services.audit_service import TargetType


def employee_history(
    db: Session, employee: Employee, *, before_id: int | None, limit: int
) -> list[AuditEvent]:
    statement = (
        select(AuditEvent)
        .where(
            AuditEvent.target_type == TargetType.EMPLOYEE.value,
            AuditEvent.target_id == str(employee.public_id),
        )
        .order_by(AuditEvent.id.desc())
        .limit(limit)
    )
    if before_id is not None:
        statement = statement.where(AuditEvent.id < before_id)
    return list(db.scalars(statement))
