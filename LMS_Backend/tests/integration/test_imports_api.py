"""Stage D import API - integration tests on crescent_lms_test (synthetic workbooks only)."""

import io
import uuid
from typing import Any
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient
from openpyxl import load_workbook
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.employees import Employee, EmployeeAssignment, ReportingRelationship
from app.models.imports import ImportJob, ImportRow, ImportValueMapping, RecordProvenance
from tests.integration.employee_helpers import EmployeeClient, employee_admin, employee_user
from tests.integration.helpers import csrf, login, make_user
from tests.support.workbooks import build, standard

pytestmark = pytest.mark.db
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


class Imports:
    """Signed-in client for /api/v1/imports."""

    def __init__(self, client: EmployeeClient) -> None:
        self.api, self.token, self.org, self.emp = client.api, client.token, client.org, client

    def upload(
        self, data: bytes, name: str = "people.xlsx", profile: str = "employees", expect: int = 201
    ) -> Any:
        response = self.api.post(
            f"/api/v1/imports?profile={profile}",
            content=data,
            headers={**csrf(self.token), "Content-Type": XLSX, "X-File-Name": quote(name)},
        )
        assert response.status_code == expect, response.text
        return response.json()

    def get(self, path: str = "", expect: int = 200, **params: Any) -> Any:
        response = self.api.get(f"/api/v1/imports{path}", params=params)
        assert response.status_code == expect, response.text
        return response.json()

    def send(self, path: str, body: dict[str, Any], expect: int = 200, method: str = "POST") -> Any:
        response = self.api.request(
            method, f"/api/v1/imports{path}", json=body, headers=csrf(self.token)
        )
        assert response.status_code == expect, response.text
        return response.json()

    def confirm(self, job: dict[str, Any]) -> dict[str, Any]:
        sections = [
            {
                "section": m["section"],
                "sheet": m["sheet"],
                "header_row": m["header_row"],
                "columns": m["columns"],
            }
            for m in job["column_mapping"]
        ]
        return dict(
            self.send(
                f"/{job['public_id']}/mapping",
                {"version": job["version"], "sections": sections},
                method="PUT",
            )
        )

    def validate(self, job: dict[str, Any], expect: int = 200) -> Any:
        return self.send(f"/{job['public_id']}/validate", {"version": job["version"]}, expect)

    def commit(self, job: dict[str, Any], expect: int = 200, **extra: Any) -> Any:
        return self.send(
            f"/{job['public_id']}/commit",
            {"version": job["version"], "confirm": True, **extra},
            expect,
        )

    def prepare(self, data: bytes) -> dict[str, Any]:
        return dict(self.validate(self.confirm(self.upload(data))))

    def rows(self, job: dict[str, Any], **params: Any) -> list[dict[str, Any]]:
        return list(self.get(f"/{job['public_id']}/rows", limit=200, **params)["items"])

    def issues(self, job: dict[str, Any], **params: Any) -> list[dict[str, Any]]:
        return list(self.get(f"/{job['public_id']}/issues", limit=200, **params)["items"])


@pytest.fixture
def hr(api: TestClient, db: Session) -> Imports:
    return Imports(employee_admin(api, db, "imp.hr.admin"))


@pytest.fixture
def setup_org(hr: Imports) -> dict[str, Any]:
    operation = hr.org.function("OPERATION")
    melt = hr.org.create_unit("IMP_MELT", "Test Melt Shop", "SUB_FUNCTION", operation["public_id"])
    operator = hr.org.post("/designations", {"code": "IMP_OPR", "title": "Test Furnace Operator"})
    return {"operation": operation, "melt": melt, "operator": operator}


def _codes(rows: list[dict[str, Any]], section: str, outcome: str) -> list[str]:
    return [
        r["values"]["employee_code"]
        for r in rows
        if r["section"] == section and r["outcome"] == outcome
    ]


def test_profiles_and_template(hr: Imports) -> None:
    profiles = hr.get("/profiles")
    assert [(p["code"], p["version"], p["can_run"], p["can_commit"]) for p in profiles] == [
        ("employees", 1, True, True)
    ]
    assert [s["kind"] for s in profiles[0]["sections"]] == ["employees", "assignments", "reporting"]
    response = hr.api.get("/api/v1/imports/profiles/employees/template")
    assert response.status_code == 200 and response.headers["content-type"] == XLSX
    assert load_workbook(io.BytesIO(response.content)).sheetnames == [
        "Instructions",
        "Employees",
        "Assignments",
        "Reporting",
    ]


def test_full_lifecycle_validates_without_writing_then_commits_once(
    hr: Imports, db: Session, setup_org: dict[str, Any]
) -> None:
    data = standard(
        employees=[
            ["00101", "Test Person One", "Active", "01-04-2025", "one@example.test"],
            ["00102", "Test Person Two", None, "2025-04-01", None],
        ],
        assignments=[
            ["00101", "Primary", "Test Melt Shop", "IMP_OPR", "01-04-2025"],
            ["00102", None, "IMP_MELT", None, "01-04-2025"],
        ],
        reporting=[["00102", "00101", "01-04-2025"]],
        formats={("Employees", r, 1): "@" for r in range(2, 4)},
    )
    job = hr.upload(data)
    assert job["status"] == "mapping_required" and not job["mapping_confirmed"]
    assert {s["name"]: s["suggested_section"] for s in job["workbook"]} == {
        "Employees": "employees",
        "Assignments": "assignments",
        "Reporting": "reporting",
    }
    before = db.scalar(select(func.count()).select_from(Employee))
    job = hr.validate(hr.confirm(job))
    assert job["status"] == "ready_for_approval", job["counts"]
    assert job["counts"]["rows"] == 5 and job["counts"]["blocking_errors"] == 0
    # The dry run executed every domain rule but wrote nothing to the domain tables.
    assert db.scalar(select(func.count()).select_from(Employee)) == before
    rows = hr.rows(job)
    assert sorted(_codes(rows, "employees", "new")) == ["00101", "00102"]
    unknown = next(
        r for r in rows if r["section"] == "employees" and r["values"]["employee_code"] == "00102"
    )
    assert "employment_status" not in unknown["values"]  # not recorded stays NULL, never active
    assert (
        next(
            r
            for r in rows
            if r["section"] == "assignments" and r["values"]["employee_code"] == "00102"
        )["values"]["assignment_type"]
        == "primary"
    )

    job = hr.commit(job)
    assert job["status"] == "completed" and job["counts"]["committed"] == {
        "created": 5,
        "updated": 0,
        "unchanged": 0,
        "skipped": 0,
    }
    created = db.scalars(
        select(Employee).where(Employee.employee_code.in_(["00101", "00102"]))
    ).all()
    assert sorted(e.employee_code for e in created) == ["00101", "00102"]
    assert next(e for e in created if e.employee_code == "00102").employment_status is None
    assert db.scalar(select(func.count()).select_from(EmployeeAssignment)) == 2
    assert db.scalar(select(func.count()).select_from(ReportingRelationship)) == 1
    assert db.scalar(select(func.count()).select_from(RecordProvenance)) == 5
    assert not job["file_stored"]

    # A committed job can never be committed again (replay / double click).
    assert hr.commit(job, expect=409)["error"]["code"] == "import_not_ready"
    # Re-importing the same workbook: a new job whose rows are all unchanged.
    again = hr.prepare(data)
    assert again["previously_imported_by"] == [job["public_id"]]
    assert {r["outcome"] for r in hr.rows(again)} == {"unchanged"}
    done = hr.commit(again)
    assert done["counts"]["committed"] == {"created": 0, "updated": 0, "unchanged": 5, "skipped": 0}
    assert (
        db.scalar(
            select(func.count())
            .select_from(Employee)
            .where(Employee.employee_code.in_(["00101", "00102"]))
        )
        == 2
    )
    assert db.scalar(select(func.count()).select_from(EmployeeAssignment)) == 2


def test_sensitive_columns_are_never_mappable_or_stored(hr: Imports, db: Session) -> None:
    data = build(
        {
            "Employees": [
                ["Employee Code", "Full Name", "CTC", "Bank Account No"],
                ["E-201", "Test Pay", 987654, "SECRET-ACCT-1"],
            ]
        }
    )
    job = hr.upload(data)
    headers = {h["text"]: h for h in job["workbook"][0]["headers"]}
    assert headers["CTC"]["excluded"] and headers["Bank Account No"]["excluded"]
    body = {
        "version": job["version"],
        "sections": [
            {
                "section": "employees",
                "sheet": "Employees",
                "header_row": 1,
                "columns": {"1": "employee_code", "2": "full_name", "3": "display_name"},
            }
        ],
    }
    assert (
        hr.send(f"/{job['public_id']}/mapping", body, 422, "PUT")["error"]["code"]
        == "import_mapping_column_excluded"
    )
    job = hr.validate(hr.confirm(job))
    stored = repr([r.values for r in db.scalars(select(ImportRow))]) + repr(
        [r.source for r in db.scalars(select(ImportRow))]
    )
    assert "987654" not in stored and "SECRET-ACCT-1" not in stored
    audits = repr(
        [
            e.event_metadata
            for e in db.scalars(select(AuditEvent).where(AuditEvent.event_type.like("import.%")))
        ]
    )
    assert "987654" not in audits and "Test Pay" not in audits and "SECRET" not in audits


def test_field_errors_block_and_warnings_do_not(hr: Imports) -> None:
    data = standard(
        employees=[
            [42, "Test Numeric Code", "Active", "2025-04-01", None],  # numeric code without a width
            ["E-302", None, "Left", "01-04-25", "bad-email"],
            [
                "E-303",
                "Test Separated",
                "Separated",
                "2025-04-01",
                None,
            ],  # needs a last working day
        ]
    )
    job = hr.prepare(data)
    assert job["status"] == "validation_failed"
    codes = sorted({i["code"] for i in hr.issues(job, severity="error")})
    assert codes == [
        "date_ambiguous",
        "email_invalid",
        "employee_code_numeric",
        "required",
        "separated_requires_last_working_day",
        "status_invalid",
    ]
    issue = next(i for i in hr.issues(job) if i["code"] == "employee_code_numeric")
    assert (issue["sheet"], issue["row_number"], issue["column"], issue["source_value"]) == (
        "Employees",
        2,
        "A",
        "42",
    )
    report = hr.api.get(f"/api/v1/imports/{job['public_id']}/error-report")
    sheet = load_workbook(io.BytesIO(report.content))["Issues"]
    assert sheet.max_row == 1 + len(hr.issues(job))


def test_numeric_codes_with_a_fixed_width_keep_leading_zeros(hr: Imports, db: Session) -> None:
    data = standard(
        employees=[[42, "Test Padded", "Active", "2025-04-01", None]],
        formats={("Employees", 2, 1): "00000"},
    )
    job = hr.commit(hr.prepare(data))
    assert job["status"] == "completed"
    assert (
        db.scalar(select(Employee.employee_code).where(Employee.full_name == "Test Padded"))
        == "00042"
    )


def test_unresolved_designations_are_staged_for_review_never_created(
    hr: Imports, db: Session, setup_org: dict[str, Any]
) -> None:
    from app.models.occupation import Designation

    designations = db.scalar(select(func.count()).select_from(Designation))
    data = standard(
        employees=[["E-401", "Test Spelling", "Active", "2025-04-01", None]],
        assignments=[["E-401", None, "IMP_MELT", "Test Furnace Opr.", "2025-04-01"]],
    )
    job = hr.prepare(data)
    assert job["status"] == "validation_failed"
    issue = next(i for i in hr.issues(job) if i["code"] == "reference_unmapped")
    assert issue["field"] == "designation" and issue["source_value"] == "Test Furnace Opr."
    assert issue["params"]["suggestions"][0]["code"] == "IMP_OPR"  # suggested, never applied
    assert db.scalar(select(func.count()).select_from(Designation)) == designations
    queue = hr.get("/mappings", status="pending")["items"]
    mapping = next(m for m in queue if m["source_text"] == "Test Furnace Opr.")
    assert mapping["kind"] == "designation" and mapping["suggestions"][0]["code"] == "IMP_OPR"

    approved = hr.send(
        f"/mappings/{mapping['public_id']}/approve",
        {
            "version": mapping["version"],
            "target_public_id": setup_org["operator"]["public_id"],
            "reason": "Same designation",
        },
    )
    assert approved["status"] == "approved" and approved["target"]["code"] == "IMP_OPR"
    job = hr.validate(job)
    assert job["status"] == "ready_for_approval"
    row = next(r for r in hr.rows(job) if r["section"] == "assignments")
    assert row["values"]["designation_method"] == "mapping"
    # A decided mapping is never edited: withdrawing keeps it as history and re-queues the label.
    requeued = hr.send(
        f"/mappings/{mapping['public_id']}/withdraw",
        {"version": approved["version"], "reason": "Recheck"},
    )
    assert requeued["status"] == "pending"
    history = db.scalars(
        select(ImportValueMapping.status).where(
            ImportValueMapping.source_text == "Test Furnace Opr."
        )
    ).all()
    assert sorted(history) == ["pending", "superseded"]
    # The approval was withdrawn after validation: the preview is stale.
    assert hr.commit(job, expect=409)["error"]["code"] == "import_revalidation_required"


def test_managers_must_exist_and_domain_rules_are_reported(
    hr: Imports, setup_org: dict[str, Any]
) -> None:
    hr.emp.create("E-500", "Test Existing Manager")
    data = standard(
        employees=[["E-501", "Test Report", "Active", "2025-04-01", None]],
        assignments=[
            ["E-501", None, "IMP_MELT", None, "2025-04-01"],
            ["E-501", None, "OPERATION", None, "2025-05-01"],
        ],
        reporting=[["E-501", "E-999", "2025-04-01"], ["E-501", "E-501", "2025-06-01"]],
    )
    job = hr.prepare(data)
    codes = {(i["field"], i["code"]) for i in hr.issues(job, severity="error")}
    assert ("manager_code", "manager_not_found") in codes  # never silently ignored
    assert (None, "self_reporting") in codes  # the C3 domain rule, from the real service
    assert (None, "primary_overlap") in codes  # second open primary assignment


def test_explicit_skip_and_listed_corrections(hr: Imports, db: Session) -> None:
    hr.emp.create("E-601", "Test Old Name", date_of_joining="2025-01-01")
    data = standard(
        employees=[
            ["E-601", "Test New Name", "On leave", None, None],
            ["E-602", None, None, None, None],
        ],
    )
    job = hr.prepare(data)
    assert job["status"] == "validation_failed"
    rows = hr.rows(job)
    update = next(r for r in rows if r["values"].get("employee_code") == "E-601")
    assert update["outcome"] == "update" and update["changes"] == {
        "full_name": {"from": "Test Old Name", "to": "Test New Name"}
    }
    assert {i["code"] for i in update["issues"]} == {
        "status_change_not_applied"
    }  # status never via import
    broken = next(r for r in rows if r["values"].get("employee_code") == "E-602")
    assert (
        hr.send(
            f"/{job['public_id']}/rows/{broken['id']}/decision",
            {"version": job["version"], "decision": "skip"},
            422,
        )["error"]["code"]
        == "import_skip_reason_required"
    )
    job = hr.send(
        f"/{job['public_id']}/rows/{broken['id']}/decision",
        {"version": job["version"], "decision": "skip", "reason": "Name missing"},
    )
    job = hr.validate(job)
    assert job["status"] == "ready_for_approval"
    # Without approving the listed corrections they are skipped, never silently applied.
    job = hr.commit(job)
    assert job["status"] == "completed_with_skips" and job["counts"]["committed"]["skipped"] == 2
    assert (
        db.scalar(select(Employee.full_name).where(Employee.employee_code == "E-601"))
        == "Test Old Name"
    )
    again = hr.commit(
        hr.prepare(standard(employees=[["E-601", "Test New Name", None, None, None]])),
        apply_updates=True,
    )
    assert again["counts"]["committed"]["updated"] == 1
    assert (
        db.scalar(select(Employee.full_name).where(Employee.employee_code == "E-601"))
        == "Test New Name"
    )


def test_probable_duplicates_need_a_decision(hr: Imports) -> None:
    hr.emp.create("E-701", "Test Twin", date_of_joining="2025-04-01")
    job = hr.prepare(standard(employees=[["E-702", "Test  Twin", "Active", "2025-04-01", None]]))
    assert job["status"] == "validation_failed" and job["counts"]["undecided_duplicates"] == 1
    row = hr.rows(job)[0]
    assert (
        row["issues"][0]["code"] == "probable_duplicate"
        and row["issues"][0]["severity"] == "warning"
    )
    job = hr.send(
        f"/{job['public_id']}/rows/{row['id']}/decision",
        {"version": job["version"], "decision": "distinct", "reason": "Different person"},
    )
    assert hr.validate(job)["status"] == "ready_for_approval"


def test_duplicate_rows_in_file_and_cancel(hr: Imports, db: Session) -> None:
    job = hr.prepare(
        standard(
            employees=[["E-801", "Test A", None, None, None], ["E-801", "Test B", None, None, None]]
        )
    )
    assert [i["code"] for i in hr.issues(job)] == ["duplicate_in_file", "duplicate_in_file"]
    cancelled = hr.send(f"/{job['public_id']}/cancel", {"version": job["version"]})
    assert cancelled["status"] == "cancelled" and not cancelled["file_stored"]
    assert hr.validate(cancelled, 409)["error"]["code"] == "import_invalid_transition"
    assert (
        db.scalar(
            select(func.count()).select_from(Employee).where(Employee.employee_code == "E-801")
        )
        == 0
    )


def test_hostile_uploads_are_rejected_and_audited(hr: Imports, db: Session) -> None:
    assert hr.upload(b"not a workbook", expect=422)["error"]["code"] == "file_not_xlsx"
    assert (
        hr.upload(standard(), name="people.xlsm", expect=422)["error"]["code"]
        == "file_extension_not_allowed"
    )
    response = hr.api.post(
        "/api/v1/imports?profile=employees",
        content=b"x",
        headers={**csrf(hr.token), "Content-Type": "text/csv"},
    )
    assert response.status_code == 415
    assert db.scalar(select(func.count()).select_from(ImportJob)) == 0
    rejected = db.scalars(
        select(AuditEvent).where(AuditEvent.event_type == "import.upload.rejected")
    ).all()
    assert [(e.event_metadata or {})["code"] for e in rejected] == [
        "file_not_xlsx",
        "file_extension_not_allowed",
    ]


def test_permissions(api: TestClient, db: Session, hr: Imports) -> None:
    job = hr.upload(standard(employees=[["E-901", "Test Perm", None, None, None]]))
    anonymous = TestClient(api.app, headers=dict(api.headers))
    assert anonymous.get("/api/v1/imports").status_code == 401
    supervisor = Imports(
        employee_user(
            TestClient(api.app, headers=dict(api.headers)), db, "imp.supervisor", "supervisor"
        )
    )
    assert supervisor.get("", expect=403)["error"]["code"] == "forbidden"
    assert supervisor.upload(standard(), expect=403)["error"]["code"] == "forbidden"
    assert supervisor.validate(job, 403)["error"]["code"] == "forbidden"
    # Every import operation is refused by the server, not merely hidden in the interface.
    jid, body, other = job["public_id"], {"version": job["version"]}, str(uuid.uuid4())
    for method, path, payload in (
        ("GET", f"/{jid}", None),
        ("GET", f"/{jid}/rows", None),
        ("GET", f"/{jid}/issues", None),
        ("GET", f"/{jid}/error-report", None),
        ("GET", "/mappings", None),
        ("GET", "/profiles", None),
        ("GET", "/profiles/employees/template", None),
        ("PUT", f"/{jid}/mapping", {**body, "sections": []}),
        ("POST", f"/{jid}/rows/1/decision", {**body, "decision": None}),
        ("POST", f"/{jid}/commit", {**body, "confirm": True}),
        ("POST", f"/{jid}/cancel", body),
        ("POST", f"/mappings/{other}/approve", {"version": 1, "target_public_id": other}),
        ("POST", f"/mappings/{other}/reject", {"version": 1}),
        ("POST", f"/mappings/{other}/withdraw", {"version": 1}),
    ):
        response = supervisor.api.request(
            method, f"/api/v1/imports{path}", json=payload, headers=csrf(supervisor.token)
        )
        assert response.status_code == 403, (method, path, response.text)
    assert hr.get(f"/{jid}")["status"] == "mapping_required"  # nothing changed
    # No CSRF token: refused before anything else.
    response = hr.api.post(
        f"/api/v1/imports/{job['public_id']}/validate", json={"version": job["version"]}
    )
    assert response.status_code == 403 and response.json()["error"]["code"] == "csrf_failed"


def test_commit_needs_the_domain_permissions_too(api: TestClient, db: Session, hr: Imports) -> None:
    """A role holding only the import permissions cannot write employees through an import."""
    job = hr.prepare(standard(employees=[["E-950", "Test Escalation", None, None, None]]))
    super_api = TestClient(api.app, headers=dict(api.headers))
    make_user(db, "imp.super", roles=("super_admin",))
    token = login(super_api, "imp.super")
    for code in ("imports.view", "imports.employees.commit"):
        assert (
            super_api.put(
                f"/api/v1/admin/access-roles/supervisor/permissions/{code}", headers=csrf(token)
            ).status_code
            == 200
        )
    supervisor = Imports(
        employee_user(
            TestClient(api.app, headers=dict(api.headers)), db, "imp.supervisor2", "supervisor"
        )
    )
    assert supervisor.commit(job, 403)["error"]["code"] == "forbidden"
    assert (
        db.scalar(
            select(func.count()).select_from(Employee).where(Employee.employee_code == "E-950")
        )
        == 0
    )


def test_audit_records_actor_job_and_outcome_without_cell_values(hr: Imports, db: Session) -> None:
    job = hr.commit(
        hr.prepare(
            standard(
                employees=[["E-990", "Test Audited Person", None, None, "audited@example.test"]]
            )
        )
    )
    events = db.scalars(
        select(AuditEvent).where(AuditEvent.target_id == job["public_id"]).order_by(AuditEvent.id)
    ).all()
    assert [e.event_type for e in events] == [
        "import.job.uploaded",
        "import.job.mapping_set",
        "import.job.validated",
        "import.job.committed",
    ]
    assert all(e.actor_user_id is not None for e in events)
    blob = repr([e.event_metadata for e in events])
    assert "Test Audited Person" not in blob and "audited@example.test" not in blob
    assert events[-1].event_metadata == {
        "profile": "employees",
        "profile_version": 1,
        "status": "completed",
        "created": 1,
        "updated": 0,
        "unchanged": 0,
        "skipped": 0,
    }
