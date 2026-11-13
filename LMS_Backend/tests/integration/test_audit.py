"""Audit events: creation, transactional integrity, immutability and the read-only API."""

import json

import pytest
from fastapi.testclient import TestClient
from pymysql.err import MySQLError
from sqlalchemy import Connection, select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from app.core.context import RequestMeta
from app.db.types import utcnow
from app.models.audit import AuditEvent, AuditImmutableError, AuditOutcome
from app.services.audit_service import (
    AuditEventType,
    UnsafeAuditMetadataError,
    record_audit_event,
)
from app.services.identity.access_control import (
    get_role,
    grant_role,
    load_permission_codes,
    load_role_codes,
)
from app.services.identity.context import Actor
from tests.integration.helpers import OTHER_PASSWORD, STRONG_PASSWORD, csrf, login, make_user

pytestmark = pytest.mark.db

AUDIT = "/api/v1/admin/audit-events"


def _types(db: Session) -> list[str]:
    return [e.event_type for e in db.scalars(select(AuditEvent).order_by(AuditEvent.id))]


def test_security_events_are_recorded(api: TestClient, db: Session) -> None:
    make_user(db, "hr.audited", roles=("hr_admin",))
    target = make_user(db, "emp.audited", roles=())
    api.post("/api/v1/auth/login", json={"login_id": "hr.audited", "password": "Bad-Guess-1234"})
    token = login(api, "hr.audited")
    api.post(
        f"/api/v1/admin/users/{target.public_id}/roles", json={"role": "sme"}, headers=csrf(token)
    )
    token = api.post(
        "/api/v1/auth/password",
        json={"current_password": STRONG_PASSWORD, "new_password": OTHER_PASSWORD},
        headers=csrf(token),
    ).json()["csrf_token"]
    api.post("/api/v1/auth/logout", headers=csrf(token))

    recorded = _types(db)
    for expected in (
        "auth.login.failed",
        "auth.login.succeeded",
        "access_role.granted",
        "auth.password.changed",
        "auth.logout",
    ):
        assert expected in recorded
    login_event = db.scalars(
        select(AuditEvent).where(AuditEvent.event_type == "auth.login.succeeded")
    ).first()
    assert login_event is not None
    assert login_event.outcome == "success"
    assert login_event.request_id and login_event.source_ip and login_event.user_agent
    assert login_event.occurred_at.tzinfo is not None


def test_audit_never_contains_secrets(api: TestClient, db: Session) -> None:
    make_user(db, "emp.secrets")
    api.post("/api/v1/auth/login", json={"login_id": "emp.secrets", "password": "Typo-Secret-55"})
    api.post("/api/v1/auth/login", json={"login_id": "Typo-Secret-55", "password": "x"})
    token = login(api, "emp.secrets")
    cookie = api.cookies.get("lms_session") or ""

    dump = json.dumps(
        [
            [e.event_type, e.target_id, e.event_metadata, e.user_agent]
            for e in db.scalars(select(AuditEvent))
        ]
    )

    for secret in ("Typo-Secret-55", STRONG_PASSWORD, token, cookie):
        assert secret not in dump


def test_metadata_with_secret_like_keys_is_refused(db: Session) -> None:
    with pytest.raises(UnsafeAuditMetadataError):
        record_audit_event(
            db,
            event_type=AuditEventType.LOGIN_FAILED,
            outcome=AuditOutcome.FAILURE,
            meta=RequestMeta(),
            metadata={"details": {"password": "x"}},
        )


def test_audit_is_written_in_the_same_transaction_as_the_change(
    api: TestClient, db: Session
) -> None:
    make_user(db, "hr.atomic", roles=("hr_admin",))
    target = make_user(db, "emp.atomic")
    token = login(api, "hr.atomic")

    refused = api.post(
        f"/api/v1/admin/users/{target.public_id}/roles",
        json={"role": "hr_admin"},
        headers=csrf(token),
    )

    assert refused.status_code == 403
    assert "access_role.granted" not in _types(db)  # nothing half-recorded
    assert "authorization.denied" in _types(db)  # the refusal itself is recorded


def test_orm_cannot_modify_or_delete_audit_events(db: Session) -> None:
    event = record_audit_event(
        db, event_type=AuditEventType.LOGOUT, outcome=AuditOutcome.SUCCESS, meta=RequestMeta()
    )
    db.commit()

    event.outcome = "failure"
    with pytest.raises(AuditImmutableError):
        db.flush()
    db.rollback()

    db.delete(db.get(AuditEvent, event.id))
    with pytest.raises(AuditImmutableError):
        db.flush()
    db.rollback()


ER_SIGNAL_EXCEPTION = 1644  # MySQL error raised by SIGNAL SQLSTATE '45000'


def _rejected_by_trigger(connection: Connection, statement: str, params: dict[str, object]) -> str:
    """Run a statement that must be refused by an audit trigger; return the message."""
    savepoint = connection.begin_nested()
    with pytest.raises(DBAPIError) as excinfo:
        connection.execute(text(statement), params)
    savepoint.rollback()
    original = excinfo.value.orig
    assert isinstance(original, MySQLError)
    assert original.args[0] == ER_SIGNAL_EXCEPTION
    return str(original.args[1])


def test_triggers_allow_insert_but_reject_update_and_delete_for_a_dml_account(
    db_connection: Connection,
) -> None:
    """Raw SQL as the test account, which holds every privilege lms_app has
    (SELECT, INSERT, UPDATE, DELETE) and more: the triggers are the barrier."""
    privileges = set(
        db_connection.execute(
            text(
                "SELECT PRIVILEGE_TYPE FROM information_schema.SCHEMA_PRIVILEGES "
                "WHERE TABLE_SCHEMA = DATABASE()"
            )
        ).scalars()
    )
    assert {"SELECT", "INSERT", "UPDATE", "DELETE"} <= privileges

    # 1. INSERT succeeds.
    db_connection.execute(
        text(
            "INSERT INTO audit_event (public_id, occurred_at, event_type, outcome) "
            "VALUES (UNHEX(REPLACE(UUID(), '-', '')), UTC_TIMESTAMP(6), 'test.trigger', 'success')"
        )
    )
    event_id = db_connection.execute(text("SELECT LAST_INSERT_ID()")).scalar_one()
    params = {"id": event_id}

    # 2. UPDATE is rejected.
    message = _rejected_by_trigger(
        db_connection, "UPDATE audit_event SET outcome = 'failure' WHERE id = :id", params
    )
    assert message == "audit_event is append-only; updates are not permitted"

    # 3. DELETE is rejected.
    message = _rejected_by_trigger(db_connection, "DELETE FROM audit_event WHERE id = :id", params)
    assert message == "audit_event is append-only; deletes are not permitted"

    # The row is still there, unchanged.
    row = db_connection.execute(
        text("SELECT event_type, outcome FROM audit_event WHERE id = :id"), params
    ).one()
    assert tuple(row) == ("test.trigger", "success")


def test_successful_admin_action_and_its_audit_event_commit_together(
    api: TestClient, db: Session
) -> None:
    make_user(db, "hr.together", roles=("hr_admin",))
    target = make_user(db, "emp.together", roles=())
    token = login(api, "hr.together")

    response = api.post(
        f"/api/v1/admin/users/{target.public_id}/roles",
        json={"role": "sme"},
        headers=csrf(token),
    )

    assert response.status_code == 200
    request_id = response.headers["X-Request-ID"]
    event = db.scalars(
        select(AuditEvent).where(AuditEvent.event_type == "access_role.granted")
    ).one()
    assert event.target_id == str(target.public_id)
    assert event.request_id == request_id
    assert event.event_metadata == {"role": "sme"}
    assert "sme" in load_role_codes(db, target.id)


def test_rolled_back_change_leaves_no_audit_event(db: Session) -> None:
    target = make_user(db, "emp.rollback", roles=())
    actor = make_user(db, "hr.rollback", roles=("hr_admin",))
    before = len(_types(db))

    grant_role(
        db,
        actor=Actor(user_id=actor.id, permissions=load_permission_codes(db, actor.id)),
        target=target,
        role=get_role(db, "sme"),
        meta=RequestMeta(),
        now=utcnow(),
    )
    db.flush()
    assert "access_role.granted" in _types(db)  # visible inside the transaction
    db.rollback()

    assert len(_types(db)) == before
    assert "sme" not in load_role_codes(db, target.id)


def test_audit_api_lists_filters_and_paginates(api: TestClient, db: Session) -> None:
    make_user(db, "hr.reader", roles=("hr_admin",))
    for _ in range(3):
        api.post("/api/v1/auth/login", json={"login_id": "nobody", "password": "Bad-Guess-1234"})
    login(api, "hr.reader")

    first = api.get(AUDIT, params={"event_type": "auth.login.failed", "limit": 2})
    assert first.status_code == 200
    page = first.json()
    assert len(page["items"]) == 2 and page["next_cursor"]
    assert all(item["event_type"] == "auth.login.failed" for item in page["items"])
    second = api.get(
        AUDIT, params={"event_type": "auth.login.failed", "limit": 2, "cursor": page["next_cursor"]}
    ).json()
    assert len(second["items"]) == 1 and second["next_cursor"] is None
    ids = {item["event_id"] for item in page["items"] + second["items"]}
    assert len(ids) == 3
    assert api.get(AUDIT, params={"cursor": "%%%"}).status_code == 422
    assert "audit.events.viewed" in _types(db)


def test_audit_api_has_no_write_methods(api: TestClient, db: Session) -> None:
    make_user(db, "root.writer", roles=("super_admin",))
    token = login(api, "root.writer")

    for method in ("post", "put", "patch", "delete"):
        response = getattr(api, method)(AUDIT, headers=csrf(token))
        assert response.status_code == 405, method
