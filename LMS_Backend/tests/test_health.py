"""Liveness and readiness endpoint tests."""

from collections.abc import Callable
from datetime import datetime

from fastapi.testclient import TestClient

from app import __version__
from app.db.session import Database
from tests.conftest import DUMMY_DB

LIVE = "/api/v1/health/live"
READY = "/api/v1/health/ready"


class StubDatabase(Database):
    """Configured-looking database whose ping succeeds or fails on demand."""

    def __init__(self, *, fail: bool = False) -> None:
        super().__init__(None)
        self.fail = fail
        self.ping_count = 0

    @property
    def is_configured(self) -> bool:
        return True

    def ping(self) -> None:
        self.ping_count += 1
        if self.fail:
            raise ConnectionError("Access denied for user 'secret_user'@'db.internal'")


def test_liveness_reports_ok(client: TestClient) -> None:
    response = client.get(LIVE)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["service"] == "crescent-lms-api"
    assert body["version"] == __version__
    datetime.fromisoformat(body["timestamp"])


def test_liveness_does_not_touch_the_database(make_client: Callable[..., TestClient]) -> None:
    database = StubDatabase(fail=True)
    client = make_client(database=database)

    response = client.get(LIVE)

    assert response.status_code == 200
    assert database.ping_count == 0


def test_readiness_when_database_not_configured(client: TestClient) -> None:
    response = client.get(READY)

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["checks"]["database"]["status"] == "not_configured"


def test_readiness_when_database_reachable(make_client: Callable[..., TestClient]) -> None:
    client = make_client(database=StubDatabase())

    response = client.get(READY)

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"]["status"] == "ok"
    assert body["checks"]["database"]["duration_ms"] >= 0


def test_readiness_failure_does_not_leak_error_details(
    make_client: Callable[..., TestClient],
) -> None:
    client = make_client(database=StubDatabase(fail=True))

    response = client.get(READY)

    assert response.status_code == 503
    check = response.json()["checks"]["database"]
    assert check["status"] == "unavailable"
    assert "secret_user" not in response.text
    assert "db.internal" not in response.text


def test_readiness_with_unreachable_mysql_server(make_client: Callable[..., TestClient]) -> None:
    """Uses the real PyMySQL driver against a closed loopback port."""
    client = make_client(**DUMMY_DB)

    response = client.get(READY)

    assert response.status_code == 503
    assert response.json()["checks"]["database"]["status"] == "unavailable"
    assert DUMMY_DB["db_password"] not in response.text
    assert DUMMY_DB["db_user"] not in response.text


def test_responses_carry_request_id_and_security_headers(client: TestClient) -> None:
    response = client.get(LIVE)

    assert len(response.headers["X-Request-ID"]) == 32
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert response.headers["Cache-Control"] == "no-store"


def test_well_formed_incoming_request_id_is_preserved(client: TestClient) -> None:
    response = client.get(LIVE, headers={"X-Request-ID": "frontend-abc.123"})

    assert response.headers["X-Request-ID"] == "frontend-abc.123"


def test_malformed_incoming_request_id_is_replaced(client: TestClient) -> None:
    response = client.get(LIVE, headers={"X-Request-ID": "bad id\nwith newline"})

    assert response.headers["X-Request-ID"] != "bad id\nwith newline"
    assert len(response.headers["X-Request-ID"]) == 32
