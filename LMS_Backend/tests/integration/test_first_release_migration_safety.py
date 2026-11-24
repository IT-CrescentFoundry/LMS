# ruff: noqa: E501 - long literal SQL fixtures
"""Migration 0011 (first release): round trip, exact seed, downgrade safeguards.

Same harness as the C1/C3/D safety tests: Alembic runs against crescent_lms_test only,
changes are COMMITTED, and the schema is rebuilt afterwards.
"""

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine
from sqlalchemy.exc import OperationalError

from tests.integration.test_c1_migration_safety import MigrationDb, load_revision
from tests.support.schema_reset import alembic_head, rebuild_test_schema

pytestmark = pytest.mark.db

NEW_TABLES = (
    "training_programme",
    "training_event",
    "training_session",
    "training_participation",
    "proficiency_scale",
    "proficiency_level",
    "competency",
    "skill_matrix",
    "skill_matrix_item",
    "competency_assessment",
    "notification",
)


@pytest.fixture
def mdb(test_engine: Engine, test_database_name: str) -> Iterator[MigrationDb]:
    db = MigrationDb(test_engine, test_database_name)
    assert db.version() == alembic_head() == "0011", "expected a clean schema at 0011"
    try:
        yield db
    finally:
        rebuild_test_schema(test_engine, test_database_name)


def test_clean_round_trip_and_exact_seed(mdb: MigrationDb) -> None:
    rev = load_revision("0011")
    assert mdb.check(rev.seed_problems) == []
    assert mdb.scalar("SELECT COUNT(*) FROM proficiency_scale") == 2
    assert mdb.scalar("SELECT COUNT(*) FROM proficiency_level") == 9
    assert (
        mdb.scalar(
            "SELECT label FROM proficiency_level l JOIN proficiency_scale s ON s.id = l.scale_id "
            "WHERE s.code = 'CF_SKILL_MATRIX_1_5' AND l.`rank` = 5"
        )
        == "Can Train Others"
    )
    mdb.migrate("downgrade", "0010")
    assert mdb.version() == "0010"
    for table in NEW_TABLES:
        assert not mdb.has_table(table), table
    assert mdb.scalar("SELECT COUNT(*) FROM access_permission WHERE code LIKE 'competency.%'") == 0
    mdb.migrate("upgrade", "0011")
    assert mdb.check(rev.seed_problems) == []


def test_downgrade_refuses_while_training_records_exist(mdb: MigrationDb) -> None:
    mdb.run(
        "INSERT INTO training_event (public_id, code, title, status, source, created_at, updated_at, version) "
        "VALUES (UNHEX(REPLACE(UUID(), '-', '')), 'TE-MIG', 'Synthetic', 'planned', 'manual', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 1)"
    )
    with pytest.raises(RuntimeError, match="training_event holds rows"):
        mdb.migrate("downgrade", "0010")
    assert mdb.version() == "0011" and mdb.has_table("training_event")
    mdb.run("DELETE FROM training_event")


def test_downgrade_refuses_changed_permission_seed(mdb: MigrationDb) -> None:
    mdb.run(
        "DELETE m FROM access_role_permission m JOIN access_permission p ON p.id = m.access_permission_id "
        "JOIN access_role r ON r.id = m.access_role_id WHERE p.code = 'competency.view' AND r.code = 'hr_admin'"
    )
    with pytest.raises(RuntimeError, match="role-permission mappings differ"):
        mdb.migrate("downgrade", "0010")
    assert mdb.version() == "0011"


def test_database_constraints_protect_evidence_rules(mdb: MigrationDb) -> None:
    # A completed event must carry an actual start date.
    with pytest.raises(OperationalError):
        mdb.run(
            "INSERT INTO training_event (public_id, code, title, status, source, created_at, updated_at, version) "
            "VALUES (UNHEX(REPLACE(UUID(), '-', '')), 'TE-BAD', 'x', 'completed', 'manual', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 1)"
        )
    # Planned months are stored as the first day of the month.
    with pytest.raises(OperationalError):
        mdb.run(
            "INSERT INTO training_event (public_id, code, title, status, source, planned_month, created_at, updated_at, version) "
            "VALUES (UNHEX(REPLACE(UUID(), '-', '')), 'TE-BAD2', 'x', 'planned', 'manual', '2026-05-15', UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 1)"
        )


# ------------------------------------------------- review 2026-11-23 additional safeguards


def test_downgrade_refuses_when_seeded_scales_were_edited(mdb: MigrationDb) -> None:
    mdb.run(
        "UPDATE proficiency_level l JOIN proficiency_scale s ON s.id = l.scale_id "
        "SET l.label = 'Edited by an administrator' "
        "WHERE s.code = 'CF_SKILL_MATRIX_1_5' AND l.`rank` = 1"
    )
    with pytest.raises(RuntimeError, match="levels of seeded scale CF_SKILL_MATRIX_1_5"):
        mdb.migrate("downgrade", "0010")
    assert mdb.version() == "0011"
    assert (
        mdb.scalar("SELECT COUNT(*) FROM proficiency_level") == 9
    )  # nothing was deleted by the refused downgrade


def test_upgrade_preflight_refuses_leftover_tables_without_changing_anything(
    mdb: MigrationDb,
) -> None:
    mdb.migrate("downgrade", "0010")
    # Simulate an interrupted earlier attempt that left one (empty) table behind.
    mdb.run("CREATE TABLE notification_preference (id BIGINT PRIMARY KEY)")
    with pytest.raises(RuntimeError, match="cannot start: these tables already exist"):
        mdb.migrate("upgrade", "0011")
    assert mdb.version() == "0010"
    assert not mdb.has_table("training_event")
    assert mdb.scalar("SELECT COUNT(*) FROM access_permission WHERE code LIKE 'competency.%'") == 0
    mdb.run("DROP TABLE notification_preference")
    mdb.migrate("upgrade", "0011")
    assert mdb.version() == "0011"


def test_competency_governance_constraints(mdb: MigrationDb) -> None:
    insert = (
        "INSERT INTO competency (public_id, code, name, is_active, status, approved_at, "
        "created_at, updated_at, version) VALUES (UNHEX(REPLACE(UUID(), '-', '')), :code, 'x', "
        "1, :status, :approved_at, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 1)"
    )
    with pytest.raises(OperationalError):  # unknown status
        mdb.run(insert, code="C-BAD1", status="published", approved_at=None)
    with pytest.raises(OperationalError):  # approved without an approval time
        mdb.run(insert, code="C-BAD2", status="approved", approved_at=None)
    mdb.run(insert, code="C-OK", status="draft", approved_at=None)
    with pytest.raises(RuntimeError, match="competency holds rows"):
        mdb.migrate("downgrade", "0010")
    mdb.run("DELETE FROM competency")
