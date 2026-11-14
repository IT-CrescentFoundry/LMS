"""Occupational reference API: job families, grades, levels, designations, functional
roles and designation mappings, responsibilities. All values are synthetic.
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from tests.integration.org_helpers import ORG, OrgClient, org_admin, org_user

pytestmark = pytest.mark.db


def _event(db: Session, event_type: str, target_id: str) -> dict[str, Any]:
    event = db.scalar(
        select(AuditEvent).where(
            AuditEvent.event_type == event_type, AuditEvent.target_id == target_id
        )
    )
    assert event is not None and event.event_metadata is not None
    return dict(event.event_metadata)


def _designation(org: OrgClient, code: str, title: str, **extra: Any) -> dict[str, Any]:
    return dict(org.post("/designations", {"code": code, "title": title, **extra}))


def _role(org: OrgClient, code: str, name: str, **extra: Any) -> dict[str, Any]:
    return dict(org.post("/functional-roles", {"code": code, "name": name, **extra}))


# --- permissions --------------------------------------------------------------------------


def test_reference_writes_need_their_own_permissions(api: TestClient, db: Session) -> None:
    org = org_user(api, db, "ref.hod", "hod")
    assert org.get("/designations")["items"] == []  # organisation.view is enough to read
    for path, body in (
        ("/designations", {"code": "D1", "title": "T"}),
        ("/grades", {"code": "G1", "name": "G"}),
        ("/functional-roles", {"code": "R1", "name": "R"}),
        ("/responsibilities", {"code": "S1", "name": "S"}),
    ):
        assert org.error("POST", path, body, 403) == "forbidden", path
    employee = org_user(api, db, "ref.employee", "employee")
    assert employee.api.get(f"{ORG}/grades").status_code == 403


# --- grades, levels and job families ----------------------------------------------------


def test_grades_and_levels_are_separate_ranked_lists(api: TestClient, db: Session) -> None:
    org = org_admin(api, db)
    org.post("/grades", {"code": "g2", "name": "Test Grade Two", "rank": 20})
    g1 = org.post("/grades", {"code": "g1", "name": "Test Grade One", "rank": 10})
    org.post("/grades", {"code": "g0", "name": "Unranked Grade"})
    org.post("/levels", {"code": "l1", "name": "Test Level One", "rank": 1})

    assert [g["code"] for g in org.get("/grades")] == ["G1", "G2", "G0"]
    assert [level["code"] for level in org.get("/levels")] == ["L1"]
    assert org.error("POST", "/grades", {"code": "G1", "name": "Dup"}, 409) == "grade_code_taken"
    # The same code may exist in both lists: they are independent (Q-45).
    org.post("/levels", {"code": "G1", "name": "Level with a grade-like code"})

    updated = org.patch(
        f"/grades/{g1['public_id']}", {"version": g1["version"], "is_active": False}
    )
    assert updated["is_active"] is False and updated["version"] == g1["version"] + 1
    assert [g["code"] for g in org.get("/grades")] == ["G2", "G0"]
    assert len(org.get("/grades", include_inactive=True)) == 3
    stale = {"version": g1["version"], "name": "X"}
    assert org.error("PATCH", f"/grades/{g1['public_id']}", stale, 409) == "version_conflict"
    assert _event(db, "grade.updated", g1["public_id"])["changes"] == {
        "is_active": {"from": True, "to": False}
    }


def test_job_family_hierarchy_rejects_cycles(api: TestClient, db: Session) -> None:
    org = org_admin(api, db)
    top = org.post("/job-families", {"code": "JF_TOP", "name": "Test Engineering"})
    mid = org.post(
        "/job-families",
        {"code": "JF_MID", "name": "Test Mechanical", "parent_id": top["public_id"]},
    )
    low = org.post(
        "/job-families", {"code": "JF_LOW", "name": "Test Tooling", "parent_id": mid["public_id"]}
    )
    assert low["parent"]["code"] == "JF_MID"
    cycle = {"version": top["version"], "parent_id": low["public_id"]}
    assert org.error("PATCH", f"/job-families/{top['public_id']}", cycle, 422) == (
        "job_family_cycle"
    )
    self_parent = {"version": top["version"], "parent_id": top["public_id"]}
    assert org.error("PATCH", f"/job-families/{top['public_id']}", self_parent, 422) == (
        "job_family_cycle"
    )
    moved = org.patch(
        f"/job-families/{low['public_id']}", {"version": low["version"], "parent_id": None}
    )
    assert moved["parent"] is None
    assert _event(db, "job_family.updated", low["public_id"])["changes"] == {
        "parent_job_family_id": {"from": "JF_MID", "to": None}
    }


# --- designations ---------------------------------------------------------------------------


def test_designations_with_translations_search_and_paging(api: TestClient, db: Session) -> None:
    org = org_admin(api, db)
    family = org.post("/job-families", {"code": "JF_QA", "name": "Test Quality"})
    designation = _designation(
        org,
        "qa_eng",
        "Test Quality Engineer",
        job_family_id=family["public_id"],
        translations={"bn": "মান প্রকৌশলী", "hi": "गुणवत्ता अभियंता", "gu": "ગુણવત્તા ઇજનેર"},
    )
    assert designation["code"] == "QA_ENG"
    assert designation["job_family"]["code"] == "JF_QA"
    assert set(designation["translations"]) == {"bn", "hi", "gu"}
    for index in range(3):
        _designation(org, f"ZZ_{index}", f"Test Filler {index}")

    found = org.get("/designations", q="quality")["items"]
    assert [item["code"] for item in found] == ["QA_ENG"]
    page = org.get("/designations", limit=2)
    assert len(page["items"]) == 2 and page["next_cursor"]
    rest = org.get("/designations", limit=2, cursor=page["next_cursor"])
    assert [item["code"] for item in rest["items"]] == ["ZZ_1", "ZZ_2"]

    updated = org.patch(
        f"/designations/{designation['public_id']}",
        {"version": designation["version"], "translations": {"gu": None, "hi": ""}},
    )
    assert updated["translations"] == {"bn": "মান প্রকৌশলী"}
    response = api.post(
        f"{ORG}/designations",
        json={"code": "X1", "title": "X", "translations": {"fr": "Ingénieur"}},
        headers={"X-CSRF-Token": org.token},
    )
    assert response.status_code == 422


# --- functional roles and mappings ----------------------------------------------------------


def test_designation_role_mapping_is_many_to_many_and_scoped(api: TestClient, db: Session) -> None:
    org = org_admin(api, db)
    operation = org.function("OPERATION")
    purchase = org.function("PURCHASE")
    operator = _designation(org, "OPR", "Test Operator")
    helper = _designation(org, "HLP", "Test Helper")
    melting = _role(org, "MELT", "Test Melting Operation", owner_unit_id=operation["public_id"])
    storing = _role(org, "STORE", "Test Store Keeping")
    assert melting["owner_unit"]["code"] == "OPERATION"

    base = f"/designations/{operator['public_id']}/functional-roles"
    everywhere = org.post(
        base, {"functional_role_id": melting["public_id"], "effective_from": "2026-01-01"}
    )
    assert everywhere["scope_unit"] is None and everywhere["include_descendants"] is False
    scoped = org.post(
        base,
        {
            "functional_role_id": storing["public_id"],
            "scope_unit_id": purchase["public_id"],
            "effective_from": "2026-01-01",
        },
    )
    assert scoped["scope_unit"]["code"] == "PURCHASE" and scoped["include_descendants"] is True
    # Same role, different scope: allowed. Same role and scope, overlapping dates: refused.
    org.post(
        base,
        {
            "functional_role_id": storing["public_id"],
            "scope_unit_id": operation["public_id"],
            "effective_from": "2026-01-01",
        },
    )
    overlap = {"functional_role_id": melting["public_id"], "effective_from": "2026-05-01"}
    assert org.error("POST", base, overlap, 409) == "mapping_overlap"
    # One role reached from two designations.
    org.post(
        f"/designations/{helper['public_id']}/functional-roles",
        {"functional_role_id": melting["public_id"], "effective_from": "2026-01-01"},
    )
    assert len(org.get(base)) == 3

    ended = org.post(
        f"{base}/{everywhere['public_id']}/end",
        {"effective_to": "2026-07-01", "reason": "Process change"},
        expect=200,
    )
    assert ended["effective_to"] == "2026-07-01"
    assert len(org.get(base)) == 2 and len(org.get(base, include_ended=True)) == 3
    again = {"effective_to": "2026-08-01"}
    assert org.error("POST", f"{base}/{everywhere['public_id']}/end", again, 409) == (
        "mapping_already_ended"
    )
    # A new period after the ended one does not overlap.
    org.post(base, {"functional_role_id": melting["public_id"], "effective_from": "2026-07-01"})
    assert _event(db, "designation_role_mapping.ended", everywhere["public_id"]) == {
        "designation": "OPR",
        "functional_role": "MELT",
        "effective_to": "2026-07-01",
        "reason": "Process change",
    }


def test_roles_designations_and_units_in_use_cannot_be_retired(
    api: TestClient, db: Session
) -> None:
    org = org_admin(api, db)
    operation = org.function("OPERATION")
    sub = org.create_unit(
        "RT_SUB", "Retire Sub", "SUB_FUNCTION", operation["public_id"], effective_from="2026-01-01"
    )["unit"]
    designation = _designation(org, "RT_DES", "Test Retiring Designation")
    role = _role(org, "RT_ROLE", "Test Retiring Role", owner_unit_id=sub["public_id"])
    mapping = org.post(
        f"/designations/{designation['public_id']}/functional-roles",
        {
            "functional_role_id": role["public_id"],
            "scope_unit_id": sub["public_id"],
            "effective_from": "2026-02-01",
        },
    )

    deactivate_role = {"version": role["version"], "is_active": False}
    assert org.error("PATCH", f"/functional-roles/{role['public_id']}", deactivate_role, 409) == (
        "functional_role_in_use"
    )
    deactivate_designation = {"version": designation["version"], "is_active": False}
    code = org.error(
        "PATCH", f"/designations/{designation['public_id']}", deactivate_designation, 409
    )
    assert code == "designation_in_use"
    response = api.post(
        f"{ORG}/units/{sub['public_id']}/close",
        json={"version": sub["version"], "effective_date": "2026-09-01"},
        headers={"X-CSRF-Token": org.token},
    )
    assert response.status_code == 409
    blockers = {item["type"] for item in response.json()["error"]["details"]}
    assert blockers == {"owned_functional_role", "scoped_mapping"}

    org.post(
        f"/designations/{designation['public_id']}/functional-roles/{mapping['public_id']}/end",
        {"effective_to": "2026-08-01"},
        expect=200,
    )
    retired = org.patch(f"/functional-roles/{role['public_id']}", deactivate_role)
    assert retired["is_active"] is False
    org.patch(f"/designations/{designation['public_id']}", deactivate_designation)
    closed = org.post(
        f"/units/{sub['public_id']}/close",
        {"version": sub["version"], "effective_date": "2026-09-01"},
        expect=200,
    )
    assert closed["unit"]["effective_to"] == "2026-09-01"
    inactive_role = {"functional_role_id": role["public_id"]}
    new_designation = _designation(org, "RT_NEW", "Test New Designation")
    code = org.error(
        "POST",
        f"/designations/{new_designation['public_id']}/functional-roles",
        inactive_role,
        422,
    )
    assert code == "functional_role_inactive"


def test_functional_role_update_records_readable_changes(api: TestClient, db: Session) -> None:
    org = org_admin(api, db)
    family = org.post("/job-families", {"code": "JF_MNT", "name": "Test Maintenance Family"})
    role = _role(org, "FR_UPD", "Test Role", translations={"bn": "ভূমিকা"})
    updated = org.patch(
        f"/functional-roles/{role['public_id']}",
        {
            "version": role["version"],
            "name": "Test Role Renamed",
            "job_family_id": family["public_id"],
            "translations": {"hi": "भूमिका"},
        },
    )
    assert updated["job_family"]["code"] == "JF_MNT"
    assert updated["translations"] == {"bn": "ভূমিকা", "hi": "भूमिका"}
    changes = _event(db, "functional_role.updated", role["public_id"])["changes"]
    assert changes["job_family"] == {"from": None, "to": "JF_MNT"}
    assert changes["name"] == {"from": "Test Role", "to": "Test Role Renamed"}
    assert changes["translations"] == {"hi": {"from": None, "to": "भूमिका"}}


# --- responsibilities -----------------------------------------------------------------------


def test_responsibilities_are_catalogue_entries_only(api: TestClient, db: Session) -> None:
    org = org_admin(api, db)
    permissions_before = api.get("/api/v1/auth/me").json()["permissions"]
    item = org.post(
        "/responsibilities",
        {
            "code": "fire_warden",
            "name": "Test Fire Warden",
            "category": "Safety",
            "translations": {"gu": "ફાયર વોર્ડન"},
        },
    )
    assert item["code"] == "FIRE_WARDEN" and item["category"] == "Safety"
    assert api.get("/api/v1/auth/me").json()["permissions"] == permissions_before
    assert [r["code"] for r in org.get("/responsibilities", q="warden")["items"]] == ["FIRE_WARDEN"]
    updated = org.patch(
        f"/responsibilities/{item['public_id']}",
        {"version": item["version"], "category": None, "is_active": False},
    )
    assert updated["category"] is None and updated["is_active"] is False
    assert org.get("/responsibilities")["items"] == []
    assert _event(db, "responsibility.created", item["public_id"]) == {
        "code": "FIRE_WARDEN",
        "name": "Test Fire Warden",
    }
