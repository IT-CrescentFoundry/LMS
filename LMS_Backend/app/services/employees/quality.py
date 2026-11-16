"""Employee data-quality checks (report only; nothing is ever corrected here).

Each check is an SQL condition on ``employee`` evaluated as of a business date, so
the view returns exact counts and code-ordered pages. Employees whose status is not
recorded are included wherever "current" employees are considered, because an
unknown status must never be silently treated as either active or separated.
"""

from collections.abc import Callable
from datetime import date

from sqlalchemy import ColumnElement, and_, exists, func, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.errors import AppError
from app.models.employees import (
    LINE_MANAGER,
    AssignmentType,
    Employee,
    EmployeeAssignment,
    EmploymentStatus,
    ReportingRelationship,
    ReportingRelationshipType,
)
from app.models.identity import AccountStatus, UserAccount
from app.models.organisation import OrgUnit
from app.services.employees.common import covers_day


def _current() -> ColumnElement[bool]:
    """Active, on leave, or status not recorded."""
    return or_(
        Employee.employment_status.is_(None),
        Employee.employment_status.in_(
            [EmploymentStatus.ACTIVE.value, EmploymentStatus.ON_LEAVE.value]
        ),
    )


def _primary_on(day: date, *extra: ColumnElement[bool]) -> ColumnElement[bool]:
    return exists().where(
        EmployeeAssignment.employee_id == Employee.id,
        EmployeeAssignment.assignment_type == AssignmentType.PRIMARY.value,
        *covers_day(EmployeeAssignment, day),
        *extra,
    )


def _line_manager_on(day: date, *extra: ColumnElement[bool]) -> ColumnElement[bool]:
    return exists().where(
        ReportingRelationship.employee_id == Employee.id,
        ReportingRelationship.relationship_type_id == ReportingRelationshipType.id,
        ReportingRelationshipType.code == LINE_MANAGER,
        *covers_day(ReportingRelationship, day),
        *extra,
    )


def _unknown_status(day: date) -> ColumnElement[bool]:
    return Employee.employment_status.is_(None)


def _no_primary_assignment(day: date) -> ColumnElement[bool]:
    return and_(_current(), ~_primary_on(day))


def _missing_location(day: date) -> ColumnElement[bool]:
    return _primary_on(
        day,
        EmployeeAssignment.location_id.is_(None),
        ~exists().where(
            OrgUnit.id == EmployeeAssignment.org_unit_id, OrgUnit.location_id.is_not(None)
        ),
    )


def _missing_designation(day: date) -> ColumnElement[bool]:
    return _primary_on(day, EmployeeAssignment.designation_id.is_(None))


def _separated_with_active_account(day: date) -> ColumnElement[bool]:
    return and_(
        Employee.employment_status == EmploymentStatus.SEPARATED.value,
        exists().where(
            UserAccount.employee_id == Employee.id,
            UserAccount.status != AccountStatus.DISABLED.value,
        ),
    )


def _manager_inactive(day: date) -> ColumnElement[bool]:
    manager = aliased(Employee)
    return and_(
        _current(),
        _line_manager_on(
            day,
            manager.id == ReportingRelationship.manager_employee_id,
            manager.employment_status.in_(
                [EmploymentStatus.SEPARATED.value, EmploymentStatus.ON_LEAVE.value]
            ),
        ),
    )


def _no_line_manager(day: date) -> ColumnElement[bool]:
    return and_(_current(), ~_line_manager_on(day))


def _incomplete_record(day: date) -> ColumnElement[bool]:
    return Employee.date_of_joining.is_(None)


CHECKS: dict[str, Callable[[date], ColumnElement[bool]]] = {
    "unknown_status": _unknown_status,
    "no_primary_assignment": _no_primary_assignment,
    "missing_location": _missing_location,
    "missing_designation": _missing_designation,
    "separated_with_active_account": _separated_with_active_account,
    "manager_inactive": _manager_inactive,
    "no_line_manager": _no_line_manager,
    "incomplete_record": _incomplete_record,
}


def _condition(check: str, as_of: date) -> ColumnElement[bool]:
    factory = CHECKS.get(check)
    if factory is None:
        raise AppError(422, "invalid_check", "Unknown data-quality check.")
    return factory(as_of)


def quality_counts(db: Session, as_of: date) -> dict[str, int]:
    return {
        check: db.scalar(select(func.count()).select_from(Employee).where(factory(as_of))) or 0
        for check, factory in CHECKS.items()
    }


def quality_list(
    db: Session, *, check: str, as_of: date, after_code: str | None, limit: int
) -> list[Employee]:
    statement = (
        select(Employee)
        .where(_condition(check, as_of))
        .order_by(Employee.employee_code)
        .limit(limit)
    )
    if after_code is not None:
        statement = statement.where(Employee.employee_code > after_code)
    return list(db.scalars(statement))
