"""The migrated test database matches the models, and protections exist in MySQL."""

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Connection, text

from app.core.config import BACKEND_DIR
from app.db.base import Base

pytestmark = pytest.mark.db


def test_database_is_at_the_latest_revision(db_connection: Connection) -> None:
    script = ScriptDirectory.from_config(Config(str(BACKEND_DIR / "alembic.ini")))
    current = MigrationContext.configure(db_connection).get_current_heads()

    assert set(current) == set(script.get_heads())


def test_migrations_and_models_do_not_drift(db_connection: Connection) -> None:
    context = MigrationContext.configure(
        db_connection, opts={"compare_type": True, "compare_server_default": True}
    )

    assert compare_metadata(context, Base.metadata) == []


def test_audit_append_only_triggers_exist(
    db_connection: Connection, test_database_name: str
) -> None:
    rows = db_connection.execute(
        text(
            "SELECT TRIGGER_NAME, ACTION_TIMING, EVENT_MANIPULATION, ACTION_STATEMENT "
            "FROM information_schema.TRIGGERS "
            "WHERE TRIGGER_SCHEMA = :schema AND EVENT_OBJECT_TABLE = 'audit_event' "
            "ORDER BY TRIGGER_NAME"
        ),
        {"schema": test_database_name},
    ).all()

    assert [(name, timing, event) for name, timing, event, _ in rows] == [
        ("trg_audit_event_no_delete", "BEFORE", "DELETE"),
        ("trg_audit_event_no_update", "BEFORE", "UPDATE"),
    ]
    for *_identity, statement in rows:
        assert "SIGNAL SQLSTATE '45000'" in statement


def test_tables_use_utf8mb4(db_connection: Connection, test_database_name: str) -> None:
    collations = set(
        db_connection.execute(
            text(
                "SELECT DISTINCT TABLE_COLLATION FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = :schema AND TABLE_NAME <> 'alembic_version'"
            ),
            {"schema": test_database_name},
        ).scalars()
    )

    assert collations and all(c.startswith("utf8mb4") for c in collations)
