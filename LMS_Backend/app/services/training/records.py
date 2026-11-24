"""Training register: programmes, events, sessions and participation.

Rules enforced here (and, where possible, by database CHECKs):

* planned and actual dates are separate; ``completed`` requires an actual start date;
* status changes follow ``ALLOWED_TRANSITIONS``; cancel/postpone need a reason;
* attendance can be recorded only for a scheduled or completed event that has started;
* completion can be recorded only for a completed event, and ``completed`` needs
  attendance (present/partial); a certificate number needs ``completed``;
* separated employees can be recorded only for training that started on or before
  their last working day (historical records stay possible; nothing after separation);
  employees with an unrecorded employment status can (status is never inferred), and
  the response flags them;
* nothing is ever deleted: withdrawals, cancellations and corrections are changes.

Notifications are created inside the same transaction as the change they describe.
"""

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any

from sqlalchemy import Select, func, or_, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.context import RequestMeta
from app.core.errors import AppError
from app.core.ids import uuid7
from app.db.types import utcnow
from app.models.employees import Employee, EmployeeAssignment, EmploymentStatus
from app.models.organisation import Location, OrgUnit
from app.models.training import (
    AttendanceStatus,
    CompletionStatus,
    EventStatus,
    NominationStatus,
    RecordSource,
    SessionStatus,
    TrainerType,
    TrainingEvent,
    TrainingParticipation,
    TrainingProgramme,
    TrainingSession,
)
from app.services import notifications as notify
from app.services.audit_service import AuditEventType, TargetType
from app.services.employees.common import covers_day
from app.services.identity.context import Actor
from app.services.organisation.graph import descendants
from app.services.organisation.support import (
    apply_changes,
    audit,
    business_today,
    clean_text,
    ensure_absent,
    ensure_version,
    flush_unique,
    get_or_404,
    like_pattern,
    normalise_code,
    touch,
)
from app.services.organisation.units import parents_on
from app.services.training.scope import RecordScope
from app.services.training.timeframe import (
    Timeframe,
    classify,
    event_window,
    overlaps_condition,
    timeframe_condition,
)

ALLOWED_TRANSITIONS: dict[str, frozenset[str]] = {
    EventStatus.PLANNED: frozenset({"scheduled", "postponed", "cancelled"}),
    EventStatus.SCHEDULED: frozenset({"planned", "completed", "postponed", "cancelled"}),
    EventStatus.POSTPONED: frozenset({"planned", "scheduled", "cancelled"}),
    EventStatus.COMPLETED: frozenset(),
    EventStatus.CANCELLED: frozenset(),
}
_PROGRAMME_TAKEN = ("training_programme_code_taken", "This programme code is already in use.")
_EVENT_TAKEN = ("training_event_code_taken", "This event code is already in use.")
SCHEDULE_FIELDS = frozenset(
    {"planned_start_date", "planned_end_date", "venue", "online_join_url", "planned_month"}
)


def manhours(duration_minutes: int | None, headcount: int | None) -> float | None:
    """Workbook formula ``Manhours = Duration x Attendees`` (columns M/N), with the
    duration held in minutes (the workbook's unit is unrecorded; see open decisions)."""
    if duration_minutes is None or headcount is None:
        return None
    return round(duration_minutes / 60 * headcount, 2)


def business_date(settings: Settings, moment: datetime) -> date:
    return (moment + timedelta(minutes=settings.business_utc_offset_minutes)).date()


# ----------------------------------------------------------------------- programmes


def get_programme(
    db: Session, public_id: uuid.UUID, *, for_update: bool = False
) -> TrainingProgramme:
    return get_or_404(
        db,
        TrainingProgramme,
        public_id,
        "training_programme_not_found",
        "Training programme not found.",
        for_update=for_update,
    )


def list_programmes(
    db: Session, *, q: str | None, category: str | None, include_inactive: bool
) -> list[TrainingProgramme]:
    statement = select(TrainingProgramme).order_by(TrainingProgramme.title, TrainingProgramme.id)
    if not include_inactive:
        statement = statement.where(TrainingProgramme.is_active.is_(True))
    if q and q.strip():
        pattern = like_pattern(q)
        statement = statement.where(
            or_(TrainingProgramme.title.like(pattern), TrainingProgramme.code.like(pattern))
        )
    if category:
        statement = statement.where(TrainingProgramme.category == category)
    return list(db.scalars(statement.limit(500)))


def _programme_values(values: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for field, raw in values.items():
        if field == "code":
            out[field] = normalise_code(raw)
        elif field == "competency_id":
            out[field] = raw
        elif isinstance(raw, str):
            out[field] = clean_text(raw)
        else:
            out[field] = raw
    if "title" in out and not out["title"]:
        raise AppError(422, "title_required", "A title is required.")
    return out


def create_programme(
    db: Session, *, actor: Actor, meta: RequestMeta, values: Mapping[str, Any]
) -> TrainingProgramme:
    data = _programme_values(values)
    ensure_absent(
        db,
        select(TrainingProgramme.id).where(TrainingProgramme.code == data["code"]),
        *_PROGRAMME_TAKEN,
    )
    programme = TrainingProgramme(
        **data, is_active=True, created_by_user_id=actor.user_id, updated_by_user_id=actor.user_id
    )
    db.add(programme)
    flush_unique(db, *_PROGRAMME_TAKEN)
    audit(
        db,
        actor,
        meta,
        AuditEventType.TRAINING_PROGRAMME_CREATED,
        TargetType.TRAINING_PROGRAMME,
        programme.public_id,
        {"code": programme.code, "title": programme.title},
    )
    return programme


def update_programme(
    db: Session,
    public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    changes: Mapping[str, Any],
) -> TrainingProgramme:
    programme = get_programme(db, public_id, for_update=True)
    ensure_version(programme, version)
    data = _programme_values(changes)
    if data.get("code", programme.code) != programme.code:
        ensure_absent(
            db,
            select(TrainingProgramme.id).where(
                TrainingProgramme.code == data["code"], TrainingProgramme.id != programme.id
            ),
            *_PROGRAMME_TAKEN,
        )
    diff = apply_changes(programme, data)
    if diff:
        touch(programme, actor)
        flush_unique(db, *_PROGRAMME_TAKEN)
        audit(
            db,
            actor,
            meta,
            AuditEventType.TRAINING_PROGRAMME_UPDATED,
            TargetType.TRAINING_PROGRAMME,
            programme.public_id,
            {"code": programme.code, "changes": diff},
        )
    return programme


# --------------------------------------------------------------------------- events


@dataclass(frozen=True)
class EventFilters:
    q: str | None = None
    status: str | None = None
    timeframe: Timeframe | None = None
    unit_id: int | None = None
    include_sub_units: bool = True
    location_id: int | None = None
    programme_id: int | None = None
    category: str | None = None
    calendar_label: str | None = None
    date_from: date | None = None
    date_to: date | None = None


def get_event(db: Session, public_id: uuid.UUID, *, for_update: bool = False) -> TrainingEvent:
    return get_or_404(
        db,
        TrainingEvent,
        public_id,
        "training_event_not_found",
        "Training event not found.",
        for_update=for_update,
    )


def ensure_event_visible(db: Session, event: TrainingEvent, scope: RecordScope) -> None:
    """Limited users see only events in which someone in their scope participates."""
    if scope.is_global:
        return
    visible = db.scalar(
        select(TrainingParticipation.id)
        .where(
            TrainingParticipation.event_id == event.id,
            TrainingParticipation.employee_id.in_(sorted(scope.employee_ids or {0})),
        )
        .limit(1)
    )
    if visible is None:
        raise AppError(404, "training_event_not_found", "Training event not found.")


def _scoped(statement: Select[Any], scope: RecordScope) -> Select[Any]:
    if scope.is_global:
        return statement
    ids = sorted(scope.employee_ids or {0})
    return statement.where(
        TrainingEvent.id.in_(
            select(TrainingParticipation.event_id).where(TrainingParticipation.employee_id.in_(ids))
        )
    )


def calendar_labels(db: Session, scope: RecordScope) -> list[str]:
    statement = _scoped(
        select(TrainingEvent.calendar_label)
        .where(TrainingEvent.calendar_label.is_not(None))
        .distinct()
        .order_by(TrainingEvent.calendar_label),
        scope,
    )
    return [label for label in db.scalars(statement) if label]


def unit_ids_for(db: Session, unit_id: int, day: date, include_sub_units: bool) -> set[int]:
    ids = {unit_id}
    if include_sub_units:
        ids |= descendants(unit_id, parents_on(db, day))
    return ids


def _event_query(
    db: Session, filters: EventFilters, scope: RecordScope, today: date
) -> Select[Any]:
    statement = _scoped(select(TrainingEvent), scope)
    if filters.q and filters.q.strip():
        pattern = like_pattern(filters.q)
        statement = statement.where(
            or_(TrainingEvent.title.like(pattern), TrainingEvent.code.like(pattern))
        )
    if filters.status:
        statement = statement.where(TrainingEvent.status == filters.status)
    if filters.timeframe:
        statement = statement.where(timeframe_condition(filters.timeframe, today))
    if filters.unit_id is not None:
        units = unit_ids_for(db, filters.unit_id, today, filters.include_sub_units)
        statement = statement.where(TrainingEvent.org_unit_id.in_(sorted(units)))
    if filters.location_id is not None:
        statement = statement.where(TrainingEvent.location_id == filters.location_id)
    if filters.programme_id is not None:
        statement = statement.where(TrainingEvent.programme_id == filters.programme_id)
    if filters.category:
        statement = statement.where(
            TrainingEvent.programme_id.in_(
                select(TrainingProgramme.id).where(TrainingProgramme.category == filters.category)
            )
        )
    if filters.calendar_label:
        statement = statement.where(TrainingEvent.calendar_label == filters.calendar_label)
    if filters.date_from or filters.date_to:
        statement = statement.where(
            overlaps_condition(filters.date_from or date.min, filters.date_to or date.max)
        )
    return statement


def list_events(
    db: Session,
    filters: EventFilters,
    scope: RecordScope,
    today: date,
    *,
    limit: int,
    offset: int,
) -> tuple[list[TrainingEvent], int]:
    statement = _event_query(db, filters, scope, today)
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    start = func.coalesce(
        TrainingEvent.actual_start_date,
        TrainingEvent.planned_start_date,
        TrainingEvent.planned_month,
    )
    rows = db.scalars(
        statement.order_by(start.is_(None), start.desc(), TrainingEvent.id.desc())
        .limit(limit)
        .offset(offset)
    ).unique()
    return list(rows), int(total)


def event_timeframe(event: TrainingEvent, settings: Settings, today: date) -> Timeframe:
    window = event_window(
        actual_start=event.actual_start_date,
        actual_end=event.actual_end_date,
        planned_start=event.planned_start_date,
        planned_end=event.planned_end_date,
        session_days=[
            business_date(settings, s.starts_at)
            for s in event.sessions
            if s.status == SessionStatus.SCHEDULED.value
        ],
        planned_month=event.planned_month,
    )
    return classify(event.status, window, today)


def participant_counts(db: Session, event_ids: Sequence[int]) -> dict[int, dict[str, int]]:
    """Per event: nominated (not withdrawn), attended (present/partial), completed."""
    counts: dict[int, dict[str, int]] = {
        event_id: {"participants": 0, "attended": 0, "completed": 0} for event_id in event_ids
    }
    if not event_ids:
        return counts
    rows = db.execute(
        select(
            TrainingParticipation.event_id,
            TrainingParticipation.nomination_status,
            TrainingParticipation.attendance_status,
            TrainingParticipation.completion_status,
        ).where(TrainingParticipation.event_id.in_(list(event_ids)))
    ).all()
    for event_id, nomination, attendance, completion in rows:
        bucket = counts[event_id]
        if nomination != NominationStatus.WITHDRAWN.value:
            bucket["participants"] += 1
        if attendance in (AttendanceStatus.PRESENT.value, AttendanceStatus.PARTIAL.value):
            bucket["attended"] += 1
        if completion == CompletionStatus.COMPLETED.value:
            bucket["completed"] += 1
    return counts


def register_summary(
    db: Session, scope: RecordScope, today: date, filters: EventFilters
) -> dict[str, int]:
    """Counts shown on the register overview. Only recorded facts are counted."""
    base = _event_query(db, filters, scope, today).subquery()
    total = db.scalar(select(func.count()).select_from(base)) or 0
    by_status: dict[str, int] = dict(
        db.execute(select(base.c.status, func.count()).group_by(base.c.status)).all()
    )
    upcoming = (
        db.scalar(
            select(func.count()).select_from(
                _event_query(
                    db,
                    EventFilters(**{**filters.__dict__, "timeframe": Timeframe.UPCOMING}),
                    scope,
                    today,
                ).subquery()
            )
        )
        or 0
    )
    part = select(TrainingParticipation).where(
        TrainingParticipation.event_id.in_(select(base.c.id))
    )
    if not scope.is_global:
        part = part.where(TrainingParticipation.employee_id.in_(sorted(scope.employee_ids or {0})))
    part_sub = part.subquery()
    participations = (
        db.scalar(
            select(func.count())
            .select_from(part_sub)
            .where(part_sub.c.nomination_status != "withdrawn")
        )
        or 0
    )
    attended = (
        db.scalar(
            select(func.count())
            .select_from(part_sub)
            .where(part_sub.c.attendance_status.in_(["present", "partial"]))
        )
        or 0
    )
    completed = (
        db.scalar(
            select(func.count())
            .select_from(part_sub)
            .where(part_sub.c.completion_status == "completed")
        )
        or 0
    )
    return {
        "events_total": int(total),
        "events_planned": int(by_status.get("planned", 0)),
        "events_scheduled": int(by_status.get("scheduled", 0)),
        "events_completed": int(by_status.get("completed", 0)),
        "events_cancelled": int(by_status.get("cancelled", 0)),
        "events_postponed": int(by_status.get("postponed", 0)),
        "events_upcoming": int(upcoming),
        "participations": int(participations),
        "attendance_recorded_present": int(attended),
        "completions_recorded": int(completed),
    }


def _resolve_event_refs(db: Session, values: dict[str, Any]) -> dict[str, Any]:
    out = dict(values)
    for field, model, code, label in (
        ("programme", TrainingProgramme, "training_programme_not_found", "Training programme"),
        ("org_unit", OrgUnit, "org_unit_not_found", "Organisation unit"),
        ("location", Location, "location_not_found", "Location"),
        ("trainer_employee", Employee, "employee_not_found", "Trainer employee"),
    ):
        if field in out:
            public_id = out.pop(field)
            out[f"{field}_id"] = (
                get_or_404(db, model, public_id, code, f"{label} not found.").id  # type: ignore[attr-defined]
                if public_id is not None
                else None
            )
    for field, raw in list(out.items()):
        if isinstance(raw, str) and field not in ("status",):
            out[field] = clean_text(raw)
    if "planned_month" in out and out["planned_month"] is not None:
        out["planned_month"] = out["planned_month"].replace(day=1)
    return out


def _check_event_rules(event: TrainingEvent) -> None:
    if (
        event.trainer_type == TrainerType.INTERNAL.value
        and event.trainer_name
        and not event.trainer_employee_id
    ):
        pass  # a free-text name for an internal trainer is allowed (employee not yet in LMS)
    if event.trainer_employee_id is not None and event.trainer_type == TrainerType.EXTERNAL.value:
        raise AppError(
            422, "trainer_type_mismatch", "An external trainer cannot be an employee record."
        )
    for start, end, code in (
        (event.planned_start_date, event.planned_end_date, "planned_period_invalid"),
        (event.actual_start_date, event.actual_end_date, "actual_period_invalid"),
    ):
        if start and end and end < start:
            raise AppError(422, code, "The end date cannot be before the start date.")
    if event.actual_end_date and not event.actual_start_date:
        raise AppError(422, "actual_start_required", "Record the actual start date first.")
    if event.status == EventStatus.COMPLETED.value and event.actual_start_date is None:
        raise AppError(
            422, "actual_dates_required", "A completed event needs its actual start date."
        )


def create_event(
    db: Session,
    settings: Settings,
    *,
    actor: Actor,
    meta: RequestMeta,
    values: Mapping[str, Any],
) -> TrainingEvent:
    data = _resolve_event_refs(db, dict(values))
    code = data.pop("code", None)
    code = normalise_code(code) if code else f"TE-{uuid7().hex[-10:].upper()}"
    ensure_absent(db, select(TrainingEvent.id).where(TrainingEvent.code == code), *_EVENT_TAKEN)
    if not data.get("title"):
        if data.get("programme_id"):
            programme = db.get(TrainingProgramme, data["programme_id"])
            data["title"] = programme.title if programme else None
        if not data.get("title"):
            raise AppError(422, "title_required", "A title (or a programme) is required.")
    status = data.pop("status", EventStatus.PLANNED.value)
    if status not in (
        EventStatus.PLANNED.value,
        EventStatus.SCHEDULED.value,
        EventStatus.COMPLETED.value,
    ):
        raise AppError(
            422, "invalid_initial_status", "New events start as planned, scheduled or completed."
        )
    event = TrainingEvent(
        code=code,
        status=status,
        source=RecordSource.MANUAL.value,
        created_by_user_id=actor.user_id,
        updated_by_user_id=actor.user_id,
        **data,
    )
    if status == EventStatus.SCHEDULED.value:
        event.published_at = utcnow()
    _check_event_rules(event)
    db.add(event)
    flush_unique(db, *_EVENT_TAKEN)
    audit(
        db,
        actor,
        meta,
        AuditEventType.TRAINING_EVENT_CREATED,
        TargetType.TRAINING_EVENT,
        event.public_id,
        {"code": event.code, "title": event.title, "status": event.status},
    )
    return event


def update_event(
    db: Session,
    settings: Settings,
    public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    changes: Mapping[str, Any],
) -> TrainingEvent:
    event = get_event(db, public_id, for_update=True)
    ensure_version(event, version)
    if event.status == EventStatus.CANCELLED.value:
        raise AppError(409, "training_event_cancelled", "A cancelled event cannot be edited.")
    data = _resolve_event_refs(db, dict(changes))
    data.pop("status", None)
    if "code" in data:
        data["code"] = normalise_code(data["code"]) if data["code"] else event.code
        if data["code"] != event.code:
            ensure_absent(
                db,
                select(TrainingEvent.id).where(
                    TrainingEvent.code == data["code"], TrainingEvent.id != event.id
                ),
                *_EVENT_TAKEN,
            )
    if "title" in data and not data["title"]:
        raise AppError(422, "title_required", "A title is required.")
    diff = apply_changes(event, data)
    if not diff:
        return event
    _check_event_rules(event)
    touch(event, actor)
    flush_unique(db, *_EVENT_TAKEN)
    audit(
        db,
        actor,
        meta,
        AuditEventType.TRAINING_EVENT_UPDATED,
        TargetType.TRAINING_EVENT,
        event.public_id,
        {"code": event.code, "changes": diff},
    )
    if event.status == EventStatus.SCHEDULED.value and SCHEDULE_FIELDS & set(diff):
        db.flush()
        _notify_schedule_change(db, event, sorted(SCHEDULE_FIELDS & set(diff)))
    return event


def _notify_schedule_change(db: Session, event: TrainingEvent, fields: list[str]) -> None:
    what = "venue" if set(fields) <= {"venue", "online_join_url"} else "schedule"
    notify.notify_employees(
        db,
        kind=notify.NotificationType.SCHEDULE_CHANGED,
        employee_ids=notify.active_participant_ids(db, event),
        title=f"Training {what} changed: {event.title}",
        body=f"The {what} of '{event.title}' has changed. Open the event for the current details.",
        key=f"changed:{event.public_id}:v{event.version}",
        event=event,
        link_path=notify.event_link(event),
    )


def change_status(
    db: Session,
    settings: Settings,
    public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    target: str,
    reason: str | None,
    actual_start_date: date | None,
    actual_end_date: date | None,
) -> TrainingEvent:
    event = get_event(db, public_id, for_update=True)
    ensure_version(event, version)
    current = event.status
    if target == current:
        raise AppError(409, "status_unchanged", "The event already has this status.")
    if target not in ALLOWED_TRANSITIONS.get(current, frozenset()):
        raise AppError(
            409,
            "status_transition_not_allowed",
            f"An event cannot move from {current} to {target}.",
        )
    reason = clean_text(reason)
    if target in (EventStatus.CANCELLED.value, EventStatus.POSTPONED.value) and not reason:
        raise AppError(422, "reason_required", "Give a reason for cancelling or postponing.")
    today = business_today(settings)
    if target == EventStatus.SCHEDULED.value and not (
        event.planned_start_date or any(s.status == "scheduled" for s in event.sessions)
    ):
        raise AppError(
            422,
            "schedule_dates_required",
            "Set the planned start date or add a session before scheduling.",
        )
    if target == EventStatus.COMPLETED.value:
        start = actual_start_date or event.actual_start_date
        end = actual_end_date or event.actual_end_date
        if start is None:
            raise AppError(
                422, "actual_dates_required", "Record the actual start date of the training."
            )
        if start > today or (end is not None and end > today):
            raise AppError(422, "actual_date_in_future", "Actual dates cannot be in the future.")
        event.actual_start_date, event.actual_end_date = start, end
    event.status = target
    event.status_reason = reason
    if target == EventStatus.SCHEDULED.value:
        event.published_at = utcnow()
    _check_event_rules(event)
    touch(event, actor)
    db.flush()
    audit(
        db,
        actor,
        meta,
        AuditEventType.TRAINING_EVENT_STATUS_CHANGED,
        TargetType.TRAINING_EVENT,
        event.public_id,
        {"code": event.code, "from": current, "to": target, "reason": reason},
    )
    participants = notify.active_participant_ids(db, event)
    if target == EventStatus.SCHEDULED.value:
        notify.notify_employees(
            db,
            kind=notify.NotificationType.PUBLISHED,
            employee_ids=participants,
            title=f"Training scheduled: {event.title}",
            body=f"'{event.title}' has been scheduled. Open it for dates, venue and instructions.",
            key=f"published:{event.public_id}:v{event.version}",
            event=event,
            link_path=notify.event_link(event),
        )
    elif target in (EventStatus.CANCELLED.value, EventStatus.POSTPONED.value):
        notify.notify_employees(
            db,
            kind=notify.NotificationType.CANCELLED
            if target == EventStatus.CANCELLED.value
            else notify.NotificationType.SCHEDULE_CHANGED,
            employee_ids=participants,
            title=f"Training {target}: {event.title}",
            body=f"'{event.title}' has been {target}. Reason: {reason}",
            key=f"{target}:{event.public_id}:v{event.version}",
            event=event,
            link_path=notify.event_link(event),
        )
    return event


# ------------------------------------------------------------------------- sessions


def get_session(db: Session, event: TrainingEvent, public_id: uuid.UUID) -> TrainingSession:
    session = db.scalar(
        select(TrainingSession)
        .where(TrainingSession.public_id == public_id, TrainingSession.event_id == event.id)
        .with_for_update()
    )
    if session is None:
        raise AppError(404, "training_session_not_found", "Training session not found.")
    return session


def sync_planned_dates(db: Session, settings: Settings, event: TrainingEvent) -> None:
    """Fill empty planned dates from the scheduled sessions (never overwrites)."""
    db.flush()
    db.refresh(event, ["sessions"])
    days = [business_date(settings, s.starts_at) for s in event.sessions if s.status == "scheduled"]
    if days and event.planned_start_date is None:
        event.planned_start_date = min(days)
        event.planned_end_date = max(days) if max(days) != min(days) else None


def _check_session(starts_at: datetime, ends_at: datetime) -> None:
    if ends_at <= starts_at:
        raise AppError(422, "session_period_invalid", "A session must end after it starts.")
    if ends_at - starts_at > timedelta(hours=24):
        raise AppError(
            422, "session_too_long", "A session cannot be longer than 24 hours; add one per day."
        )


def add_session(
    db: Session,
    settings: Settings,
    event_public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    starts_at: datetime,
    ends_at: datetime,
    venue: str | None,
    online_join_url: str | None,
    notes: str | None,
) -> TrainingSession:
    event = get_event(db, event_public_id, for_update=True)
    if event.status in (EventStatus.CANCELLED.value, EventStatus.COMPLETED.value):
        raise AppError(409, "training_event_closed", "Sessions cannot be added to a closed event.")
    _check_session(starts_at, ends_at)
    session = TrainingSession(
        event_id=event.id,
        starts_at=starts_at,
        ends_at=ends_at,
        venue=clean_text(venue),
        online_join_url=clean_text(online_join_url),
        notes=clean_text(notes),
        status=SessionStatus.SCHEDULED.value,
        created_by_user_id=actor.user_id,
        updated_by_user_id=actor.user_id,
    )
    db.add(session)
    sync_planned_dates(db, settings, event)
    touch(event, actor)
    db.flush()
    audit(
        db,
        actor,
        meta,
        AuditEventType.TRAINING_SESSION_CREATED,
        TargetType.TRAINING_EVENT,
        event.public_id,
        {"code": event.code, "session": str(session.public_id), "starts_at": starts_at.isoformat()},
    )
    if event.status == EventStatus.SCHEDULED.value:
        _notify_schedule_change(db, event, ["planned_start_date"])
    return session


def update_session(
    db: Session,
    settings: Settings,
    event_public_id: uuid.UUID,
    session_public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    changes: Mapping[str, Any],
) -> TrainingSession:
    event = get_event(db, event_public_id, for_update=True)
    if event.status in (EventStatus.CANCELLED.value, EventStatus.COMPLETED.value):
        raise AppError(
            409, "training_event_closed", "Sessions of a closed event cannot be changed."
        )
    session = get_session(db, event, session_public_id)
    ensure_version(session, version)
    data: dict[str, Any] = {
        k: (clean_text(v) if isinstance(v, str) else v) for k, v in changes.items()
    }
    if data.get("status") and data["status"] not in {s.value for s in SessionStatus}:
        raise AppError(422, "invalid_session_status", "Unknown session status.")
    _check_session(
        data.get("starts_at") or session.starts_at, data.get("ends_at") or session.ends_at
    )
    diff = apply_changes(session, data)
    if not diff:
        return session
    touch(session, actor)
    touch(event, actor)
    db.flush()
    audit(
        db,
        actor,
        meta,
        AuditEventType.TRAINING_SESSION_UPDATED,
        TargetType.TRAINING_EVENT,
        event.public_id,
        {"code": event.code, "session": str(session.public_id), "changes": diff},
    )
    if event.status == EventStatus.SCHEDULED.value:
        fields = (
            ["venue"]
            if set(diff) <= {"venue", "online_join_url", "notes"}
            else ["planned_start_date"]
        )
        if set(diff) != {"notes"}:
            _notify_schedule_change(db, event, fields)
    return session


# -------------------------------------------------------------------- participation


@dataclass(frozen=True)
class AddResult:
    added: list[TrainingParticipation]
    already: list[str]
    status_unrecorded: list[str]


def event_start_date(settings: Settings, event: TrainingEvent) -> date | None:
    """First day of the event: actual start, else planned start, else the first
    scheduled session, else the planned month. ``None`` when the event has no date."""
    window = event_window(
        actual_start=event.actual_start_date,
        actual_end=event.actual_end_date,
        planned_start=event.planned_start_date,
        planned_end=event.planned_end_date,
        session_days=[
            business_date(settings, s.starts_at)
            for s in event.sessions
            if s.status == SessionStatus.SCHEDULED.value
        ],
        planned_month=event.planned_month,
    )
    return window.start


def add_participants(
    db: Session,
    settings: Settings,
    event_public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    employee_public_ids: Sequence[uuid.UUID],
    nomination_status: str,
) -> AddResult:
    event = get_event(db, event_public_id, for_update=True)
    if event.status == EventStatus.CANCELLED.value:
        raise AppError(
            409, "training_event_cancelled", "A cancelled event cannot take participants."
        )
    if nomination_status not in (
        NominationStatus.NOMINATED.value,
        NominationStatus.CONFIRMED.value,
    ):
        raise AppError(
            422, "invalid_nomination_status", "Add participants as nominated or confirmed."
        )
    unique_ids = list(dict.fromkeys(employee_public_ids))
    employees = list(db.scalars(select(Employee).where(Employee.public_id.in_(unique_ids))))
    if len(employees) != len(unique_ids):
        raise AppError(404, "employee_not_found", "One or more employees were not found.")
    # A separated employee may still be recorded for training that took place during
    # their employment (historical records); never for training after their last day.
    event_start = event_start_date(settings, event)
    separated = [
        e.employee_code
        for e in employees
        if e.employment_status == EmploymentStatus.SEPARATED.value
        and not (
            e.date_of_separation is not None
            and event_start is not None
            and event_start <= e.date_of_separation
        )
    ]
    if separated:
        raise AppError(
            409,
            "employee_separated",
            "Separated employees can be recorded only for training that started on or "
            f"before their last working day: {', '.join(separated)}.",
        )
    existing = {
        row.employee_id: row
        for row in db.scalars(
            select(TrainingParticipation)
            .where(
                TrainingParticipation.event_id == event.id,
                TrainingParticipation.employee_id.in_([e.id for e in employees]),
            )
            .with_for_update()
        )
    }
    added: list[TrainingParticipation] = []
    already: list[str] = []
    for employee in employees:
        row = existing.get(employee.id)
        if row is not None and row.nomination_status != NominationStatus.WITHDRAWN.value:
            already.append(employee.employee_code)
            continue
        if row is not None:  # re-nominating a withdrawn participant
            row.nomination_status = nomination_status
            touch(row, actor)
            added.append(row)
            continue
        row = TrainingParticipation(
            event_id=event.id,
            employee_id=employee.id,
            nomination_status=nomination_status,
            source=RecordSource.MANUAL.value,
            created_by_user_id=actor.user_id,
            updated_by_user_id=actor.user_id,
        )
        db.add(row)
        added.append(row)
    db.flush()
    if added:
        audit(
            db,
            actor,
            meta,
            AuditEventType.TRAINING_PARTICIPANT_ADDED,
            TargetType.TRAINING_EVENT,
            event.public_id,
            {
                "code": event.code,
                "employees": [db.get(Employee, r.employee_id).employee_code for r in added],  # type: ignore[union-attr]
                "nomination_status": nomination_status,
            },
        )
        if event.status in (EventStatus.PLANNED.value, EventStatus.SCHEDULED.value):
            for row in added:
                notify.notify_employees(
                    db,
                    kind=notify.NotificationType.NOMINATED,
                    employee_ids=[row.employee_id],
                    title=f"You have been nominated: {event.title}",
                    body=f"You have been {nomination_status} for '{event.title}'.",
                    key=f"nominated:{row.public_id}:v{row.version}",
                    event=event,
                    link_path=notify.event_link(event),
                )
    status_unrecorded = [e.employee_code for e in employees if e.employment_status is None]
    return AddResult(added, already, status_unrecorded)


def get_participation(
    db: Session, event: TrainingEvent, public_id: uuid.UUID
) -> TrainingParticipation:
    row = db.scalar(
        select(TrainingParticipation)
        .where(
            TrainingParticipation.public_id == public_id, TrainingParticipation.event_id == event.id
        )
        .with_for_update()
    )
    if row is None:
        raise AppError(404, "training_participation_not_found", "Participation record not found.")
    return row


def event_has_started(db: Session, settings: Settings, event: TrainingEvent, today: date) -> bool:
    if event.actual_start_date is not None:
        return event.actual_start_date <= today
    if event.planned_start_date is not None and event.planned_start_date <= today:
        return True
    return any(
        business_date(settings, s.starts_at) <= today
        for s in event.sessions
        if s.status == "scheduled"
    )


def update_participation(
    db: Session,
    settings: Settings,
    event_public_id: uuid.UUID,
    participation_public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    changes: Mapping[str, Any],
) -> TrainingParticipation:
    event = get_event(db, event_public_id, for_update=True)
    row = get_participation(db, event, participation_public_id)
    ensure_version(row, version)
    today = business_today(settings)
    data: dict[str, Any] = {
        k: (clean_text(v) if isinstance(v, str) else v) for k, v in changes.items()
    }
    now = utcnow()

    if "nomination_status" in data and data["nomination_status"] not in {
        s.value for s in NominationStatus
    }:
        raise AppError(422, "invalid_nomination_status", "Unknown nomination status.")
    if "attendance_status" in data or "attended_minutes" in data:
        if event.status not in (EventStatus.SCHEDULED.value, EventStatus.COMPLETED.value):
            raise AppError(
                409,
                "attendance_not_allowed",
                "Attendance can be recorded only for a scheduled or completed event.",
            )
        if not event_has_started(db, settings, event, today):
            raise AppError(
                409,
                "event_not_started",
                "Attendance cannot be recorded before the training starts.",
            )
        status = data.get("attendance_status", row.attendance_status)
        if status is not None and status not in {s.value for s in AttendanceStatus}:
            raise AppError(422, "invalid_attendance_status", "Unknown attendance status.")
        if data.get("attended_minutes") is not None and status not in ("present", "partial"):
            raise AppError(
                422,
                "minutes_need_attendance",
                "Minutes can be recorded only for present or partial.",
            )
        row.attendance_recorded_at = now
        row.attendance_recorded_by_user_id = actor.user_id
    if "completion_status" in data:
        if data["completion_status"] is not None:
            if event.status != EventStatus.COMPLETED.value:
                raise AppError(
                    409,
                    "completion_not_allowed",
                    "Completion can be recorded only after the event is completed.",
                )
            if data["completion_status"] not in {s.value for s in CompletionStatus}:
                raise AppError(422, "invalid_completion_status", "Unknown completion status.")
        row.completion_recorded_at = now
        row.completion_recorded_by_user_id = actor.user_id
    attendance = data.get("attendance_status", row.attendance_status)
    completion = data.get("completion_status", row.completion_status)
    certificate = data.get("certificate_number", row.certificate_number)
    if completion == CompletionStatus.COMPLETED.value and attendance not in ("present", "partial"):
        raise AppError(
            422,
            "completion_needs_attendance",
            "Completion needs attendance recorded as present or partial.",
        )
    if certificate and completion != CompletionStatus.COMPLETED.value:
        raise AppError(
            422,
            "certificate_needs_completion",
            "A certificate can be recorded only for a completed participant.",
        )
    if data.get("nomination_status") == NominationStatus.WITHDRAWN.value and (
        attendance or completion
    ):
        raise AppError(
            409,
            "withdraw_after_attendance",
            "A participant with recorded attendance cannot be withdrawn.",
        )

    before_completion, before_certificate = row.completion_status, row.certificate_number
    diff = apply_changes(row, data)
    if not diff:
        return row
    touch(row, actor)
    db.flush()
    employee = db.get(Employee, row.employee_id)
    audit(
        db,
        actor,
        meta,
        AuditEventType.TRAINING_PARTICIPATION_UPDATED,
        TargetType.TRAINING_EVENT,
        event.public_id,
        {
            "code": event.code,
            "employee": employee.employee_code if employee else None,
            "changes": diff,
        },
    )
    if row.completion_status == "completed" and before_completion != "completed":
        notify.notify_employees(
            db,
            kind=notify.NotificationType.COMPLETED,
            employee_ids=[row.employee_id],
            title=f"Training completed: {event.title}",
            body=f"Your completion of '{event.title}' has been recorded.",
            key=f"completed:{row.public_id}:v{row.version}",
            event=event,
            link_path=notify.event_link(event),
        )
    if row.certificate_number and row.certificate_number != before_certificate:
        notify.notify_employees(
            db,
            kind=notify.NotificationType.CERTIFICATE,
            employee_ids=[row.employee_id],
            title=f"Certificate recorded: {event.title}",
            body=f"Certificate {row.certificate_number} has been recorded for '{event.title}'.",
            key=f"certificate:{row.public_id}:v{row.version}",
            event=event,
            link_path=notify.event_link(event),
        )
    return row


def list_participations(
    db: Session,
    scope: RecordScope,
    *,
    event_id: int | None = None,
    employee_id: int | None = None,
    q: str | None = None,
    unit_ids: set[int] | None = None,
    designation_id: int | None = None,
    attendance: str | None = None,
    completion: str | None = None,
    day: date,
    limit: int = 200,
    offset: int = 0,
) -> tuple[list[TrainingParticipation], int]:
    statement = select(TrainingParticipation).join(
        Employee, Employee.id == TrainingParticipation.employee_id
    )
    if not scope.is_global:
        statement = statement.where(
            TrainingParticipation.employee_id.in_(sorted(scope.employee_ids or {0}))
        )
    if event_id is not None:
        statement = statement.where(TrainingParticipation.event_id == event_id)
    if employee_id is not None:
        statement = statement.where(TrainingParticipation.employee_id == employee_id)
    if q and q.strip():
        pattern = like_pattern(q)
        statement = statement.where(
            or_(Employee.full_name.like(pattern), Employee.employee_code.like(pattern))
        )
    if unit_ids is not None or designation_id is not None:
        assignment = select(EmployeeAssignment.employee_id).where(
            *covers_day(EmployeeAssignment, day)
        )
        if unit_ids is not None:
            assignment = assignment.where(EmployeeAssignment.org_unit_id.in_(sorted(unit_ids)))
        if designation_id is not None:
            assignment = assignment.where(EmployeeAssignment.designation_id == designation_id)
        statement = statement.where(TrainingParticipation.employee_id.in_(assignment))
    if attendance == "not_recorded":
        statement = statement.where(TrainingParticipation.attendance_status.is_(None))
    elif attendance:
        statement = statement.where(TrainingParticipation.attendance_status == attendance)
    if completion == "not_recorded":
        statement = statement.where(TrainingParticipation.completion_status.is_(None))
    elif completion:
        statement = statement.where(TrainingParticipation.completion_status == completion)
    total = db.scalar(select(func.count()).select_from(statement.order_by(None).subquery())) or 0
    rows = db.scalars(
        statement.order_by(Employee.employee_code, TrainingParticipation.id)
        .limit(limit)
        .offset(offset)
    ).unique()
    return list(rows), int(total)


def calendar_entries(
    db: Session,
    settings: Settings,
    scope: RecordScope,
    *,
    start: date,
    end: date,
    filters: EventFilters,
) -> list[tuple[TrainingEvent, TrainingSession | None]]:
    """Calendar items in [start, end]: each scheduled session, or (for events without
    sessions) the event's own window. Derived from the register - nothing is copied."""
    today = business_today(settings)
    events, _ = list_events(
        db,
        EventFilters(**{**filters.__dict__, "date_from": start, "date_to": end}),
        scope,
        today,
        limit=1000,
        offset=0,
    )
    items: list[tuple[TrainingEvent, TrainingSession | None]] = []
    for event in events:
        sessions = [s for s in event.sessions]
        in_range = [s for s in sessions if start <= business_date(settings, s.starts_at) <= end]
        if sessions:
            items.extend((event, s) for s in in_range)
        else:
            items.append((event, None))
    return items
