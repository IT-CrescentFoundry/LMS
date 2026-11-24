"""Training records register and training calendar (first release, migration 0011).

Viewing needs one of ``training.records.view`` (every employee), ``team.learning.view``
(the signed-in employee's reporting team) or ``learning.own.view`` (own records only);
the service narrows every list and refuses records outside that scope with 404.
Changes need ``training_events.manage``. Every change is audited.
"""

import uuid
from datetime import date, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.deps import (
    DbSessionDep,
    RequestMetaDep,
    SettingsDep,
    require_any_permission,
    require_permission,
    require_schema,
)
from app.core.config import Settings
from app.core.errors import AppError
from app.models.employees import Employee
from app.models.occupation import Designation
from app.models.organisation import Location, OrgUnit
from app.models.training import TrainingEvent, TrainingParticipation, TrainingSession
from app.schemas.errors import ErrorResponse
from app.schemas.organisation import RefOut
from app.schemas.training import (
    CalendarItem,
    CalendarOut,
    EmployeeRef,
    EventBrief,
    EventCounts,
    EventCreate,
    EventOut,
    EventStatusChange,
    EventUpdate,
    OffsetPage,
    ParticipantsAdd,
    ParticipantsAddResult,
    ParticipationOut,
    ParticipationUpdate,
    ProgrammeCreate,
    ProgrammeOut,
    ProgrammeUpdate,
    RegisterSummary,
    SessionCreate,
    SessionOut,
    SessionUpdate,
)
from app.services.identity.context import AuthContext
from app.services.identity.permissions import Permission
from app.services.organisation.support import business_today, get_or_404
from app.services.training import records
from app.services.training.records import EventFilters
from app.services.training.scope import RecordScope, record_scope
from app.services.training.timeframe import Timeframe, event_window

SCHEMA = "0011"
router = APIRouter(
    prefix="/training",
    tags=["training: register and calendar"],
    dependencies=[Depends(require_schema(SCHEMA))],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)

ViewTraining = Annotated[
    AuthContext,
    Depends(
        require_any_permission(
            Permission.TRAINING_RECORDS_VIEW,
            Permission.TEAM_LEARNING_VIEW,
            Permission.LEARNING_OWN_VIEW,
            Permission.TRAINING_EVENTS_MANAGE,
        )
    ),
]
ManageTraining = Annotated[
    AuthContext, Depends(require_permission(Permission.TRAINING_EVENTS_MANAGE))
]
Limit = Annotated[int, Query(ge=1, le=200)]
Offset = Annotated[int, Query(ge=0, le=100000)]


def _scope(db: Session, auth: AuthContext, settings: Settings) -> RecordScope:
    # Managing events implies seeing the whole register (the manager of training
    # operations must see every participant to record attendance).
    if auth.has(Permission.TRAINING_EVENTS_MANAGE):
        return RecordScope(None, "global", auth.user.employee_id)
    return record_scope(
        db, auth, business_today(settings), global_permission=Permission.TRAINING_RECORDS_VIEW
    )


# ---------------------------------------------------------------------- presenters


def _ref(entity: OrgUnit | Location | None) -> RefOut | None:
    if entity is None:
        return None
    return RefOut(public_id=entity.public_id, code=entity.code, name=entity.name)


def employee_ref(employee: Employee) -> EmployeeRef:
    return EmployeeRef(
        public_id=employee.public_id,
        employee_code=employee.employee_code,
        name=employee.display_name or employee.full_name,
    )


def session_out(session: TrainingSession) -> SessionOut:
    return SessionOut.model_validate(session, from_attributes=True)


def event_brief(event: TrainingEvent, settings: Settings, today: date) -> EventBrief:
    window = event_window(
        actual_start=event.actual_start_date,
        actual_end=event.actual_end_date,
        planned_start=event.planned_start_date,
        planned_end=event.planned_end_date,
        session_days=[records.business_date(settings, s.starts_at) for s in event.sessions],
        planned_month=event.planned_month,
    )
    return EventBrief(
        public_id=event.public_id,
        code=event.code,
        title=event.title,
        status=event.status,
        timeframe=records.event_timeframe(event, settings, today).value,
        start=window.start,
        end=window.end,
    )


def event_out(
    event: TrainingEvent, settings: Settings, today: date, counts: dict[str, int]
) -> EventOut:
    programme = event.programme
    return EventOut(
        public_id=event.public_id,
        code=event.code,
        title=event.title,
        description=event.description,
        status=event.status,
        status_reason=event.status_reason,
        timeframe=records.event_timeframe(event, settings, today).value,
        delivery_mode=event.delivery_mode,
        programme=RefOut(public_id=programme.public_id, code=programme.code, name=programme.title)
        if programme
        else None,
        category=programme.category if programme else None,
        org_unit=_ref(event.org_unit),
        location=_ref(event.location),
        calendar_label=event.calendar_label,
        planned_month=event.planned_month,
        planned_start_date=event.planned_start_date,
        planned_end_date=event.planned_end_date,
        actual_start_date=event.actual_start_date,
        actual_end_date=event.actual_end_date,
        planned_duration_minutes=event.planned_duration_minutes,
        venue=event.venue,
        online_join_url=event.online_join_url,
        trainer_type=event.trainer_type,
        trainer_employee=employee_ref(event.trainer_employee) if event.trainer_employee else None,
        trainer_name=event.trainer_name,
        provider_name=event.provider_name,
        capacity=event.capacity,
        planned_participant_count=event.planned_participant_count,
        reported_attendance_count=event.reported_attendance_count,
        planned_manhours=records.manhours(
            event.planned_duration_minutes, event.planned_participant_count
        ),
        reported_manhours=records.manhours(
            event.planned_duration_minutes, event.reported_attendance_count
        ),
        target_audience=event.target_audience,
        instructions=event.instructions,
        source=event.source,
        published_at=event.published_at,
        counts=EventCounts(**counts),
        sessions=[session_out(s) for s in event.sessions],
        version=event.version,
    )


def _event_with_counts(db: Session, event: TrainingEvent, settings: Settings) -> EventOut:
    db.refresh(event)
    counts = records.participant_counts(db, [event.id])[event.id]
    return event_out(event, settings, business_today(settings), counts)


def participation_out(
    row: TrainingParticipation, settings: Settings, today: date
) -> ParticipationOut:
    return ParticipationOut(
        public_id=row.public_id,
        employee=employee_ref(row.employee),
        event=event_brief(row.event, settings, today),
        nomination_status=row.nomination_status,
        attendance_status=row.attendance_status,
        attended_minutes=row.attended_minutes,
        completion_status=row.completion_status,
        assessment_result=row.assessment_result,
        certificate_number=row.certificate_number,
        remarks=row.remarks,
        source=row.source,
        attendance_recorded_at=row.attendance_recorded_at,
        completion_recorded_at=row.completion_recorded_at,
        version=row.version,
    )


def _filters(
    db: Session,
    *,
    q: str | None,
    status_filter: str | None,
    timeframe: Timeframe | None,
    unit: uuid.UUID | None,
    include_sub_units: bool,
    location: uuid.UUID | None,
    category: str | None,
    calendar_label: str | None,
    date_from: date | None,
    date_to: date | None,
) -> EventFilters:
    return EventFilters(
        q=q,
        status=status_filter,
        timeframe=timeframe,
        unit_id=get_or_404(db, OrgUnit, unit, "org_unit_not_found", "Unit not found.").id
        if unit
        else None,
        include_sub_units=include_sub_units,
        location_id=get_or_404(db, Location, location, "location_not_found", "Not found.").id
        if location
        else None,
        category=category,
        calendar_label=calendar_label,
        date_from=date_from,
        date_to=date_to,
    )


StatusQ = Annotated[
    str | None,
    Query(alias="status", pattern="^(planned|scheduled|completed|postponed|cancelled)$"),
]
TextQ = Annotated[str | None, Query(max_length=100)]


# ---------------------------------------------------------------------- programmes


@router.get("/programmes", response_model=list[ProgrammeOut], summary="Training catalogue")
def list_programmes(
    _auth: ViewTraining,
    db: DbSessionDep,
    q: TextQ = None,
    category: TextQ = None,
    include_inactive: bool = False,
) -> list[ProgrammeOut]:
    return [
        ProgrammeOut.model_validate(p, from_attributes=True)
        for p in records.list_programmes(
            db, q=q, category=category, include_inactive=include_inactive
        )
    ]


@router.post(
    "/programmes",
    response_model=ProgrammeOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a training programme to the catalogue",
)
def create_programme(
    body: ProgrammeCreate, auth: ManageTraining, db: DbSessionDep, meta: RequestMetaDep
) -> ProgrammeOut:
    programme = records.create_programme(db, actor=auth.actor, meta=meta, values=body.model_dump())
    db.commit()
    return ProgrammeOut.model_validate(programme, from_attributes=True)


@router.patch("/programmes/{public_id}", response_model=ProgrammeOut, summary="Update a programme")
def update_programme(
    public_id: uuid.UUID,
    body: ProgrammeUpdate,
    auth: ManageTraining,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> ProgrammeOut:
    programme = records.update_programme(
        db, public_id, actor=auth.actor, meta=meta, version=body.version, changes=body.changes()
    )
    db.commit()
    return ProgrammeOut.model_validate(programme, from_attributes=True)


# ------------------------------------------------------------------------- summary


@router.get("/summary", response_model=RegisterSummary, summary="Register overview counts")
def summary(
    auth: ViewTraining,
    db: DbSessionDep,
    settings: SettingsDep,
    unit: uuid.UUID | None = None,
    include_sub_units: bool = True,
    location: uuid.UUID | None = None,
) -> RegisterSummary:
    scope = _scope(db, auth, settings)
    filters = _filters(
        db,
        q=None,
        status_filter=None,
        timeframe=None,
        unit=unit,
        include_sub_units=include_sub_units,
        location=location,
        category=None,
        calendar_label=None,
        date_from=None,
        date_to=None,
    )
    counts = records.register_summary(db, scope, business_today(settings), filters)
    return RegisterSummary(scope=scope.kind, **counts)  # type: ignore[arg-type]


# -------------------------------------------------------------------------- events


@router.get("/events", response_model=OffsetPage[EventOut], summary="Training events register")
def list_events(
    auth: ViewTraining,
    db: DbSessionDep,
    settings: SettingsDep,
    q: TextQ = None,
    status_filter: StatusQ = None,
    timeframe: Timeframe | None = None,
    unit: uuid.UUID | None = None,
    include_sub_units: bool = True,
    location: uuid.UUID | None = None,
    category: TextQ = None,
    calendar_label: Annotated[str | None, Query(max_length=150)] = None,
    date_from: date | None = None,
    date_to: date | None = None,
    limit: Limit = 50,
    offset: Offset = 0,
) -> OffsetPage[EventOut]:
    scope = _scope(db, auth, settings)
    today = business_today(settings)
    filters = _filters(
        db,
        q=q,
        status_filter=status_filter,
        timeframe=timeframe,
        unit=unit,
        include_sub_units=include_sub_units,
        location=location,
        category=category,
        calendar_label=calendar_label,
        date_from=date_from,
        date_to=date_to,
    )
    events, total = records.list_events(db, filters, scope, today, limit=limit, offset=offset)
    counts = records.participant_counts(db, [e.id for e in events])
    return OffsetPage[EventOut](
        items=[event_out(e, settings, today, counts[e.id]) for e in events],
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get("/calendar-labels", response_model=list[str], summary="Calendar labels in use")
def calendar_labels(auth: ViewTraining, db: DbSessionDep, settings: SettingsDep) -> list[str]:
    # Only labels of events the caller may see (limited users: their own/team events).
    return records.calendar_labels(db, _scope(db, auth, settings))


@router.post(
    "/events",
    response_model=EventOut,
    status_code=status.HTTP_201_CREATED,
    summary="Record a training event (planned, scheduled or already conducted)",
)
def create_event(
    body: EventCreate,
    auth: ManageTraining,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> EventOut:
    event = records.create_event(
        db, settings, actor=auth.actor, meta=meta, values=body.model_dump()
    )
    db.commit()
    return _event_with_counts(db, event, settings)


@router.get("/events/{public_id}", response_model=EventOut, summary="Training event details")
def get_event(
    public_id: uuid.UUID, auth: ViewTraining, db: DbSessionDep, settings: SettingsDep
) -> EventOut:
    event = records.get_event(db, public_id)
    records.ensure_event_visible(db, event, _scope(db, auth, settings))
    counts = records.participant_counts(db, [event.id])[event.id]
    return event_out(event, settings, business_today(settings), counts)


@router.patch("/events/{public_id}", response_model=EventOut, summary="Update event details")
def update_event(
    public_id: uuid.UUID,
    body: EventUpdate,
    auth: ManageTraining,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> EventOut:
    event = records.update_event(
        db,
        settings,
        public_id,
        actor=auth.actor,
        meta=meta,
        version=body.version,
        changes=body.changes(),
    )
    db.commit()
    return _event_with_counts(db, event, settings)


@router.post(
    "/events/{public_id}/status",
    response_model=EventOut,
    summary="Schedule, complete, postpone or cancel an event",
)
def change_event_status(
    public_id: uuid.UUID,
    body: EventStatusChange,
    auth: ManageTraining,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> EventOut:
    event = records.change_status(
        db,
        settings,
        public_id,
        actor=auth.actor,
        meta=meta,
        version=body.version,
        target=body.status,
        reason=body.reason,
        actual_start_date=body.actual_start_date,
        actual_end_date=body.actual_end_date,
    )
    db.commit()
    return _event_with_counts(db, event, settings)


@router.post(
    "/events/{public_id}/sessions",
    response_model=EventOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a dated session",
)
def add_session(
    public_id: uuid.UUID,
    body: SessionCreate,
    auth: ManageTraining,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> EventOut:
    records.add_session(
        db,
        settings,
        public_id,
        actor=auth.actor,
        meta=meta,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        venue=body.venue,
        online_join_url=body.online_join_url,
        notes=body.notes,
    )
    db.commit()
    return _event_with_counts(db, records.get_event(db, public_id), settings)


@router.patch(
    "/events/{public_id}/sessions/{session_id}",
    response_model=EventOut,
    summary="Reschedule, relocate or cancel a session",
)
def update_session(
    public_id: uuid.UUID,
    session_id: uuid.UUID,
    body: SessionUpdate,
    auth: ManageTraining,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> EventOut:
    records.update_session(
        db,
        settings,
        public_id,
        session_id,
        actor=auth.actor,
        meta=meta,
        version=body.version,
        changes=body.changes(),
    )
    db.commit()
    return _event_with_counts(db, records.get_event(db, public_id), settings)


# ------------------------------------------------------------------- participation


@router.get(
    "/events/{public_id}/participants",
    response_model=list[ParticipationOut],
    summary="Participants of an event (narrowed to your scope)",
)
def event_participants(
    public_id: uuid.UUID, auth: ViewTraining, db: DbSessionDep, settings: SettingsDep
) -> list[ParticipationOut]:
    scope = _scope(db, auth, settings)
    event = records.get_event(db, public_id)
    records.ensure_event_visible(db, event, scope)
    today = business_today(settings)
    rows, _ = records.list_participations(db, scope, event_id=event.id, day=today, limit=1000)
    return [participation_out(r, settings, today) for r in rows]


@router.post(
    "/events/{public_id}/participants",
    response_model=ParticipantsAddResult,
    summary="Nominate or confirm employees",
)
def add_participants(
    public_id: uuid.UUID,
    body: ParticipantsAdd,
    auth: ManageTraining,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> ParticipantsAddResult:
    result = records.add_participants(
        db,
        settings,
        public_id,
        actor=auth.actor,
        meta=meta,
        employee_public_ids=body.employees,
        nomination_status=body.nomination_status,
    )
    db.commit()
    return ParticipantsAddResult(
        added=len(result.added),
        already_participating=result.already,
        employment_status_not_recorded=result.status_unrecorded,
    )


@router.patch(
    "/events/{public_id}/participants/{participation_id}",
    response_model=ParticipationOut,
    summary="Record nomination, attendance, completion or certificate",
)
def update_participation(
    public_id: uuid.UUID,
    participation_id: uuid.UUID,
    body: ParticipationUpdate,
    auth: ManageTraining,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> ParticipationOut:
    row = records.update_participation(
        db,
        settings,
        public_id,
        participation_id,
        actor=auth.actor,
        meta=meta,
        version=body.version,
        changes=body.changes(),
    )
    db.commit()
    db.refresh(row)
    return participation_out(row, settings, business_today(settings))


@router.get(
    "/participations",
    response_model=OffsetPage[ParticipationOut],
    summary="Employee training records (narrowed to your scope)",
)
def list_participations(
    auth: ViewTraining,
    db: DbSessionDep,
    settings: SettingsDep,
    employee: uuid.UUID | None = None,
    mine: bool = False,
    q: TextQ = None,
    unit: uuid.UUID | None = None,
    include_sub_units: bool = True,
    designation: uuid.UUID | None = None,
    attendance: Annotated[
        str | None, Query(pattern="^(present|partial|absent|excused|not_recorded)$")
    ] = None,
    completion: Annotated[
        str | None, Query(pattern="^(completed|not_completed|not_recorded)$")
    ] = None,
    limit: Limit = 100,
    offset: Offset = 0,
) -> OffsetPage[ParticipationOut]:
    scope = _scope(db, auth, settings)
    today = business_today(settings)
    employee_id = None
    if mine:
        if auth.user.employee_id is None:
            return OffsetPage[ParticipationOut](items=[], total=0, limit=limit, offset=offset)
        employee_id = auth.user.employee_id
    elif employee:
        employee_id = get_or_404(db, Employee, employee, "employee_not_found", "Not found.").id
        if not scope.allows(employee_id):
            raise AppError(404, "employee_not_found", "Employee not found.")
    unit_ids = (
        records.unit_ids_for(
            db,
            get_or_404(db, OrgUnit, unit, "org_unit_not_found", "Unit not found.").id,
            today,
            include_sub_units,
        )
        if unit
        else None
    )
    designation_id = (
        get_or_404(db, Designation, designation, "designation_not_found", "Not found.").id
        if designation
        else None
    )
    rows, total = records.list_participations(
        db,
        scope,
        employee_id=employee_id,
        q=q,
        unit_ids=unit_ids,
        designation_id=designation_id,
        attendance=attendance,
        completion=completion,
        day=today,
        limit=limit,
        offset=offset,
    )
    return OffsetPage[ParticipationOut](
        items=[participation_out(r, settings, today) for r in rows],
        total=total,
        limit=limit,
        offset=offset,
    )


# ------------------------------------------------------------------------ calendar


@router.get("/calendar", response_model=CalendarOut, summary="Training calendar for a date range")
def calendar(
    auth: ViewTraining,
    db: DbSessionDep,
    settings: SettingsDep,
    start: date,
    end: date,
    mine: bool = False,
    unit: uuid.UUID | None = None,
    include_sub_units: bool = True,
    location: uuid.UUID | None = None,
    status_filter: StatusQ = None,
    calendar_label: Annotated[str | None, Query(max_length=150)] = None,
) -> CalendarOut:
    if end < start or end - start > timedelta(days=100):
        raise AppError(422, "invalid_range", "Choose a range of at most 100 days.")
    scope = _scope(db, auth, settings)
    if mine:
        own = auth.user.employee_id
        scope = RecordScope(frozenset({own} if own else set()), "own", own)
    filters = _filters(
        db,
        q=None,
        status_filter=status_filter,
        timeframe=None,
        unit=unit,
        include_sub_units=include_sub_units,
        location=location,
        category=None,
        calendar_label=calendar_label,
        date_from=None,
        date_to=None,
    )
    today = business_today(settings)
    entries = records.calendar_entries(db, settings, scope, start=start, end=end, filters=filters)
    my_status: dict[int, str] = {}
    if auth.user.employee_id is not None and entries:
        from sqlalchemy import select

        my_status = dict(
            db.execute(
                select(
                    TrainingParticipation.event_id, TrainingParticipation.nomination_status
                ).where(
                    TrainingParticipation.employee_id == auth.user.employee_id,
                    TrainingParticipation.event_id.in_({e.id for e, _ in entries}),
                )
            ).all()
        )
    items: list[CalendarItem] = []
    for event, session in entries:
        brief = event_brief(event, settings, today)
        items.append(
            CalendarItem(
                event=brief,
                session=session_out(session) if session else None,
                all_day=session is None,
                starts_at=session.starts_at if session else None,
                ends_at=session.ends_at if session else None,
                start_date=records.business_date(settings, session.starts_at)
                if session
                else brief.start,
                end_date=records.business_date(settings, session.ends_at) if session else brief.end,
                month_only=session is None
                and event.planned_start_date is None
                and event.actual_start_date is None
                and event.planned_month is not None,
                venue=(session.venue if session else None) or event.venue,
                online=bool(
                    (session.online_join_url if session else None) or event.online_join_url
                ),
                delivery_mode=event.delivery_mode,
                org_unit=_ref(event.org_unit),
                location=_ref(event.location),
                my_status=my_status.get(event.id),
            )
        )
    items.sort(
        key=lambda i: (i.start_date or date.max, i.starts_at.isoformat() if i.starts_at else "")
    )
    return CalendarOut(scope=scope.kind, start=start, end=end, items=items)  # type: ignore[arg-type]
