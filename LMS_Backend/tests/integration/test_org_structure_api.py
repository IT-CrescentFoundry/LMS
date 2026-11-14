"""Organisation structure API: unit types, units, hierarchy history, locations.

All unit names below are synthetic test data, not Crescent Foundry's real structure.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.organisation import OrgUnit, OrgUnitHierarchy
from tests.integration.helpers import csrf, make_user
from tests.integration.org_helpers import ORG, OrgClient, org_admin, org_user

pytestmark = pytest.mark.db


def _events(db: Session, event_type: str, target_id: str | None = None) -> list[AuditEvent]:
    statement = select(AuditEvent).where(AuditEvent.event_type == event_type)
    if target_id is not None:
        statement = statement.where(AuditEvent.target_id == target_id)
    return list(db.scalars(statement.order_by(AuditEvent.id)))


def _meta(event: AuditEvent) -> dict[str, Any]:
    assert event.event_metadata is not None
    return event.event_metadata


def _team_type(org: OrgClient) -> dict[str, Any]:
    return dict(org.post("/unit-types", {"code": "test_team", "name": "Test Team"}))


# --- permissions --------------------------------------------------------------------------


def test_anonymous_requests_are_rejected(api: TestClient) -> None:
    assert api.get(f"{ORG}/units").status_code == 401
    assert api.get(f"{ORG}/tree").status_code == 401


def test_employee_cannot_view_or_change_the_structure(api: TestClient, db: Session) -> None:
    org = org_user(api, db, "org.employee", "employee")
    assert api.get(f"{ORG}/units").status_code == 403
    assert api.get(f"{ORG}/unit-types").status_code == 403
    assert org.error("POST", "/locations", {"code": "L1", "name": "Site"}, 403) == "forbidden"


def test_supervisor_can_view_but_not_change(api: TestClient, db: Session) -> None:
    org = org_user(api, db, "org.supervisor", "supervisor")
    assert len(org.get("/units")["items"]) == 5
    function = org.function("OPERATION")
    body = {"code": "T1", "name": "T", "unit_type_id": function["unit_type"]["public_id"]}
    assert org.error("POST", "/units", body, 403) == "forbidden"
    assert org.error("POST", "/unit-types", {"code": "X", "name": "X"}, 403) == "forbidden"
    denied = _events(db, "authorization.denied")
    assert denied and _meta(denied[-1])["required"] == ["organisation.manage"]


def test_writes_require_csrf_token(api: TestClient, db: Session) -> None:
    org_admin(api, db)
    response = api.post(f"{ORG}/locations", json={"code": "L1", "name": "Site"})
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "csrf_failed"


# --- listing ------------------------------------------------------------------------------


def test_list_tree_and_pagination_show_the_baseline(api: TestClient, db: Session) -> None:
    org = org_admin(api, db)
    first = org.get("/units", limit=2)
    assert [item["code"] for item in first["items"]] == ["ACC_COM", "HR_ADMIN_IT"]
    second = org.get("/units", limit=2, cursor=first["next_cursor"])
    third = org.get("/units", limit=2, cursor=second["next_cursor"])
    assert [item["code"] for item in second["items"]] == ["OPERATION", "PURCHASE"]
    assert [item["code"] for item in third["items"]] == ["SALES_BD"]
    assert third["next_cursor"] is None
    unit = first["items"][1]
    assert unit["name"] == "HR, Admin & IT"
    assert unit["parent"] is None and unit["path"] == [] and unit["status"] == "active"

    tree = org.get("/tree")
    assert len(tree["nodes"]) == 5
    assert all(node["parent_id"] is None for node in tree["nodes"])
    assert api.get(f"{ORG}/units", params={"cursor": "%%"}).status_code == 422


# --- unit types and rules ---------------------------------------------------------------


def test_unit_type_lifecycle_and_rules_are_audited(api: TestClient, db: Session) -> None:
    org = org_admin(api, db)
    team = org.post(
        "/unit-types",
        {"code": "test_team", "name": "Test Team", "translations": {"hi": "टीम"}},
    )
    assert team["code"] == "TEST_TEAM"
    assert team["allow_root"] is False and team["allowed_parent_types"] == []
    assert team["translations"] == {"hi": "टीम"}
    assert org.error("POST", "/unit-types", {"code": "TEST_TEAM", "name": "X"}, 409) == (
        "unit_type_code_taken"
    )

    department = org.unit_type("DEPARTMENT")
    ruled = org.send(
        "PUT",
        f"/unit-types/{team['public_id']}/parent-rules",
        {
            "version": team["version"],
            "allow_root": False,
            "parent_type_ids": [department["public_id"]],
        },
    )
    assert [item["code"] for item in ruled["allowed_parent_types"]] == ["DEPARTMENT"]
    assert ruled["version"] == team["version"] + 1

    stale = {"version": team["version"], "name": "Renamed"}
    assert org.error("PATCH", f"/unit-types/{team['public_id']}", stale, 409) == "version_conflict"
    updated = org.patch(
        f"/unit-types/{team['public_id']}",
        {"version": ruled["version"], "parent_rule_mode": "strict", "translations": {"hi": None}},
    )
    assert updated["parent_rule_mode"] == "strict" and updated["translations"] == {}

    events = _events(db, "org_unit_type.parent_rules_changed", team["public_id"])
    assert _meta(events[0]) == {"code": "TEST_TEAM", "from": [], "to": ["DEPARTMENT"]}
    changes = _meta(_events(db, "org_unit_type.updated", team["public_id"])[0])["changes"]
    assert changes["parent_rule_mode"] == {"from": "advisory", "to": "strict"}
    assert changes["translations"] == {"hi": {"from": "टीम", "to": None}}


def test_advisory_rules_warn_and_strict_rules_reject(api: TestClient, db: Session) -> None:
    org = org_admin(api, db)
    operation = org.function("OPERATION")

    sub = org.create_unit("OP_SUB", "Test Sub-function", "SUB_FUNCTION", operation["public_id"])
    assert sub["warnings"] == []
    direct = org.create_unit("OP_DEPT", "Test Department", "DEPARTMENT", operation["public_id"])
    assert direct["warnings"] == []  # Function -> Department is an allowed shortcut

    root_sub = org.create_unit("ROOT_SUB", "Rootless Sub-function", "SUB_FUNCTION")
    assert [w["code"] for w in root_sub["warnings"]] == ["type_rule_advisory"]
    created = _events(db, "org_unit.created", root_sub["unit"]["public_id"])[0]
    assert _meta(created)["warnings"] == ["type_rule_advisory"]

    sub_type = org.unit_type("SUB_FUNCTION")
    org.patch(
        f"/unit-types/{sub_type['public_id']}",
        {"version": sub_type["version"], "parent_rule_mode": "strict"},
    )
    body = {"code": "ROOT_SUB2", "name": "Another", "unit_type_id": sub_type["public_id"]}
    assert org.error("POST", "/units", body, 422) == "type_rule_violation"

    # A type without rules may go anywhere.
    _team_type(org)
    team = org.create_unit("FREE_TEAM", "Free Team", "TEST_TEAM", sub["unit"]["public_id"])
    assert team["warnings"] == []


# --- creation, codes and sibling names --------------------------------------------------


def test_codes_are_unique_case_insensitively_and_validated(api: TestClient, db: Session) -> None:
    org = org_admin(api, db)
    operation = org.function("OPERATION")
    org.create_unit("ops-maint", "Test Maintenance", "DEPARTMENT", operation["public_id"])
    dept = org.unit_type("DEPARTMENT")["public_id"]
    duplicate = {"code": "OPS-MAINT", "name": "Other", "unit_type_id": dept}
    assert org.error("POST", "/units", duplicate, 409) == "unit_code_taken"
    invalid = {"code": "has space", "name": "Other", "unit_type_id": dept}
    assert org.error("POST", "/units", invalid, 422) == "invalid_code"


def test_same_name_allowed_under_different_parents_only(api: TestClient, db: Session) -> None:
    org = org_admin(api, db)
    operation = org.function("OPERATION")["public_id"]
    purchase = org.function("PURCHASE")["public_id"]
    org.create_unit("OPS_M", "Test Maintenance", "DEPARTMENT", operation)
    org.create_unit("PUR_M", "Test Maintenance", "DEPARTMENT", purchase)  # different parent

    dept = org.unit_type("DEPARTMENT")["public_id"]
    clash = {"code": "OPS_M2", "name": "test maintenance", "unit_type_id": dept}
    assert org.error("POST", "/units", {**clash, "parent_id": operation}, 409) == (
        "sibling_name_taken"
    )
    # Root names are unique among roots too ("Operation" is a seeded root).
    function_type = org.unit_type("FUNCTION")["public_id"]
    root = {"code": "OPS_COPY", "name": "Operation", "unit_type_id": function_type}
    assert org.error("POST", "/units", root, 409) == "sibling_name_taken"


def test_child_cannot_start_before_its_parent(api: TestClient, db: Session) -> None:
    org = org_admin(api, db)
    operation = org.function("OPERATION")["public_id"]
    created = org.create_unit(
        "LATE_SUB", "Late Sub", "SUB_FUNCTION", operation, effective_from="2099-01-01"
    )["unit"]
    assert created["as_of"] == "2099-01-01"  # a future unit is shown from its start date
    assert created["status"] == "active" and created["parent"]["code"] == "OPERATION"
    today_view = org.unit(created["public_id"])
    assert today_view["status"] == "not_started" and today_view["parent"] is None

    dept = org.unit_type("DEPARTMENT")["public_id"]
    body = {
        "code": "EARLY",
        "name": "Early",
        "unit_type_id": dept,
        "parent_id": created["public_id"],
        "effective_from": "2098-06-01",
    }
    assert org.error("POST", "/units", body, 422) == "parent_not_active"
    body.pop("effective_from")  # an unrecorded start could be earlier than the parent's
    assert org.error("POST", "/units", body, 422) == "parent_not_active"


# --- moves and history ------------------------------------------------------------------


def test_move_keeps_history_and_as_of_views(api: TestClient, db: Session) -> None:
    org = org_admin(api, db)
    operation = org.function("OPERATION")["public_id"]
    purchase = org.function("PURCHASE")["public_id"]
    sub = org.create_unit(
        "MV_SUB", "Movable Sub", "SUB_FUNCTION", operation, effective_from="2026-01-01"
    )["unit"]
    dept = org.create_unit(
        "MV_DEPT", "Movable Dept", "DEPARTMENT", sub["public_id"], effective_from="2026-01-01"
    )["unit"]

    moved = org.post(
        f"/units/{sub['public_id']}/move",
        {"version": sub["version"], "new_parent_id": purchase, "effective_date": "2026-06-01"},
        expect=200,
    )
    assert moved["unit"]["parent"]["code"] == "PURCHASE"
    assert moved["unit"]["version"] == sub["version"] + 1

    before = org.unit(dept["public_id"], as_of="2026-03-01")
    after = org.unit(dept["public_id"], as_of="2026-07-01")
    assert [item["code"] for item in before["path"]] == ["OPERATION", "MV_SUB"]
    assert [item["code"] for item in after["path"]] == ["PURCHASE", "MV_SUB"]

    history = org.get(f"/units/{sub['public_id']}/history")
    assert [
        (p["parent"]["code"], p["effective_from"], p["effective_to"]) for p in history["placements"]
    ] == [("OPERATION", "2026-01-01", "2026-06-01"), ("PURCHASE", "2026-06-01", None)]
    event = _meta(_events(db, "org_unit.moved", sub["public_id"])[0])
    assert event["from_parent"] == "OPERATION" and event["to_parent"] == "PURCHASE"

    # Earlier than the latest placement change: refused (use corrections instead).
    stale = {"version": moved["unit"]["version"], "new_parent_id": operation}
    code = org.error(
        "POST", f"/units/{sub['public_id']}/move", {**stale, "effective_date": "2026-03-01"}, 409
    )
    assert code == "later_change_exists"
    same = {**stale, "new_parent_id": purchase, "effective_date": "2026-08-01"}
    assert org.error("POST", f"/units/{sub['public_id']}/move", same, 422) == "no_change"

    # Becoming a root later is a move as well.
    root = org.post(
        f"/units/{sub['public_id']}/move",
        {**stale, "new_parent_id": None, "effective_date": "2026-09-01"},
        expect=200,
    )
    assert root["unit"]["parent"] is None
    assert [w["code"] for w in root["warnings"]] == ["type_rule_advisory"]


def test_circular_hierarchy_is_rejected(api: TestClient, db: Session) -> None:
    org = org_admin(api, db)
    _team_type(org)
    a = org.create_unit("CY_A", "Cycle A", "TEST_TEAM", effective_from="2026-01-01")["unit"]
    b = org.create_unit(
        "CY_B", "Cycle B", "TEST_TEAM", a["public_id"], effective_from="2026-01-01"
    )["unit"]
    c = org.create_unit(
        "CY_C", "Cycle C", "TEST_TEAM", b["public_id"], effective_from="2026-01-01"
    )["unit"]

    move = {"version": a["version"], "effective_date": "2026-05-01"}
    for target in (c, b, a):
        body = {**move, "new_parent_id": target["public_id"]}
        assert org.error("POST", f"/units/{a['public_id']}/move", body, 422) == "hierarchy_cycle"
    assert (
        db.scalar(
            select(OrgUnitHierarchy).where(
                OrgUnitHierarchy.child_unit_id
                == db.scalar(select(OrgUnit.id).where(OrgUnit.code == "CY_A"))
            )
        )
        is None
    )


# --- corrections ------------------------------------------------------------------------


def test_correction_changes_data_with_version_and_audit(api: TestClient, db: Session) -> None:
    org = org_admin(api, db)
    operation = org.function("OPERATION")["public_id"]
    unit = org.create_unit(
        "CR_DEPT",
        "Misspelt Dept",
        "DEPARTMENT",
        operation,
        effective_from="2026-02-01",
        translations={"bn": "বিভাগ", "gu": "વિભાગ"},
    )["unit"]
    corrected = org.patch(
        f"/units/{unit['public_id']}",
        {
            "version": unit["version"],
            "reason": "Spelling",
            "code": "cr_dept_fixed",
            "name": "Corrected Dept",
            "effective_from": "2026-01-15",
            "translations": {"gu": None, "hi": "विभाग"},
        },
    )["unit"]
    assert corrected["code"] == "CR_DEPT_FIXED"
    assert corrected["effective_from"] == "2026-01-15"
    assert corrected["translations"] == {"bn": "বিভাগ", "hi": "विभाग"}
    history = org.get(f"/units/{unit['public_id']}/history")["placements"]
    assert history[0]["effective_from"] == "2026-01-15"  # first placement moved with it

    event = _meta(_events(db, "org_unit.corrected", unit["public_id"])[0])
    assert event["reason"] == "Spelling"
    assert event["changes"]["name"] == {"from": "Misspelt Dept", "to": "Corrected Dept"}
    assert event["changes"]["code"] == {"from": "CR_DEPT", "to": "CR_DEPT_FIXED"}
    assert event["changes"]["translations"]["gu"] == {"from": "વિભાગ", "to": None}

    stale = {"version": unit["version"], "name": "Again"}
    assert org.error("PATCH", f"/units/{unit['public_id']}", stale, 409) == "version_conflict"
    null_name = {"version": corrected["version"], "name": None}
    response = api.patch(
        f"{ORG}/units/{unit['public_id']}", json=null_name, headers=csrf(org.token)
    )
    assert response.status_code == 422


# --- closing and reopening ----------------------------------------------------------------


def test_close_blocks_on_dependants_and_reopen_restores(api: TestClient, db: Session) -> None:
    org = org_admin(api, db)
    operation = org.function("OPERATION")["public_id"]
    parent = org.create_unit(
        "CL_SUB", "Closing Sub", "SUB_FUNCTION", operation, effective_from="2026-01-01"
    )["unit"]
    child = org.create_unit(
        "CL_DEPT", "Closing Dept", "DEPARTMENT", parent["public_id"], effective_from="2026-01-01"
    )["unit"]

    close = {"version": parent["version"], "effective_date": "2026-10-01", "reason": "Merged"}
    response = api.post(
        f"{ORG}/units/{parent['public_id']}/close", json=close, headers=csrf(org.token)
    )
    assert response.status_code == 409
    error = response.json()["error"]
    assert error["code"] == "unit_has_dependants"
    assert error["details"] == [
        {
            "location": ["children", "CL_DEPT"],
            "message": "Active child unit",
            "type": "active_child",
        }
    ]

    closed_child = org.post(
        f"/units/{child['public_id']}/close",
        {"version": child["version"], "effective_date": "2026-10-01"},
        expect=200,
    )["unit"]
    closed_parent = org.post(f"/units/{parent['public_id']}/close", close, expect=200)["unit"]
    assert closed_parent["effective_to"] == "2026-10-01"
    assert org.unit(parent["public_id"], as_of="2026-10-01")["status"] == "closed"
    assert org.unit(parent["public_id"], as_of="2026-09-30")["status"] == "active"
    assert "CL_SUB" not in [i["code"] for i in org.get("/units", as_of="2026-11-01")["items"]]
    assert "CL_SUB" in [
        i["code"] for i in org.get("/units", as_of="2026-11-01", include_closed=True)["items"]
    ]
    tree = org.get("/tree", as_of="2026-11-01", include_closed=True)["nodes"]
    closed_node = next(node for node in tree if node["code"] == "CL_DEPT")
    assert closed_node["parent_id"] == parent["public_id"] and closed_node["status"] == "closed"

    again = {"version": closed_parent["version"], "effective_date": "2026-12-01"}
    assert org.error("POST", f"/units/{parent['public_id']}/close", again, 409) == (
        "unit_already_closed"
    )
    dept = org.unit_type("DEPARTMENT")["public_id"]
    under_closed = {
        "code": "NEW_UNDER_CLOSED",
        "name": "New",
        "unit_type_id": dept,
        "parent_id": parent["public_id"],
        "effective_from": "2026-11-01",
    }
    assert org.error("POST", "/units", under_closed, 422) == "parent_not_active"

    reopen_child = {"version": closed_child["version"]}
    assert org.error("POST", f"/units/{child['public_id']}/reopen", reopen_child, 409) == (
        "parent_closed"
    )
    reopened = org.post(
        f"/units/{parent['public_id']}/reopen",
        {"version": closed_parent["version"], "reason": "Closed by mistake"},
        expect=200,
    )["unit"]
    assert reopened["effective_to"] is None and reopened["parent"]["code"] == "OPERATION"
    org.post(f"/units/{child['public_id']}/reopen", reopen_child, expect=200)
    assert org.unit(child["public_id"])["parent"]["code"] == "CL_SUB"
    assert len(_events(db, "org_unit.closed")) == 2
    assert len(_events(db, "org_unit.reopened")) == 2


# --- locations --------------------------------------------------------------------------


def test_locations_lifecycle(api: TestClient, db: Session) -> None:
    org = org_admin(api, db)
    location = org.post(
        "/locations",
        {
            "code": "site_a",
            "name": "Test Site A",
            "city": "Test City",
            "country_code": "in",
            "time_zone": "Asia/Kolkata",
        },
    )
    assert location["code"] == "SITE_A" and location["country_code"] == "IN"
    bad_tz = {"code": "SITE_B", "name": "B", "time_zone": "Mars/Base"}
    assert org.error("POST", "/locations", bad_tz, 422) == "invalid_time_zone"
    assert org.error("POST", "/locations", {"code": "site_a", "name": "Dup"}, 409) == (
        "location_code_taken"
    )

    _team_type(org)
    unit = org.create_unit(
        "LOC_TEAM", "Located Team", "TEST_TEAM", location_id=location["public_id"]
    )["unit"]
    assert unit["location"]["code"] == "SITE_A"
    deactivate = {"version": location["version"], "is_active": False}
    assert org.error("PATCH", f"/locations/{location['public_id']}", deactivate, 409) == (
        "location_in_use"
    )
    org.patch(
        f"/units/{unit['public_id']}",
        {"version": unit["version"], "location_id": None, "reason": "Wrong site"},
    )
    inactive = org.patch(f"/locations/{location['public_id']}", deactivate)
    assert inactive["is_active"] is False
    assert org.get("/locations") == []
    assert len(org.get("/locations", include_inactive=True)) == 1
    body = {
        "code": "LOC_TEAM2",
        "name": "Team 2",
        "unit_type_id": org.unit_type("TEST_TEAM")["public_id"],
        "location_id": location["public_id"],
    }
    assert org.error("POST", "/units", body, 422) == "location_inactive"
    assert _meta(_events(db, "location.updated", location["public_id"])[0])["changes"] == {
        "is_active": {"from": True, "to": False}
    }


def test_unknown_records_return_404(api: TestClient, db: Session) -> None:
    make_user(db, "org.viewer", roles=("hod",))
    org = org_user(api, db, "org.viewer2", "hod")
    missing = "00000000-0000-7000-8000-000000000000"
    response = api.get(f"{ORG}/units/{missing}")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "org_unit_not_found"
    assert org.api.get(f"{ORG}/locations/{missing}").status_code == 404
