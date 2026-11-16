"""Assignments, functional roles and responsibilities. All data is synthetic."""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.employees import EmployeeAssignment
from app.models.organisation import OrgUnit
from tests.integration.employee_helpers import EmployeeClient, employee_admin, events_for

pytestmark = pytest.mark.db


def _person(hr: EmployeeClient, code: str = "AS-1") -> dict[str, Any]:
    return hr.create(code, employment_status="active", date_of_joining="2026-01-01")


# --- assignments -----------------------------------------------------------------------------


def test_transfer_keeps_history_and_the_as_of_path(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    operation = hr.org.function("OPERATION")
    purchase = hr.org.function("PURCHASE")
    melt = hr.org.create_unit("AS_MELT", "Test Melting", "DEPARTMENT", operation["public_id"])
    person = _person(hr)
    first = hr.assign(person, melt["unit"], effective_from="2026-01-01")
    base = f"/{person['public_id']}/assignments"

    moved = hr.post(
        f"{base}/{first['public_id']}/change",
        {
            "version": first["version"],
            "effective_date": "2026-04-01",
            "org_unit_id": purchase["public_id"],
            "reason": "Transfer",
        },
    )["assignment"]
    assert moved["org_unit"]["code"] == "PURCHASE" and moved["effective_from"] == "2026-04-01"
    timeline = hr.get(base)
    assert [(r["org_unit"]["code"], r["effective_from"], r["effective_to"]) for r in timeline] == [
        ("AS_MELT", "2026-01-01", "2026-04-01"),
        ("PURCHASE", "2026-04-01", None),
    ]
    assert len(hr.get(base, include_ended=False)) == 1

    # A later reorganisation does not rewrite where the employee sat in February.
    melt_now = hr.org.unit(melt["unit"]["public_id"])
    hr.org.post(
        f"/units/{melt['unit']['public_id']}/move",
        {
            "version": melt_now["version"],
            "new_parent_id": purchase["public_id"],
            "effective_date": "2026-06-01",
        },
        expect=200,
    )
    feb = hr.get(f"/{person['public_id']}", as_of="2026-02-15")
    assert feb["primary_unit"]["code"] == "AS_MELT"
    assert [unit["code"] for unit in feb["path"]] == ["OPERATION"]
    assert hr.get(f"/{person['public_id']}", as_of="2026-05-01")["primary_unit"]["code"] == (
        "PURCHASE"
    )
    types = [e.event_type for e in events_for(db, person["public_id"])]
    assert types == [
        "employee.created",
        "employee_assignment.created",
        "employee_assignment.changed",
    ]


def test_primary_and_same_unit_overlaps_are_refused(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    operation = hr.org.function("OPERATION")
    purchase = hr.org.function("PURCHASE")
    person = _person(hr)
    base = f"/{person['public_id']}/assignments"
    hr.assign(person, operation, effective_from="2026-01-01")
    second_primary = {"org_unit_id": purchase["public_id"], "effective_from": "2026-03-01"}
    assert hr.error("POST", base, second_primary, 409) == "primary_overlap"
    additional = hr.assign(
        person, purchase, assignment_type="additional", effective_from="2026-03-01"
    )
    assert additional["assignment_type"] == "additional"
    hr.assign(
        person,
        hr.org.function("SALES_BD"),
        assignment_type="acting",
        effective_from="2026-03-01",
        effective_to="2026-04-01",
    )
    same_unit = {
        "assignment_type": "deputation",
        "org_unit_id": purchase["public_id"],
        "effective_from": "2026-05-01",
    }
    assert hr.error("POST", base, same_unit, 409) == "assignment_overlap"
    # Earlier, non-overlapping primary history is fine... but not before joining.
    early = {
        "org_unit_id": purchase["public_id"],
        "effective_from": "2025-06-01",
        "effective_to": "2026-01-01",
    }
    assert hr.error("POST", base, early, 422) == "outside_employment_period"
    no_start = {"org_unit_id": purchase["public_id"], "assignment_type": "acting"}
    assert hr.error("POST", base, no_start, 422) == "assignment_start_required"


def test_database_allows_only_one_open_primary(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    person = _person(hr)
    row = hr.assign(person, hr.org.function("OPERATION"), effective_from="2026-01-01")
    existing = db.scalars(
        select(EmployeeAssignment).where(
            EmployeeAssignment.public_id == uuid.UUID(row["public_id"])
        )
    ).one()
    purchase = db.scalars(select(OrgUnit).where(OrgUnit.code == "PURCHASE")).one()
    db.add(
        EmployeeAssignment(
            employee_id=existing.employee_id, org_unit_id=purchase.id, assignment_type="primary"
        )
    )
    with pytest.raises(IntegrityError, match="uq_employee_assignment_employee_id_primary_open"):
        db.flush()  # the generated primary_open column backs up the service check
    db.rollback()


def test_closed_units_and_inactive_references_are_refused(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    operation = hr.org.function("OPERATION")
    old = hr.org.create_unit("AS_OLD", "Test Old Dept", "DEPARTMENT", operation["public_id"])
    hr.org.post(
        f"/units/{old['unit']['public_id']}/close",
        {"version": old["unit"]["version"], "effective_date": "2026-03-01"},
        expect=200,
    )
    person = _person(hr)
    base = f"/{person['public_id']}/assignments"
    body = {"org_unit_id": old["unit"]["public_id"], "effective_from": "2026-02-01"}
    assert hr.error("POST", base, body, 422) == "unit_not_active"
    # History inside the unit's lifetime is still recordable.
    hr.post(base, {**body, "effective_to": "2026-03-01"})

    grade = hr.org.post("/grades", {"code": "AS_G", "name": "Test Grade"})
    hr.org.patch(f"/grades/{grade['public_id']}", {"version": grade["version"], "is_active": False})
    body = {
        "assignment_type": "additional",
        "org_unit_id": operation["public_id"],
        "grade_id": grade["public_id"],
        "effective_from": "2026-03-01",
    }
    assert hr.error("POST", base, body, 422) == "reference_inactive"


def test_unit_closure_is_blocked_by_open_assignments(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    operation = hr.org.function("OPERATION")
    dept = hr.org.create_unit(
        "AS_BLOCK", "Test Blocking Dept", "DEPARTMENT", operation["public_id"]
    )
    person = _person(hr)
    row = hr.assign(person, dept["unit"], effective_from="2026-01-01")
    close = {"version": dept["unit"]["version"], "effective_date": "2026-06-01"}
    response = hr.api.post(
        f"/api/v1/org/units/{dept['unit']['public_id']}/close",
        json=close,
        headers={"X-CSRF-Token": hr.token},
    )
    assert response.status_code == 409, response.text
    error = response.json()["error"]
    assert error["code"] == "unit_has_dependants"
    assert [d["type"] for d in error["details"]] == ["employee_assignment"]
    # Ending the assignment on (or before) the closure date unblocks it.
    hr.post(
        f"/{person['public_id']}/assignments/{row['public_id']}/end",
        {"version": row["version"], "effective_to": "2026-06-01"},
        expect=200,
    )
    hr.org.post(f"/units/{dept['unit']['public_id']}/close", close, expect=200)


def test_changes_ends_and_corrections(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    operation = hr.org.function("OPERATION")
    designation = hr.org.post("/designations", {"code": "AS_D1", "title": "Test Moulder"})
    senior = hr.org.post("/designations", {"code": "AS_D2", "title": "Test Senior Moulder"})
    level = hr.org.post("/levels", {"code": "AS_L1", "name": "Test Level"})
    person = _person(hr)
    base = f"/{person['public_id']}/assignments"
    row = hr.assign(
        person, operation, effective_from="2026-01-01", designation_id=designation["public_id"]
    )
    promoted = hr.post(
        f"{base}/{row['public_id']}/change",
        {
            "version": row["version"],
            "effective_date": "2026-07-01",
            "designation_id": senior["public_id"],
            "job_level_id": level["public_id"],
        },
    )["assignment"]
    assert promoted["designation"]["code"] == "AS_D2" and promoted["job_level"]["code"] == "AS_L1"
    same = {"version": promoted["version"], "effective_date": "2026-08-01"}
    assert hr.error("POST", f"{base}/{promoted['public_id']}/change", same, 422) == "no_change"
    bad_date = {**same, "effective_date": "2026-07-01", "designation_id": designation["public_id"]}
    assert hr.error("POST", f"{base}/{promoted['public_id']}/change", bad_date, 422) == (
        "change_date_invalid"
    )

    # Back-dated fix of the first row through an explicit, audited correction.
    first = hr.get(base)[0]
    fixed = hr.patch(
        f"{base}/{first['public_id']}",
        {"version": first["version"], "effective_from": "2026-01-05", "reason": "Wrong date"},
    )["assignment"]
    assert fixed["effective_from"] == "2026-01-05"
    corrected = events_for(db, person["public_id"])[-1]
    assert corrected.event_type == "employee_assignment.corrected"
    assert corrected.event_metadata is not None
    assert corrected.event_metadata["from"]["from"] == "2026-01-01"
    assert corrected.event_metadata["to"]["from"] == "2026-01-05"

    ended = hr.post(
        f"{base}/{promoted['public_id']}/end",
        {"version": promoted["version"], "effective_to": "2026-10-01"},
        expect=200,
    )
    assert ended["effective_to"] == "2026-10-01"
    again = {"version": ended["version"], "effective_to": "2026-11-01"}
    assert hr.error("POST", f"{base}/{promoted['public_id']}/end", again, 409) == (
        "assignment_already_ended"
    )


def test_assignment_to_a_non_assignable_unit_type_warns(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    unit_type = hr.org.post(
        "/unit-types",
        {"code": "AS_GROUP", "name": "Test Grouping", "allows_employee_assignment": False},
    )
    group = hr.org.create_unit("AS_GRP", "Test Group", unit_type["code"])
    person = _person(hr)
    written = hr.post(
        f"/{person['public_id']}/assignments",
        {"org_unit_id": group["unit"]["public_id"], "effective_from": "2026-01-01"},
    )
    assert [w["code"] for w in written["warnings"]] == ["unit_type_not_assignable"]


# --- functional roles ------------------------------------------------------------------------


def test_derived_manual_and_excluded_roles(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    operation = hr.org.function("OPERATION")
    purchase = hr.org.function("PURCHASE")
    melt = hr.org.create_unit("FR_MELT", "Test Melt Shop", "DEPARTMENT", operation["public_id"])
    operator = hr.org.post("/designations", {"code": "FR_OPR", "title": "Test Furnace Operator"})
    buyer = hr.org.post("/designations", {"code": "FR_BUY", "title": "Test Buyer"})
    melting = hr.org.post("/functional-roles", {"code": "FR_MELTING", "name": "Test Melting"})
    safety = hr.org.post("/functional-roles", {"code": "FR_SAFETY", "name": "Test Safety"})
    buying = hr.org.post("/functional-roles", {"code": "FR_BUYING", "name": "Test Buying"})
    audit = hr.org.post("/functional-roles", {"code": "FR_AUDIT", "name": "Test Audit"})
    hr.org.post(
        f"/designations/{operator['public_id']}/functional-roles",
        {
            "functional_role_id": melting["public_id"],
            "scope_unit_id": operation["public_id"],
            "effective_from": "2026-01-01",
        },
    )
    hr.org.post(
        f"/designations/{operator['public_id']}/functional-roles",
        {"functional_role_id": safety["public_id"], "effective_from": "2026-01-01"},
    )
    hr.org.post(
        f"/designations/{buyer['public_id']}/functional-roles",
        {"functional_role_id": buying["public_id"], "effective_from": "2026-01-01"},
    )
    person = _person(hr)
    hr.assign(
        person, melt["unit"], effective_from="2026-01-01", designation_id=operator["public_id"]
    )
    hr.assign(
        person,
        purchase,
        assignment_type="additional",
        effective_from="2026-01-01",
        designation_id=buyer["public_id"],
    )
    path = f"/{person['public_id']}/functional-roles"

    def roles() -> dict[str, dict[str, Any]]:
        listing = hr.get(path, as_of="2026-06-01")
        return {item["functional_role"]["code"]: item for item in listing["roles"]}

    current = roles()
    assert set(current) == {"FR_MELTING", "FR_SAFETY", "FR_BUYING"}  # every assignment counts
    assert current["FR_MELTING"]["derived_from"][0]["org_unit"]["code"] == "FR_MELT"
    assert all(item["effective"] for item in current.values())

    manual = hr.post(
        path,
        {
            "functional_role_id": audit["public_id"],
            "effective_from": "2026-02-01",
            "reason": "Internal auditor",
        },
    )
    excluded = hr.post(
        path,
        {
            "functional_role_id": safety["public_id"],
            "kind": "exclusion",
            "effective_from": "2026-02-01",
        },
    )
    current = roles()
    assert current["FR_AUDIT"]["manual"]["public_id"] == manual["public_id"]
    assert current["FR_SAFETY"]["effective"] is False
    assert current["FR_SAFETY"]["exclusion"]["public_id"] == excluded["public_id"]
    overlap = {"functional_role_id": audit["public_id"], "effective_from": "2026-03-01"}
    assert hr.error("POST", path, overlap, 409) == "role_assignment_overlap"

    hr.post(f"{path}/{excluded['public_id']}/end", {"effective_to": "2026-05-01"}, expect=200)
    assert roles()["FR_SAFETY"]["effective"] is True
    types = [e.event_type for e in events_for(db, person["public_id"])][-3:]
    assert types == [
        "employee_functional_role.assigned",
        "employee_functional_role.excluded",
        "employee_functional_role.ended",
    ]


# --- responsibilities ------------------------------------------------------------------------


def test_responsibilities_with_context(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    operation = hr.org.function("OPERATION")
    plant = hr.org.post("/locations", {"code": "RS_PLANT", "name": "Test Plant Two"})
    warden = hr.org.post("/responsibilities", {"code": "RS_WARDEN", "name": "Test Fire Warden"})
    person = _person(hr)
    path = f"/{person['public_id']}/responsibilities"
    record = hr.post(
        path,
        {
            "responsibility_id": warden["public_id"],
            "context_unit_id": operation["public_id"],
            "effective_from": "2026-02-01",
        },
    )
    assert record["context_unit"]["code"] == "OPERATION" and record["context_location"] is None
    same = {
        "responsibility_id": warden["public_id"],
        "context_unit_id": operation["public_id"],
        "effective_from": "2026-03-01",
    }
    assert hr.error("POST", path, same, 409) == "responsibility_overlap"
    # The same duty in another context is a separate record.
    hr.post(
        path,
        {
            "responsibility_id": warden["public_id"],
            "context_location_id": plant["public_id"],
            "effective_from": "2026-02-01",
        },
    )
    assert len(hr.get(path)) == 2
    ended = hr.post(f"{path}/{record['public_id']}/end", {"effective_to": "2026-09-01"}, expect=200)
    assert ended["effective_to"] == "2026-09-01"
    assert len(hr.get(path)) == 1 and len(hr.get(path, include_ended=True)) == 2
