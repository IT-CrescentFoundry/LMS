"""Login, session restoration, expiry, revocation, logout and password change."""

import logging
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.types import utcnow
from app.models.identity import AccountStatus, UserSession
from tests.integration.helpers import (
    OTHER_PASSWORD,
    STRONG_PASSWORD,
    csrf,
    login,
    make_user,
)

pytestmark = pytest.mark.db

LOGIN = "/api/v1/auth/login"


def test_login_sets_secure_httponly_cookie_and_returns_no_secrets(
    api: TestClient, db: Session
) -> None:
    user = make_user(db, "emp.login")

    response = api.post(LOGIN, json={"login_id": "emp.login", "password": STRONG_PASSWORD})

    assert response.status_code == 200
    body = response.json()
    assert body["authenticated"] is True
    assert body["user"]["login_id"] == "emp.login"
    assert body["user"]["roles"] == ["employee"]
    assert "learning.own.view" in body["user"]["permissions"]
    assert body["csrf_token"]
    cookie = response.headers["set-cookie"]
    assert cookie.startswith("lms_session=")
    assert "HttpOnly" in cookie
    assert "SameSite=lax" in cookie
    assert "Path=/" in cookie
    token = cookie.split(";")[0].split("=", 1)[1]
    assert token not in response.text  # token only in the cookie
    for forbidden in ("password", "hash", STRONG_PASSWORD, user.password_hash or "-"):
        assert forbidden not in response.text.replace("password_must_change", "")
    stored = db.scalars(select(UserSession).where(UserSession.user_account_id == user.id)).one()
    assert stored.token_hash != token and len(stored.token_hash) == 64


def test_login_is_case_insensitive_for_login_id(api: TestClient, db: Session) -> None:
    make_user(db, "EMP0042")

    assert (
        api.post(LOGIN, json={"login_id": "emp0042", "password": STRONG_PASSWORD}).status_code
        == 200
    )


def test_wrong_password_and_unknown_user_get_identical_generic_errors(
    api: TestClient, db: Session
) -> None:
    make_user(db, "emp.generic")

    wrong = api.post(LOGIN, json={"login_id": "emp.generic", "password": "Wrong-Password-123"})
    unknown = api.post(LOGIN, json={"login_id": "no.such.user", "password": "Wrong-Password-123"})

    assert wrong.status_code == unknown.status_code == 401
    assert wrong.json()["error"]["code"] == unknown.json()["error"]["code"] == "invalid_credentials"
    assert wrong.json()["error"]["message"] == unknown.json()["error"]["message"]
    assert "set-cookie" not in wrong.headers


@pytest.mark.parametrize(
    "status", [AccountStatus.PENDING_ACTIVATION, AccountStatus.SUSPENDED, AccountStatus.DISABLED]
)
def test_inactive_accounts_cannot_sign_in(
    api: TestClient, db: Session, status: AccountStatus
) -> None:
    make_user(db, f"emp.{status.value}", status=status)

    correct = api.post(LOGIN, json={"login_id": f"emp.{status.value}", "password": STRONG_PASSWORD})
    wrong = api.post(LOGIN, json={"login_id": f"emp.{status.value}", "password": "Nope-Nope-1234"})

    assert correct.status_code == 403
    assert correct.json()["error"]["code"] == "account_inactive"
    # Status is only revealed to someone who knows the password.
    assert wrong.json()["error"]["code"] == "invalid_credentials"


def test_session_restoration_and_current_user(api: TestClient, db: Session) -> None:
    make_user(db, "emp.restore")
    token = login(api, "emp.restore")

    session = api.get("/api/v1/auth/session")
    me = api.get("/api/v1/auth/me")

    assert session.status_code == 200
    assert session.json()["authenticated"] is True
    assert session.json()["csrf_token"] == token  # stable for the session
    assert me.status_code == 200
    assert me.json()["login_id"] == "emp.restore"


def test_anonymous_session_status_and_me(api: TestClient) -> None:
    assert api.get("/api/v1/auth/session").json() == {
        "authenticated": False,
        "user": None,
        "csrf_token": None,
        "idle_expires_at": None,
        "absolute_expires_at": None,
    }
    response = api.get("/api/v1/auth/me")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthenticated"


def test_logout_revokes_the_server_side_session(api: TestClient, db: Session) -> None:
    make_user(db, "emp.logout")
    token = login(api, "emp.logout")
    cookie_value = api.cookies.get("lms_session")

    response = api.post("/api/v1/auth/logout", headers=csrf(token))

    assert response.status_code == 204
    assert "lms_session=" in response.headers["set-cookie"]
    assert api.get("/api/v1/auth/me").status_code == 401
    # Replaying the old cookie must not work either.
    api.cookies.clear()
    api.cookies.set("lms_session", cookie_value or "")
    assert api.get("/api/v1/auth/me").status_code == 401
    record = db.scalars(select(UserSession)).one()
    db.refresh(record)
    assert record.revoked_at is not None and record.revoked_reason == "logout"


def test_new_login_replaces_presented_session(api: TestClient, db: Session) -> None:
    make_user(db, "emp.fixation")
    login(api, "emp.fixation")
    first_cookie = api.cookies.get("lms_session")

    login(api, "emp.fixation")
    second_cookie = api.cookies.get("lms_session")

    assert first_cookie != second_cookie
    sessions = list(db.scalars(select(UserSession).order_by(UserSession.id)))
    for record in sessions:
        db.refresh(record)
    assert [s.revoked_reason for s in sessions] == ["replaced_by_login", None]
    # Replaying the first token alone must fail.
    api.cookies.clear()
    api.cookies.set("lms_session", first_cookie or "")
    assert api.get("/api/v1/auth/me").status_code == 401


@pytest.mark.parametrize("field", ["idle_expires_at", "absolute_expires_at"])
def test_expired_sessions_are_rejected(api: TestClient, db: Session, field: str) -> None:
    make_user(db, f"emp.{field[:4]}")
    login(api, f"emp.{field[:4]}")
    record = db.scalars(select(UserSession)).one()
    setattr(record, field, utcnow() - timedelta(seconds=1))
    db.commit()

    response = api.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert "lms_session=" in response.headers.get("set-cookie", "")
    assert api.get("/api/v1/auth/session").json()["authenticated"] is False


def test_activity_slides_the_idle_window(api: TestClient, db: Session) -> None:
    make_user(db, "emp.slide")
    login(api, "emp.slide")
    record = db.scalars(select(UserSession)).one()
    earlier = utcnow() - timedelta(minutes=10)
    record.last_seen_at = earlier
    record.idle_expires_at = earlier + timedelta(minutes=30)
    db.commit()

    assert api.get("/api/v1/auth/me").status_code == 200

    db.refresh(record)
    assert record.idle_expires_at > earlier + timedelta(minutes=30)
    assert record.idle_expires_at <= record.absolute_expires_at


def test_suspension_revokes_active_sessions(api: TestClient, db: Session) -> None:
    user = make_user(db, "emp.suspended.later")
    login(api, "emp.suspended.later")
    db.refresh(user)  # the login updated the row (optimistic-locking version)
    user.status = AccountStatus.SUSPENDED.value
    db.commit()

    assert api.get("/api/v1/auth/me").status_code == 401


def test_password_change_rotates_session_and_revokes_others(
    api: TestClient, second_api: TestClient, db: Session
) -> None:
    make_user(db, "emp.pwchange")
    token = login(api, "emp.pwchange")
    login(second_api, "emp.pwchange")
    old_cookie = api.cookies.get("lms_session")

    response = api.post(
        "/api/v1/auth/password",
        json={"current_password": STRONG_PASSWORD, "new_password": OTHER_PASSWORD},
        headers=csrf(token),
    )

    assert response.status_code == 200
    new_token = response.json()["csrf_token"]
    assert new_token != token
    assert api.cookies.get("lms_session") != old_cookie
    assert api.get("/api/v1/auth/me").status_code == 200
    assert second_api.get("/api/v1/auth/me").status_code == 401  # other device signed out
    assert api.post("/api/v1/auth/logout", headers=csrf(token)).status_code == 403  # old CSRF
    # Old password no longer works; new one does.
    assert (
        second_api.post(
            LOGIN, json={"login_id": "emp.pwchange", "password": STRONG_PASSWORD}
        ).status_code
        == 401
    )
    login(second_api, "emp.pwchange", OTHER_PASSWORD)


def test_password_change_validation(api: TestClient, db: Session) -> None:
    make_user(db, "emp.pwpolicy")
    token = login(api, "emp.pwpolicy")

    wrong_current = api.post(
        "/api/v1/auth/password",
        json={"current_password": "Not-The-Password-9", "new_password": OTHER_PASSWORD},
        headers=csrf(token),
    )
    weak = api.post(
        "/api/v1/auth/password",
        json={"current_password": STRONG_PASSWORD, "new_password": "short"},
        headers=csrf(token),
    )
    same = api.post(
        "/api/v1/auth/password",
        json={"current_password": STRONG_PASSWORD, "new_password": STRONG_PASSWORD},
        headers=csrf(token),
    )

    assert wrong_current.status_code == 400
    assert wrong_current.json()["error"]["code"] == "invalid_current_password"
    assert weak.status_code == 422
    assert weak.json()["error"]["details"][0]["type"] == "too_short"
    assert same.status_code == 422
    assert same.json()["error"]["details"][0]["type"] == "same_as_current"


def test_must_change_password_limits_access_until_changed(api: TestClient, db: Session) -> None:
    make_user(db, "hr.mustchange", roles=("hr_admin",), must_change=True)
    token = login(api, "hr.mustchange")

    assert api.get("/api/v1/auth/me").json()["password_must_change"] is True
    blocked = api.get("/api/v1/admin/users")
    assert blocked.status_code == 403
    assert blocked.json()["error"]["code"] == "password_change_required"

    changed = api.post(
        "/api/v1/auth/password",
        json={"current_password": STRONG_PASSWORD, "new_password": OTHER_PASSWORD},
        headers=csrf(token),
    )
    assert changed.status_code == 200
    assert api.get("/api/v1/admin/users").status_code == 200


def test_passwords_are_never_logged(
    api: TestClient, db: Session, caplog: pytest.LogCaptureFixture
) -> None:
    make_user(db, "emp.logs")
    caplog.set_level(logging.DEBUG)

    api.post(LOGIN, json={"login_id": "emp.logs", "password": "Wrong-Secret-Value-1"})
    token = login(api, "emp.logs")
    api.post(
        "/api/v1/auth/password",
        json={"current_password": STRONG_PASSWORD, "new_password": OTHER_PASSWORD},
        headers=csrf(token),
    )

    logged = caplog.text
    for secret in ("Wrong-Secret-Value-1", STRONG_PASSWORD, OTHER_PASSWORD, token):
        assert secret not in logged
