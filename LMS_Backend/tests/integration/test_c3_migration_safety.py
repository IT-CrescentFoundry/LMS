"""C3 migrations 0008-0009: downgrade safeguards and seed integrity, on real MySQL.

Same rules and harness as the C1 safety tests: Alembic runs against crescent_lms_test
only (as lms_test@127.0.0.1, verified on every connection), changes are COMMITTED,
and the schema is rebuilt afterwards. A refused downgrade changes nothing, and
employee data or account links are never deleted by a migration.
"""

from collections.abc import Callable, Iterator

import pytest
from sqlalchemy import Engine

from tests.integration.test_c1_migration_safety import MigrationDb, load_revision
from tests.support.schema_reset import alembic_head, rebuild_test_schema

pytestmark = pytest.mark.db

EMPLOYEE_PERMISSIONS = (
    "'employees.view', 'employees.history.view', 'employees.manage', 'reporting_lines.manage'"
)
C3_TABLES = (
    "employee",
    "employee_assignment",
    "employee_functional_role",
    "employee_responsibility",
    "reporting_relationship_type",
    "reporting_relationship_type_translation",
    "reporting_relationship",
)


@pytest.fixture
def mdb(test_engine: Engine, test_database_name: str) -> Iterator[MigrationDb]:
    db = MigrationDb(test_engine, test_database_name)
    assert db.version() == alembic_head() == "0009", "expected a clean schema at 0009"
    try:
        yield db
    finally:
        rebuild_test_schema(test_engine, test_database_name)


def _employee_permissions(db: MigrationDb) -> int:
    return int(
        db.scalar(
            f"SELECT COUNT(*) FROM access_permission WHERE code IN ({EMPLOYEE_PERMISSIONS})"  # noqa: S608
        )
    )


def _employee_mappings(db: MigrationDb) -> int:
    return int(
        db.scalar(
            "SELECT COUNT(*) FROM access_role_permission m "  # noqa: S608 - constant codes
            "JOIN access_permission p ON p.id = m.access_permission_id "
            f"WHERE p.code IN ({EMPLOYEE_PERMISSIONS})"
        )
    )


def _add_employee(db: MigrationDb, code: str = "MIG-1") -> None:
    db.run(
        "INSERT INTO employee (public_id, employee_code, full_name, created_at, updated_at, "
        "version) VALUES (UNHEX(REPLACE(UUID(), '-', '')), :c, 'Migration Test', "
        "UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 1)",
        c=code,
    )


# --- clean round trip ----------------------------------------------------------------------


def test_clean_round_trip_0009_to_0007_and_back(mdb: MigrationDb) -> None:
    rev8, rev9 = load_revision("0008"), load_revision("0009")
    assert mdb.check(rev8.seed_problems) == []
    assert mdb.check(rev9.seed_problems) == []
    assert _employee_permissions(mdb) == 4 and _employee_mappings(mdb) == 8

    mdb.migrate("downgrade", "0008")
    assert mdb.version() == "0008"
    assert _employee_permissions(mdb) == 0 and _employee_mappings(mdb) == 0
    mdb.migrate("downgrade", "0007")
    assert mdb.version() == "0007"
    for table in C3_TABLES:
        assert not mdb.has_table(table), table
    assert (
        mdb.scalar(
            "SELECT COUNT(*) FROM information_schema.COLUMNS WHERE TABLE_SCHEMA = DATABASE() "
            "AND TABLE_NAME = 'user_account' AND COLUMN_NAME IN ('employee_id', "
            "'linked_employee_active')"
        )
        == 0
    )
    assert mdb.scalar("SELECT COUNT(*) FROM graph_lock") == 1  # org_hierarchy (0004) kept
    assert mdb.scalar("SELECT COUNT(*) FROM access_permission") == 22

    mdb.migrate("upgrade", "0009")
    assert mdb.check(rev8.seed_problems) == []
    assert mdb.check(rev9.seed_problems) == []
    assert mdb.scalar(
        "SELECT LOWER(HEX(public_id)) FROM reporting_relationship_type WHERE code = 'LINE_MANAGER'"
    ) == rev8.LINE_MANAGER_ID.replace("-", "")  # same fixed identity again


# --- 0008 ------------------------------------------------------------------------------------


def _link_account(db: MigrationDb) -> None:
    _add_employee(db)
    db.run(
        "INSERT INTO user_account (public_id, login_id, display_name, status, "
        "status_changed_at, created_at, updated_at, version, password_must_change, employee_id) "
        "SELECT UNHEX(REPLACE(UUID(), '-', '')), 'mig.linked', 'Mig', 'disabled', "
        "UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 1, 0, id FROM employee"
    )


DOWNGRADE_0008_CASES: dict[str, tuple[Callable[[MigrationDb], None], str]] = {
    "employee rows": (_add_employee, r"employee has 1 row\(s\)"),
    "linked account": (_link_account, r"1 user account\(s\) are linked to employees"),
    "modified seed": (
        lambda db: db.run(
            "UPDATE reporting_relationship_type SET name = 'Boss' WHERE code = 'LINE_MANAGER'"
        ),
        r"LINE_MANAGER was modified \(name\)",
    ),
    "added type": (
        lambda db: db.run(
            "INSERT INTO reporting_relationship_type (public_id, code, name, allows_multiple, "
            "is_hierarchical, is_active, created_at, updated_at, version) VALUES "
            "(UNHEX(REPLACE(UUID(), '-', '')), 'MENTOR', 'Mentor', 1, 0, 1, "
            "UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 1)"
        ),
        r"other reporting types exist \['MENTOR'\]",
    ),
    "unknown lock": (
        lambda db: db.run(
            "INSERT INTO graph_lock (name, description) VALUES ('later_graph', 'Later')"
        ),
        r"graph_lock holds rows of later revisions \['later_graph'\]",
    ),
}


@pytest.mark.parametrize("case", list(DOWNGRADE_0008_CASES))
def test_0008_downgrade_refuses_data_links_and_changed_seed(mdb: MigrationDb, case: str) -> None:
    change, message = DOWNGRADE_0008_CASES[case]
    mdb.migrate("downgrade", "0008")
    change(mdb)
    employees_before = mdb.scalar("SELECT COUNT(*) FROM employee")

    with pytest.raises(RuntimeError, match=message):
        mdb.migrate("downgrade", "0007")

    assert mdb.version() == "0008"
    assert mdb.has_table("employee") and mdb.has_table("reporting_relationship")
    assert mdb.scalar("SELECT COUNT(*) FROM employee") == employees_before


def test_0008_seed_verification_detects_a_missing_seed(mdb: MigrationDb) -> None:
    rev8 = load_revision("0008")
    mdb.run("DELETE FROM graph_lock WHERE name = 'reporting'")
    assert mdb.check(rev8.seed_problems) == ["graph_lock row 'reporting' is missing"]


# --- 0009 ------------------------------------------------------------------------------------


DOWNGRADE_0009_CASES: dict[str, tuple[str, str]] = {
    "additional mapping": (
        "INSERT INTO access_role_permission (access_role_id, access_permission_id, granted_at) "
        "SELECT r.id, p.id, NOW(6) FROM access_role r, access_permission p "
        "WHERE r.code = 'hod' AND p.code = 'employees.view'",
        r"additional role-permission mappings \[\('hod', 'employees.view'\)\]",
    ),
    "modified permission": (
        "UPDATE access_permission SET description = 'Edited' WHERE code = 'employees.manage'",
        r"permission employees.manage was modified",
    ),
    "other reference": (
        "UPDATE access_role SET assign_permission_id = "
        "(SELECT id FROM access_permission WHERE code = 'employees.view') WHERE code = 'sme'",
        r"access_role.assign_permission_id refer to these permissions",
    ),
}


@pytest.mark.parametrize("case", list(DOWNGRADE_0009_CASES))
def test_0009_downgrade_refuses_changed_permission_data(mdb: MigrationDb, case: str) -> None:
    setup, message = DOWNGRADE_0009_CASES[case]
    mdb.run(setup)
    mappings_before = _employee_mappings(mdb)

    with pytest.raises(RuntimeError, match=message):
        mdb.migrate("downgrade", "0008")

    assert mdb.version() == "0009"
    assert _employee_permissions(mdb) == 4
    assert _employee_mappings(mdb) == mappings_before


def test_0009_upgrade_refuses_pre_existing_codes(mdb: MigrationDb) -> None:
    mdb.migrate("downgrade", "0008")
    mdb.run(
        "INSERT INTO access_permission (code, description, is_privileged, created_at) "
        "VALUES ('employees.view', 'Pre-existing', 0, NOW(6))"
    )
    with pytest.raises(RuntimeError, match=r"already exist \['employees.view'\]"):
        mdb.migrate("upgrade", "0009")
    assert mdb.version() == "0008"
    assert _employee_mappings(mdb) == 0
