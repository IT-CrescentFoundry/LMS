"""Fixtures for database integration tests (marker ``db``).

Target: exactly ``crescent_lms_test`` as MySQL account ``lms_test@127.0.0.1``
(configured by LMS_TEST_DB_* in LMS_Backend/.env.test) — never the development
database. Once per test session the schema is rebuilt from scratch by
tests/support/schema_reset.py (cleanup, upgrade, downgrade, upgrade, each phase
verified), so leftovers from earlier runs cannot break the reset. Each test then
runs inside an outer transaction that is rolled back afterwards; application
commits become savepoint releases.
"""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import Database
from app.main import create_app
from tests.conftest import BASE_TEST_SETTINGS, TEST_ORIGIN
from tests.support.database import (
    IntegrationDatabaseSettings,
    assert_connected_to,
    assert_safe_test_target,
    development_database_name,
)
from tests.support.schema_reset import rebuild_test_schema


class TransactionalDatabase(Database):
    """Database bound to one connection whose outer transaction the test owns."""

    def __init__(self, connection: Connection) -> None:
        super().__init__(None)
        self._connection = connection

    @property
    def is_configured(self) -> bool:
        return True

    def session(self) -> Session:
        return Session(
            bind=self._connection,
            join_transaction_mode="create_savepoint",
            autoflush=False,
            expire_on_commit=False,
        )

    def ping(self) -> None:
        self._connection.execute(text("SELECT 1"))

    def dispose(self) -> None:
        pass


@pytest.fixture(scope="session")
def integration_settings() -> IntegrationDatabaseSettings:
    settings = IntegrationDatabaseSettings()
    if not settings.configured:
        pytest.skip(
            "Database integration tests skipped: LMS_Backend/.env.test "
            "(LMS_TEST_DB_*) is not configured."
        )
    return settings


@pytest.fixture(scope="session")
def test_database_name(integration_settings: IntegrationDatabaseSettings) -> str:
    return assert_safe_test_target(integration_settings, development_database_name())


@pytest.fixture(scope="session")
def test_engine(
    integration_settings: IntegrationDatabaseSettings, test_database_name: str
) -> Iterator[Engine]:
    engine = create_engine(
        integration_settings.url(),
        pool_pre_ping=True,
        connect_args={"connect_timeout": 5, "init_command": "SET time_zone = '+00:00'"},
    )
    try:
        rebuild_test_schema(engine, test_database_name)
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def db_connection(test_engine: Engine, test_database_name: str) -> Iterator[Connection]:
    connection = test_engine.connect()
    transaction = connection.begin()
    assert_connected_to(connection, test_database_name)
    try:
        yield connection
    finally:
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def database(db_connection: Connection) -> TransactionalDatabase:
    return TransactionalDatabase(db_connection)


@pytest.fixture
def db(database: TransactionalDatabase) -> Iterator[Session]:
    session = database.session()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def app_settings(integration_settings: IntegrationDatabaseSettings, tmp_path: Path) -> Settings:
    password = integration_settings.password
    assert password is not None
    values: dict[str, Any] = dict(BASE_TEST_SETTINGS)
    values.update(
        db_host=integration_settings.host,
        db_port=integration_settings.port,
        db_name=integration_settings.name,
        db_user=integration_settings.user,
        db_password=password.get_secret_value(),
        import_storage_dir=tmp_path / "imports",  # Stage D: never the real storage folder
    )
    return Settings(_env_file=None, **values)


def build_client(settings: Settings, database: TransactionalDatabase) -> TestClient:
    app = create_app(settings)
    app.state.database = database
    return TestClient(app, headers={"Origin": TEST_ORIGIN})


@pytest.fixture
def api(app_settings: Settings, database: TransactionalDatabase) -> Iterator[TestClient]:
    with build_client(app_settings, database) as client:
        yield client


@pytest.fixture
def second_api(app_settings: Settings, database: TransactionalDatabase) -> Iterator[TestClient]:
    """An independent browser (separate cookie jar) against the same transaction."""
    with build_client(app_settings, database) as client:
        yield client
