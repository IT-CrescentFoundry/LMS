# ruff: noqa: E501 - long literal SQL fixtures
"""Stage D migration 0010: round trip, downgrade safeguards, seed and constraints.

Same harness as the C1/C3 safety tests: Alembic runs against crescent_lms_test only (as
lms_test@127.0.0.1, verified on every connection), changes are COMMITTED, and the
schema is rebuilt afterwards. Import history is never deleted by a migration.
"""

from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError, OperationalError

from tests.integration.test_c1_migration_safety import MigrationDb, load_revision
from tests.support.schema_reset import alembic_head, rebuild_test_schema

pytestmark = pytest.mark.db

IMPORT_TABLES = (
    "import_job",
    "import_row",
    "import_issue",
    "import_value_mapping",
    "record_provenance",
)
IMPORT_PERMISSIONS = (
    "'imports.view', 'imports.employees.run', 'imports.employees.commit', 'imports.mappings.manage'"
)


@pytest.fixture
def mdb(test_engine: Engine, test_database_name: str) -> Iterator[MigrationDb]:
    db = MigrationDb(test_engine, test_database_name)
    assert db.version() == alembic_head() == "0010", "expected a clean schema at 0010"
    try:
        yield db
    finally:
        rebuild_test_schema(test_engine, test_database_name)


def _count_permissions(db: MigrationDb) -> int:
    return int(
        db.scalar(f"SELECT COUNT(*) FROM access_permission WHERE code IN ({IMPORT_PERMISSIONS})")  # noqa: S608
    )


def _grants(db: MigrationDb) -> list[str]:
    sql = text(
        "SELECT CONCAT(r.code, ':', p.code) FROM access_role_permission m "  # noqa: S608
        "JOIN access_role r ON r.id = m.access_role_id "
        "JOIN access_permission p ON p.id = m.access_permission_id "
        f"WHERE p.code IN ({IMPORT_PERMISSIONS}) ORDER BY 1"
    )
    return [
        str(pair) for pair in db.check(lambda connection: list(connection.execute(sql).scalars()))
    ]


def _add_job(db: MigrationDb) -> None:
    db.run(
        "INSERT INTO import_job (public_id, profile_code, profile_version, status, original_filename, "
        "file_sha256, file_size, file_stored, workbook, uploaded_by_user_id, uploaded_at, updated_at, version) "
        "SELECT UNHEX(REPLACE(UUID(), '-', '')), 'employees', 1, 'cancelled', 'x.xlsx', REPEAT('a', 64), 1, 0, "
        "JSON_ARRAY(), id, UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 1 FROM user_account LIMIT 1"
    )


def test_clean_round_trip_and_exact_seed(mdb: MigrationDb) -> None:
    rev10 = load_revision("0010")
    assert mdb.check(rev10.seed_problems) == []
    assert _count_permissions(mdb) == 4
    assert _grants(mdb) == sorted(
        f"{role}:{code}" for role in ("hr_admin", "super_admin") for code in rev10.ALL_CODES
    )
    mdb.migrate("downgrade", "0009")
    assert mdb.version() == "0009"
    for table in IMPORT_TABLES:
        assert not mdb.has_table(table), table
    assert _count_permissions(mdb) == 0
    assert mdb.scalar("SELECT COUNT(*) FROM graph_lock WHERE name = 'imports'") == 0
    mdb.migrate("upgrade", "0010")
    assert mdb.check(rev10.seed_problems) == []


def test_downgrade_refuses_while_import_history_exists(mdb: MigrationDb) -> None:
    mdb.run(
        "INSERT INTO user_account (public_id, login_id, display_name, status, status_changed_at, "
        "password_must_change, created_at, updated_at, version) VALUES (UNHEX(REPLACE(UUID(), '-', '')), "
        "'mig.importer', 'Migration Importer', 'pending_activation', UTC_TIMESTAMP(6), 0, UTC_TIMESTAMP(6), "
        "UTC_TIMESTAMP(6), 1)"
    )
    _add_job(mdb)
    with pytest.raises(RuntimeError, match="import_job has 1 row"):
        mdb.migrate("downgrade", "0009")
    assert mdb.version() == "0010" and mdb.has_table("import_job")


def test_downgrade_refuses_changed_permission_seed(mdb: MigrationDb) -> None:
    mdb.run(
        "DELETE m FROM access_role_permission m JOIN access_permission p ON p.id = m.access_permission_id "
        "JOIN access_role r ON r.id = m.access_role_id WHERE p.code = 'imports.view' AND r.code = 'hr_admin'"
    )
    with pytest.raises(RuntimeError, match="role-permission mappings differ"):
        mdb.migrate("downgrade", "0009")
    assert mdb.version() == "0010" and _count_permissions(mdb) == 4


def test_upgrade_refuses_pre_existing_codes(mdb: MigrationDb) -> None:
    mdb.migrate("downgrade", "0009")
    mdb.run(
        "INSERT INTO access_permission (code, description, is_privileged, created_at) VALUES ('imports.view', 'x', 0, UTC_TIMESTAMP(6))"
    )
    with pytest.raises(RuntimeError, match="permission codes already exist"):
        mdb.migrate("upgrade", "0010")
    assert mdb.version() == "0009"
    mdb.run("DELETE FROM access_permission WHERE code = 'imports.view'")


def test_one_current_mapping_decision_per_label(mdb: MigrationDb) -> None:
    insert = (
        "INSERT INTO import_value_mapping (public_id, kind, source_text, normalised_text, status, "
        "target_public_id, created_at, version) VALUES (UNHEX(REPLACE(UUID(), '-', '')), 'designation', "
        "'Sr. Opr', 'sr opr', :status, :target, UTC_TIMESTAMP(6), 1)"
    )
    mdb.run(insert, status="pending", target=None)
    with pytest.raises(IntegrityError):
        mdb.run(insert, status="pending", target=None)
    mdb.run("UPDATE import_value_mapping SET status = 'superseded'")
    mdb.run(
        insert, status="pending", target=None
    )  # superseded history does not block a new decision
    with pytest.raises(OperationalError):  # approved without a target (check constraint)
        mdb.run("UPDATE import_value_mapping SET status = 'approved' WHERE status = 'pending'")
    mdb.run("DELETE FROM import_value_mapping")
