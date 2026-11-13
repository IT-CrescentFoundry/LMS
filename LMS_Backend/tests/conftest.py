"""Shared test fixtures.

Unit tests never read LMS_Backend/.env and never connect to a real MySQL server.
Database integration tests (``tests/integration``, marker ``db``) use only the
dedicated test database configured by ``LMS_TEST_DB_*`` (see tests/support/database.py).
All values below are dummies; no real employee data or credentials are used.
"""

import os
from collections.abc import Callable, Iterator
from typing import Any

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.db.session import Database
from app.main import create_app

SettingsFactory = Callable[..., Settings]

# TestClient's base URL; used as the trusted origin for state-changing requests.
TEST_ORIGIN = "http://testserver"
TEST_SECRET_KEY = "unit-test-secret-key-0123456789-abcdefghijklmnopqrstuvwxyz"

# Dummy database settings. Port 1 on loopback is used wherever a "real but
# unreachable" server is needed, so no test can reach the local MySQL service.
DUMMY_DB: dict[str, Any] = {
    "db_host": "127.0.0.1",
    "db_port": 1,
    "db_name": "lms_test_dummy",
    "db_user": "lms_test_user",
    "db_password": "not-a-real-password",
    "db_connect_timeout_seconds": 1,
}
DUMMY_MIGRATION: dict[str, Any] = {
    "migration_db_user": "lms_test_migrator",
    "migration_db_password": "not-a-real-migration-password",
}

# Settings every test app needs (no .env is ever read in tests).
BASE_TEST_SETTINGS: dict[str, Any] = {
    "environment": "test",
    "log_format": "console",
    "secret_key": TEST_SECRET_KEY,
    "trusted_origins": [TEST_ORIGIN],
    "session_cookie_secure": False,  # TestClient talks plain http
}


@pytest.fixture(autouse=True)
def _isolate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove any LMS_* variables from the real environment for each test."""
    for name in list(os.environ):
        if name.upper().startswith("LMS_"):
            monkeypatch.delenv(name, raising=False)


@pytest.fixture
def make_settings() -> SettingsFactory:
    def factory(**overrides: Any) -> Settings:
        values: dict[str, Any] = dict(BASE_TEST_SETTINGS)
        values.update(overrides)
        return Settings(_env_file=None, **values)

    return factory


@pytest.fixture
def make_client(make_settings: SettingsFactory) -> Iterator[Callable[..., TestClient]]:
    """Build a TestClient for an app created with the given settings overrides.

    ``database`` may be passed to replace the app's Database (e.g. with a stub).
    Every request carries the trusted ``Origin`` header, as a browser would.
    """
    clients: list[TestClient] = []

    def factory(*, database: Database | None = None, **overrides: Any) -> TestClient:
        app: FastAPI = create_app(make_settings(**overrides))
        if database is not None:
            app.state.database = database
        client = TestClient(app, headers={"Origin": TEST_ORIGIN})
        client.__enter__()  # run lifespan startup
        clients.append(client)
        return client

    yield factory
    for client in clients:
        client.__exit__(None, None, None)


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    """Client for an app with no database configured."""
    return make_client()
