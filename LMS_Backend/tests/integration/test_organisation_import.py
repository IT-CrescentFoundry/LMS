"""Import profile ``organisation`` v1: preview without writing, parents first, updates of
existing units only after explicit approval, and transactional commit with provenance.

All unit codes and names are synthetic."""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.imports import RecordProvenance
from app.models.organisation import OrgUnit
from tests.integration.employee_helpers import employee_admin
from tests.integration.helpers import csrf, login, make_user
from tests.integration.test_imports_api import Imports
from tests.support.workbooks import build

pytestmark = pytest.mark.db

HEADERS = ["Unit Code", "Unit Name", "Unit Type", "Parent Unit Code"]


@pytest.fixture
def hr(api: TestClient, db: Session) -> Imports:
    return Imports(employee_admin(api, db, "orgimp.hr"))


def _workbook(rows: list[list[Any]]) -> bytes:
    return build({"Organisation Units": [HEADERS, *rows]})


def _prepare(hr: Imports, data: bytes) -> dict[str, Any]:
    job = hr.upload(data, name="units.xlsx", profile="organisation")
    return dict(hr.validate(hr.confirm(job)))


def _outcomes(hr: Imports, job: dict[str, Any]) -> dict[str, str]:
    return {r["values"]["unit_code"]: r["outcome"] for r in hr.rows(job)}


def test_preview_then_commit_creates_children_after_parents(hr: Imports, db: Session) -> None:
    data = _workbook(
        [
            # Child listed before its parent: ordering is resolved by the import.
            ["SYN-DEP-QA", "Synthetic Quality", "DEPARTMENT", "SYN-SUB-OPS"],
            ["SYN-SUB-OPS", "Synthetic Plant Ops", "Sub-function", "OPERATION"],
        ]
    )
    job = _prepare(hr, data)
    assert job["status"] == "ready_for_approval", job
    assert _outcomes(hr, job) == {"SYN-DEP-QA": "new", "SYN-SUB-OPS": "new"}
    # The dry run wrote nothing.
    assert (
        db.scalar(select(func.count()).select_from(OrgUnit).where(OrgUnit.code.like("SYN-%"))) == 0
    )
    job = hr.commit(job)
    assert job["status"] == "completed"
    created = {u.code for u in db.scalars(select(OrgUnit).where(OrgUnit.code.like("SYN-%")))}
    assert created == {"SYN-DEP-QA", "SYN-SUB-OPS"}
    tree_child = hr.org.get("/units", q="SYN-DEP-QA")["items"][0]
    assert tree_child["parent"]["code"] == "SYN-SUB-OPS"
    assert (
        db.scalar(
            select(func.count())
            .select_from(RecordProvenance)
            .where(RecordProvenance.target_type == "org_unit")
        )
        == 2
    )
    # Uploading the same file again changes nothing: every row is unchanged.
    again = _prepare(hr, data)
    assert set(_outcomes(hr, again).values()) == {"unchanged"}


def test_blocking_errors_are_reported_and_nothing_is_written(hr: Imports, db: Session) -> None:
    hr.org.create_unit(
        "SYN-EXIST", "Synthetic Existing", "SUB_FUNCTION", hr.org.function("OPERATION")["public_id"]
    )
    data = _workbook(
        [
            ["SYN-A", "Synthetic A", "NOT_A_TYPE", ""],
            ["SYN-B", "Synthetic B", "DEPARTMENT", "NO-SUCH-PARENT"],
            ["SYN-C", "Synthetic C", "DEPARTMENT", "SYN-D"],
            ["SYN-D", "Synthetic D", "DEPARTMENT", "SYN-C"],
            ["SYN-DUP", "Synthetic Dup 1", "DEPARTMENT", "OPERATION"],
            ["SYN-DUP", "Synthetic Dup 2", "DEPARTMENT", "OPERATION"],
            ["SYN-EXIST", "Renamed by import", "SUB_FUNCTION", "OPERATION"],
        ]
    )
    job = _prepare(hr, data)
    assert job["status"] == "validation_failed"
    codes = {(i["code"]) for i in hr.issues(job)}
    assert {
        "unit_type_unknown",
        "parent_not_found",
        "parent_cycle_in_file",
        "duplicate_in_file",
    } <= codes
    # The existing unit's different name is a proposed update, never an error.
    assert _outcomes(hr, job)["SYN-EXIST"] == "update"
    assert (
        db.scalar(select(OrgUnit.name).where(OrgUnit.code == "SYN-EXIST")) == "Synthetic Existing"
    )
    hr.commit(job, expect=409)


def test_commit_needs_organisation_manage(api: TestClient, db: Session) -> None:
    make_user(db, "orgimp.viewer", roles=("employee",))
    token = login(api, "orgimp.viewer")
    response = api.post(
        "/api/v1/imports?profile=organisation",
        content=_workbook([["SYN-X", "X", "DEPARTMENT", "OPERATION"]]),
        headers={
            **csrf(token),
            "Content-Type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        },
    )
    assert response.status_code == 403


def test_existing_units_are_updated_only_after_explicit_approval(hr: Imports, db: Session) -> None:
    ops = hr.org.function("OPERATION")["public_id"]
    hr.org.create_unit(
        "SYN-OLDP", "Synthetic Old Parent", "SUB_FUNCTION", ops, effective_from="2026-01-01"
    )
    hr.org.create_unit(
        "SYN-NEWP", "Synthetic New Parent", "SUB_FUNCTION", ops, effective_from="2026-01-01"
    )
    old_parent = hr.org.get("/units", q="SYN-OLDP")["items"][0]["public_id"]
    hr.org.create_unit(
        "SYN-MOVE", "Synthetic Movable", "DEPARTMENT", old_parent, effective_from="2026-01-01"
    )
    data = _workbook([["SYN-MOVE", "Synthetic Renamed", "DEPARTMENT", "SYN-NEWP"]])

    # Preview: the differences are listed, with the move's effective date; nothing written.
    job = _prepare(hr, data)
    assert job["status"] == "ready_for_approval", job
    [row] = hr.rows(job)
    assert row["outcome"] == "update"
    assert row["changes"]["unit_name"] == {"from": "Synthetic Movable", "to": "Synthetic Renamed"}
    assert row["changes"]["parent_code"]["from"] == "SYN-OLDP"
    assert row["changes"]["parent_code"]["to"] == "SYN-NEWP"
    assert row["changes"]["parent_code"]["effective_date"]
    assert db.scalar(select(OrgUnit.name).where(OrgUnit.code == "SYN-MOVE")) == "Synthetic Movable"

    # Approved without "apply updates": the unit stays exactly as it was.
    done = hr.commit(job)
    assert done["status"] == "completed_with_skips"  # the update row was skipped
    assert db.scalar(select(OrgUnit.name).where(OrgUnit.code == "SYN-MOVE")) == "Synthetic Movable"

    # Approved with "apply updates": audited correction + effective-dated move.
    job = _prepare(hr, data)
    done = hr.commit(job, apply_updates=True)
    assert done["status"] == "completed"
    unit = hr.org.get("/units", q="SYN-MOVE")["items"][0]
    assert unit["name"] == "Synthetic Renamed"
    assert unit["parent"]["code"] == "SYN-NEWP"
    history = hr.org.get(f"/units/{unit['public_id']}/history")
    assert len(history["placements"]) == 2  # the previous placement is kept
    kinds = set(
        db.scalars(select(AuditEvent.event_type).where(AuditEvent.target_id == unit["public_id"]))
    )
    assert {"org_unit.corrected", "org_unit.moved"} <= kinds

    # Re-importing the same file is now unchanged; a blank parent never removes one.
    again = _prepare(hr, data)
    assert _outcomes(hr, again) == {"SYN-MOVE": "unchanged"}
    blank = _prepare(hr, _workbook([["SYN-MOVE", "Synthetic Renamed", "DEPARTMENT", ""]]))
    assert _outcomes(hr, blank) == {"SYN-MOVE": "unchanged"}
