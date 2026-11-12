"""Shared test fixtures.

Tests never read LMS_Backend/.env and never connect to a real MySQL server.
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


@pytest.fixture(autouse=True)
def _isolate_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    """Remove any LMS_* variables from the real environment for each test."""
    for name in list(os.environ):
        if name.upper().startswith("LMS_"):
            monkeypatch.delenv(name, raising=False)


@pytest.fixture
def make_settings() -> SettingsFactory:
    def factory(**overrides: Any) -> Settings:
        values: dict[str, Any] = {"environment": "test", "log_format": "console"}
        values.update(overrides)
        return Settings(_env_file=None, **values)

    return factory


@pytest.fixture
def make_client(make_settings: SettingsFactory) -> Iterator[Callable[..., TestClient]]:
    """Build a TestClient for an app created with the given settings overrides.

    ``database`` may be passed to replace the app's Database (e.g. with a stub).
    """
    clients: list[TestClient] = []

    def factory(*, database: Database | None = None, **overrides: Any) -> TestClient:
        app: FastAPI = create_app(make_settings(**overrides))
        if database is not None:
            app.state.database = database
        client = TestClient(app)
        client.__enter__()  # run lifespan startup
        clients.append(client)
        return client

    yield factory
    for client in clients:
        client.__exit__(None, None, None)


@pytest.fixture
def client(make_client: Callable[..., TestClient]) -> TestClient:
    """Client for an app with no database configured (the Stage A default)."""
    return make_client()
