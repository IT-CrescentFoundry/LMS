"""C1 migrations 0004-0007: downgrade safeguards and seed integrity, on real MySQL.

Every test drives Alembic against crescent_lms_test only (as lms_test@127.0.0.1,
verified on every connection), COMMITS changes, and rebuilds the schema afterwards
with the Stage B reset harness. No mocked migration functions are used: the guards
run exactly as they would in a real upgrade or downgrade.

A refused downgrade must change nothing: the revision, the data and the tables stay as
they were. Administrator-created data is never deleted by a migration.
"""

import importlib.util
import re
from collections.abc import Callable, Iterator
from types import ModuleType
from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, text

from app.core import config as app_config
from app.core.config import BACKEND_DIR
from tests.integration.test_migration_cli_path import _cli_settings
from tests.support.database import IntegrationDatabaseSettings, assert_connected_to
from tests.support.schema_reset import _alembic_config, alembic_head, rebuild_test_schema

pytestmark = pytest.mark.db

VERSIONS = BACKEND_DIR / "alembic" / "versions"
ORG_PERMISSIONS = (
    "organisation.view",
    "organisation.manage",
    "designations.manage",
    "functional_roles.manage",
    "responsibilities.manage",
)


def load_revision(revision: str) -> ModuleType:
    path = next(VERSIONS.glob(f"*-{revision}_*.py"))
    spec = importlib.util.spec_from_file_location(f"c1_revision_{revision}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class MigrationDb:
    """Committed access to crescent_lms_test; every connection is verified first."""

    def __init__(self, engine: Engine, name: str) -> None:
        self.engine = engine
        self.name = name

    def migrate(self, direction: str, target: str) -> None:
        with self.engine.begin() as connection:
            assert_connected_to(connection, self.name)
            getattr(command, direction)(_alembic_config(connection), target)

    def run(self, sql: str, **params: Any) -> None:
        with self.engine.begin() as connection:
            assert_connected_to(connection, self.name)
            connection.execute(text(sql), params)

    def scalar(self, sql: str, **params: Any) -> Any:
        with self.engine.connect() as connection:  # fresh connection: committed state
            assert_connected_to(connection, self.name)
            return connection.execute(text(sql), params).scalar()

    def check(self, func: Callable[[Connection], Any]) -> Any:
        with self.engine.connect() as connection:
            assert_connected_to(connection, self.name)
            return func(connection)

    def version(self) -> str:
        return str(self.scalar("SELECT version_num FROM alembic_version"))

    def has_table(self, table: str) -> bool:
        return bool(
            self.scalar(
                "SELECT COUNT(*) FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = :t",
                t=table,
            )
        )

    def org_mappings(self) -> int:
        return int(
            self.scalar(
                "SELECT COUNT(*) FROM access_role_permission m "
                "JOIN access_permission p ON p.id = m.access_permission_id "
                "WHERE p.code IN ('organisation.view', 'organisation.manage', "
                "'designations.manage', 'functional_roles.manage', 'responsibilities.manage')"
            )
        )

    def org_permissions(self) -> int:
        return int(
            self.scalar(
                "SELECT COUNT(*) FROM access_permission WHERE code IN ('organisation.view', "
                "'organisation.manage', 'designations.manage', 'functional_roles.manage', "
                "'responsibilities.manage')"
            )
        )

    def seeded_functions(self) -> int:
        ids = ", ".join(
            f"UNHEX('{public_id.replace('-', '')}')"
            for public_id, *_ in load_revision("0005").FUNCTIONS
        )
        return int(self.scalar(f"SELECT COUNT(*) FROM org_unit WHERE public_id IN ({ids})"))  # noqa: S608


@pytest.fixture
def mdb(test_engine: Engine, test_database_name: str) -> Iterator[MigrationDb]:
    db = MigrationDb(test_engine, test_database_name)
    assert db.version() == alembic_head(), "expected a clean schema at head"
    try:
        yield db
    finally:
        rebuild_test_schema(test_engine, test_database_name)


# --- clean upgrade / downgrade ----------------------------------------------------------


def test_clean_step_by_step_round_trip(mdb: MigrationDb) -> None:
    rev5, rev7 = load_revision("0005"), load_revision("0007")
    assert mdb.check(rev5.baseline_problems) == []
    assert mdb.check(rev7.seed_problems) == []
    assert mdb.seeded_functions() == 5
    assert mdb.org_mappings() == 13

    for target in ("0006", "0005", "0004", "0003"):
        mdb.migrate("downgrade", target)
        assert mdb.version() == target
        if target == "0006":  # 0007 removed exactly its 13 mappings and 5 permissions
            assert mdb.org_mappings() == 0 and mdb.org_permissions() == 0
        if target == "0004":  # 0005 removed the unchanged baseline
            for table in ("org_unit", "org_unit_type", "org_unit_type_rule"):
                assert mdb.scalar(f"SELECT COUNT(*) FROM {table}") == 0  # noqa: S608
    assert not mdb.has_table("org_unit") and not mdb.has_table("designation")
    assert mdb.scalar("SELECT COUNT(*) FROM access_permission") == 17  # Stage B intact

    for target in ("0004", "0005", "0006", "0007"):
        mdb.migrate("upgrade", target)
        assert mdb.version() == target
    assert mdb.check(rev5.baseline_problems) == []
    assert mdb.check(rev7.seed_problems) == []
    assert mdb.seeded_functions() == 5  # same fixed public_ids again


def test_full_round_trip_through_base(test_engine: Engine, test_database_name: str) -> None:
    report = rebuild_test_schema(test_engine, test_database_name)  # up -> base -> up
    assert report.phases["final_upgrade"].version == (alembic_head(),)
    assert MigrationDb(test_engine, test_database_name).seeded_functions() == 5


# --- 0007 ---------------------------------------------------------------------------------


def _grant(db: MigrationDb, role: str, permission: str) -> None:
    db.run(
        "INSERT INTO access_role_permission (access_role_id, access_permission_id, granted_at) "
        "SELECT r.id, p.id, NOW(6) FROM access_role r, access_permission p "
        "WHERE r.code = :r AND p.code = :p",
        r=role,
        p=permission,
    )


def _regrant(db: MigrationDb) -> None:
    # Plain SQL, not the ORM model: the model follows head (C3 added columns), while
    # this runs against the schema at revision 0007.
    db.run(
        "INSERT INTO user_account (public_id, login_id, display_name, status, "
        "status_changed_at, password_must_change, created_at, updated_at, version) "
        "VALUES (UUID_TO_BIN(UUID()), 'migration.admin', 'Test migration.admin', "
        "'pending_activation', "
        "NOW(6), 0, NOW(6), NOW(6), 1)"
    )
    user_id = db.scalar("SELECT id FROM user_account WHERE login_id = 'migration.admin'")
    db.run(
        "UPDATE access_role_permission m JOIN access_role r ON r.id = m.access_role_id "
        "JOIN access_permission p ON p.id = m.access_permission_id "
        "SET m.granted_by_user_id = :u "
        "WHERE r.code = 'hr_admin' AND p.code = 'organisation.manage'",
        u=user_id,
    )


DOWNGRADE_0007_CASES: dict[str, tuple[Callable[[MigrationDb], None], str]] = {
    "additional mapping": (
        lambda db: _grant(db, "hod", "organisation.manage"),
        r"additional role-permission mappings \[\('hod', 'organisation.manage'\)\]",
    ),
    "missing mapping": (
        lambda db: db.run(
            "DELETE m FROM access_role_permission m JOIN access_role r ON r.id = m.access_role_id "
            "JOIN access_permission p ON p.id = m.access_permission_id "
            "WHERE r.code = 'sme' AND p.code = 'organisation.view'"
        ),
        r"missing role-permission mappings \[\('sme', 'organisation.view'\)\]",
    ),
    "re-granted mapping": (_regrant, r"mappings modified \(granted by a user\)"),
    "modified permission": (
        lambda db: db.run(
            "UPDATE access_permission SET description = 'Edited' WHERE code = 'designations.manage'"
        ),
        r"permission designations.manage was modified",
    ),
    "other reference": (
        lambda db: db.run(
            "UPDATE access_role SET assign_permission_id = "
            "(SELECT id FROM access_permission WHERE code = 'organisation.view') WHERE code = 'sme'"
        ),
        r"access_role.assign_permission_id refer to these permissions",
    ),
}


@pytest.mark.parametrize("case", list(DOWNGRADE_0007_CASES))
def test_0007_downgrade_refuses_changed_permission_data(mdb: MigrationDb, case: str) -> None:
    # Start at 0007 itself (as the other revision tests do): the harness runs a
    # multi-revision downgrade in one transaction, so a refusal below later revisions
    # would mix their committed DDL with a rolled-back version row.
    mdb.migrate("downgrade", "0007")
    change, message = DOWNGRADE_0007_CASES[case]
    change(mdb)
    mappings_before = mdb.org_mappings()

    with pytest.raises(RuntimeError, match=message):
        mdb.migrate("downgrade", "0006")

    assert mdb.version() == "0007"
    assert mdb.org_permissions() == 5
    assert mdb.org_mappings() == mappings_before  # nothing deleted, including the extra row


UPGRADE_0007_CASES: dict[str, tuple[str, str]] = {
    "missing role": (
        "UPDATE access_role SET code = 'sme_renamed' WHERE code = 'sme'",
        r"missing roles \['sme'\]",
    ),
    "existing permission": (
        "INSERT INTO access_permission (code, description, is_privileged, created_at) "
        "VALUES ('organisation.view', 'Pre-existing', 0, NOW(6))",
        r"permission codes already exist \['organisation.view'\]",
    ),
}


@pytest.mark.parametrize("case", list(UPGRADE_0007_CASES))
def test_0007_upgrade_refuses_when_the_seed_cannot_be_established(
    mdb: MigrationDb, case: str
) -> None:
    mdb.migrate("downgrade", "0006")
    setup, message = UPGRADE_0007_CASES[case]
    mdb.run(setup)

    with pytest.raises(RuntimeError, match=message):
        mdb.migrate("upgrade", "0007")

    assert mdb.version() == "0006"
    assert mdb.org_mappings() == 0  # no partial seed was kept


def test_0007_seed_verification_detects_an_incomplete_seed(mdb: MigrationDb) -> None:
    rev7 = load_revision("0007")
    assert mdb.check(rev7.seed_problems) == []
    mdb.run(
        "DELETE m FROM access_role_permission m JOIN access_role r ON r.id = m.access_role_id "
        "JOIN access_permission p ON p.id = m.access_permission_id "
        "WHERE p.code = 'responsibilities.manage'"
    )
    mdb.run("DELETE FROM access_permission WHERE code = 'responsibilities.manage'")
    problems = mdb.check(rev7.seed_problems)
    assert any("permissions present" in p for p in problems)
    assert any("missing role-permission mappings" in p for p in problems)


# --- 0005 ---------------------------------------------------------------------------------


def _add_department_under_purchase(db: MigrationDb) -> None:
    db.run(
        "INSERT INTO org_unit (public_id, code, name, unit_type_id, created_at, updated_at, "
        "version) SELECT UUID_TO_BIN(UUID()), 'TEST_DEPT', 'Test Dept', id, NOW(6), NOW(6), 1 "
        "FROM org_unit_type WHERE code = 'DEPARTMENT'"
    )
    db.run(
        "INSERT INTO org_unit_hierarchy (child_unit_id, parent_unit_id, created_at) "
        "SELECT c.id, p.id, NOW(6) FROM org_unit c, org_unit p "
        "WHERE c.code = 'TEST_DEPT' AND p.code = 'PURCHASE'"
    )


def _add_team_type_under_function(db: MigrationDb) -> None:
    db.run(
        "INSERT INTO org_unit_type (public_id, code, name, sort_order, allows_employee_assignment, "
        "is_active, parent_rule_mode, created_at, updated_at, version) "
        "VALUES (UUID_TO_BIN(UUID()), "
        "'TEST_TEAM', 'Test Team', 40, 1, 1, 'advisory', NOW(6), NOW(6), 1)"
    )
    db.run(
        "INSERT INTO org_unit_type_rule (child_type_id, parent_type_id, created_at) "
        "SELECT c.id, p.id, NOW(6) FROM org_unit_type c, org_unit_type p "
        "WHERE c.code = 'TEST_TEAM' AND p.code = 'FUNCTION'"
    )


DOWNGRADE_0005_CASES: dict[str, tuple[Callable[[MigrationDb], None], list[str]]] = {
    "code corrected": (
        lambda db: db.run("UPDATE org_unit SET code = 'OPS_RENAMED' WHERE code = 'OPERATION'"),
        [
            r"seeded function OPERATION \(01a1d85c-46d3-7cce-834b-a055ef122b53\) "
            r"was modified \(code\)"
        ],
    ),
    "name corrected through the application": (
        lambda db: db.run(
            "UPDATE org_unit SET name = 'Operations', version = version + 1 "
            "WHERE code = 'OPERATION'"
        ),
        [r"seeded function OPERATION .* was modified \(name, version\)"],
    ),
    "translation added": (
        lambda db: db.run(
            "INSERT INTO org_unit_translation (org_unit_id, locale, name) "
            "SELECT id, 'gu', 'ટેસ્ટ' FROM org_unit WHERE code = 'ACC_COM'"
        ),
        [r"1 row\(s\) in org_unit_translation.org_unit_id refer to seeded org_unit rows"],
    ),
    "child unit and hierarchy link": (
        _add_department_under_purchase,
        [
            r"org_unit_hierarchy.parent_unit_id refer to seeded org_unit rows",
            r"org_unit.unit_type_id refer to seeded org_unit_type rows",
        ],
    ),
    "unit type modified": (
        lambda db: db.run(
            "UPDATE org_unit_type SET parent_rule_mode = 'strict', version = 2 "
            "WHERE code = 'DEPARTMENT'"
        ),
        [r"seeded unit type DEPARTMENT was modified \(parent_rule_mode, version\)"],
    ),
    "rule from another type": (
        _add_team_type_under_function,
        [r"org_unit_type_rule \d+ is not a seeded rule", r"org_unit_type_rule.parent_type_id"],
    ),
}


@pytest.mark.parametrize("case", list(DOWNGRADE_0005_CASES))
def test_0005_downgrade_refuses_changed_or_referenced_baseline(mdb: MigrationDb, case: str) -> None:
    mdb.migrate("downgrade", "0005")
    change, messages = DOWNGRADE_0005_CASES[case]
    change(mdb)
    counts = {
        table: mdb.scalar(f"SELECT COUNT(*) FROM {table}")  # noqa: S608
        for table in (
            "org_unit",
            "org_unit_type",
            "org_unit_type_rule",
            "org_unit_translation",
            "org_unit_hierarchy",
        )
    }

    with pytest.raises(RuntimeError) as excinfo:
        mdb.migrate("downgrade", "0004")

    for message in messages:
        assert re.search(message, str(excinfo.value)), (message, str(excinfo.value))
    assert mdb.version() == "0005"
    assert mdb.seeded_functions() == 5  # found by fixed public_id even if the code changed
    for table, count in counts.items():
        assert mdb.scalar(f"SELECT COUNT(*) FROM {table}") == count, table  # noqa: S608


# --- 0004 and 0006 ----------------------------------------------------------------------

DOWNGRADE_0004_CASES: dict[str, tuple[str, str]] = {
    "location": (
        "INSERT INTO location (public_id, code, name, is_active, created_at, updated_at, version) "
        "VALUES (UUID_TO_BIN(UUID()), 'TEST_SITE', 'Test Site', 1, NOW(6), NOW(6), 1)",
        r"location has 1 row\(s\)",
    ),
    "unit type": (
        "INSERT INTO org_unit_type (public_id, code, name, sort_order, allows_employee_assignment, "
        "is_active, parent_rule_mode, created_at, updated_at, version) "
        "VALUES (UUID_TO_BIN(UUID()), "
        "'TEST_PLANT', 'Test Plant', 50, 1, 1, 'advisory', NOW(6), NOW(6), 1)",
        r"org_unit_type has 1 row\(s\)",
    ),
    "extra graph lock": (
        "INSERT INTO graph_lock (name, description) VALUES ('test_lock', 'Test')",
        r"graph_lock holds \['org_hierarchy', 'test_lock'\]",
    ),
}


@pytest.mark.parametrize("case", list(DOWNGRADE_0004_CASES))
def test_0004_downgrade_refuses_populated_organisation_tables(mdb: MigrationDb, case: str) -> None:
    mdb.migrate("downgrade", "0004")
    setup, message = DOWNGRADE_0004_CASES[case]
    mdb.run(setup)

    with pytest.raises(RuntimeError, match=message):
        mdb.migrate("downgrade", "0003")

    assert mdb.version() == "0004"
    for table in ("org_unit", "org_unit_type", "location", "graph_lock"):
        assert mdb.has_table(table), table


def test_0006_downgrade_refuses_populated_reference_tables(mdb: MigrationDb) -> None:
    mdb.migrate("downgrade", "0006")
    mdb.run(
        "INSERT INTO grade (public_id, code, name, is_active, created_at, updated_at, version) "
        "VALUES (UUID_TO_BIN(UUID()), 'TEST_G1', 'Test Grade', 1, NOW(6), NOW(6), 1)"
    )
    mdb.run(
        "INSERT INTO responsibility (public_id, code, name, is_active, created_at, updated_at, "
        "version) VALUES (UUID_TO_BIN(UUID()), 'TEST_R1', 'Test Duty', 1, NOW(6), NOW(6), 1)"
    )

    with pytest.raises(RuntimeError) as excinfo:
        mdb.migrate("downgrade", "0005")

    message = str(excinfo.value)
    assert "responsibility (1 row(s))" in message and "grade (1 row(s))" in message
    assert "designation (" not in message  # only the populated tables are named
    assert mdb.version() == "0006"
    assert mdb.scalar("SELECT COUNT(*) FROM grade") == 1
    assert mdb.has_table("designation_functional_role")


# --- CLI path: a refusal part-way through a multi-revision downgrade ---------------------


def test_cli_multi_step_downgrade_stops_consistently_at_the_refusing_revision(
    mdb: MigrationDb,
    monkeypatch: pytest.MonkeyPatch,
    integration_settings: IntegrationDatabaseSettings,
) -> None:
    """The real CLI path commits each revision separately on MySQL, so when 0005 refuses
    after 0007 and 0006 succeeded, the database is consistently at 0005."""
    mdb.run(
        "INSERT INTO org_unit_translation (org_unit_id, locale, name) "
        "SELECT id, 'bn', 'পরীক্ষা' FROM org_unit WHERE code = 'SALES_BD'"
    )
    settings = _cli_settings(integration_settings, mdb.name)
    monkeypatch.setattr(app_config, "get_settings", lambda: settings)

    with pytest.raises(RuntimeError, match="org_unit_translation"):
        command.downgrade(Config(str(BACKEND_DIR / "alembic.ini")), "0004")

    assert mdb.version() == "0005"
    assert not mdb.has_table("designation")  # 0006 completed and was committed
    assert mdb.org_permissions() == 0  # 0007 completed and was committed
    assert mdb.seeded_functions() == 5  # 0005 refused: baseline and translation kept
    assert mdb.scalar("SELECT COUNT(*) FROM org_unit_translation") == 1
