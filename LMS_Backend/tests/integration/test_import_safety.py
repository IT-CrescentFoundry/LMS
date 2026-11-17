"""Stage D acceptance hardening - integration tests on crescent_lms_test.

Uploaded-file cleanup ordering and recovery, abandoned validations, expiry enforced on
every action, commits that no longer match the approved preview, rollback of a commit
that breaks a rule, the fixed header row, and end-to-end protection of sensitive
spreadsheet values. Synthetic data only.
"""

import io
import logging
import os
import time
import uuid
import zipfile
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Select, func, literal_column, select, update
from sqlalchemy import table as sql_table
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.types import utcnow
from app.models.audit import AuditEvent
from app.models.employees import Employee, EmployeeAssignment, ReportingRelationship
from app.models.imports import ImportIssue, ImportJob, ImportRow, RecordProvenance
from app.services.imports.storage import storage_dir
from tests.integration.employee_helpers import employee_admin
from tests.integration.helpers import csrf
from tests.integration.test_imports_api import Imports
from tests.support.workbooks import build, standard

pytestmark = pytest.mark.db


@pytest.fixture
def hr(api: TestClient, db: Session) -> Imports:
    return Imports(employee_admin(api, db, "safe.hr.admin"))


def _files(settings: Settings) -> set[str]:
    return {path.name for path in storage_dir(settings).iterdir()}


def _job_id(job: dict[str, Any]) -> uuid.UUID:
    return uuid.UUID(job["public_id"])


def _set(db: Session, job: dict[str, Any], **values: Any) -> None:
    db.execute(update(ImportJob).where(ImportJob.public_id == _job_id(job)).values(**values))
    db.flush()


def _fail_commit_while(monkeypatch: pytest.MonkeyPatch, condition: Any) -> None:
    """Make Session.commit raise (a simulated database failure) when ``condition`` holds."""
    original = Session.commit

    def commit(self: Session) -> None:
        if condition(self):
            raise RuntimeError("simulated database failure")
        original(self)

    monkeypatch.setattr(Session, "commit", commit)


def _job_pending(status: str) -> Any:
    return lambda session: any(
        isinstance(item, ImportJob) and item.status == status
        for item in (*session.new, *session.dirty)
    )


# ------------------------------------------------------------------------- file cleanup


def test_a_failed_save_keeps_the_open_job_and_its_file(
    hr: Imports, app_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    job = hr.confirm(hr.upload(standard(employees=[["E-C1", "Test Cancel", None, None, None]])))
    name = f"{job['public_id']}.xlsx"
    assert _files(app_settings) == {name}
    with monkeypatch.context() as patch:
        _fail_commit_while(patch, _job_pending("cancelled"))
        response = hr.api.post(
            f"/api/v1/imports/{job['public_id']}/cancel",
            json={"version": job["version"]},
            headers=csrf(hr.token),
        )
    assert response.status_code == 500
    # The status change was not saved, so the workbook was not touched either.
    assert _files(app_settings) == {name}
    current = hr.get(f"/{job['public_id']}")
    assert current["status"] == "mapping_required" and current["file_stored"]
    assert hr.validate(current)["status"] == "ready_for_approval"  # still fully usable


def test_a_failed_deletion_is_completed_by_housekeeping(
    hr: Imports, app_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    job = hr.upload(standard(employees=[["E-C2", "Test Locked File", None, None, None]]))

    def locked(self: Path, missing_ok: bool = False) -> None:
        raise PermissionError("simulated: file in use")

    with monkeypatch.context() as patch:
        patch.setattr(Path, "unlink", locked)
        cancelled = hr.send(f"/{job['public_id']}/cancel", {"version": job["version"]})
    assert cancelled["status"] == "cancelled" and not cancelled["file_stored"]
    assert _files(app_settings) == {f"{job['public_id']}.xlsx"}  # left for retry
    hr.get("")  # the job list runs the storage housekeeping
    assert _files(app_settings) == set()


def test_an_upload_whose_transaction_fails_leaves_no_file(
    hr: Imports, db: Session, app_settings: Settings, monkeypatch: pytest.MonkeyPatch
) -> None:
    with monkeypatch.context() as patch:
        _fail_commit_while(patch, _job_pending("mapping_required"))
        hr.upload(standard(employees=[["E-C3", "Test Upload", None, None, None]]), expect=500)
    assert _files(app_settings) == set()
    assert db.scalar(select(func.count()).select_from(ImportJob)) == 0


def test_housekeeping_removes_orphans_after_a_grace_period_only(
    hr: Imports, app_settings: Settings
) -> None:
    folder = storage_dir(app_settings)
    two_hours_ago = time.time() - 7200

    def place(name: str, *, old: bool) -> str:
        (folder / name).write_bytes(b"synthetic")
        if old:
            os.utime(folder / name, (two_hours_ago, two_hours_ago))
        return name

    old_orphan = place(f"{uuid.uuid4()}.xlsx", old=True)
    old_partial = place(f"{uuid.uuid4()}.part", old=True)
    recent_orphan = place(f"{uuid.uuid4()}.xlsx", old=False)  # an upload may be in flight
    foreign = place("readme.txt", old=True)  # not a name the import storage creates
    held = hr.upload(standard(employees=[["E-C4", "Test Held", None, None, None]]))
    held_name = f"{held['public_id']}.xlsx"
    os.utime(folder / held_name, (two_hours_ago, two_hours_ago))

    hr.get("")
    remaining = _files(app_settings)
    assert old_orphan not in remaining and old_partial not in remaining
    assert remaining == {recent_orphan, foreign, held_name}  # an open job keeps its file


# ---------------------------------------------------------------- recovery and expiry


def test_an_abandoned_validation_returns_to_mapping(hr: Imports, db: Session) -> None:
    job = hr.confirm(hr.upload(standard(employees=[["E-V1", "Test Stuck", None, None, None]])))
    _set(db, job, status="validating")  # as if the validating request had died
    current = hr.get(f"/{job['public_id']}")
    assert current["status"] == "validating"  # recent: it may still be running
    assert (
        hr.send(f"/{job['public_id']}/cancel", {"version": current["version"]}, 409)["error"][
            "code"
        ]
        == "import_invalid_transition"
    )
    _set(db, job, updated_at=utcnow() - timedelta(minutes=31))
    recovered = hr.get(f"/{job['public_id']}")
    assert recovered["status"] == "mapping_required"
    assert db.scalar(
        select(func.count())
        .select_from(AuditEvent)
        .where(
            AuditEvent.event_type == "import.job.validation_abandoned",
            AuditEvent.target_id == job["public_id"],
        )
    )
    assert hr.validate(recovered)["status"] == "ready_for_approval"


def test_expired_jobs_are_refused_even_before_anyone_views_them(
    hr: Imports, db: Session, app_settings: Settings
) -> None:
    job = hr.prepare(standard(employees=[["E-X1", "Test Expiry", None, None, None]]))
    assert job["status"] == "ready_for_approval"
    _set(db, job, uploaded_at=utcnow() - timedelta(days=8))
    # Direct API calls: no page has marked the job expired yet.
    assert hr.commit(job, 409)["error"]["code"] == "import_job_expired"
    assert hr.validate(job, 409)["error"]["code"] == "import_job_expired"
    assert db.scalar(select(func.count()).select_from(Employee)) == 0
    hr.get("")  # housekeeping marks it expired and removes the workbook
    expired = hr.get(f"/{job['public_id']}")
    assert expired["status"] == "expired" and not expired["file_stored"]
    assert _files(app_settings) == set()
    assert hr.commit(expired, 409)["error"]["code"] == "import_job_expired"


# ------------------------------------------------------------------ commit integrity


def test_a_commit_that_no_longer_matches_the_preview_writes_nothing(
    hr: Imports, db: Session
) -> None:
    job = hr.prepare(
        standard(
            employees=[
                ["E-D1", "Test Drift From Workbook", None, None, None],
                ["E-D2", "Test Drift Two", None, None, None],
            ]
        )
    )
    assert {r["outcome"] for r in hr.rows(job)} == {"new"}
    # Someone creates E-D1 on the employee screens after the preview was approved.
    hr.emp.create("E-D1", "Test Drift From Screen")
    refused = hr.commit(job, 409, apply_updates=True)
    assert refused["error"]["code"] == "import_records_changed"
    names = {
        code: name for code, name in db.execute(select(Employee.employee_code, Employee.full_name))
    }
    assert names == {"E-D1": "Test Drift From Screen"}  # not overwritten; E-D2 not created
    assert db.scalar(select(func.count()).select_from(RecordProvenance)) == 0
    current = hr.get(f"/{job['public_id']}")
    assert current["status"] == "ready_for_approval" and current["file_stored"]

    again = hr.validate(current)
    changed = next(r for r in hr.rows(again) if r["values"]["employee_code"] == "E-D1")
    assert changed["outcome"] == "update" and "full_name" in changed["changes"]
    done = hr.commit(again)  # listed corrections not approved: E-D1 is left as it is
    assert done["status"] == "completed_with_skips"
    names = {
        code: name for code, name in db.execute(select(Employee.employee_code, Employee.full_name))
    }
    assert names == {"E-D1": "Test Drift From Screen", "E-D2": "Test Drift Two"}


def test_a_commit_that_breaks_a_rule_is_rolled_back_completely(
    hr: Imports, db: Session, app_settings: Settings
) -> None:
    operation = hr.org.function("OPERATION")
    melt = hr.org.create_unit("SAFE_MELT", "Test Safe Melt", "SUB_FUNCTION", operation["public_id"])
    existing = hr.emp.create("E-R0", "Test Existing Manager")
    job = hr.prepare(
        standard(
            employees=[["E-R1", "Test Rollback New", None, None, None]],
            assignments=[
                ["E-R1", "Primary", "SAFE_MELT", None, "01-04-2025"],
                ["E-R0", "Primary", "SAFE_MELT", None, "01-04-2025"],
            ],
            reporting=[["E-R1", "E-R0", "01-04-2025"]],
        )
    )
    assert job["status"] == "ready_for_approval", job["counts"]
    # After approval, an overlapping primary assignment is recorded on the screens.
    hr.emp.assign(existing, melt["unit"], effective_from="2025-03-01")
    before = {
        "assignments": db.scalar(select(func.count()).select_from(EmployeeAssignment)),
        "reporting": db.scalar(select(func.count()).select_from(ReportingRelationship)),
    }
    failed = hr.commit(job)
    assert failed["status"] == "failed" and not failed["file_stored"]
    # Nothing from the import was kept: not the new employee, not its valid rows.
    assert db.scalar(select(func.count()).select_from(Employee)) == 1
    assert db.scalar(select(func.count()).select_from(EmployeeAssignment)) == before["assignments"]
    assert db.scalar(select(func.count()).select_from(ReportingRelationship)) == before["reporting"]
    assert db.scalar(select(func.count()).select_from(RecordProvenance)) == 0
    commit_issues = [
        i for i in hr.issues(failed) if (i.get("params") or {}).get("phase") == "commit"
    ]
    assert commit_issues and {i["sheet"] for i in commit_issues} == {"Assignments"}
    assert _files(app_settings) == set()
    assert hr.commit(failed, 409)["error"]["code"] == "import_not_ready"


# ------------------------------------------------------------- sensitive information


def test_the_header_row_cannot_be_moved_onto_data_to_bypass_exclusions(
    hr: Imports, db: Session
) -> None:
    job = hr.upload(
        build(
            {
                "Employees": [
                    ["Employee Code", "Full Name", "Aadhaar No"],
                    ["E-H1", "Test Header One", "SYNTH-AADHAAR-0001"],
                    ["E-H2", "Test Header Two", "SYNTH-AADHAAR-0002"],
                ]
            }
        )
    )
    body = {
        "version": job["version"],
        "sections": [
            {
                "section": "employees",
                "sheet": "Employees",
                "header_row": 2,  # a data row posing as the header row
                "columns": {"1": "employee_code", "2": "full_name", "3": "display_name"},
            }
        ],
    }
    error = hr.send(f"/{job['public_id']}/mapping", body, 422, "PUT")["error"]
    assert error["code"] == "import_mapping_header_row"
    assert db.scalar(select(func.count()).select_from(ImportRow)) == 0
    stored = repr(db.scalars(select(ImportJob.column_mapping)).all())
    assert "SYNTH-AADHAAR" not in stored


SENSITIVE = {
    "CTC": "ZZSENS-CTC-1",
    "Basic Salary": "ZZSENS-SAL-2",
    "Bank Account No": "ZZSENS-BANK-3",
    "IFSC": "ZZSENS-IFSC-4",
    "Aadhaar No": "ZZSENS-AADH-5",
    "PAN": "ZZSENS-PAN-6",
    "Date of Birth": "ZZSENS-DOB-7",
    "Gender": "ZZSENS-GEN-8",
    "Residential Address": "ZZSENS-ADDR-9",
    "Blood Group": "ZZSENS-BLOOD-10",
    "Medical Notes": "ZZSENS-MED-11",
    "Father's Name": "ZZSENS-FAM-12",
    "Spouse Name": "ZZSENS-SPOUSE-13",
    "Mobile": "ZZSENS-MOB-14",
    "Personal Email": "ZZSENS-PMAIL-15",
    "Emergency Contact Number": "ZZSENS-EMERG-16",
}


def test_sensitive_values_never_reach_storage_logs_audit_or_reports(
    hr: Imports, db: Session, app_settings: Settings, caplog: pytest.LogCaptureFixture
) -> None:
    caplog.set_level(logging.DEBUG)
    headers = ["Employee Code", "Full Name", "Date of Joining", *SENSITIVE]
    secrets = list(SENSITIVE.values())
    data = build(
        {
            "Employees": [
                headers,
                ["E-S1", "Test Sensitive One", "01-04-2025", *secrets],
                ["+E-S2", "Test Bad Code", "31-02-2025", *secrets],  # two errors
            ]
        }
    )
    job = hr.upload(data)
    flags = {h["text"]: h["excluded"] for h in job["workbook"][0]["headers"]}
    assert all(flags[name] for name in SENSITIVE), flags
    job = hr.validate(hr.confirm(job))
    bad = next(r for r in hr.rows(job) if r["row_number"] == 3)
    job = hr.send(
        f"/{job['public_id']}/rows/{bad['id']}/decision",
        {"version": job["version"], "decision": "skip", "reason": "Synthetic error row"},
    )
    job = hr.commit(hr.validate(job))
    assert job["status"] == "completed_with_skips"

    report = hr.api.get(f"/api/v1/imports/{job['public_id']}/error-report").content
    with zipfile.ZipFile(io.BytesIO(report)) as archive:
        report_xml = "".join(archive.read(n).decode("utf-8", "ignore") for n in archive.namelist())
    assert "'+E-S2" in report_xml  # formula-like source text is neutralised, not dropped

    outputs = [
        repr(job),
        repr(hr.rows(job)),
        repr(hr.issues(job)),
        repr(hr.get("")),
        report_xml,
        caplog.text,
    ]
    for table in (
        "import_job",
        "import_row",
        "import_issue",
        "import_value_mapping",
        "record_provenance",
        "audit_event",
        "employee",
        "employee_assignment",
        "reporting_relationship",
    ):
        everything: Select[Any] = select(literal_column("*")).select_from(sql_table(table))
        outputs.append(repr(db.execute(everything).all()))
    blob = "\n".join(outputs)
    leaked = [value for value in secrets if value in blob]
    assert leaked == []
    assert "ZZSENS" not in blob
    assert _files(app_settings) == set()  # the workbook itself is gone after the commit
    assert (db.scalar(select(func.count()).select_from(ImportIssue)) or 0) > 0  # issues stored
