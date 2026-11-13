"""The test-schema rebuild must refuse an unexpected target BEFORE any destructive statement.

These tests use recording fakes (no database): connecting with a wrong account
for real is not possible safely - no other credentials exist for the test
database, and development credentials must never be used by tests.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import pytest
from alembic import command as alembic_command

from tests.support.database import UnsafeTestDatabaseError
from tests.support.schema_reset import drop_all_tables, quote_identifier, rebuild_test_schema

GOOD_IDENTITY = ("crescent_lms_test", "lms_test@127.0.0.1")


class _Result:
    def __init__(self, rows: list[tuple[Any, ...]]) -> None:
        self._rows = rows

    def one(self) -> tuple[Any, ...]:
        return self._rows[0]

    def all(self) -> list[tuple[Any, ...]]:
        return self._rows

    def scalars(self) -> list[Any]:
        return [row[0] for row in self._rows]


class RecordingConnection:
    """Answers the identity and information_schema queries; records every statement."""

    def __init__(
        self,
        identity: tuple[str, str] = GOOD_IDENTITY,
        foreign_keys: list[tuple[str, str]] | None = None,
        tables: list[str] | None = None,
    ) -> None:
        self.identity = identity
        self.foreign_keys = foreign_keys or []
        self.tables = tables or []
        self.statements: list[str] = []

    def execute(self, statement: object, *_args: object) -> _Result:
        sql = str(statement)
        self.statements.append(sql)
        if "CURRENT_USER()" in sql:
            return _Result([self.identity])
        if "REFERENTIAL_CONSTRAINTS" in sql:
            return _Result(list(self.foreign_keys))
        if "information_schema.TABLES" in sql:
            return _Result([(table,) for table in self.tables])
        return _Result([])

    def destructive(self) -> list[str]:
        return [s for s in self.statements if s.startswith(("ALTER", "DROP", "TRUNCATE", "DELETE"))]


class RecordingEngine:
    def __init__(self, connection: RecordingConnection) -> None:
        self.connection = connection

    @contextmanager
    def begin(self) -> Iterator[RecordingConnection]:
        yield self.connection

    @contextmanager
    def connect(self) -> Iterator[RecordingConnection]:
        yield self.connection


WRONG_IDENTITIES = [
    ("crescent_lms_test", "lms_app@127.0.0.1"),
    ("crescent_lms_test", "lms_migrator@127.0.0.1"),
    ("crescent_lms_test", "lms_test@%"),
    ("crescent_lms_dev", "lms_test@127.0.0.1"),
    ("crescent_lms_dev", "lms_app@127.0.0.1"),
]


@pytest.mark.parametrize("identity", WRONG_IDENTITIES)
def test_drop_all_tables_rejects_unexpected_identity_without_any_ddl(
    identity: tuple[str, str],
) -> None:
    connection = RecordingConnection(identity, foreign_keys=[("t", "fk_t")], tables=["t"])

    with pytest.raises(UnsafeTestDatabaseError):
        drop_all_tables(connection, "crescent_lms_test")  # type: ignore[arg-type]

    assert connection.statements == ["SELECT DATABASE(), CURRENT_USER()"]
    assert connection.destructive() == []


@pytest.mark.parametrize("identity", WRONG_IDENTITIES)
def test_rebuild_rejects_unexpected_identity_before_cleanup_or_migrations(
    identity: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    def must_not_run(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("Alembic must not run after a failed identity check")

    monkeypatch.setattr(alembic_command, "upgrade", must_not_run)
    monkeypatch.setattr(alembic_command, "downgrade", must_not_run)
    connection = RecordingConnection(identity, foreign_keys=[("t", "fk_t")], tables=["t"])

    with pytest.raises(UnsafeTestDatabaseError):
        rebuild_test_schema(RecordingEngine(connection), "crescent_lms_test")  # type: ignore[arg-type]

    assert connection.destructive() == []


@pytest.mark.parametrize("name", ["crescent_lms_dev", "other_lms_test", "crescent_lms"])
def test_rebuild_refuses_any_other_database_name_without_connecting(name: str) -> None:
    connection = RecordingConnection()

    with pytest.raises(UnsafeTestDatabaseError, match="only 'crescent_lms_test' may be reset"):
        rebuild_test_schema(RecordingEngine(connection), name)  # type: ignore[arg-type]

    assert connection.statements == []


def test_drop_all_tables_drops_foreign_keys_before_tables() -> None:
    connection = RecordingConnection(
        foreign_keys=[("user_access_role", "fk_user_access_role_access_role_id_access_role")],
        tables=["access_role", "user_access_role"],
    )

    drop_all_tables(connection, "crescent_lms_test")  # type: ignore[arg-type]

    assert connection.destructive() == [
        "ALTER TABLE `user_access_role` DROP FOREIGN KEY "
        "`fk_user_access_role_access_role_id_access_role`",
        "DROP TABLE `access_role`",
        "DROP TABLE `user_access_role`",
    ]
    assert not any("FOREIGN_KEY_CHECKS" in s for s in connection.statements)


def test_unexpected_identifiers_are_rejected_before_any_ddl() -> None:
    connection = RecordingConnection(tables=["fine_table", "bad`; DROP DATABASE x; --"])

    with pytest.raises(UnsafeTestDatabaseError, match="unexpected identifier"):
        drop_all_tables(connection, "crescent_lms_test")  # type: ignore[arg-type]

    assert connection.destructive() == []
    for bad in ["a-b", "a b", "a`b", "", "db.table"]:
        with pytest.raises(UnsafeTestDatabaseError):
            quote_identifier(bad)
    assert quote_identifier("audit_event") == "`audit_event`"
