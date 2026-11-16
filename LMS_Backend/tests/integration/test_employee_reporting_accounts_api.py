"""Reporting lines, account links, data quality and the Stage B user-list additions.
All employees and accounts are synthetic.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import AppError
from app.models.identity import AccountStatus, UserAccount
from app.services.identity.access_control import (
    active_grants,
    ensure_can_manage_account,
    load_permission_codes,
)
from app.services.identity.context import Actor
from tests.integration.employee_helpers import EmployeeClient, employee_admin, events_for
from tests.integration.helpers import csrf, login, make_user

pytestmark = pytest.mark.db


def _people(hr: EmployeeClient, *codes: str) -> list[dict[str, Any]]:
    return [
        hr.create(code, employment_status="active", date_of_joining="2025-01-01") for code in codes
    ]


def _manage(
    hr: EmployeeClient, employee: dict[str, Any], manager: dict[str, Any], start: str
) -> Any:
    return hr.post(
        f"/{employee['public_id']}/reporting",
        {"manager_id": manager["public_id"], "effective_from": start},
    )


# --- reporting lines -------------------------------------------------------------------------


def test_line_manager_change_keeps_history(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    worker, first, second = _people(hr, "RP-W", "RP-M1", "RP-M2")
    types = hr.get("/reporting-types")
    assert [t["code"] for t in types] == ["LINE_MANAGER"]  # the only seeded type
    _manage(hr, worker, first, "2026-01-01")
    changed = _manage(hr, worker, second, "2026-05-01")
    assert changed["manager"]["employee_code"] == "RP-M2"

    view = hr.get(f"/{worker['public_id']}/reporting", as_of="2026-03-01")
    assert [m["manager"]["employee_code"] for m in view["managers"]] == ["RP-M1"]
    assert [
        (h["manager"]["employee_code"], h["effective_from"], h["effective_to"])
        for h in view["history"]
    ] == [("RP-M1", "2026-01-01", "2026-05-01"), ("RP-M2", "2026-05-01", None)]
    reports = hr.get(f"/{second['public_id']}/reporting", as_of="2026-06-01")["direct_reports"]
    assert [r["employee"]["employee_code"] for r in reports] == ["RP-W"]
    assert (
        hr.get(f"/{worker['public_id']}", as_of="2026-06-01")["line_manager"]["employee_code"]
        == "RP-M2"
    )

    earlier = {"manager_id": first["public_id"], "effective_from": "2026-04-01"}
    assert hr.error("POST", f"/{worker['public_id']}/reporting", earlier, 409) == (
        "later_change_exists"
    )
    again = {"manager_id": second["public_id"], "effective_from": "2026-07-01"}
    assert hr.error("POST", f"/{worker['public_id']}/reporting", again, 422) == "no_change"
    event = events_for(db, worker["public_id"])[-1]
    assert event.event_type == "reporting_relationship.created"
    assert event.event_metadata is not None
    assert event.event_metadata["previous_manager_code"] == "RP-M1"

    ended = hr.post(
        f"/{worker['public_id']}/reporting/{changed['public_id']}/end",
        {"effective_to": "2026-09-01"},
        expect=200,
    )
    assert ended["effective_to"] == "2026-09-01"


def test_self_reporting_cycles_and_separated_managers_are_refused(
    api: TestClient, db: Session
) -> None:
    hr = employee_admin(api, db)
    a, b, c = _people(hr, "CY-A", "CY-B", "CY-C")
    path = f"/{a['public_id']}/reporting"
    assert hr.error("POST", path, {"manager_id": a["public_id"]}, 422) == "self_reporting"
    _manage(hr, a, b, "2026-01-01")  # A -> B
    _manage(hr, b, c, "2026-01-01")  # B -> C
    cycle = {"manager_id": a["public_id"], "effective_from": "2026-02-01"}
    assert hr.error("POST", f"/{c['public_id']}/reporting", cycle, 409) == "reporting_cycle"

    gone = hr.create(
        "CY-GONE",
        employment_status="separated",
        date_of_joining="2025-01-01",
        date_of_separation="2025-12-31",
    )
    body = {"manager_id": gone["public_id"], "effective_from": "2026-03-01"}
    assert hr.error("POST", f"/{c['public_id']}/reporting", body, 422) == "manager_separated"


def test_being_a_manager_grants_no_access(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    worker, boss = _people(hr, "NA-W", "NA-B")
    account = make_user(db, "na.boss.login")
    hr.send("PUT", f"/{boss['public_id']}/account", {"user_public_id": str(account.public_id)}, 200)
    _manage(hr, worker, boss, "2026-01-01")
    assert [grant.role.code for grant in active_grants(db, account.id)] == ["employee"]


# --- account links ---------------------------------------------------------------------------


def test_link_and_unlink_are_controlled_and_audited(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    person, other = _people(hr, "AC-1", "AC-2")
    first = make_user(db, "ac.first.login")
    second = make_user(db, "ac.second.login")
    path = f"/{person['public_id']}/account"
    linked = hr.send("PUT", path, {"user_public_id": str(first.public_id), "reason": "New"}, 200)
    assert [a["login_id"] for a in linked["accounts"]] == ["ac.first.login"]
    assert [e["event_type"] for e in linked["history"]] == ["employee_account.linked"]

    body = {"user_public_id": str(second.public_id)}
    assert hr.error("PUT", path, body, 409) == "employee_has_active_account"
    taken = {"user_public_id": str(first.public_id)}
    assert hr.error("PUT", f"/{other['public_id']}/account", taken, 409) == (
        "account_already_linked"
    )
    assert hr.error("PUT", path, taken, 422) == "no_change"
    wrong = {"user_public_id": str(second.public_id)}
    assert hr.error("POST", f"{path}/unlink", wrong, 409) == "account_not_linked"

    unlinked = hr.post(f"{path}/unlink", {"user_public_id": str(first.public_id)}, expect=200)
    assert unlinked["accounts"] == []
    assert [e["event_type"] for e in unlinked["history"]] == [
        "employee_account.unlinked",
        "employee_account.linked",
    ]
    db.refresh(first)
    assert first.status == "active"  # the account itself is untouched
    metadata = events_for(db, person["public_id"])[-1].event_metadata
    assert metadata is not None and metadata["login_id"] == "ac.first.login"
    assert not any("password" in key or "hash" in key for key in metadata)


def test_link_guards_reuse_stage_b_rules(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    person = _people(hr, "AG-1")[0]
    path = f"/{person['public_id']}/account"
    own = db.scalars(select(UserAccount).where(UserAccount.login_id == "emp.hr.admin")).one()
    assert hr.error("PUT", path, {"user_public_id": str(own.public_id)}, 403) == (
        "self_modification_forbidden"
    )
    admin = make_user(db, "ag.super.login", roles=("super_admin",))
    assert hr.error("PUT", path, {"user_public_id": str(admin.public_id)}, 403) == (
        "insufficient_privilege"
    )
    supervisor_api = TestClient(api.app, headers=dict(api.headers))
    from tests.integration.helpers import login

    make_user(db, "ag.viewer", roles=("supervisor",))
    token = login(supervisor_api, "ag.viewer")
    response = supervisor_api.put(
        f"/api/v1/employees/{person['public_id']}/account",
        json={"user_public_id": str(admin.public_id)},
        headers=csrf(token),
    )
    assert response.status_code == 403


def test_disabled_accounts_keep_their_link_but_cannot_be_reactivated_alongside_another(
    api: TestClient, db: Session
) -> None:
    hr = employee_admin(api, db)
    person = _people(hr, "DS-1")[0]
    old = make_user(db, "ds.old.login")
    new = make_user(db, "ds.new.login")
    path = f"/{person['public_id']}/account"
    hr.send("PUT", path, {"user_public_id": str(old.public_id)}, 200)
    disabled = hr.api.post(
        f"/api/v1/admin/users/{old.public_id}/disable", json={}, headers=csrf(hr.token)
    )
    assert disabled.status_code == 200, disabled.text
    both = hr.send("PUT", path, {"user_public_id": str(new.public_id)}, 200)
    assert sorted((a["login_id"], a["status"]) for a in both["accounts"]) == [
        ("ds.new.login", "active"),
        ("ds.old.login", "disabled"),
    ]
    reactivate = hr.api.post(
        f"/api/v1/admin/users/{old.public_id}/activate", json={}, headers=csrf(hr.token)
    )
    assert reactivate.status_code == 409, reactivate.text
    assert reactivate.json()["error"]["code"] == "employee_has_active_account"
    db.refresh(old)
    assert old.status == AccountStatus.DISABLED.value


def test_user_list_shows_links_and_filters_by_them(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    person = _people(hr, "UL-1")[0]
    account = make_user(db, "ul.linked.login")
    hr.send(
        "PUT", f"/{person['public_id']}/account", {"user_public_id": str(account.public_id)}, 200
    )

    def users(**params: bool) -> dict[str, Any]:
        response = hr.api.get("/api/v1/admin/users", params=params)
        assert response.status_code == 200, response.text
        return {item["login_id"]: item for item in response.json()["items"]}

    assert list(users(linked=True)) == ["ul.linked.login"]
    assert users(linked=True)["ul.linked.login"]["employee"] == {
        "public_id": person["public_id"],
        "employee_code": "UL-1",
        "full_name": "Test Person",
    }
    unlinked = users(linked=False)
    assert "ul.linked.login" not in unlinked and "emp.hr.admin" in unlinked
    assert unlinked["emp.hr.admin"]["employee"] is None
    detail = hr.api.get(f"/api/v1/admin/users/{account.public_id}").json()
    assert detail["employee"]["employee_code"] == "UL-1"


def test_linked_employee_is_hidden_from_account_viewers_without_employees_view(
    api: TestClient, db: Session
) -> None:
    """A role may be given user_accounts.view at runtime (Super Admin); without
    employees.view the employee code and name are not sent at all."""
    hr = employee_admin(api, db)
    person = _people(hr, "PV-1")[0]
    account = make_user(db, "pv.linked.login")
    hr.send(
        "PUT", f"/{person['public_id']}/account", {"user_public_id": str(account.public_id)}, 200
    )
    admin_api = TestClient(api.app, headers=dict(api.headers))
    make_user(db, "pv.super", roles=("super_admin",))
    admin_token = login(admin_api, "pv.super")
    granted = admin_api.put(
        "/api/v1/admin/access-roles/supervisor/permissions/user_accounts.view",
        headers=csrf(admin_token),
    )
    assert granted.status_code == 200, granted.text

    viewer_api = TestClient(api.app, headers=dict(api.headers))
    make_user(db, "pv.viewer", roles=("supervisor",))
    login(viewer_api, "pv.viewer")
    listed = viewer_api.get("/api/v1/admin/users", params={"limit": 100})
    assert listed.status_code == 200, listed.text
    rows = {item["login_id"]: item for item in listed.json()["items"]}
    assert rows["pv.linked.login"]["employee"] is None
    assert "PV-1" not in listed.text
    detail = viewer_api.get(f"/api/v1/admin/users/{account.public_id}")
    assert detail.status_code == 200 and detail.json()["employee"] is None
    # Callers who may view employees still see the link.
    seen = hr.api.get(f"/api/v1/admin/users/{account.public_id}").json()
    assert seen["employee"]["employee_code"] == "PV-1"


def test_user_list_can_offer_only_accounts_the_caller_may_manage(
    api: TestClient, db: Session
) -> None:
    hr = employee_admin(api, db)
    make_user(db, "mg.plain")
    make_user(db, "mg.peer", roles=("hr_admin",))
    make_user(db, "mg.super", roles=("super_admin",))

    def logins(**params: Any) -> set[str]:
        response = hr.api.get("/api/v1/admin/users", params={"limit": 100, **params})
        assert response.status_code == 200, response.text
        return {item["login_id"] for item in response.json()["items"]}

    everyone = logins()
    offered = logins(manageable=True)
    assert {"mg.plain", "mg.peer", "mg.super", "emp.hr.admin"} <= everyone
    assert {"mg.plain", "mg.peer"} <= offered
    assert "mg.super" not in offered  # holds permissions HR Admin lacks
    assert "emp.hr.admin" not in offered  # own account
    assert logins(manageable=True, linked=False) <= offered  # filters combine

    # The list filter agrees with the rule every change enforces.
    me = db.scalars(select(UserAccount).where(UserAccount.login_id == "emp.hr.admin")).one()
    actor = Actor(user_id=me.id, permissions=load_permission_codes(db, me.id))
    for account in db.scalars(select(UserAccount)):
        try:
            ensure_can_manage_account(db, actor, account)
            allowed = True
        except AppError:
            allowed = False
        assert (account.login_id in offered) == allowed, account.login_id


# --- data quality ----------------------------------------------------------------------------


def test_data_quality_reports_without_correcting(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    operation = hr.org.function("OPERATION")
    unknown = hr.create("DQ-1")  # no status, no joining date, no assignment, no manager
    complete, boss = _people(hr, "DQ-2", "DQ-3")
    designation = hr.org.post("/designations", {"code": "DQ_D", "title": "Test Clerk"})
    location = hr.org.post("/locations", {"code": "DQ_L", "name": "Test Site"})
    hr.assign(
        complete,
        operation,
        effective_from="2025-01-01",
        designation_id=designation["public_id"],
        location_id=location["public_id"],
    )
    hr.assign(boss, operation, effective_from="2025-01-01")
    _manage(hr, complete, boss, "2025-01-01")
    hr.post(
        f"/{boss['public_id']}/employment-status",
        {"version": boss["version"], "status": "on_leave"},
        expect=200,
    )

    report = hr.get("/data-quality", as_of="2026-06-01")
    assert report["counts"] == {
        "unknown_status": 1,
        "no_primary_assignment": 1,
        "missing_location": 1,
        "missing_designation": 1,
        "separated_with_active_account": 0,
        "manager_inactive": 1,
        "no_line_manager": 2,
        "incomplete_record": 1,
    }
    listed = hr.get("/data-quality", as_of="2026-06-01", check="no_line_manager", limit=1)
    assert [item["employee_code"] for item in listed["items"]] == ["DQ-1"]
    rest = hr.get(
        "/data-quality", as_of="2026-06-01", check="no_line_manager", cursor=listed["next_cursor"]
    )
    assert [item["employee_code"] for item in rest["items"]] == ["DQ-3"]
    inactive = hr.get("/data-quality", as_of="2026-06-01", check="manager_inactive")
    assert [item["employee_code"] for item in inactive["items"]] == ["DQ-2"]
    assert hr.api.get("/api/v1/employees/data-quality", params={"check": "nope"}).status_code == 422
    assert hr.get(f"/{unknown['public_id']}")["employment_status"] is None  # unchanged
