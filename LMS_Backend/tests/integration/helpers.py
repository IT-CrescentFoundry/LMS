"""Helpers for integration tests. All accounts and passwords are synthetic."""

from collections.abc import Sequence

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.context import RequestMeta
from app.core.security.passwords import hash_password
from app.db.types import utcnow
from app.models.identity import AccountStatus, UserAccount
from app.services.identity.access_control import get_role, grant_role

STRONG_PASSWORD = "Molten-Iron-Pours-At-Dawn-42"
OTHER_PASSWORD = "Sand-Moulds-Cool-Slowly-77"


def make_user(
    db: Session,
    login_id: str,
    *,
    roles: Sequence[str] = ("employee",),
    password: str | None = STRONG_PASSWORD,
    status: AccountStatus = AccountStatus.ACTIVE,
    must_change: bool = False,
) -> UserAccount:
    now = utcnow()
    account = UserAccount(
        login_id=login_id,
        display_name=f"Test {login_id}",
        password_hash=hash_password(password) if password else None,
        password_created_at=now if password else None,
        password_changed_at=now if password else None,
        password_must_change=must_change,
        status=status.value,
        status_changed_at=now,
        activated_at=now if status is AccountStatus.ACTIVE else None,
    )
    db.add(account)
    db.flush()
    for code in roles:
        grant_role(
            db,
            actor=None,
            target=account,
            role=get_role(db, code),
            meta=RequestMeta(),
            now=now,
            audit=False,
        )
    db.commit()
    return account


def login(client: TestClient, login_id: str, password: str = STRONG_PASSWORD) -> str:
    """Sign in and return the CSRF token."""
    response = client.post("/api/v1/auth/login", json={"login_id": login_id, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["csrf_token"]
    assert isinstance(token, str) and token
    return token


def csrf(token: str) -> dict[str, str]:
    return {"X-CSRF-Token": token}
