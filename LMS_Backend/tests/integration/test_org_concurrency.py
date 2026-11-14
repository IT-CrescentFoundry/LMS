"""Concurrency: hierarchy changes and dependency checks see committed data.

Two administrators move A under B and B under A at the same time. Each move alone
is valid; together they would form a loop. The ``org_hierarchy`` graph lock
serialises them, and the second move must then see the first one's committed link,
even though its transaction took a REPEATABLE READ snapshot earlier. That is why
the service uses locking reads after taking the lock.

These tests COMMIT (on crescent_lms_test only, as lms_test@127.0.0.1); the schema
is rebuilt afterwards so later tests start from the clean seeded state.
"""

import threading
import time
from collections.abc import Iterator
from datetime import date

import pytest
from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from app.core.context import RequestMeta
from app.core.errors import AppError
from app.models.organisation import OrgUnit, OrgUnitHierarchy, OrgUnitType, ParentRuleMode
from app.services.identity.context import Actor
from app.services.organisation import functional_roles, reference, unit_types, units
from tests.integration.helpers import make_user
from tests.support.database import assert_connected_to
from tests.support.schema_reset import rebuild_test_schema

pytestmark = pytest.mark.db

META = RequestMeta(request_id="org-concurrency")
START = date(2026, 1, 1)
MOVE_DATE = date(2026, 6, 1)


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


def test_concurrent_opposite_moves_cannot_create_a_cycle(
    committing_engine: Engine, test_database_name: str
) -> None:
    with _session(committing_engine, test_database_name) as setup:
        admin = make_user(setup, "race.admin", roles=("hr_admin",))
        actor = Actor(user_id=admin.id, permissions=frozenset())
        team = unit_types.create_unit_type(
            setup,
            actor=actor,
            meta=META,
            code="RACE_TEAM",
            name="Race Team",
            description=None,
            sort_order=0,
            allows_employee_assignment=True,
            parent_rule_mode=ParentRuleMode.ADVISORY,
            translations={},
        )
        created = {}
        for code in ("RACE_A", "RACE_B"):
            unit, _ = units.create_unit(
                setup,
                actor=actor,
                meta=META,
                code=code,
                name=f"Race {code[-1]}",
                short_name=None,
                unit_type_id=team.public_id,
                location_id=None,
                parent_id=None,
                effective_from=START,
                external_ref=None,
                translations={},
            )
            created[code] = (unit.public_id, unit.version)
        setup.commit()

    (a_id, a_version), (b_id, b_version) = created["RACE_A"], created["RACE_B"]
    first = _session(committing_engine, test_database_name)
    second = _session(committing_engine, test_database_name)
    try:
        # The second transaction takes its consistent-read snapshot NOW, before the
        # first move exists. A plain (non-locking) read later would miss that move.
        assert len(second.execute(select(OrgUnit.id)).all()) == 7

        units.move_unit(
            first,
            a_id,
            actor=actor,
            meta=META,
            version=a_version,
            new_parent_id=b_id,
            effective_date=MOVE_DATE,
        )  # holds the graph lock until commit

        outcome: dict[str, str] = {}

        def opposite_move() -> None:
            try:
                units.move_unit(
                    second,
                    b_id,
                    actor=actor,
                    meta=META,
                    version=b_version,
                    new_parent_id=a_id,
                    effective_date=MOVE_DATE,
                )
                second.commit()
                outcome["result"] = "moved"
            except AppError as exc:
                second.rollback()
                outcome["result"] = exc.code

        worker = threading.Thread(target=opposite_move)
        worker.start()
        time.sleep(1.0)
        assert worker.is_alive(), "the second move did not wait for the graph lock"
        first.commit()
        worker.join(timeout=60)
        assert not worker.is_alive()
        assert outcome == {"result": "hierarchy_cycle"}
    finally:
        first.close()
        second.close()

    with _session(committing_engine, test_database_name) as check:
        links = [
            (link.child_unit_id, link.parent_unit_id, link.effective_from)
            for link in check.scalars(select(OrgUnitHierarchy))
        ]
        ids = {code: unit_id for code, unit_id in check.execute(select(OrgUnit.code, OrgUnit.id))}
        assert links == [(ids["RACE_A"], ids["RACE_B"], MOVE_DATE)]


def test_closure_sees_a_scoped_mapping_committed_after_its_snapshot(
    committing_engine: Engine, test_database_name: str
) -> None:
    """A request reads (e.g. its session) before the service runs, so its snapshot is
    older than the service call. The closure's dependency checks must still see a
    mapping that another transaction committed in between."""
    with _session(committing_engine, test_database_name) as setup:
        admin = make_user(setup, "snapshot.admin", roles=("hr_admin",))
        actor = Actor(user_id=admin.id, permissions=frozenset())
        function_type = setup.scalars(
            select(OrgUnitType).where(OrgUnitType.code == "FUNCTION")
        ).one()
        unit, _ = units.create_unit(
            setup,
            actor=actor,
            meta=META,
            code="SNAP_UNIT",
            name="Snapshot Unit",
            short_name=None,
            unit_type_id=function_type.public_id,
            location_id=None,
            parent_id=None,
            effective_from=START,
            external_ref=None,
            translations={},
        )
        designation = reference.create_reference(
            setup,
            reference.DESIGNATION,
            actor=actor,
            meta=META,
            values={"code": "SNAP_DES", "title": "Snapshot Designation"},
        )
        role = functional_roles.create_role(
            setup,
            actor=actor,
            meta=META,
            code="SNAP_ROLE",
            name="Snapshot Role",
            description=None,
            job_family_id=None,
            owner_unit_id=None,
            translations={},
        )
        setup.commit()
        unit_id, unit_version = unit.public_id, unit.version

    closer = _session(committing_engine, test_database_name)
    try:
        assert closer.execute(select(OrgUnit.id)).all()  # the request's earlier snapshot
        with _session(committing_engine, test_database_name) as mapper:
            functional_roles.create_mapping(
                mapper,
                designation.public_id,
                actor=actor,
                meta=META,
                functional_role_id=role.public_id,
                scope_unit_id=unit_id,
                include_descendants=True,
                effective_from=START,
            )
            mapper.commit()

        with pytest.raises(AppError) as excinfo:
            units.close_unit(
                closer,
                unit_id,
                actor=actor,
                meta=META,
                version=unit_version,
                effective_date=MOVE_DATE,
                reason=None,
            )
        assert excinfo.value.code == "unit_has_dependants"
        assert [issue.type for issue in excinfo.value.details or []] == ["scoped_mapping"]
    finally:
        closer.rollback()
        closer.close()
