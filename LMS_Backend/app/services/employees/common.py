"""Shared helpers for the employee services.

Concurrency (same lesson as C1): a request reads its session before the service
runs, so under InnoDB REPEATABLE READ a plain read may use an older snapshot. Every
write therefore locks the employee row first and then reads the rows it checks with
*locking* reads (FOR SHARE / FOR UPDATE), which always see the latest committed data.

Lock acquisition order (deadlock prevention), used by every employee write:

1. the ``graph_lock`` row ``reporting`` - taken by every write to
   ``reporting_relationship`` (set or end a manager) and by separation, which may end
   reporting lines of the employee and of their direct reports;
2. employee rows, FOR UPDATE, in ascending internal id order (``lock_employees``);
3. the dependent rows, with locking reads.

A transaction never waits for an earlier step while holding a later one, so two
operations involving the same employees cannot deadlock. Writes that touch one
employee only (assignments, roles, responsibilities, account links) skip step 1.
"""

import base64
import binascii
import re
import uuid
from collections.abc import Sequence
from datetime import date, timedelta
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.employees import REPORTING_LOCK, Employee, EmploymentStatus
from app.models.organisation import GraphLock
from app.services.organisation.periods import InvalidPeriodError, Period
from app.services.organisation.support import get_or_404

_EMPLOYEE_CODE = re.compile(r"^[A-Z0-9][A-Z0-9/._-]{0,29}$")


def normalise_employee_code(raw: str) -> str:
    """Trimmed, upper-cased; letters, digits, '/', '.', '_' and '-' (max 30).

    Leading zeros are kept: codes are text, never numbers.
    """
    code = raw.strip().upper()
    if not _EMPLOYEE_CODE.fullmatch(code):
        raise AppError(
            422,
            "invalid_employee_code",
            "Employee codes may contain letters, digits, '/', '.', '_' and '-' (max 30).",
        )
    return code


def get_employee(db: Session, public_id: uuid.UUID, *, for_update: bool = False) -> Employee:
    return get_or_404(
        db, Employee, public_id, "employee_not_found", "Employee not found.", for_update=for_update
    )


def lock_employee(db: Session, public_id: uuid.UUID) -> Employee:
    """Row lock that serialises every change to one employee's records."""
    return get_employee(db, public_id, for_update=True)


def lock_reporting(db: Session) -> None:
    """Step 1 of the lock order: serialises every reporting-relationship write."""
    db.execute(
        select(GraphLock.name).where(GraphLock.name == REPORTING_LOCK).with_for_update()
    ).one()


def lock_employees(db: Session, public_ids: Sequence[uuid.UUID]) -> dict[uuid.UUID, Employee]:
    """Step 2 of the lock order: lock several employees in ascending internal id order.

    Internal ids never change, so resolving them with a plain read first is safe.
    Unknown public ids are simply absent from the result.
    """
    rows = db.execute(
        select(Employee.id, Employee.public_id).where(Employee.public_id.in_(set(public_ids)))
    )
    ids: dict[int, uuid.UUID] = {internal_id: public_id for internal_id, public_id in rows}
    locked: dict[uuid.UUID, Employee] = {}
    for internal_id in sorted(ids):
        employee = db.scalars(
            select(Employee)
            .where(Employee.id == internal_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        ).one()
        locked[ids[internal_id]] = employee
    return locked


def locking[*Ts](statement: Select[*Ts]) -> Select[*Ts]:
    """A FOR SHARE read that ignores stale identity-map state."""
    return statement.with_for_update(read=True).execution_options(populate_existing=True)


def make_period(start: date | None, end: date | None) -> Period:
    try:
        return Period(start, end)
    except InvalidPeriodError:
        raise AppError(
            422, "invalid_period", "The end date must be after the start date."
        ) from None


def employment_end(employee: Employee) -> date | None:
    """Exclusive end of employment: the day after the separation date (last working day)."""
    if employee.date_of_separation is None:
        return None
    return employee.date_of_separation + timedelta(days=1)


def ensure_within_employment(employee: Employee, period: Period) -> None:
    """Records must fall within known employment dates."""
    if employee.date_of_joining is not None:
        if period.start is None:
            raise AppError(
                422,
                "assignment_start_required",
                "A start date is required because the employee's joining date is recorded.",
            )
        if period.start < employee.date_of_joining:
            raise AppError(
                422,
                "outside_employment_period",
                "The dates fall outside the employee's employment period.",
            )
    end = employment_end(employee)
    if end is not None and (period.end is None or period.end > end):
        raise AppError(
            422,
            "outside_employment_period",
            "The dates fall outside the employee's employment period.",
        )


def is_separated(employee: Employee) -> bool:
    return employee.employment_status == EmploymentStatus.SEPARATED.value


def overlap_conditions(model: Any, period: Period) -> list[Any]:
    """SQL conditions selecting rows of ``model`` whose period overlaps ``period``."""
    conditions = []
    if period.end is not None:
        conditions.append((model.effective_from.is_(None)) | (model.effective_from < period.end))
    if period.start is not None:
        conditions.append((model.effective_to.is_(None)) | (model.effective_to > period.start))
    return conditions


def covers_day(model: Any, day: date) -> list[Any]:
    return [
        (model.effective_from.is_(None)) | (model.effective_from <= day),
        (model.effective_to.is_(None)) | (model.effective_to > day),
    ]


def encode_text_cursor(value: str) -> str:
    return base64.urlsafe_b64encode(value.encode()).decode().rstrip("=")


def decode_employee_cursor(cursor: str | None) -> str | None:
    if not cursor:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value = base64.b64decode(padded, altchars=b"-_", validate=True).decode()
    except (binascii.Error, UnicodeDecodeError, ValueError):
        value = ""
    if not _EMPLOYEE_CODE.fullmatch(value):
        raise AppError(422, "invalid_cursor", "The pagination cursor is invalid.")
    return value
