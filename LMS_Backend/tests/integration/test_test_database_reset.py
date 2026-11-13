"""Regression: the test-database rebuild must be data-independent, repeatable and verified.

A browser E2E run once left synthetic role grants committed in crescent_lms_test.
The old reset (``downgrade base``) then failed on a foreign key (migration 0002
deletes the seeded roles) after its DDL had already dropped the audit triggers,
leaving a partial schema. These tests drive the real rebuild against
crescent_lms_test (as lms_test@127.0.0.1) and check the COMMITTED state after
every phase. They never drop or disable an audit trigger themselves.
"""

from datetime import timedelta

import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.context import RequestMeta
from app.db.types import utcnow
from app.models.audit import AuditOutcome
from app.services.audit_service import AuditEventType, record_audit_event
from app.services.identity import accounts, bootstrap, sessions, throttling
from app.services.identity.access_control import load_permission_codes
from app.services.identity.context import Actor
from tests.support.database import assert_connected_to
from tests.support.schema_reset import (
    AUDIT_TRIGGERS,
    PHASES,
    SchemaState,
    alembic_head,
    committed_state,
    model_tables,
    quote_identifier,
    rebuild_test_schema,
)

pytestmark = pytest.mark.db

STAGE_B_ROLES = 6
STAGE_B_PERMISSIONS = 17
META = RequestMeta(request_id="reset-regression", ip_address="127.0.0.1")


def _assert_clean_head(state: SchemaState) -> None:
    assert state.tables == model_tables()
    assert state.version == (alembic_head(),)
    assert state.triggers == AUDIT_TRIGGERS
    assert state.roles == STAGE_B_ROLES
    assert state.permissions == STAGE_B_PERMISSIONS
    assert state.accounts == 0


def _row_count(engine: Engine, name: str, table: str) -> int:
    with engine.connect() as connection:
        assert_connected_to(connection, name)
        statement = text(f"SELECT COUNT(*) FROM {quote_identifier(table)}")  # noqa: S608 - validated
        return int(connection.execute(statement).scalar_one())


def test_complete_reset_sequence_commits_and_verifies_every_phase(
    test_engine: Engine, test_database_name: str
) -> None:
    report = rebuild_test_schema(test_engine, test_database_name)

    assert tuple(report.phases) == PHASES
    cleanup = report.phases["cleanup"]
    assert cleanup.tables == frozenset() and cleanup.triggers == frozenset()

    upgraded = report.phases["upgrade"]
    assert upgraded.tables == model_tables()
    assert upgraded.version == (alembic_head(),)
    assert upgraded.triggers == AUDIT_TRIGGERS

    downgraded = report.phases["downgrade"]
    assert downgraded.tables == {"alembic_version"}
    assert downgraded.version == ()
    assert downgraded.triggers == frozenset()

    _assert_clean_head(report.phases["final_upgrade"])
    # Independent re-check of the committed state on a separate connection.
    assert committed_state(test_engine, test_database_name) == report.phases["final_upgrade"]


def test_reset_succeeds_despite_committed_browser_test_residue(
    test_engine: Engine, test_database_name: str, app_settings: Settings
) -> None:
    now = utcnow()
    with Session(bind=test_engine) as db:
        # Same leftovers a browser E2E run produces - committed, with triggers present.
        superadmin = bootstrap.create_initial_super_admin(
            db,
            app_settings,
            login_id="residue.superadmin",
            display_name="Residue Super Admin",
            email=None,
            password="Residue-Password-0001",
            operator="pytest",
            now=now,
        )
        actor = Actor(user_id=superadmin.id, permissions=load_permission_codes(db, superadmin.id))
        employee = accounts.create_account(
            db,
            app_settings,
            actor=actor,
            login_id="residue.employee",
            display_name="Residue Employee",
            email=None,
            temporary_password="Residue-Password-0002",
            role_codes=["employee"],
            meta=META,
            now=now,
        )
        sessions.start_session(db, app_settings, employee, META, now)
        keys = throttling.throttle_keys(
            app_settings, purpose="login", identifier="residue.employee", ip="127.0.0.1"
        )
        throttling.register_failure(db, app_settings, keys, now + timedelta(seconds=1))
        record_audit_event(
            db,
            event_type=AuditEventType.LOGIN_FAILED,
            outcome=AuditOutcome.FAILURE,
            meta=META,
            metadata={"reason": "residue"},
        )
        db.commit()

    for table, minimum in {
        "user_account": 2,
        "user_access_role": 2,
        "user_session": 1,
        "login_throttle": 1,
        "audit_event": 3,
    }.items():
        assert _row_count(test_engine, test_database_name, table) >= minimum, table
    assert committed_state(test_engine, test_database_name).triggers == AUDIT_TRIGGERS

    report = rebuild_test_schema(test_engine, test_database_name)

    _assert_clean_head(report.phases["final_upgrade"])
    for table in ("user_access_role", "user_session", "login_throttle", "audit_event"):
        assert _row_count(test_engine, test_database_name, table) == 0, table


def test_repeated_resets_are_idempotent(test_engine: Engine, test_database_name: str) -> None:
    first = rebuild_test_schema(test_engine, test_database_name)
    second = rebuild_test_schema(test_engine, test_database_name)

    _assert_clean_head(first.phases["final_upgrade"])
    _assert_clean_head(second.phases["final_upgrade"])
    assert first.phases == second.phases


def test_reset_heals_a_partially_built_schema(test_engine: Engine, test_database_name: str) -> None:
    # Simulate an interrupted reset: version row gone and one table missing.
    # (Audit triggers are deliberately left alone.)
    with test_engine.begin() as connection:
        assert_connected_to(connection, test_database_name)
        connection.execute(text("DELETE FROM alembic_version"))
        connection.execute(text("DROP TABLE login_throttle"))
    broken = committed_state(test_engine, test_database_name)
    assert "login_throttle" not in broken.tables
    assert broken.version == ()

    report = rebuild_test_schema(test_engine, test_database_name)

    _assert_clean_head(report.phases["final_upgrade"])
