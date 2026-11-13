"""Rebuild the dedicated test schema (``crescent_lms_test``) from scratch.

Why not just ``alembic downgrade base``? Downgrades delete seeded rows, so any
committed leftovers that reference them (for example role grants left by a
browser test run) make the downgrade fail part-way. MySQL DDL is not
transactional, so such a failure leaves a half-reset schema.

The rebuild therefore never depends on leftover data:

1. **cleanup**        drop every foreign key, then every table, in the verified test
                      schema (triggers go with their tables);
2. **upgrade**        ``alembic upgrade head`` on the empty schema;
3. **downgrade**      ``alembic downgrade base`` (keeps downgrade coverage, always on
                      a clean schema);
4. **final_upgrade**  ``alembic upgrade head``.

Transaction lifecycle: each phase runs in its own ``engine.begin()`` block (the
same pattern the harness has always used for one Alembic command). The injected
connection is already inside that transaction, so Alembic neither begins nor
commits; ``engine.begin()`` commits when the phase ends. Nothing here commits
manually. After every phase the COMMITTED state is read on a new connection and
checked; any surprise raises :class:`SchemaResetError`, so no test ever runs on a
partial schema. Because every rebuild starts with the cleanup, a rebuild that
failed half-way is repaired by the next one.

Every connection is checked with :func:`assert_connected_to` (database
``crescent_lms_test``, account ``lms_test@127.0.0.1``) before anything else runs
on it. Foreign-key checks are never disabled, and nothing here touches any
database other than the verified test schema.
"""

import re
from collections.abc import Callable
from dataclasses import dataclass, field

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import Connection, Engine, text

import app.models  # noqa: F401  (registers every model on Base.metadata)
from app.core.config import BACKEND_DIR
from app.db.base import Base
from tests.support.database import (
    REQUIRED_TEST_DATABASE_NAME,
    UnsafeTestDatabaseError,
    assert_connected_to,
)

ALEMBIC_INI = BACKEND_DIR / "alembic.ini"
VERSION_TABLE = "alembic_version"
AUDIT_TRIGGERS = frozenset({"trg_audit_event_no_update", "trg_audit_event_no_delete"})
PHASES = ("cleanup", "upgrade", "downgrade", "final_upgrade")
_IDENTIFIER = re.compile(r"^[A-Za-z0-9_]+$")


class SchemaResetError(RuntimeError):
    """The test schema did not reach the expected state after a rebuild phase."""


@dataclass(frozen=True)
class SchemaState:
    """Committed state of the test schema, as seen from a new connection."""

    tables: frozenset[str]
    version: tuple[str, ...]
    triggers: frozenset[str]
    roles: int | None
    permissions: int | None
    accounts: int | None


@dataclass
class ResetReport:
    phases: dict[str, SchemaState] = field(default_factory=dict)


def quote_identifier(name: str) -> str:
    """Backtick-quote a table/constraint name, refusing anything unexpected."""
    if not _IDENTIFIER.fullmatch(name):
        raise UnsafeTestDatabaseError(f"Refusing to use unexpected identifier {name!r}.")
    return f"`{name}`"


def drop_all_tables(connection: Connection, expected_name: str) -> None:
    """Drop every foreign key, then every base table, in the verified test schema.

    The identity check runs first on this connection; every identifier is
    validated before the first DDL statement is executed.
    """
    assert_connected_to(connection, expected_name)
    foreign_keys = connection.execute(
        text(
            "SELECT TABLE_NAME, CONSTRAINT_NAME FROM information_schema.REFERENTIAL_CONSTRAINTS "
            "WHERE CONSTRAINT_SCHEMA = DATABASE() ORDER BY TABLE_NAME, CONSTRAINT_NAME"
        )
    ).all()
    tables = list(
        connection.execute(
            text(
                "SELECT TABLE_NAME FROM information_schema.TABLES WHERE TABLE_SCHEMA = DATABASE() "
                "AND TABLE_TYPE = 'BASE TABLE' ORDER BY TABLE_NAME"
            )
        ).scalars()
    )
    statements = [
        f"ALTER TABLE {quote_identifier(table)} DROP FOREIGN KEY {quote_identifier(constraint)}"
        for table, constraint in foreign_keys
    ] + [f"DROP TABLE {quote_identifier(table)}" for table in tables]
    for statement in statements:
        connection.execute(text(statement))


def _count(connection: Connection, table: str, tables: frozenset[str]) -> int | None:
    if table not in tables:
        return None
    return int(
        connection.execute(
            text(f"SELECT COUNT(*) FROM {quote_identifier(table)}")  # noqa: S608 - validated identifier
        ).scalar_one()
    )


def read_state(connection: Connection) -> SchemaState:
    tables = frozenset(
        connection.execute(
            text(
                "SELECT TABLE_NAME FROM information_schema.TABLES "
                "WHERE TABLE_SCHEMA = DATABASE() AND TABLE_TYPE = 'BASE TABLE'"
            )
        ).scalars()
    )
    version: tuple[str, ...] = ()
    if VERSION_TABLE in tables:
        version = tuple(
            connection.execute(text("SELECT version_num FROM alembic_version")).scalars()
        )
    triggers = frozenset(
        connection.execute(
            text(
                "SELECT TRIGGER_NAME FROM information_schema.TRIGGERS "
                "WHERE TRIGGER_SCHEMA = DATABASE()"
            )
        ).scalars()
    )
    return SchemaState(
        tables=tables,
        version=version,
        triggers=triggers,
        roles=_count(connection, "access_role", tables),
        permissions=_count(connection, "access_permission", tables),
        accounts=_count(connection, "user_account", tables),
    )


def committed_state(engine: Engine, expected_name: str) -> SchemaState:
    """Read the committed state on a separate connection (identity verified)."""
    with engine.connect() as connection:
        assert_connected_to(connection, expected_name)
        state = read_state(connection)
        connection.rollback()
    return state


def alembic_head() -> str:
    head = ScriptDirectory.from_config(Config(str(ALEMBIC_INI))).get_current_head()
    if head is None:
        raise SchemaResetError("No Alembic head revision found.")
    return head


def model_tables() -> frozenset[str]:
    return frozenset(Base.metadata.tables) | {VERSION_TABLE}


def _alembic_config(connection: Connection) -> Config:
    config = Config(str(ALEMBIC_INI))
    config.attributes["connection"] = connection
    return config


def _problems_at_head(state: SchemaState, head: str) -> list[str]:
    problems = []
    if state.tables != model_tables():
        problems.append(f"tables {sorted(state.tables)} != models {sorted(model_tables())}")
    if state.version != (head,):
        problems.append(f"alembic_version {state.version} != ({head!r},)")
    if state.triggers != AUDIT_TRIGGERS:
        problems.append(f"triggers {sorted(state.triggers)} != {sorted(AUDIT_TRIGGERS)}")
    return problems


def _check(phase: str, state: SchemaState, head: str) -> list[str]:
    if phase == "cleanup":
        return [] if not state.tables and not state.triggers else [f"leftover {state}"]
    if phase == "downgrade":
        problems = []
        if state.tables != {VERSION_TABLE}:
            problems.append(f"tables {sorted(state.tables)} != ['{VERSION_TABLE}']")
        if state.version:
            problems.append(f"alembic_version not empty: {state.version}")
        if state.triggers:
            problems.append(f"triggers still present: {sorted(state.triggers)}")
        return problems
    problems = _problems_at_head(state, head)
    if phase == "final_upgrade":
        if not state.roles or not state.permissions:
            problems.append(
                f"seed data missing (roles={state.roles}, permissions={state.permissions})"
            )
        if state.accounts != 0:
            problems.append(f"user accounts present: {state.accounts}")
    return problems


def rebuild_test_schema(engine: Engine, expected_name: str) -> ResetReport:
    """Rebuild the verified test schema; returns the committed state after each phase."""
    if expected_name != REQUIRED_TEST_DATABASE_NAME:
        raise UnsafeTestDatabaseError(
            f"Refusing to rebuild {expected_name!r}: "
            f"only {REQUIRED_TEST_DATABASE_NAME!r} may be reset."
        )
    head = alembic_head()
    actions: dict[str, Callable[[Connection], None]] = {
        "cleanup": lambda connection: drop_all_tables(connection, expected_name),
        "upgrade": lambda connection: command.upgrade(_alembic_config(connection), "head"),
        "downgrade": lambda connection: command.downgrade(_alembic_config(connection), "base"),
        "final_upgrade": lambda connection: command.upgrade(_alembic_config(connection), "head"),
    }
    report = ResetReport()
    for phase in PHASES:
        with engine.begin() as connection:
            assert_connected_to(connection, expected_name)
            actions[phase](connection)
        state = committed_state(engine, expected_name)
        problems = _check(phase, state, head)
        if problems:
            raise SchemaResetError(
                f"Test database rebuild failed after the {phase!r} phase: {'; '.join(problems)}. "
                "No tests were run. The next run starts again from a full cleanup."
            )
        report.phases[phase] = state
    return report
