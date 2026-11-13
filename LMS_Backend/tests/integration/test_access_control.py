"""RBAC: permission enforcement, role-assignment guards and account administration."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.identity import AccessPermission, AccessRole
from app.services.identity.access_control import role_permission_codes
from app.services.identity.permissions import Permission
from tests.integration.helpers import STRONG_PASSWORD, csrf, login, make_user

pytestmark = pytest.mark.db

USERS = "/api/v1/admin/users"
LOGIN_PATH = "/api/v1/auth/login"


def _create(
    api: TestClient, token: str, login_id: str, roles: list[str] | None = None
) -> dict[str, Any]:
    body: dict[str, object] = {
        "login_id": login_id,
        "display_name": f"Created {login_id}",
        "temporary_password": "Temporary-Pass-2026",
    }
    if roles is not None:
        body["roles"] = roles
    response = api.post(USERS, json=body, headers=csrf(token))
    assert response.status_code == 201, response.text
    return dict(response.json())


# --- Seed consistency ---------------------------------------------------------------


def test_seeded_roles_and_permissions_match_the_design(db: Session) -> None:
    codes = set(db.scalars(select(AccessPermission.code)))
    assert {permission.value for permission in Permission} <= codes

    roles = {role.code: role for role in db.scalars(select(AccessRole))}
    assert set(roles) == {"employee", "supervisor", "hod", "sme", "hr_admin", "super_admin"}
    assert roles["super_admin"].is_api_assignable is False
    assert role_permission_codes(roles["super_admin"]) == codes
    hr = role_permission_codes(roles["hr_admin"])
    assert Permission.USER_ROLES_ASSIGN in hr
    assert Permission.USER_ROLES_ASSIGN_ADMIN not in hr
    assert Permission.ACCESS_ROLES_MANAGE not in hr
    privileged = set(
        db.scalars(select(AccessPermission.code).where(AccessPermission.is_privileged))
    )
    for code, role in roles.items():
        if code != "super_admin":
            assert not role_permission_codes(role) & privileged, code
    assert roles["hr_admin"].assign_permission is not None
    assert roles["hr_admin"].assign_permission.code == Permission.USER_ROLES_ASSIGN_ADMIN
    for code in ("employee", "sme", "supervisor", "hod"):
        role = roles[code]
        assert role.assign_permission is not None
        assert role.assign_permission.code == Permission.USER_ROLES_ASSIGN
        assert role_permission_codes(role) <= hr  # HR Admin may grant them


# --- Permission enforcement -------------------------------------------------------------


def test_anonymous_requests_to_admin_endpoints_get_401(api: TestClient) -> None:
    assert api.get(USERS).status_code == 401
    assert api.get("/api/v1/admin/audit-events").status_code == 401


def test_employee_is_denied_admin_endpoints_and_denial_is_audited(
    api: TestClient, db: Session
) -> None:
    employee = make_user(db, "emp.denied")
    login(api, "emp.denied")

    for path in (USERS, "/api/v1/admin/audit-events", "/api/v1/admin/access-roles"):
        response = api.get(path)
        assert response.status_code == 403, path
        assert response.json()["error"]["code"] == "forbidden"

    denials = list(
        db.scalars(
            select(AuditEvent).where(
                AuditEvent.event_type == "authorization.denied",
                AuditEvent.actor_user_id == employee.id,
            )
        )
    )
    assert len(denials) == 3


def test_designation_like_data_grants_nothing(api: TestClient, db: Session) -> None:
    # An account with no access role has no permissions at all.
    make_user(db, "no.roles", roles=())
    login(api, "no.roles")

    assert api.get("/api/v1/auth/me").json()["permissions"] == []
    assert api.get(USERS).status_code == 403


# --- Account administration ------------------------------------------------------------------


def test_hr_admin_creates_pending_account_with_forced_password_change(
    api: TestClient, db: Session
) -> None:
    make_user(db, "hr.creator", roles=("hr_admin",))
    token = login(api, "hr.creator")

    created = _create(api, token, "new.joiner")

    assert created["status"] == "pending_activation"
    assert created["password_must_change"] is True
    assert created["roles"] == ["employee"]
    assert "password" not in str(created).replace("password_must_change", "").replace(
        "password_changed_at", ""
    )
    pending = api.post(
        LOGIN_PATH, json={"login_id": "new.joiner", "password": "Temporary-Pass-2026"}
    )
    assert pending.status_code == 403  # not yet activated

    activated = api.post(f"{USERS}/{created['public_id']}/activate", json={}, headers=csrf(token))
    assert activated.status_code == 200
    assert activated.json()["status"] == "active"


def test_duplicate_login_ids_are_rejected_case_insensitively(api: TestClient, db: Session) -> None:
    make_user(db, "hr.dupes", roles=("hr_admin",))
    token = login(api, "hr.dupes")
    _create(api, token, "Dup.User")

    response = api.post(
        USERS,
        json={
            "login_id": "dup.user",
            "display_name": "Dup",
            "temporary_password": "Temporary-Pass-2026",
        },
        headers=csrf(token),
    )

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "login_id_taken"


def test_invalid_status_transition_is_rejected(api: TestClient, db: Session) -> None:
    make_user(db, "hr.transitions", roles=("hr_admin",))
    token = login(api, "hr.transitions")
    created = _create(api, token, "transition.user")

    response = api.post(f"{USERS}/{created['public_id']}/suspend", json={}, headers=csrf(token))

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invalid_status_transition"


def test_suspension_by_admin_revokes_target_sessions(
    api: TestClient, second_api: TestClient, db: Session
) -> None:
    make_user(db, "hr.suspender", roles=("hr_admin",))
    target = make_user(db, "emp.to.suspend")
    token = login(api, "hr.suspender")
    login(second_api, "emp.to.suspend")

    response = api.post(
        f"{USERS}/{target.public_id}/suspend", json={"reason": "Investigation"}, headers=csrf(token)
    )

    assert response.status_code == 200
    assert second_api.get("/api/v1/auth/me").status_code == 401


# --- Role-assignment guards ------------------------------------------------------------------


@pytest.mark.parametrize("role", ["employee", "sme", "supervisor", "hod"])
def test_hr_admin_can_grant_standard_roles(api: TestClient, db: Session, role: str) -> None:
    make_user(db, "hr.granter", roles=("hr_admin",))
    target = make_user(db, "emp.grantee", roles=())
    token = login(api, "hr.granter")

    response = api.post(
        f"{USERS}/{target.public_id}/roles", json={"role": role}, headers=csrf(token)
    )

    assert response.status_code == 200
    assert role in response.json()["roles"]


def test_hr_admin_cannot_grant_hr_admin_or_super_admin(api: TestClient, db: Session) -> None:
    make_user(db, "hr.limited", roles=("hr_admin",))
    target = make_user(db, "emp.ambitious")
    token = login(api, "hr.limited")

    hr = api.post(
        f"{USERS}/{target.public_id}/roles", json={"role": "hr_admin"}, headers=csrf(token)
    )
    sa = api.post(
        f"{USERS}/{target.public_id}/roles", json={"role": "super_admin"}, headers=csrf(token)
    )

    assert hr.status_code == 403 and hr.json()["error"]["code"] == "forbidden"
    assert sa.status_code == 403 and sa.json()["error"]["code"] == "role_not_assignable"
    assert api.get(f"{USERS}/{target.public_id}").json()["roles"] == ["employee"]


def test_super_admin_can_grant_hr_admin_but_never_super_admin_via_api(
    api: TestClient, db: Session
) -> None:
    make_user(db, "root.admin", roles=("super_admin",))
    target = make_user(db, "future.hr")
    token = login(api, "root.admin")

    hr = api.post(
        f"{USERS}/{target.public_id}/roles", json={"role": "hr_admin"}, headers=csrf(token)
    )
    sa = api.post(
        f"{USERS}/{target.public_id}/roles", json={"role": "super_admin"}, headers=csrf(token)
    )

    assert hr.status_code == 200
    assert sa.status_code == 403 and sa.json()["error"]["code"] == "role_not_assignable"


def test_nobody_can_change_their_own_roles(api: TestClient, db: Session) -> None:
    me = make_user(db, "hr.self", roles=("hr_admin",))
    token = login(api, "hr.self")

    grant = api.post(f"{USERS}/{me.public_id}/roles", json={"role": "sme"}, headers=csrf(token))
    revoke = api.delete(f"{USERS}/{me.public_id}/roles/hr_admin", headers=csrf(token))

    assert grant.status_code == revoke.status_code == 403
    assert grant.json()["error"]["code"] == "self_modification_forbidden"


def test_hr_admin_cannot_manage_a_more_privileged_account(api: TestClient, db: Session) -> None:
    make_user(db, "hr.junior", roles=("hr_admin",))
    root = make_user(db, "root.target", roles=("super_admin",))
    token = login(api, "hr.junior")

    reset = api.post(
        f"{USERS}/{root.public_id}/password-reset",
        json={"temporary_password": "Takeover-Attempt-99"},
        headers=csrf(token),
    )
    suspend = api.post(f"{USERS}/{root.public_id}/suspend", json={}, headers=csrf(token))

    assert reset.status_code == suspend.status_code == 403
    assert reset.json()["error"]["code"] == "insufficient_privilege"
    login(api, "root.target", STRONG_PASSWORD)  # password unchanged


def test_role_revocation_removes_permissions(
    api: TestClient, second_api: TestClient, db: Session
) -> None:
    make_user(db, "hr.revoker", roles=("hr_admin",))
    target = make_user(db, "emp.sme", roles=("employee", "sme"))
    token = login(api, "hr.revoker")
    login(second_api, "emp.sme")
    assert "learning_content.review" in second_api.get("/api/v1/auth/me").json()["permissions"]

    response = api.delete(f"{USERS}/{target.public_id}/roles/sme", headers=csrf(token))

    assert response.status_code == 200
    assert "learning_content.review" not in second_api.get("/api/v1/auth/me").json()["permissions"]


# --- Role-permission administration ---------------------------------------------------------


def test_only_super_admin_edits_role_permissions_and_privileged_ones_are_blocked(
    api: TestClient, second_api: TestClient, db: Session
) -> None:
    make_user(db, "hr.editor", roles=("hr_admin",))
    make_user(db, "root.editor", roles=("super_admin",))
    hr_token = login(api, "hr.editor")
    root_token = login(second_api, "root.editor")
    path = "/api/v1/admin/access-roles"

    hr_attempt = api.put(f"{path}/sme/permissions/team.learning.view", headers=csrf(hr_token))
    ok = second_api.put(f"{path}/sme/permissions/team.learning.view", headers=csrf(root_token))
    privileged = second_api.put(f"{path}/sme/permissions/settings.manage", headers=csrf(root_token))
    super_role = second_api.delete(
        f"{path}/super_admin/permissions/audit.view", headers=csrf(root_token)
    )

    assert hr_attempt.status_code == 403
    assert ok.status_code == 200 and "team.learning.view" in ok.json()["permissions"]
    assert privileged.status_code == 403
    assert privileged.json()["error"]["code"] == "privileged_permission"
    assert super_role.status_code == 403
    assert super_role.json()["error"]["code"] == "role_not_editable"
    event = db.scalars(
        select(AuditEvent).where(AuditEvent.event_type == "access_role.permission_granted")
    ).one()
    assert event.target_id == "sme"
