"""Volume: a synthetic workbook of 2,000 employees, 2,000 assignments and 1,999 reporting
lines validates, commits once and re-imports as unchanged (Stage D exit criterion).

Synthetic data only; crescent_lms_test only (the shared ``db`` fixture is rolled back).
"""

import time

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.employees import Employee, EmployeeAssignment, ReportingRelationship
from app.models.imports import RecordProvenance
from tests.integration.employee_helpers import employee_admin
from tests.integration.test_imports_api import Imports
from tests.support.workbooks import standard

pytestmark = pytest.mark.db

PEOPLE = 2_000
# Generous ceilings that catch accidental quadratic behaviour without being flaky.
VALIDATE_SECONDS = 300
COMMIT_SECONDS = 300


@pytest.fixture
def hr(api: TestClient, db: Session) -> Imports:
    return Imports(employee_admin(api, db, "vol.hr.admin"))


@pytest.fixture
def setup_org(hr: Imports) -> None:
    operation = hr.org.function("OPERATION")
    hr.org.create_unit("IMP_MELT", "Test Melt Shop", "SUB_FUNCTION", operation["public_id"])
    hr.org.post("/designations", {"code": "IMP_OPR", "title": "Test Furnace Operator"})


def _workbook() -> bytes:
    codes = [f"VOL-{n:05d}" for n in range(1, PEOPLE + 1)]
    return standard(
        employees=[
            [code, f"Volume Person {code[4:]}", "Active", "2025-04-01", None] for code in codes
        ],
        assignments=[[code, "Primary", "IMP_MELT", "IMP_OPR", "2025-04-01"] for code in codes],
        # Everyone reports to the first person (a deep chain would also be valid, but
        # a flat team keeps the cycle check representative of real line structures).
        reporting=[[code, codes[0], "2025-04-01"] for code in codes[1:]],
    )


def test_two_thousand_employees_validate_commit_and_reimport(
    hr: Imports, db: Session, setup_org: None
) -> None:
    data = _workbook()
    total = PEOPLE * 2 + PEOPLE - 1

    started = time.monotonic()
    job = hr.prepare(data)
    validate_seconds = time.monotonic() - started
    assert job["status"] == "ready_for_approval", job["counts"]
    assert job["counts"]["rows"] == total and job["counts"]["blocking_errors"] == 0
    assert db.scalar(select(func.count()).select_from(Employee)) == 0  # dry run wrote nothing

    started = time.monotonic()
    job = hr.commit(job)
    commit_seconds = time.monotonic() - started
    assert job["status"] == "completed"
    assert job["counts"]["committed"]["created"] == total
    assert db.scalar(select(func.count()).select_from(Employee)) == PEOPLE
    assert db.scalar(select(func.count()).select_from(EmployeeAssignment)) == PEOPLE
    assert db.scalar(select(func.count()).select_from(ReportingRelationship)) == PEOPLE - 1
    assert db.scalar(select(func.count()).select_from(RecordProvenance)) == total

    again = hr.prepare(data)
    assert again["status"] == "ready_for_approval"
    assert again["counts"]["importable"] == total
    assert hr.commit(again)["counts"]["committed"]["unchanged"] == total
    assert db.scalar(select(func.count()).select_from(Employee)) == PEOPLE

    print(f"\nvolume: validate {validate_seconds:.1f}s, commit {commit_seconds:.1f}s")
    assert validate_seconds < VALIDATE_SECONDS and commit_seconds < COMMIT_SECONDS
