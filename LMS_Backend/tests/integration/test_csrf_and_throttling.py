"""CSRF (session-bound token + origin) and database-backed login throttling."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models.identity import LoginThrottle
from tests.integration.conftest import TransactionalDatabase, build_client
from tests.integration.helpers import STRONG_PASSWORD, csrf, login, make_user

pytestmark = pytest.mark.db

LOGIN = "/api/v1/auth/login"


def test_state_change_without_csrf_token_is_rejected(api: TestClient, db: Session) -> None:
    make_user(db, "emp.csrf1")
    login(api, "emp.csrf1")

    missing = api.post("/api/v1/auth/logout")
    invalid = api.post("/api/v1/auth/logout", headers=csrf("forged-token-value"))

    assert missing.status_code == invalid.status_code == 403
    assert missing.json()["error"]["code"] == "csrf_failed"
    assert api.get("/api/v1/auth/me").status_code == 200  # still signed in


def test_csrf_token_of_another_session_is_rejected(
    api: TestClient, second_api: TestClient, db: Session
) -> None:
    make_user(db, "emp.csrf2")
    make_user(db, "emp.csrf3")
    login(api, "emp.csrf2")
    other_token = login(second_api, "emp.csrf3")

    response = api.post("/api/v1/auth/logout", headers=csrf(other_token))

    assert response.status_code == 403


def test_authenticated_request_from_untrusted_origin_is_rejected(
    api: TestClient, db: Session
) -> None:
    make_user(db, "emp.origin")
    token = login(api, "emp.origin")

    response = api.post(
        "/api/v1/auth/logout", headers={**csrf(token), "Origin": "https://evil.example"}
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "origin_not_allowed"


def test_identifier_throttling_locks_after_repeated_failures(api: TestClient, db: Session) -> None:
    make_user(db, "emp.throttle")
    for _ in range(5):
        response = api.post(LOGIN, json={"login_id": "emp.throttle", "password": "Bad-Guess-1234"})
        assert response.status_code == 401

    locked = api.post(LOGIN, json={"login_id": "emp.throttle", "password": STRONG_PASSWORD})

    assert locked.status_code == 429
    assert locked.json()["error"]["code"] == "too_many_attempts"


def test_unknown_identifiers_are_throttled_the_same_way(api: TestClient) -> None:
    for _ in range(5):
        api.post(LOGIN, json={"login_id": "ghost.user", "password": "Bad-Guess-1234"})

    response = api.post(LOGIN, json={"login_id": "ghost.user", "password": "Bad-Guess-1234"})

    assert response.status_code == 429


def test_successful_login_resets_identifier_counter(api: TestClient, db: Session) -> None:
    make_user(db, "emp.reset")
    for _ in range(4):
        api.post(LOGIN, json={"login_id": "emp.reset", "password": "Bad-Guess-1234"})
    login(api, "emp.reset")

    for _ in range(4):
        api.post(LOGIN, json={"login_id": "emp.reset", "password": "Bad-Guess-1234"})

    assert login(api, "emp.reset")  # 4 + 4 failures, but reset in between


@pytest.fixture
def strict_ip_api(app_settings: Settings, database: TransactionalDatabase) -> Iterator[TestClient]:
    settings = app_settings.model_copy(update={"login_max_failures_per_ip": 3})
    with build_client(settings, database) as client:
        yield client


def test_ip_throttling_limits_password_spraying(strict_ip_api: TestClient, db: Session) -> None:
    make_user(db, "emp.spray")
    for name in ("a.one", "b.two", "c.three"):
        strict_ip_api.post(LOGIN, json={"login_id": name, "password": "Spray-Guess-1234"})

    response = strict_ip_api.post(
        LOGIN, json={"login_id": "emp.spray", "password": STRONG_PASSWORD}
    )

    assert response.status_code == 429


def test_throttle_table_stores_no_raw_identifiers(api: TestClient, db: Session) -> None:
    api.post(LOGIN, json={"login_id": "raw.identifier.check", "password": "Bad-Guess-1234"})

    rows = list(db.scalars(select(LoginThrottle)))

    assert {row.scope for row in rows} == {"identifier", "ip"}
    for row in rows:
        assert "raw.identifier.check" not in row.key_hash
        assert len(row.key_hash) == 64
