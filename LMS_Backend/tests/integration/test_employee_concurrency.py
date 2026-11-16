"""Concurrency: employee and reporting writes see committed data.

Lock order under test (``app.services.employees.common``): the ``reporting`` graph
lock, then employee rows in ascending internal id order, then dependent rows.

Each race test starts two transactions. The second takes its REPEATABLE READ snapshot
before the first change exists, then makes a change that is valid on its own but
conflicts with the first one. The services lock first (the ``reporting`` graph lock
or the employee row) and then use locking reads, so the second change must wait,
see the committed first change, and be refused.

These tests COMMIT (on crescent_lms_test only, as lms_test@127.0.0.1); the schema
is rebuilt afterwards so later tests start from the clean seeded state. All data is
synthetic.
"""

import threading
import time
import uuid
from collections.abc import Callable, Iterator
from datetime import date
from typing import Any

import pytest
from sqlalchemy import Engine, event, func, select
from sqlalchemy.orm import Session

from app.core.context import RequestMeta
from app.core.errors import AppError
from app.models.employees import (
    AssignmentType,
    Employee,
    EmployeeAssignment,
    EmploymentStatus,
    ReportingRelationship,
)
from app.models.organisation import OrgUnit
from app.services.employees import assignments, employees, reporting
from app.services.identity.context import Actor
from tests.integration.helpers import make_user
from tests.support.database import assert_connected_to
from tests.support.schema_reset import rebuild_test_schema

pytestmark = pytest.mark.db

META = RequestMeta(request_id="employee-concurrency")
START = date(2026, 1, 1)


@pytest.fixture
def committing_engine(test_engine: Engine, test_database_name: str) -> Iterator[Engine]:
    try:
        yield test_engine
    finally:
        rebuild_test_schema(test_engine, test_database_name)


def _session(engine: Engine, name: str) -> Session:
    session = Session(bind=engine, autoflush=False, expire_on_commit=False)
    assert_connected_to(session.connection(), name)
    return session


def _setup(engine: Engine, name: str, codes: tuple[str, ...]) -> tuple[Actor, list[uuid.UUID]]:
    with _session(engine, name) as setup:
        admin = make_user(setup, "race.employee.admin", roles=("hr_admin",))
        actor = Actor(user_id=admin.id, permissions=frozenset())
        ids = []
        for code in codes:
            employee = employees.create_employee(
                setup,
                actor=actor,
                meta=META,
                values={
                    "employee_code": code,
                    "full_name": f"Race {code}",
                    "employment_status": "active",
                    "date_of_joining": START,
                },
            )
            ids.append(employee.public_id)
        setup.commit()
    return actor, ids


def _race(
    engine: Engine,
    name: str,
    first_change: Callable[[Session], object],
    second_change: Callable[[Session], object],
) -> dict[str, str]:
    first = _session(engine, name)
    second = _session(engine, name)
    try:
        # The second transaction takes its consistent-read snapshot NOW.
        second.execute(select(func.count()).select_from(Employee)).scalar_one()
        first_change(first)  # holds its lock until commit
        outcome: dict[str, str] = {}

        def run_second() -> None:
            try:
                second_change(second)
                second.commit()
                outcome["result"] = "applied"
            except AppError as exc:
                second.rollback()
                outcome["result"] = exc.code
                if exc.details:
                    outcome["details"] = ",".join(sorted(d.type for d in exc.details))
            except Exception as exc:  # e.g. a deadlock: reported, never hidden
                second.rollback()
                outcome["result"] = f"unexpected {type(exc).__name__}: {exc}"

        worker = threading.Thread(target=run_second)
        worker.start()
        time.sleep(1.0)
        assert worker.is_alive(), "the second change did not wait for the lock"
        first.commit()
        worker.join(timeout=60)
        assert not worker.is_alive()
        return outcome
    finally:
        first.close()
        second.close()


def test_concurrent_opposite_reporting_lines_cannot_create_a_cycle(
    committing_engine: Engine, test_database_name: str
) -> None:
    actor, (a_id, b_id) = _setup(committing_engine, test_database_name, ("RACE-A", "RACE-B"))

    def manage(employee: uuid.UUID, manager: uuid.UUID) -> Callable[[Session], object]:
        return lambda session: reporting.set_manager(
            session,
            employee,
            actor=actor,
            meta=META,
            manager_id=manager,
            relationship_type_id=None,
            effective_from=START,
            reason=None,
        )

    outcome = _race(committing_engine, test_database_name, manage(a_id, b_id), manage(b_id, a_id))
    assert outcome == {"result": "reporting_cycle"}
    with _session(committing_engine, test_database_name) as check:
        assert check.scalar(select(func.count()).select_from(ReportingRelationship)) == 1


def test_concurrent_primary_assignments_cannot_overlap(
    committing_engine: Engine, test_database_name: str
) -> None:
    actor, (person,) = _setup(committing_engine, test_database_name, ("RACE-P",))
    with _session(committing_engine, test_database_name) as lookup:
        unit_ids = {
            code: public_id
            for code, public_id in lookup.execute(
                select(OrgUnit.code, OrgUnit.public_id).where(
                    OrgUnit.code.in_(["OPERATION", "PURCHASE"])
                )
            )
        }

    def primary(unit_code: str, start: date) -> Callable[[Session], object]:
        return lambda session: assignments.create_assignment(
            session,
            person,
            actor=actor,
            meta=META,
            assignment_type=AssignmentType.PRIMARY,
            raw={"org_unit_id": unit_ids[unit_code]},
            effective_from=start,
            effective_to=None,
            reason=None,
        )

    # Different units and start dates, so only the "one primary at a time" rule can
    # catch the overlap (the open-primary unique key would also, as a backstop).
    outcome = _race(
        committing_engine,
        test_database_name,
        primary("OPERATION", START),
        primary("PURCHASE", date(2026, 3, 1)),
    )
    assert outcome == {"result": "primary_overlap"}
    with _session(committing_engine, test_database_name) as check:
        assert check.scalar(select(func.count()).select_from(EmployeeAssignment)) == 1


# --- separation racing reporting-line changes ----------------------------------------------

SEPARATION_DATE = date(2026, 6, 30)  # last working day; records end on 2026-07-01


def _separate(actor: Actor, employee: uuid.UUID, **flags: bool) -> Callable[[Session], object]:
    return lambda session: employees.change_employment_status(
        session,
        employee,
        actor=actor,
        meta=META,
        version=1,
        status=EmploymentStatus.SEPARATED,
        separation_date=SEPARATION_DATE,
        end_open_records=flags.get("end_open_records", False),
        end_direct_reports=flags.get("end_direct_reports", False),
        reason=None,
    )


def _manage(actor: Actor, employee: uuid.UUID, manager: uuid.UUID) -> Callable[[Session], object]:
    return lambda session: reporting.set_manager(
        session,
        employee,
        actor=actor,
        meta=META,
        manager_id=manager,
        relationship_type_id=None,
        effective_from=START,
        reason=None,
    )


def _lines(engine: Engine, name: str) -> list[tuple[Any, ...]]:
    with _session(engine, name) as check:
        return [
            (row.employee.employee_code, row.manager.employee_code, row.effective_to)
            for row in check.scalars(select(ReportingRelationship)).unique()
        ]


def _status(engine: Engine, name: str, code: str) -> str | None:
    with _session(engine, name) as check:
        return check.scalar(
            select(Employee.employment_status).where(Employee.employee_code == code)
        )


@pytest.mark.parametrize("first", ["separation", "new_direct_report"])
def test_manager_separation_races_a_new_direct_report(
    committing_engine: Engine, test_database_name: str, first: str
) -> None:
    actor, (manager, report) = _setup(committing_engine, test_database_name, ("RM-M", "RM-R"))
    separation = _separate(actor, manager, end_open_records=True)
    new_line = _manage(actor, report, manager)

    if first == "separation":
        outcome = _race(committing_engine, test_database_name, separation, new_line)
        assert outcome == {"result": "manager_separated"}
        assert _lines(committing_engine, test_database_name) == []
        assert _status(committing_engine, test_database_name, "RM-M") == "separated"
    else:
        # Separation waits for the reporting lock, then sees the committed direct report
        # and refuses rather than detaching it (end_direct_reports was not requested).
        outcome = _race(committing_engine, test_database_name, new_line, separation)
        assert outcome == {
            "result": "open_records_on_separation",
            "details": "open_direct_report",
        }
        assert _lines(committing_engine, test_database_name) == [("RM-R", "RM-M", None)]
        assert _status(committing_engine, test_database_name, "RM-M") == "active"


@pytest.mark.parametrize("first", ["separation", "new_manager"])
def test_subordinate_separation_races_a_new_manager(
    committing_engine: Engine, test_database_name: str, first: str
) -> None:
    actor, (report, manager) = _setup(committing_engine, test_database_name, ("RS-R", "RS-M"))
    separation = _separate(actor, report, end_open_records=True)
    new_line = _manage(actor, report, manager)

    if first == "separation":
        outcome = _race(committing_engine, test_database_name, separation, new_line)
        assert outcome == {"result": "outside_employment_period"}
        assert _lines(committing_engine, test_database_name) == []
    else:
        # The separation's locking read sees the line committed after its snapshot and
        # ends it on the day after the last working day - it is never left open.
        outcome = _race(committing_engine, test_database_name, new_line, separation)
        assert outcome == {"result": "applied"}
        assert _lines(committing_engine, test_database_name) == [("RS-R", "RS-M", date(2026, 7, 1))]
    assert _status(committing_engine, test_database_name, "RS-R") == "separated"


# --- deterministic lock acquisition order -----------------------------------------------------


def test_lock_acquisition_order_is_deterministic(
    test_engine: Engine, db: Session, test_database_name: str
) -> None:
    """Record the FOR UPDATE statements actually sent: the reporting graph lock first,
    then employee rows in ascending internal id, whatever role each employee plays."""
    assert_connected_to(db.connection(), test_database_name)
    admin = make_user(db, "lock.order.admin", roles=("hr_admin",))
    actor = Actor(user_id=admin.id, permissions=frozenset())
    created = [
        employees.create_employee(
            db,
            actor=actor,
            meta=META,
            values={"employee_code": code, "full_name": "Lock Order", "date_of_joining": START},
        )
        for code in ("LO-A", "LO-B", "LO-C")
    ]
    a, b, c = sorted(created, key=lambda employee: employee.id)
    statements: list[tuple[str, Any]] = []

    def record(_conn: Any, _cursor: Any, statement: str, parameters: Any, *_: Any) -> None:
        if "FOR UPDATE" in statement:
            statements.append((statement, parameters))

    def locks() -> list[str]:
        order = []
        for statement, parameters in statements:
            if "FROM graph_lock" in statement:
                order.append(f"graph_lock:{parameters['name_1']}")
            elif "FROM employee" in statement and "employee.id = " in statement:
                order.append(f"employee:{parameters['id_1']}")
            elif "FROM employee" in statement:
                order.append("employee")
        statements.clear()
        return order

    def manage(employee: Any, manager: Any) -> None:
        reporting.set_manager(
            db,
            employee.public_id,
            actor=actor,
            meta=META,
            manager_id=manager.public_id,
            relationship_type_id=None,
            effective_from=START,
            reason=None,
        )

    event.listen(test_engine, "before_cursor_execute", record)
    try:
        manage(c, a)  # the subject has the larger id: the manager row is locked first
        assert locks()[:3] == ["graph_lock:reporting", f"employee:{a.id}", f"employee:{c.id}"]
        manage(a, b)  # the subject has the smaller id: the subject row is locked first
        assert locks()[:3] == ["graph_lock:reporting", f"employee:{a.id}", f"employee:{b.id}"]
        employees.change_employment_status(
            db,
            a.public_id,
            actor=actor,
            meta=META,
            version=a.version,
            status=EmploymentStatus.SEPARATED,
            separation_date=SEPARATION_DATE,
            end_open_records=True,
            end_direct_reports=True,
            reason=None,
        )
        assert locks()[:2] == ["graph_lock:reporting", "employee"]
    finally:
        event.remove(test_engine, "before_cursor_execute", record)
