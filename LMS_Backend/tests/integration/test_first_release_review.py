# ruff: noqa: RUF001 - band codes are written with an en dash in the company library
"""Integration tests for the 2026-11-23 post-implementation review fixes (migration 0011).

Covers: historical records for separated employees, scoped calendar labels, reminder
text in business time and the scheduled reminder job, competency draft/approval
governance, grade-band requirement configuration, and additional negative access
tests (managers, employees, notifications). Every person, code and name is synthetic.
"""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app import jobs
from app.core.config import Settings
from app.models.audit import AuditEvent
from app.models.competency import CompetencyAssessment
from app.models.employees import Employee
from app.models.notifications import Notification
from tests.integration.conftest import TransactionalDatabase
from tests.integration.helpers import csrf
from tests.integration.test_first_release_api import (
    CP,
    NT,
    TODAY,
    TR,
    employee,
    link,
    notifications_of,
    people,
    reports_to,
    signed_in,
)

pytestmark = pytest.mark.db
__all__ = ["people"]  # fixture re-used from the first-release suite


def _logout(api: TestClient, token: str) -> None:
    api.post("/api/v1/auth/logout", headers=csrf(token))


# ------------------------------------------------------- separated employees / history


def test_separated_employee_can_be_recorded_for_training_during_employment(
    api: TestClient, db: Session, people: dict[str, Any]
) -> None:
    gone = Employee(
        employee_code="T-SP02",
        full_name="Synthetic separated",
        employment_status="separated",
        date_of_separation=TODAY - timedelta(days=10),
    )
    db.add(gone)  # the schema requires a date for separated employees
    db.commit()
    hr = signed_in(api, "fr.hr")
    past = hr.post(
        f"{TR}/events",
        {
            "title": "Historical induction",
            "status": "completed",
            "actual_start_date": str(TODAY - timedelta(days=40)),
        },
        expect=201,
    )
    result = hr.post(
        f"{TR}/events/{past['public_id']}/participants", {"employees": [str(gone.public_id)]}
    )
    assert result["added"] == 1
    # The historical record can be completed.
    row = hr.get(f"{TR}/events/{past['public_id']}/participants")[0]
    row = hr.patch(
        f"{TR}/events/{past['public_id']}/participants/{row['public_id']}",
        {"version": row["version"], "attendance_status": "present"},
    )
    row = hr.patch(
        f"{TR}/events/{past['public_id']}/participants/{row['public_id']}",
        {"version": row["version"], "completion_status": "completed"},
    )
    assert row["completion_status"] == "completed"

    # Training after the last working day: refused.
    future = hr.post(
        f"{TR}/events", {"title": "Later", "planned_start_date": str(TODAY)}, expect=201
    )
    for person in (gone,):
        assert (
            hr.error(
                "POST",
                f"{TR}/events/{future['public_id']}/participants",
                {"employees": [str(person.public_id)]},
                409,
            )
            == "employee_separated"
        )
    undated = hr.post(f"{TR}/events", {"title": "No date yet"}, expect=201)
    assert (
        hr.error(
            "POST",
            f"{TR}/events/{undated['public_id']}/participants",
            {"employees": [str(gone.public_id)]},
            409,
        )
        == "employee_separated"
    )


# ------------------------------------------------------------------------ scope / IDOR


def test_calendar_labels_and_records_are_limited_to_the_callers_scope(
    api: TestClient, db: Session, people: dict[str, Any]
) -> None:
    hr = signed_in(api, "fr.hr")
    for title, label, person in (
        ("Worker event", "Worker calendar", people["worker"]),
        ("Other event", "Other calendar", people["other"]),
    ):
        event = hr.post(
            f"{TR}/events",
            {"title": title, "calendar_label": label, "planned_start_date": str(TODAY)},
            expect=201,
        )
        hr.post(
            f"{TR}/events/{event['public_id']}/participants",
            {"employees": [str(person.public_id)]},
        )
    assert hr.get(f"{TR}/calendar-labels") == ["Other calendar", "Worker calendar"]
    _logout(api, hr.token)

    worker = signed_in(api, "fr.worker")
    assert worker.get(f"{TR}/calendar-labels") == ["Worker calendar"]
    # Direct API calls for another employee's records are indistinguishable from absent.
    worker.get(f"{TR}/participations", expect=404, employee=str(people["other"].public_id))
    worker.get(f"{CP}/employees/{people['other'].public_id}/assessments", expect=404)
    worker.get(f"{CP}/employees/{people['other'].public_id}/skills", expect=404)
    assert worker.error("POST", f"{CP}/competencies", {"code": "X", "name": "X"}, 403)
    _logout(api, worker.token)

    # A second manager with their own report cannot see the first manager's team, an
    # employee without a manager, or anyone outside their reporting line.
    manager2 = employee(db, "T-MG02")
    report2 = employee(db, "T-WK02")
    loner = employee(db, "T-LN01")  # no reporting manager at all
    reports_to(db, report2, manager2)
    link(db, "fr.manager2", manager2, ("supervisor",))
    m2 = signed_in(api, "fr.manager2")
    team = m2.get(f"{TR}/participations")
    assert {r["employee"]["employee_code"] for r in team["items"]} <= {"T-WK02", "T-MG02"}
    for outsider in (people["worker"], people["other"], loner):
        m2.get(f"{TR}/participations", expect=404, employee=str(outsider.public_id))
        m2.get(f"{CP}/employees/{outsider.public_id}/assessments", expect=404)
    m2.get(f"{CP}/employees/{report2.public_id}/assessments")  # own report: allowed
    assert m2.get(f"{TR}/calendar-labels") == []


def test_notifications_of_another_user_cannot_be_read_or_changed(
    api: TestClient, db: Session, people: dict[str, Any]
) -> None:
    hr = signed_in(api, "fr.hr")
    event = hr.post(f"{TR}/events", {"title": "Nomination notice"}, expect=201)
    hr.post(
        f"{TR}/events/{event['public_id']}/participants",
        {"employees": [str(people["worker"].public_id)]},
    )
    _logout(api, hr.token)
    [notice] = notifications_of(db, "fr.worker")
    other = signed_in(api, "fr.other")
    assert all(i["public_id"] != str(notice.public_id) for i in other.get(NT)["items"])
    assert (
        other.error("POST", f"{NT}/{notice.public_id}/read", {"read": True}, 404)
        == "notification_not_found"
    )
    db.refresh(notice)
    assert notice.read_at is None


# -------------------------------------------------------------------------- reminders


def _scheduled_event_with_session(hr: Any, people: dict[str, Any], starts: datetime) -> Any:
    event = hr.post(f"{TR}/events", {"title": "Synthetic forklift safety"}, expect=201)
    hr.post(
        f"{TR}/events/{event['public_id']}/participants",
        {"employees": [str(people["worker"].public_id)]},
    )
    event = hr.post(
        f"{TR}/events/{event['public_id']}/sessions",
        {
            "starts_at": starts.isoformat(),
            "ends_at": (starts + timedelta(hours=2)).isoformat(),
            "venue": "Synthetic hall",
        },
        expect=201,
    )
    return hr.post(
        f"{TR}/events/{event['public_id']}/status",
        {"version": event["version"], "status": "scheduled"},
    )


def test_scheduled_job_creates_reminders_in_business_time_idempotently(
    api: TestClient,
    db: Session,
    database: TransactionalDatabase,
    app_settings: Settings,
    people: dict[str, Any],
    capsys: pytest.CaptureFixture[str],
) -> None:
    hr = signed_in(api, "fr.hr")
    starts = (datetime.now(UTC) + timedelta(hours=20)).replace(minute=30, second=0, microsecond=0)
    event = _scheduled_event_with_session(hr, people, starts)
    _logout(api, hr.token)  # nobody is signed in when the job runs

    assert (
        jobs.main(["training-reminders", "--dry-run"], database=database, settings=app_settings)
        == 0
    )
    assert "would be created" in capsys.readouterr().out
    reminders = [
        n for n in notifications_of(db, "fr.worker") if n.notification_type == "training.reminder"
    ]
    assert reminders == []  # dry run saved nothing

    assert jobs.main(["training-reminders"], database=database, settings=app_settings) == 0
    assert jobs.main(["training-reminders"], database=database, settings=app_settings) == 0
    reminders = [
        n for n in notifications_of(db, "fr.worker") if n.notification_type == "training.reminder"
    ]
    assert len(reminders) == 1  # second run created nothing (de-duplication)
    local = starts + timedelta(minutes=app_settings.business_utc_offset_minutes)
    assert f"{local:%Y-%m-%d %H:%M} IST" in reminders[0].body
    assert reminders[0].link_path == f"/training/events/{event['public_id']}"

    # Cancelling the event suppresses any further reminders.
    hr = signed_in(api, "fr.hr")
    event = hr.get(f"{TR}/events/{event['public_id']}")
    hr.post(
        f"{TR}/events/{event['public_id']}/status",
        {"version": event["version"], "status": "cancelled", "reason": "Synthetic reason"},
    )
    db.execute(delete(Notification).where(Notification.notification_type == "training.reminder"))
    assert jobs.main(["training-reminders"], database=database, settings=app_settings) == 0
    assert not [
        n for n in notifications_of(db, "fr.worker") if n.notification_type == "training.reminder"
    ]


# --------------------------------------------------------------- competency governance


def _library_scale(hr: Any) -> dict[str, Any]:
    return next(s for s in hr.get(f"{CP}/scales") if s["code"] == "CF_TC_LIBRARY_1_4")


def test_competencies_start_as_drafts_and_approval_is_explicit_and_audited(
    api: TestClient, db: Session, people: dict[str, Any]
) -> None:
    hr = signed_in(api, "fr.hr")
    created = hr.post(
        f"{CP}/competencies",
        {"code": "SYN-GOV", "name": "Synthetic governed", "status": "approved"},
        expect=201,
    )
    assert created["status"] == "draft" and created["approved_at"] is None
    assert [c["code"] for c in hr.get(f"{CP}/competencies", status="draft")["items"]] == ["SYN-GOV"]
    assert hr.get(f"{CP}/competencies", status="approved")["items"] == []
    url = f"{CP}/competencies/{created['public_id']}"
    approved = hr.post(f"{url}/status", {"version": created["version"], "status": "approved"})
    assert approved["status"] == "approved" and approved["approved_at"] is not None
    assert (
        hr.error("POST", f"{url}/status", {"version": approved["version"], "status": "draft"}, 422)
        == "reason_required"
    )
    back = hr.post(
        f"{url}/status",
        {"version": approved["version"], "status": "draft", "reason": "Synthetic re-review"},
    )
    assert back["status"] == "draft" and back["approved_at"] is None
    events = db.scalars(
        select(AuditEvent).where(AuditEvent.event_type == "competency.status_changed")
    ).all()
    assert [(e.event_metadata or {}).get("to") for e in events] == ["approved", "draft"]
    _logout(api, hr.token)

    worker = signed_in(api, "fr.worker")
    assert (
        worker.error(
            "POST", f"{url}/status", {"version": back["version"], "status": "approved"}, 403
        )
        == "forbidden"
    )


def test_grade_band_requirements_are_configurable_audited_and_leave_assessments(
    api: TestClient, db: Session, people: dict[str, Any]
) -> None:
    hr = signed_in(api, "fr.hr")
    scale = _library_scale(hr)
    level = {lvl["rank"]: lvl["public_id"] for lvl in scale["levels"]}
    other_scale = next(s for s in hr.get(f"{CP}/scales") if s["code"] == "CF_SKILL_MATRIX_1_5")
    comp = hr.post(
        f"{CP}/competencies",
        {"code": "SYN-BAND", "name": "Synthetic banded", "scale": scale["public_id"]},
        expect=201,
    )
    url = f"{CP}/competencies/{comp['public_id']}/band-requirements"
    hr.post(
        f"{CP}/assessments",
        {
            "employee": str(people["worker"].public_id),
            "competency": comp["public_id"],
            "level": level[2],
            "assessed_on": str(TODAY - timedelta(days=3)),
        },
        expect=201,
    )
    comp = hr.put(
        url,
        {
            "version": comp["version"],
            "items": [
                {"band_code": "L7", "required_level": level[4]},
                {"band_code": "L6–L5", "band_label": "Managers", "required_level": level[3]},
                {"band_code": "L2–L"},  # requirement pending
            ],
        },
    )
    bands = {b["band_code"]: b for b in comp["band_requirements"]}
    assert set(bands) == {"L7", "L6–L5", "L2–L"}
    assert bands["L6–L5"]["required_level"]["rank"] == 3
    assert bands["L2–L"]["required_level"] is None
    # Changing a requirement keeps the recorded assessment untouched.
    comp = hr.put(
        url,
        {"version": comp["version"], "items": [{"band_code": "L7", "required_level": level[3]}]},
    )
    assert [b["band_code"] for b in comp["band_requirements"]] == ["L7"]
    assert db.scalar(select(CompetencyAssessment.id)) is not None
    assert (
        hr.error(
            "PUT",
            url,
            {
                "version": comp["version"],
                "items": [
                    {"band_code": "L7", "required_level": other_scale["levels"][0]["public_id"]}
                ],
            },
            422,
        )
        == "level_not_in_scale"
    )
    assert (
        hr.error(
            "PUT",
            url,
            {"version": comp["version"], "items": [{"band_code": "L7"}, {"band_code": "l7"}]},
            422,
        )
        == "duplicate_band"
    )
    changes = db.scalars(
        select(AuditEvent).where(AuditEvent.event_type == "competency.band_requirements_changed")
    ).all()
    assert len(changes) == 2
    assert (changes[1].event_metadata or {})["from"]["L7"]["level"] == "L4"
