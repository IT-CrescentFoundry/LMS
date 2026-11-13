"""Super Admin bootstrap and controlled grant/revoke commands."""

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import cli
from app.core.config import Settings
from app.models.audit import AuditEvent
from app.models.identity import AccountStatus, UserAccount
from app.services.identity.access_control import load_role_codes
from tests.integration.conftest import TransactionalDatabase
from tests.integration.helpers import login, make_user

pytestmark = pytest.mark.db

PASSWORD = "First-Super-Admin-Pass-2026"


def _passwords(*values: str) -> Callable[[str], str]:
    iterator: Iterator[str] = iter(values)
    return lambda _prompt: next(iterator)


def _run(
    argv: list[str],
    database: TransactionalDatabase,
    settings: Settings,
    *,
    confirm: str | None = None,
    passwords: tuple[str, ...] = (PASSWORD, PASSWORD),
    interactive: bool = True,
) -> int:
    return cli.main(
        argv,
        database=database,
        settings=settings,
        input_fn=lambda _prompt: confirm if confirm is not None else str(settings.db_name),
        password_fn=_passwords(*passwords),
        is_interactive=lambda: interactive,
        operator="test-operator",
    )


CREATE = ["create-super-admin", "--login-id", "root.first", "--display-name", "First Admin"]


def test_bootstrap_creates_active_super_admin_and_audits(
    database: TransactionalDatabase, app_settings: Settings, db: Session, api: TestClient
) -> None:
    assert _run(CREATE, database, app_settings) == 0

    account = db.scalars(select(UserAccount).where(UserAccount.login_id == "root.first")).one()
    assert account.status == AccountStatus.ACTIVE
    assert account.password_hash and account.password_hash.startswith("$argon2id$")
    assert PASSWORD not in account.password_hash
    assert load_role_codes(db, account.id) == ("super_admin",)
    event = db.scalars(
        select(AuditEvent).where(AuditEvent.event_type == "super_admin.bootstrapped")
    ).one()
    assert event.event_metadata == {
        "channel": "cli",
        "operator": "test-operator",
        "login_id": "root.first",
    }
    login(api, "root.first", PASSWORD)


def test_second_bootstrap_is_refused(
    database: TransactionalDatabase, app_settings: Settings, db: Session
) -> None:
    assert _run(CREATE, database, app_settings) == 0

    again = ["create-super-admin", "--login-id", "root.second", "--display-name", "Second"]
    assert _run(again, database, app_settings) == 1
    assert (
        db.scalars(select(UserAccount).where(UserAccount.login_id == "root.second")).first() is None
    )


def test_bootstrap_requires_interactive_terminal_and_confirmation(
    database: TransactionalDatabase, app_settings: Settings, db: Session
) -> None:
    assert _run(CREATE, database, app_settings, interactive=False) == 2
    assert _run(CREATE, database, app_settings, confirm="crescent_lms_dev") == 1
    assert _run(CREATE, database, app_settings, passwords=(PASSWORD, "different")) == 1
    assert _run(CREATE, database, app_settings, passwords=("short", "short")) == 1
    assert db.scalars(select(UserAccount)).first() is None


def test_grant_and_revoke_super_admin_never_removes_the_last_one(
    database: TransactionalDatabase, app_settings: Settings, db: Session
) -> None:
    assert _run(CREATE, database, app_settings) == 0
    second = make_user(db, "root.candidate")

    assert _run(["revoke-super-admin", "--login-id", "root.first"], database, app_settings) == 1
    assert _run(["grant-super-admin", "--login-id", "root.candidate"], database, app_settings) == 0
    assert "super_admin" in load_role_codes(db, second.id)
    assert _run(["revoke-super-admin", "--login-id", "root.first"], database, app_settings) == 0
    assert _run(["revoke-super-admin", "--login-id", "root.candidate"], database, app_settings) == 1
    recorded = {e.event_type for e in db.scalars(select(AuditEvent))}
    assert {"super_admin.granted", "super_admin.revoked"} <= recorded
