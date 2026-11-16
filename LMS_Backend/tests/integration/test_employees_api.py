"""Employee master API: records, codes, status, separation, directory, permissions,
audit and history. All employees are synthetic.
"""

import uuid
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.models.employees import (
    Employee,
    EmployeeAssignment,
    EmployeeFunctionalRole,
    EmployeeResponsibility,
    ReportingRelationship,
)
from app.models.identity import UserAccount
from tests.integration.employee_helpers import (
    EMP,
    EmployeeClient,
    employee_admin,
    employee_user,
    events_for,
)
from tests.integration.helpers import make_user

pytestmark = pytest.mark.db


# --- records and codes ---------------------------------------------------------------------


def test_create_employee_without_an_account(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    created = hr.create(
        "  cf-00042 ",
        "Test Person One",
        display_name="Tester",
        preferred_language="gu",
        work_email="tester@example.test",
        date_of_joining="2026-01-05",
        employment_status="active",
    )
    assert created["employee_code"] == "CF-00042"
    assert created["employment_status"] == "active"
    assert created["accounts"] == [] and created["has_active_account"] is False
    assert created["primary_unit"] is None and created["line_manager"] is None
    # Nothing outside the minimal employee master is ever stored or returned.
    for forbidden in ("salary", "ctc", "date_of_birth", "gender", "address", "aadhaar", "pan"):
        assert forbidden not in created
    events = events_for(db, created["public_id"])
    assert [e.event_type for e in events] == ["employee.created"]
    assert events[0].event_metadata == {
        "employee_code": "CF-00042",
        "employment_status": "active",
    }


def test_codes_keep_leading_zeros_and_are_unique_ignoring_case(
    api: TestClient, db: Session
) -> None:
    hr = employee_admin(api, db)
    first = hr.create("00123")
    assert first["employee_code"] == "00123"
    hr.create("123")  # a different code: leading zeros are significant
    assert hr.error("POST", "", {"employee_code": "00123 ", "full_name": "T"}, 409) == (
        "employee_code_taken"
    )
    hr.create("ab-1")
    assert hr.error("POST", "", {"employee_code": "AB-1", "full_name": "T"}, 409) == (
        "employee_code_taken"
    )
    assert hr.error("POST", "", {"employee_code": "AB 1", "full_name": "T"}, 422) == (
        "invalid_employee_code"
    )
    assert hr.error("POST", "", {"employee_code": "X" * 31, "full_name": "T"}, 422) == (
        "validation_error"
    )


def test_database_enforces_case_insensitive_code_uniqueness(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    hr.create("CASE-1")
    with pytest.raises(IntegrityError):
        db.execute(
            text(
                "INSERT INTO employee (public_id, employee_code, full_name, created_at, "
                "updated_at, version) VALUES (UNHEX(REPLACE(UUID(), '-', '')), 'case-1', 'T', "
                "UTC_TIMESTAMP(6), UTC_TIMESTAMP(6), 1)"
            )
        )
    db.rollback()


def test_employment_status_rules(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    unknown = hr.create("U-1")
    assert unknown["employment_status"] is None  # not recorded, never assumed active
    bad = {"employee_code": "S-1", "full_name": "T", "employment_status": "separated"}
    assert hr.error("POST", "", bad, 422) == "separation_date_required"
    bad = {"employee_code": "S-1", "full_name": "T", "date_of_separation": "2026-01-01"}
    assert hr.error("POST", "", bad, 422) == "separation_date_not_allowed"
    bad = {
        "employee_code": "S-1",
        "full_name": "T",
        "employment_status": "separated",
        "date_of_joining": "2026-02-01",
        "date_of_separation": "2026-01-31",
    }
    assert hr.error("POST", "", bad, 422) == "invalid_employment_dates"
    assert hr.error("POST", "", {**bad, "employment_status": "retired"}, 422) == (
        "validation_error"
    )


def test_database_checks_back_up_the_status_rules(db: Session) -> None:
    db.add(Employee(employee_code="DB-1", full_name="T", employment_status="separated"))
    with pytest.raises(OperationalError, match="ck_employee_separated_has_date"):
        db.flush()  # MySQL reports CHECK violations as error 3819
    db.rollback()


def test_unknown_status_is_never_counted_as_active(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    hr.create("A-1", employment_status="active")
    hr.create("A-2")
    hr.create("A-3", employment_status="on_leave")

    def codes(**params: object) -> list[str]:
        return [item["employee_code"] for item in hr.get("", **params)["items"]]

    assert codes(status="active") == ["A-1"]
    assert codes(status="unknown") == ["A-2"]
    assert codes(status="on_leave") == ["A-3"]
    assert codes() == ["A-1", "A-2", "A-3"]


def test_correction_is_versioned_and_audited(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    person = hr.create("C-1", "Test Persn", date_of_joining="2026-01-01")
    path = f"/{person['public_id']}"
    corrected = hr.patch(
        path,
        {"version": person["version"], "full_name": "Test Person", "reason": "Typo"},
    )
    assert corrected["full_name"] == "Test Person"
    stale = {"version": person["version"], "display_name": "X"}
    assert hr.error("PATCH", path, stale, 409) == "version_conflict"
    assert hr.error("PATCH", path, {"version": corrected["version"], "full_name": None}, 422) == (
        "validation_error"
    )
    event = events_for(db, person["public_id"])[-1]
    assert event.event_type == "employee.corrected"
    assert event.event_metadata is not None
    assert event.event_metadata["changes"]["full_name"] == {
        "from": "Test Persn",
        "to": "Test Person",
    }


# --- separation ------------------------------------------------------------------------------


def _separation_setup(hr: EmployeeClient) -> tuple[dict[str, Any], dict[str, Any], str]:
    person = hr.create("SEP-1", employment_status="active", date_of_joining="2026-01-01")
    boss = hr.create("SEP-B", employment_status="active", date_of_joining="2025-01-01")
    unit = hr.org.function("OPERATION")
    assignment = hr.assign(person, unit, effective_from="2026-01-01")
    hr.post(
        f"/{person['public_id']}/reporting",
        {"manager_id": boss["public_id"], "effective_from": "2026-01-01"},
    )
    return person, assignment, f"/{person['public_id']}/employment-status"


def test_separation_is_refused_while_records_stay_open(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    person, _assignment, path = _separation_setup(hr)
    body = {"version": person["version"], "status": "separated", "separation_date": "2026-06-30"}
    error = hr.error_body("POST", path, body, 409)
    assert error["code"] == "open_records_on_separation"
    kinds = sorted(detail["type"] for detail in error["details"])
    assert kinds == ["open_assignment", "open_reporting_line"]
    # Nothing changed.
    detail = hr.get(f"/{person['public_id']}")
    assert detail["employment_status"] == "active" and detail["date_of_separation"] is None
    assert hr.error("POST", path, {**body, "separation_date": None}, 422) == (
        "separation_date_required"
    )


def _admin_id(db: Session, login_id: str = "emp.hr.admin") -> int:
    return int(db.scalars(select(UserAccount.id).where(UserAccount.login_id == login_id)).one())


def test_separation_can_end_open_records_explicitly(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    admin_id = _admin_id(db)
    person, assignment, path = _separation_setup(hr)
    role = hr.org.post("/functional-roles", {"code": "SEP_ROLE", "name": "Test Sep Role"})
    duty = hr.org.post("/responsibilities", {"code": "SEP_DUTY", "name": "Test Sep Duty"})
    hr.post(
        f"/{person['public_id']}/functional-roles",
        {"functional_role_id": role["public_id"], "effective_from": "2026-01-01"},
    )
    hr.post(
        f"/{person['public_id']}/responsibilities",
        {"responsibility_id": duty["public_id"], "effective_from": "2026-01-01"},
    )
    body = {
        "version": person["version"],
        "status": "separated",
        "separation_date": "2026-06-30",
        "end_open_records": True,
        "reason": "Resigned",
    }
    separated = hr.post(path, body, expect=200)
    assert separated["employment_status"] == "separated"
    assert separated["date_of_separation"] == "2026-06-30"
    rows = hr.get(f"/{person['public_id']}/assignments")
    assert [(r["public_id"], r["effective_to"]) for r in rows] == [
        (assignment["public_id"], "2026-07-01")  # the day after the last working day
    ]
    reporting = hr.get(f"/{person['public_id']}/reporting", as_of="2026-06-30")
    assert reporting["history"][0]["effective_to"] == "2026-07-01"

    # Row-level attribution to the acting administrator, in the same transaction.
    employee_id = db.scalars(
        select(Employee.id).where(Employee.public_id == uuid.UUID(person["public_id"]))
    ).one()
    row = db.scalars(
        select(EmployeeAssignment).where(EmployeeAssignment.employee_id == employee_id)
    ).one()
    db.refresh(row)
    assert row.updated_by_user_id == admin_id and row.ended_by_user_id == admin_id
    assert row.version == assignment["version"] + 1 and row.ended_at is not None
    models: tuple[type[Any], ...] = (
        EmployeeFunctionalRole,
        EmployeeResponsibility,
        ReportingRelationship,
    )
    for model in models:
        ended = db.scalars(select(model).where(model.employee_id == employee_id)).unique().one()
        db.refresh(ended)
        assert ended.ended_by_user_id == admin_id and ended.ended_at is not None, model
        assert str(ended.effective_to) == "2026-07-01", model

    # ... and in the audit event.
    event = events_for(db, person["public_id"])[-1]
    assert event.event_type == "employee.status_changed"
    assert event.actor_user_id == admin_id
    assert event.event_metadata is not None
    assert set(event.event_metadata["ended_records"]) == {
        "assignment",
        "functional_role",
        "responsibility",
        "reporting_line",
    }
    # New open records are now refused for the separated employee.
    unit = hr.org.function("PURCHASE")
    body = {"org_unit_id": unit["public_id"], "effective_from": "2026-06-01"}
    assert hr.error("POST", f"/{person['public_id']}/assignments", body, 422) == (
        "outside_employment_period"
    )


def test_separating_a_manager_never_detaches_direct_reports_silently(
    api: TestClient, db: Session
) -> None:
    hr = employee_admin(api, db)
    admin_id = _admin_id(db)
    boss = hr.create("MGR-1", employment_status="active", date_of_joining="2025-01-01")
    first = hr.create("MGR-R1", employment_status="active", date_of_joining="2025-01-01")
    second = hr.create("MGR-R2", employment_status="active", date_of_joining="2025-01-01")
    for report in (first, second):
        hr.post(
            f"/{report['public_id']}/reporting",
            {"manager_id": boss["public_id"], "effective_from": "2026-01-01"},
        )
    path = f"/{boss['public_id']}/employment-status"
    body = {"version": boss["version"], "status": "separated", "separation_date": "2026-06-30"}

    # Every affected subordinate is identified, by employee code.
    for attempt in (body, {**body, "end_open_records": True}):
        error = hr.error_body("POST", path, attempt, 409)
        assert error["code"] == "open_records_on_separation"
        assert sorted((d["type"], d["location"][-1]) for d in error["details"]) == [
            ("open_direct_report", "MGR-R1"),
            ("open_direct_report", "MGR-R2"),
        ]
    assert hr.get(f"/{boss['public_id']}")["employment_status"] == "active"
    assert len(hr.get(f"/{boss['public_id']}/reporting", as_of="2026-08-01")["direct_reports"]) == 2

    # Ending them is a separate, explicit choice.
    done = hr.post(path, {**body, "end_direct_reports": True, "reason": "Retired"}, expect=200)
    assert done["employment_status"] == "separated"
    assert hr.get(f"/{boss['public_id']}/reporting", as_of="2026-08-01")["direct_reports"] == []
    for report in (first, second):
        view = hr.get(f"/{report['public_id']}/reporting", as_of="2026-06-30")
        assert [m["manager"]["employee_code"] for m in view["managers"]] == ["MGR-1"]
        assert view["history"][0]["effective_to"] == "2026-07-01"
        # Audited on the subordinate's own history, attributed to the administrator.
        event = events_for(db, report["public_id"])[-1]
        assert event.event_type == "reporting_relationship.ended"
        assert event.actor_user_id == admin_id
        assert event.event_metadata is not None
        assert event.event_metadata["cause"] == "manager_separated"
        assert event.event_metadata["manager_code"] == "MGR-1"
        assert event.event_metadata["reason"] == "Retired"
    status_event = events_for(db, boss["public_id"])[-1]
    assert status_event.event_metadata is not None
    assert len(status_event.event_metadata["ended_records"]["direct_report"]) == 2
    rows = db.scalars(select(ReportingRelationship)).unique().all()
    assert {row.ended_by_user_id for row in rows} == {admin_id}


def _preview_setup(hr: EmployeeClient) -> dict[str, dict[str, Any]]:
    people = {
        code: hr.create(
            code, f"Test {code}", employment_status="active", date_of_joining="2025-01-01"
        )
        for code in ("PV-TOP", "PV-MGR", "PV-R1", "PV-R2")
    }
    mgr = people["PV-MGR"]
    hr.assign(mgr, hr.org.function("OPERATION"), effective_from="2025-01-01")

    def manage(employee: str, manager: str, start: str) -> None:
        hr.post(
            f"/{people[employee]['public_id']}/reporting",
            {"manager_id": people[manager]["public_id"], "effective_from": start},
        )

    manage("PV-MGR", "PV-TOP", "2025-01-01")  # the manager is also a subordinate
    manage("PV-R1", "PV-MGR", "2025-02-01")
    manage("PV-R2", "PV-MGR", "2026-08-01")  # starts after the last working day
    return people


def test_separation_preview_is_read_only_and_matches_the_separation(
    api: TestClient, db: Session
) -> None:
    hr = employee_admin(api, db)
    people = _preview_setup(hr)
    mgr = people["PV-MGR"]
    path = f"/{mgr['public_id']}/separation-preview"
    events_before = len(events_for(db, mgr["public_id"]))

    preview = hr.get(path, separation_date="2026-06-30")
    assert preview["separation_date"] == "2026-06-30"  # exactly as requested
    assert preview["records_end_on"] == "2026-07-01"  # the following day, once
    assert preview["employee"]["employee_code"] == "PV-MGR"
    assert preview["version"] == mgr["version"]
    assert [
        (r["kind"], r["code"], r["name"], r["starts_after_separation"])
        for r in preview["own_records"]
    ] == [
        ("assignment", "OPERATION", "Operation", False),
        ("reporting_line", "PV-TOP", "Test PV-TOP", False),
    ]
    assert [
        (
            r["employee"]["employee_code"],
            r["employee"]["full_name"],
            r["relationship_type"]["code"],
            r["effective_from"],
            r["starts_after_separation"],
        )
        for r in preview["direct_reports"]
    ] == [
        ("PV-R1", "Test PV-R1", "LINE_MANAGER", "2025-02-01", False),
        ("PV-R2", "Test PV-R2", "LINE_MANAGER", "2026-08-01", True),
    ]
    assert preview["requires_end_open_records"] is True
    assert preview["requires_end_direct_reports"] is True
    assert preview["blocked"] is True

    # Nothing was written or audited, and the employee's version is unchanged.
    assert len(events_for(db, mgr["public_id"])) == events_before
    detail = hr.get(f"/{mgr['public_id']}")
    assert detail["employment_status"] == "active" and detail["version"] == mgr["version"]

    # The real separation refuses for exactly the record the preview marked as blocking.
    body = {
        "version": mgr["version"],
        "status": "separated",
        "separation_date": "2026-06-30",
        "end_open_records": True,
        "end_direct_reports": True,
    }
    error = hr.error_body("POST", f"/{mgr['public_id']}/employment-status", body, 409)
    assert [(d["type"], d["location"][-1]) for d in error["details"]] == [
        ("starts_after_separation", "PV-R2")
    ]

    # A later last working day: nothing starts after it, so the preview is not blocked
    # and the separation succeeds with both explicit confirmations.
    later = hr.get(path, separation_date="2026-09-30")
    assert later["blocked"] is False and later["records_end_on"] == "2026-10-01"
    assert [r["employee"]["employee_code"] for r in later["direct_reports"]] == ["PV-R1", "PV-R2"]
    hr.post(
        f"/{mgr['public_id']}/employment-status",
        {**body, "separation_date": "2026-09-30"},
        expect=200,
    )
    after = hr.get(path, separation_date="2026-09-30")
    assert after["own_records"] == [] and after["direct_reports"] == []
    assert after["requires_end_open_records"] is False and after["blocked"] is False


def test_separation_preview_validation_and_access(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    person = hr.create("PV-V1", employment_status="active", date_of_joining="2026-03-01")
    path = f"{EMP}/{person['public_id']}/separation-preview"
    empty = hr.get(f"/{person['public_id']}/separation-preview", separation_date="2026-06-30")
    assert empty["own_records"] == [] and empty["direct_reports"] == []
    assert empty["requires_end_open_records"] is False
    assert empty["requires_end_direct_reports"] is False

    def code(params: dict[str, str], status: int, url: str = path) -> str:
        response = hr.api.get(url, params=params)
        assert response.status_code == status, response.text
        return str(response.json()["error"]["code"])

    assert code({"separation_date": "2026-02-28"}, 422) == "invalid_employment_dates"
    assert code({}, 422) == "validation_error"
    assert code({"separation_date": "not-a-date"}, 422) == "validation_error"
    missing = f"{EMP}/{uuid.uuid4()}/separation-preview"
    assert code({"separation_date": "2026-06-30"}, 404, missing) == "employee_not_found"

    api.cookies.clear()
    viewer = employee_user(api, db, "pv.supervisor", "supervisor")
    response = viewer.api.get(path, params={"separation_date": "2026-06-30"})
    assert response.status_code == 403


def test_separation_does_not_touch_the_linked_account(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    person = hr.create("SEP-2", employment_status="active")
    account = make_user(db, "sep.two.login")
    hr.send(
        "PUT", f"/{person['public_id']}/account", {"user_public_id": str(account.public_id)}, 200
    )
    body = {"version": person["version"], "status": "separated", "separation_date": "2026-06-30"}
    hr.post(f"/{person['public_id']}/employment-status", body, expect=200)
    db.refresh(account)
    assert account.status == "active"  # Q-50: never suspended automatically
    summary = hr.get(f"/{person['public_id']}/account")
    assert summary["flags"] == ["separated_with_active_account"]


# --- directory -----------------------------------------------------------------------------


def test_directory_filters_and_paging(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    operation = hr.org.function("OPERATION")
    sub = hr.org.create_unit("DIR_SUB", "Test Dir Sub", "SUB_FUNCTION", operation["public_id"])
    location = hr.org.post("/locations", {"code": "DIR_LOC", "name": "Test Plant"})
    designation = hr.org.post("/designations", {"code": "DIR_DES", "title": "Test Fitter"})
    top = hr.create("D-1", employment_status="active")
    below = hr.create("D-2", employment_status="active")
    hr.create("D-3", employment_status="active")
    hr.assign(top, operation)
    hr.assign(
        below,
        sub["unit"],
        location_id=location["public_id"],
        designation_id=designation["public_id"],
    )
    linked = make_user(db, "dir.one.login")
    hr.send("PUT", f"/{top['public_id']}/account", {"user_public_id": str(linked.public_id)}, 200)

    def codes(**params: object) -> list[str]:
        return [item["employee_code"] for item in hr.get("", **params)["items"]]

    unit_id = operation["public_id"]
    assert codes(unit=unit_id) == ["D-1"]
    assert codes(unit=unit_id, include_descendants=True) == ["D-1", "D-2"]
    assert codes(location=location["public_id"]) == ["D-2"]
    assert codes(designation=designation["public_id"]) == ["D-2"]
    assert codes(has_account=True) == ["D-1"]
    assert codes(has_account=False) == ["D-2", "D-3"]
    assert codes(q="d-2") == ["D-2"]

    row = next(item for item in hr.get("")["items"] if item["employee_code"] == "D-2")
    assert [unit["code"] for unit in row["path"]] == ["OPERATION"]
    assert row["primary_unit"]["code"] == "DIR_SUB"
    assert row["location"]["code"] == "DIR_LOC" and row["designation"]["code"] == "DIR_DES"

    first = hr.get("", limit=2)
    assert [item["employee_code"] for item in first["items"]] == ["D-1", "D-2"]
    second = hr.get("", limit=2, cursor=first["next_cursor"])
    assert [item["employee_code"] for item in second["items"]] == ["D-3"]
    assert second["next_cursor"] is None
    assert hr.api.get(EMP, params={"cursor": "not-a-cursor"}).status_code == 422


# --- permissions and history -------------------------------------------------------------------


@pytest.mark.parametrize("role", ["employee", "supervisor", "hod", "sme"])
def test_non_hr_roles_cannot_read_or_change_employees(
    api: TestClient, db: Session, role: str
) -> None:
    hr = employee_admin(api, db)
    person = hr.create("P-1")
    api.cookies.clear()
    other = employee_user(api, db, f"perm.{role}", role)
    assert other.api.get(EMP).status_code == 403
    assert other.api.get(f"{EMP}/{person['public_id']}").status_code == 403
    assert other.error("POST", "", {"employee_code": "P-2", "full_name": "T"}, 403) == "forbidden"


def test_history_lists_events_targeting_the_employee(api: TestClient, db: Session) -> None:
    hr = employee_admin(api, db)
    person = hr.create("H-1", date_of_joining="2026-01-01")
    hr.assign(person, hr.org.function("OPERATION"), effective_from="2026-01-01")
    page = hr.get(f"/{person['public_id']}/history", limit=1)
    assert [item["event_type"] for item in page["items"]] == ["employee_assignment.created"]
    rest = hr.get(f"/{person['public_id']}/history", cursor=page["next_cursor"])
    assert [item["event_type"] for item in rest["items"]] == ["employee.created"]
    assert rest["next_cursor"] is None
    # Network details stay in the audit log (audit.view); HR history views omit them.
    assert all(item["source_ip"] is None and item["user_agent"] is None for item in rest["items"])
    assert rest["items"][0]["actor"]["login_id"] == "emp.hr.admin"
