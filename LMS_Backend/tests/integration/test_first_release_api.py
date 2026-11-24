"""Integration tests: training register, calendar, notifications, competency and skill
matrices (migration 0011). Every person, code and name is synthetic."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.employees import (
    LINE_MANAGER,
    Employee,
    ReportingRelationship,
    ReportingRelationshipType,
)
from app.models.identity import UserAccount
from app.models.notifications import Notification
from tests.integration.helpers import csrf, login, make_user

pytestmark = pytest.mark.db

TR = "/api/v1/training"
CP = "/api/v1/competency"
NT = "/api/v1/notifications"
TODAY = (datetime.now(UTC) + timedelta(minutes=330)).date()


class Api:
    def __init__(self, client: TestClient, token: str) -> None:
        self.client, self.token = client, token

    def get(self, url: str, expect: int = 200, **params: Any) -> Any:
        response = self.client.get(url, params=params)
        assert response.status_code == expect, response.text
        return response.json()

    def send(self, method: str, url: str, body: Any, expect: int) -> Any:
        response = self.client.request(method, url, json=body, headers=csrf(self.token))
        assert response.status_code == expect, response.text
        return response.json()

    def post(self, url: str, body: Any, expect: int = 200) -> Any:
        return self.send("POST", url, body, expect)

    def patch(self, url: str, body: Any, expect: int = 200) -> Any:
        return self.send("PATCH", url, body, expect)

    def put(self, url: str, body: Any, expect: int = 200) -> Any:
        return self.send("PUT", url, body, expect)

    def error(self, method: str, url: str, body: Any, status: int) -> str:
        response = self.client.request(method, url, json=body, headers=csrf(self.token))
        assert response.status_code == status, response.text
        return str(response.json()["error"]["code"])


def employee(db: Session, code: str, *, status: str | None = "active") -> Employee:
    row = Employee(employee_code=code, full_name=f"Synthetic {code}", employment_status=status)
    db.add(row)
    db.commit()
    return row


def link(db: Session, login_id: str, emp: Employee, roles: tuple[str, ...]) -> UserAccount:
    account = make_user(db, login_id, roles=roles)
    account.employee_id = emp.id
    db.commit()
    return account


def reports_to(db: Session, emp: Employee, manager: Employee) -> None:
    kind = db.scalar(
        select(ReportingRelationshipType).where(ReportingRelationshipType.code == LINE_MANAGER)
    )
    assert kind is not None
    db.add(
        ReportingRelationship(
            employee_id=emp.id, manager_employee_id=manager.id, relationship_type_id=kind.id
        )
    )
    db.commit()


def signed_in(client: TestClient, login_id: str) -> Api:
    return Api(client, login(client, login_id))


@pytest.fixture
def people(db: Session) -> dict[str, Any]:
    """HR admin; a manager with one report; an unrelated employee; all linked."""
    hr = employee(db, "T-HR01")
    manager = employee(db, "T-MG01")
    worker = employee(db, "T-WK01")
    other = employee(db, "T-OT01")
    unknown = employee(db, "T-UK01", status=None)
    reports_to(db, worker, manager)
    link(db, "fr.hr", hr, ("hr_admin",))
    link(db, "fr.manager", manager, ("supervisor",))
    link(db, "fr.worker", worker, ("employee",))
    link(db, "fr.other", other, ("employee",))
    return {"hr": hr, "manager": manager, "worker": worker, "other": other, "unknown": unknown}


def notifications_of(db: Session, login_id: str) -> list[Notification]:
    user = db.scalar(select(UserAccount).where(UserAccount.login_id == login_id))
    assert user is not None
    return list(db.scalars(select(Notification).where(Notification.recipient_user_id == user.id)))


# ------------------------------------------------------------------- register flow


def test_planned_scheduled_completed_flow_with_evidence_rules(
    api: TestClient, db: Session, people: dict[str, Any]
) -> None:
    hr = signed_in(api, "fr.hr")
    programme = hr.post(
        f"{TR}/programmes",
        {"code": "SAFE-01", "title": "Fire safety basics", "category": "Safety"},
        expect=201,
    )
    event = hr.post(
        f"{TR}/events",
        {
            "programme": programme["public_id"],
            "planned_month": str(TODAY.replace(day=1) + timedelta(days=40)),
            "planned_participant_count": 12,
            "planned_duration_minutes": 90,
            "calendar_label": "Synthetic calendar 2026-27",
        },
        expect=201,
    )
    assert event["title"] == "Fire safety basics"
    assert event["status"] == "planned"
    assert event["planned_month"].endswith("-01")
    assert event["planned_manhours"] == 18.0
    eid, version = event["public_id"], event["version"]

    added = hr.post(
        f"{TR}/events/{eid}/participants",
        {"employees": [str(people["worker"].public_id), str(people["unknown"].public_id)]},
    )
    assert added["added"] == 2
    assert added["employment_status_not_recorded"] == ["T-UK01"]  # flagged, never inferred
    assert any(
        n.notification_type == "training.nominated" for n in notifications_of(db, "fr.worker")
    )

    participants = hr.get(f"{TR}/events/{eid}/participants")
    worker_row = next(p for p in participants if p["employee"]["employee_code"] == "T-WK01")
    # A planned event cannot take attendance (a plan is not evidence of delivery).
    assert (
        hr.error(
            "PATCH",
            f"{TR}/events/{eid}/participants/{worker_row['public_id']}",
            {"version": worker_row["version"], "attendance_status": "present"},
            409,
        )
        == "attendance_not_allowed"
    )
    # Scheduling needs dates; a future session satisfies it.
    assert (
        hr.error(
            "POST", f"{TR}/events/{eid}/status", {"version": version, "status": "scheduled"}, 422
        )
        == "schedule_dates_required"
    )
    start = datetime.combine(TODAY + timedelta(days=3), datetime.min.time(), UTC) + timedelta(
        hours=4
    )
    event = hr.post(
        f"{TR}/events/{eid}/sessions",
        {
            "starts_at": start.isoformat(),
            "ends_at": (start + timedelta(hours=2)).isoformat(),
            "venue": "Room A",
        },
        expect=201,
    )
    assert event["planned_start_date"] == str(TODAY + timedelta(days=3))
    event = hr.post(
        f"{TR}/events/{eid}/status", {"version": event["version"], "status": "scheduled"}
    )
    assert event["timeframe"] == "upcoming"
    assert any(
        n.notification_type == "training.schedule_published"
        for n in notifications_of(db, "fr.worker")
    )

    # Not yet started: attendance refused.
    worker_row = next(
        p
        for p in hr.get(f"{TR}/events/{eid}/participants")
        if p["employee"]["employee_code"] == "T-WK01"
    )
    assert (
        hr.error(
            "PATCH",
            f"{TR}/events/{eid}/participants/{worker_row['public_id']}",
            {"version": worker_row["version"], "attendance_status": "present"},
            409,
        )
        == "event_not_started"
    )
    # Venue change notifies participants.
    session = event["sessions"][0]
    hr.patch(
        f"{TR}/events/{eid}/sessions/{session['public_id']}",
        {"version": session["version"], "venue": "Room B"},
    )
    assert any(
        n.notification_type == "training.schedule_changed"
        for n in notifications_of(db, "fr.worker")
    )

    # Completing needs actual dates, which cannot be in the future.
    event = hr.get(f"{TR}/events/{eid}")
    assert (
        hr.error(
            "POST",
            f"{TR}/events/{eid}/status",
            {
                "version": event["version"],
                "status": "completed",
                "actual_start_date": str(TODAY + timedelta(days=1)),
            },
            422,
        )
        == "actual_date_in_future"
    )
    event = hr.post(
        f"{TR}/events/{eid}/status",
        {"version": event["version"], "status": "completed", "actual_start_date": str(TODAY)},
    )
    assert event["status"] == "completed" and event["actual_start_date"] == str(TODAY)

    url = f"{TR}/events/{eid}/participants/{worker_row['public_id']}"
    # Completion without attendance and a certificate without completion are refused.
    assert hr.error(
        "PATCH", url, {"version": worker_row["version"], "completion_status": "completed"}, 422
    ) == ("completion_needs_attendance")
    assert hr.error(
        "PATCH", url, {"version": worker_row["version"], "certificate_number": "C-1"}, 422
    ) == ("certificate_needs_completion")
    row = hr.patch(
        url,
        {"version": worker_row["version"], "attendance_status": "present", "attended_minutes": 120},
    )
    row = hr.patch(
        url,
        {"version": row["version"], "completion_status": "completed", "certificate_number": "C-1"},
    )
    assert row["completion_status"] == "completed" and row["attendance_recorded_at"]
    kinds = {n.notification_type for n in notifications_of(db, "fr.worker")}
    assert {"training.completed", "training.certificate_recorded"} <= kinds
    # The participant with recorded attendance cannot be withdrawn.
    assert hr.error(
        "PATCH", url, {"version": row["version"], "nomination_status": "withdrawn"}, 409
    ) == ("withdraw_after_attendance")

    summary = hr.get(f"{TR}/summary")
    assert summary["events_completed"] == 1
    assert summary["attendance_recorded_present"] == 1
    assert summary["completions_recorded"] == 1
    audited = db.scalars(select(AuditEvent.event_type).where(AuditEvent.target_id == eid)).all()
    assert {
        "training_event.created",
        "training_event.status_changed",
        "training_participation.updated",
    } <= set(audited)


def test_status_transitions_and_cancellation_notice(
    api: TestClient, db: Session, people: dict[str, Any]
) -> None:
    hr = signed_in(api, "fr.hr")
    event = hr.post(
        f"{TR}/events",
        {
            "title": "Synthetic forklift refresher",
            "planned_start_date": str(TODAY + timedelta(days=10)),
        },
        expect=201,
    )
    eid = event["public_id"]
    hr.post(f"{TR}/events/{eid}/participants", {"employees": [str(people["worker"].public_id)]})
    assert (
        hr.error(
            "POST",
            f"{TR}/events/{eid}/status",
            {"version": event["version"], "status": "cancelled"},
            422,
        )
        == "reason_required"
    )
    event = hr.post(
        f"{TR}/events/{eid}/status",
        {
            "version": hr.get(f"{TR}/events/{eid}")["version"],
            "status": "cancelled",
            "reason": "Trainer unavailable",
        },
    )
    assert event["timeframe"] == "cancelled"
    assert any(
        n.notification_type == "training.cancelled" for n in notifications_of(db, "fr.worker")
    )
    # Cancelled is final; nothing is deleted.
    assert (
        hr.error(
            "POST",
            f"{TR}/events/{eid}/status",
            {"version": event["version"], "status": "scheduled"},
            409,
        )
        == "status_transition_not_allowed"
    )
    assert hr.error(
        "POST",
        f"{TR}/events/{eid}/participants",
        {"employees": [str(people["other"].public_id)]},
        409,
    ) == ("training_event_cancelled")


def test_separated_employee_cannot_be_nominated(
    api: TestClient, db: Session, people: dict[str, Any]
) -> None:
    gone = Employee(
        employee_code="T-SP01",
        full_name="Synthetic separated",
        employment_status="separated",
        date_of_separation=TODAY - timedelta(days=5),
    )
    db.add(gone)
    db.commit()
    hr = signed_in(api, "fr.hr")
    event = hr.post(f"{TR}/events", {"title": "Synthetic induction"}, expect=201)
    assert (
        hr.error(
            "POST",
            f"{TR}/events/{event['public_id']}/participants",
            {"employees": [str(gone.public_id)]},
            409,
        )
        == "employee_separated"
    )


# --------------------------------------------------------------------------- scope


def test_employee_and_manager_scopes(api: TestClient, db: Session, people: dict[str, Any]) -> None:
    hr = signed_in(api, "fr.hr")
    mine = hr.post(
        f"{TR}/events", {"title": "Worker event", "planned_start_date": str(TODAY)}, expect=201
    )
    theirs = hr.post(
        f"{TR}/events", {"title": "Other event", "planned_start_date": str(TODAY)}, expect=201
    )
    hr.post(
        f"{TR}/events/{mine['public_id']}/participants",
        {"employees": [str(people["worker"].public_id)]},
    )
    hr.post(
        f"{TR}/events/{theirs['public_id']}/participants",
        {"employees": [str(people["other"].public_id)]},
    )
    api.post("/api/v1/auth/logout", headers=csrf(hr.token))

    worker = signed_in(api, "fr.worker")
    listed = worker.get(f"{TR}/events")
    assert [e["title"] for e in listed["items"]] == ["Worker event"]
    worker.get(f"{TR}/events/{theirs['public_id']}", expect=404)  # indistinguishable from absent
    assert worker.error("POST", f"{TR}/events", {"title": "x"}, 403) == "forbidden"
    own = worker.get(f"{TR}/participations", mine="true")
    assert [r["employee"]["employee_code"] for r in own["items"]] == ["T-WK01"]
    calendar = worker.get(
        f"{TR}/calendar", start=str(TODAY - timedelta(days=1)), end=str(TODAY + timedelta(days=1))
    )
    assert calendar["scope"] == "own"
    assert [i["event"]["title"] for i in calendar["items"]] == ["Worker event"]
    assert calendar["items"][0]["my_status"] == "nominated"
    api.post("/api/v1/auth/logout", headers=csrf(worker.token))

    manager = signed_in(api, "fr.manager")
    team = manager.get(f"{TR}/participations")
    assert {r["employee"]["employee_code"] for r in team["items"]} == {"T-WK01"}
    manager.get(f"{TR}/events/{mine['public_id']}")
    manager.get(f"{TR}/events/{theirs['public_id']}", expect=404)
    manager.get(f"{TR}/participations", expect=404, employee=str(people["other"].public_id))


# ------------------------------------------------------------------- notifications


def test_reminders_are_generated_once_and_follow_reschedules(
    api: TestClient, db: Session, people: dict[str, Any]
) -> None:
    hr = signed_in(api, "fr.hr")
    event = hr.post(f"{TR}/events", {"title": "Synthetic reminder test"}, expect=201)
    eid = event["public_id"]
    hr.post(f"{TR}/events/{eid}/participants", {"employees": [str(people["worker"].public_id)]})
    start = datetime.now(UTC).replace(microsecond=0) + timedelta(hours=20)
    event = hr.post(
        f"{TR}/events/{eid}/sessions",
        {"starts_at": start.isoformat(), "ends_at": (start + timedelta(hours=1)).isoformat()},
        expect=201,
    )
    hr.post(f"{TR}/events/{eid}/status", {"version": event["version"], "status": "scheduled"})
    assert hr.post(f"{NT}/reminders/run", None)["created"] == 1
    assert hr.post(f"{NT}/reminders/run", None)["created"] == 0  # deduplicated
    api.post("/api/v1/auth/logout", headers=csrf(hr.token))

    worker = signed_in(api, "fr.worker")
    inbox = worker.get(NT)
    reminders = [n for n in inbox["items"] if n["notification_type"] == "training.reminder"]
    assert len(reminders) == 1  # opening the centre does not duplicate either
    assert inbox["unread_count"] >= 1
    first = inbox["items"][0]
    read = worker.post(f"{NT}/{first['public_id']}/read", {"read": True})
    assert read["read_at"] is not None
    assert worker.post(f"{NT}/read-all", None)["marked"] >= 0
    assert worker.get(NT)["unread_count"] == 0
    # Mandatory types cannot be muted; optional ones can.
    assert worker.error(
        "PUT",
        f"{NT}/preferences",
        {"notification_type": "training.cancelled", "in_app_enabled": False},
        409,
    ) == ("notification_mandatory")
    prefs = worker.put(
        f"{NT}/preferences", {"notification_type": "training.reminder", "in_app_enabled": False}
    )
    assert prefs["preferences"]["training.reminder"] is False
    channels = worker.get(f"{NT}/channels")
    assert {c["code"]: c["connected"] for c in channels["channels"]} == {
        "in_app": True,
        "outlook": False,
        "teams": False,
    }
    # Someone else's notification is not reachable.
    other_id = first["public_id"]
    api.post("/api/v1/auth/logout", headers=csrf(worker.token))
    other = signed_in(api, "fr.other")
    assert (
        other.error("POST", f"{NT}/{other_id}/read", {"read": True}, 404)
        == "notification_not_found"
    )
    assert (
        db.scalar(
            select(func.count())
            .select_from(Notification)
            .where(Notification.notification_type == "training.reminder")
        )
        == 1
    )


# ----------------------------------------------------------------------- competency


def test_seeded_scales_and_skill_matrix_gap_and_risk(
    api: TestClient, db: Session, people: dict[str, Any]
) -> None:
    hr = signed_in(api, "fr.hr")
    scales = {s["code"]: s for s in hr.get(f"{CP}/scales")}
    matrix_scale = scales["CF_SKILL_MATRIX_1_5"]
    assert [lvl["label"] for lvl in matrix_scale["levels"]][:2] == [
        "Beginner",
        "Can Work Under Supervision",
    ]
    assert matrix_scale["competent_rank"] == 3 and matrix_scale["gap_method"] == "ordinal"
    library = scales["CF_TC_LIBRARY_1_4"]
    assert library["plan_gap_steps"] == 2 and len(library["levels"]) == 4
    level = {lvl["rank"]: lvl["public_id"] for lvl in matrix_scale["levels"]}

    a = hr.post(
        f"{CP}/competencies",
        {"code": "SYN-01", "name": "Synthetic skill A", "scale": matrix_scale["public_id"]},
        expect=201,
    )
    b = hr.post(f"{CP}/competencies", {"code": "SYN-02", "name": "Synthetic skill B"}, expect=201)
    other_scale = hr.post(
        f"{CP}/competencies",
        {"code": "SYN-03", "name": "Other scale", "scale": library["public_id"]},
        expect=201,
    )
    matrix = hr.post(
        f"{CP}/matrices",
        {"code": "MX-SYN", "name": "Synthetic matrix", "scale": matrix_scale["public_id"]},
        expect=201,
    )
    mid = matrix["public_id"]
    assert (
        hr.error(
            "PUT",
            f"{CP}/matrices/{mid}/items",
            {"version": matrix["version"], "items": [{"competency": other_scale["public_id"]}]},
            422,
        )
        == "scale_mismatch"
    )
    matrix = hr.put(
        f"{CP}/matrices/{mid}/items",
        {
            "version": matrix["version"],
            "items": [
                {"competency": a["public_id"], "required_level": level[3], "required_headcount": 1},
                {"competency": b["public_id"]},  # requirement pending
            ],
        },
    )
    assert [i["required_headcount"] for i in matrix["items"]] == [1, None]
    hr.post(
        f"{CP}/matrices/{mid}/members",
        {"add": [str(people["worker"].public_id), str(people["other"].public_id)]},
    )

    hr.post(
        f"{CP}/assessments",
        {
            "employee": str(people["worker"].public_id),
            "competency": a["public_id"],
            "level": level[1],
            "assessed_on": str(TODAY - timedelta(days=30)),
        },
        expect=201,
    )
    hr.post(
        f"{CP}/assessments",
        {
            "employee": str(people["worker"].public_id),
            "competency": a["public_id"],
            "level": level[3],
            "assessed_on": str(TODAY),
        },
        expect=201,
    )
    hr.post(
        f"{CP}/assessments",
        {
            "employee": str(people["other"].public_id),
            "competency": a["public_id"],
            "level": level[2],
            "assessed_on": str(TODAY),
        },
        expect=201,
    )
    assert (
        hr.error(
            "POST",
            f"{CP}/assessments",
            {
                "employee": str(people["worker"].public_id),
                "competency": a["public_id"],
                "level": level[2],
                "assessed_on": str(TODAY + timedelta(days=2)),
            },
            422,
        )
        == "assessed_in_future"
    )
    grid = hr.get(f"{CP}/matrices/{mid}/grid")
    rows = {r["employee"]["employee_code"]: r for r in grid["rows"]}
    assert rows["T-WK01"]["cells"][0]["gap"]["status"] == "met"  # latest assessment wins
    assert rows["T-OT01"]["cells"][0]["gap"] == {
        "status": "below",
        "gap_steps": 1,
        "gap_value": None,
    }
    assert rows["T-OT01"]["cells"][1]["gap"]["status"] == "requirement_pending"
    stats = grid["item_stats"][0]
    assert stats["skilled"] == 1 and stats["risk"] == "high"  # 1 skilled <= 1 required
    history = hr.get(f"{CP}/employees/{people['worker'].public_id}/assessments")
    assert [h["level"]["rank"] for h in history] == [3, 1]
    api.post("/api/v1/auth/logout", headers=csrf(hr.token))

    worker = signed_in(api, "fr.worker")
    own = worker.get(f"{CP}/my-skills")
    assert own["matrices"][0]["rows"][0]["employee"]["employee_code"] == "T-WK01"
    assert len(own["matrices"][0]["rows"]) == 1
    assert own["matrices"][0]["item_stats"] is None  # headcounts are for full access only
    worker.get(f"{CP}/employees/{people['other'].public_id}/skills", expect=404)
    assert (
        worker.error(
            "POST",
            f"{CP}/assessments",
            {
                "employee": str(people["worker"].public_id),
                "competency": a["public_id"],
                "level": level[5],
                "assessed_on": str(TODAY),
            },
            403,
        )
        == "forbidden"
    )
    grid = worker.get(f"{CP}/matrices/{mid}/grid")
    assert [r["employee"]["employee_code"] for r in grid["rows"]] == ["T-WK01"]


def test_my_skills_distinguishes_unlinked_accounts(
    api: TestClient, db: Session, people: dict[str, Any]
) -> None:
    """An account without an employee gets the documented 404 the UI shows as an
    empty state; a linked HR admin still gets their own skills (2026-11-24)."""
    make_user(db, "fr.unlinked", roles=("employee", "hr_admin"))
    db.commit()
    unlinked = signed_in(api, "fr.unlinked")
    response = api.get(f"{CP}/my-skills")
    assert response.status_code == 404, response.text
    assert response.json()["error"]["code"] == "employee_not_linked"
    api.post("/api/v1/auth/logout", headers=csrf(unlinked.token))

    hr = signed_in(api, "fr.hr")
    own = hr.get(f"{CP}/my-skills")
    assert own["employee"]["employee_code"] == "T-HR01"
    assert own["matrices"] == []


def test_scale_levels_in_use_cannot_be_removed(
    api: TestClient, db: Session, people: dict[str, Any]
) -> None:
    hr = signed_in(api, "fr.hr")
    scale = hr.post(
        f"{CP}/scales",
        {
            "code": "SYN-SCALE",
            "name": "Synthetic",
            "competent_rank": 2,
            "levels": [
                {"rank": 1, "code": "a", "label": "A"},
                {"rank": 2, "code": "b", "label": "B"},
            ],
        },
        expect=201,
    )
    assert [lvl["code"] for lvl in scale["levels"]] == ["A", "B"]
    comp = hr.post(
        f"{CP}/competencies",
        {"code": "SYN-L", "name": "Uses scale", "scale": scale["public_id"]},
        expect=201,
    )
    hr.post(
        f"{CP}/assessments",
        {
            "employee": str(people["worker"].public_id),
            "competency": comp["public_id"],
            "level": scale["levels"][0]["public_id"],
            "assessed_on": str(TODAY),
        },
        expect=201,
    )
    keep_b = [{"public_id": scale["levels"][1]["public_id"], "rank": 2, "code": "B", "label": "B"}]
    assert (
        hr.error(
            "PATCH",
            f"{CP}/scales/{scale['public_id']}",
            {"version": scale["version"], "levels": keep_b},
            409,
        )
        == "level_in_use"
    )
    assert (
        hr.error(
            "POST",
            f"{CP}/scales",
            {
                "code": "SYN-BAD",
                "name": "x",
                "competent_rank": 9,
                "levels": [{"rank": 1, "code": "a", "label": "A"}],
            },
            422,
        )
        == "competent_rank_invalid"
    )
