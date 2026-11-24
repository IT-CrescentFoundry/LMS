"""Who may see which employees' training and skill records.

Permissions decide the *kind* of access; the employee linked to the signed-in account
decides *whose* records a limited user sees. Being a line manager never grants a
permission on its own (ADR-023): a manager sees their team only if their access role
grants ``team.learning.view``.

* ``training.records.view`` / ``competency.view``  → every employee ("global").
* ``team.learning.view``  → the employees who report to the user's linked employee
  through open LINE_MANAGER relationships (direct and indirect), plus themself.
* ``learning.own.view``   → only the user's linked employee.

A user without a linked employee has no team and no own records.
"""

from dataclasses import dataclass
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.employees import LINE_MANAGER, ReportingRelationship, ReportingRelationshipType
from app.services.employees.common import covers_day
from app.services.identity.context import AuthContext
from app.services.identity.permissions import Permission

_MAX_DEPTH = 25  # guards against corrupt (cyclic) data; cycles are refused on write


@dataclass(frozen=True)
class RecordScope:
    """``employee_ids`` None = every employee; otherwise exactly these employees."""

    employee_ids: frozenset[int] | None
    kind: str  # "global" | "team" | "own" | "none"
    own_employee_id: int | None

    @property
    def is_global(self) -> bool:
        return self.employee_ids is None

    def allows(self, employee_id: int) -> bool:
        return self.employee_ids is None or employee_id in self.employee_ids


def team_of(db: Session, manager_id: int, day: date) -> set[int]:
    """Direct and indirect reports of ``manager_id`` on ``day`` (excluding the manager)."""
    found: set[int] = set()
    frontier = {manager_id}
    for _ in range(_MAX_DEPTH):
        if not frontier:
            break
        rows = db.scalars(
            select(ReportingRelationship.employee_id)
            .join(ReportingRelationshipType)
            .where(
                ReportingRelationshipType.code == LINE_MANAGER,
                ReportingRelationship.manager_employee_id.in_(frontier),
                *covers_day(ReportingRelationship, day),
            )
        ).all()
        frontier = {row for row in rows if row not in found and row != manager_id}
        found |= frontier
    return found


def record_scope(
    db: Session, auth: AuthContext, day: date, *, global_permission: str
) -> RecordScope:
    own = auth.user.employee_id
    if auth.has(global_permission):
        return RecordScope(None, "global", own)
    if auth.has(Permission.TEAM_LEARNING_VIEW) and own is not None:
        return RecordScope(frozenset(team_of(db, own, day) | {own}), "team", own)
    if auth.has(Permission.LEARNING_OWN_VIEW) and own is not None:
        return RecordScope(frozenset({own}), "own", own)
    if auth.has(Permission.TEAM_LEARNING_VIEW) or auth.has(Permission.LEARNING_OWN_VIEW):
        return RecordScope(frozenset(), "none", None)
    raise AppError(403, "forbidden", "You do not have permission to view training records.")
