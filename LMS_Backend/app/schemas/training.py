"""Training register, calendar and notification schemas (first release)."""

import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, Field

from app.schemas.organisation import Code, PatchModel, RefOut, Version

DeliveryMode = Literal["classroom", "online", "hybrid", "ojt"]
EventStatus = Literal["planned", "scheduled", "completed", "postponed", "cancelled"]
TimeframeName = Literal["past", "ongoing", "upcoming", "unscheduled", "cancelled"]
TrainerType = Literal["internal", "external"]
Title = Annotated[str, Field(min_length=1, max_length=250)]
Text500 = Annotated[str, Field(max_length=500)]
LongText = Annotated[str, Field(max_length=10000)]


class OffsetPage[T](BaseModel):
    items: list[T]
    total: int
    limit: int
    offset: int


# ----------------------------------------------------------------------- programmes


class ProgrammeFields(BaseModel):
    title: Title | None = None
    category: Annotated[str, Field(max_length=100)] | None = None
    description: LongText | None = None
    objectives: LongText | None = None
    target_audience: Text500 | None = None
    default_delivery_mode: DeliveryMode | None = None
    standard_duration_minutes: Annotated[int, Field(gt=0, le=100000)] | None = None


class ProgrammeCreate(ProgrammeFields):
    code: Code
    title: Title


class ProgrammeUpdate(ProgrammeFields, PatchModel):
    required_if_sent = ("code", "title", "is_active")
    version: Version
    code: Code | None = None
    is_active: bool | None = None


class ProgrammeOut(BaseModel):
    public_id: uuid.UUID
    code: str
    title: str
    category: str | None
    description: str | None
    objectives: str | None
    target_audience: str | None
    default_delivery_mode: str | None
    standard_duration_minutes: int | None
    is_active: bool
    version: int


# --------------------------------------------------------------------------- events


class EventFields(BaseModel):
    title: Title | None = None
    programme: uuid.UUID | None = None
    description: LongText | None = None
    delivery_mode: DeliveryMode | None = None
    org_unit: uuid.UUID | None = None
    location: uuid.UUID | None = None
    calendar_label: Annotated[str, Field(max_length=150)] | None = None
    planned_month: date | None = Field(default=None, description="Any day of the month.")
    planned_start_date: date | None = None
    planned_end_date: date | None = None
    actual_start_date: date | None = None
    actual_end_date: date | None = None
    planned_duration_minutes: Annotated[int, Field(gt=0, le=100000)] | None = None
    venue: Annotated[str, Field(max_length=250)] | None = None
    online_join_url: Annotated[str, Field(max_length=500, pattern=r"^https://")] | None = None
    trainer_type: TrainerType | None = None
    trainer_employee: uuid.UUID | None = None
    trainer_name: Annotated[str, Field(max_length=200)] | None = None
    provider_name: Annotated[str, Field(max_length=200)] | None = None
    capacity: Annotated[int, Field(gt=0, le=100000)] | None = None
    planned_participant_count: Annotated[int, Field(ge=0, le=100000)] | None = None
    reported_attendance_count: Annotated[int, Field(ge=0, le=100000)] | None = Field(
        default=None, description="Headcount reported by the organiser; not individual attendance."
    )
    target_audience: Text500 | None = None
    instructions: LongText | None = None


class EventCreate(EventFields):
    code: Code | None = None
    status: Literal["planned", "scheduled", "completed"] = "planned"


class EventUpdate(EventFields, PatchModel):
    required_if_sent = ("title",)
    version: Version
    code: Code | None = None


class EventStatusChange(BaseModel):
    version: Version
    status: EventStatus
    reason: Text500 | None = None
    actual_start_date: date | None = None
    actual_end_date: date | None = None


class SessionOut(BaseModel):
    public_id: uuid.UUID
    starts_at: datetime
    ends_at: datetime
    venue: str | None
    online_join_url: str | None
    status: str
    notes: str | None
    version: int


class SessionCreate(BaseModel):
    starts_at: AwareDatetime
    ends_at: AwareDatetime
    venue: Annotated[str, Field(max_length=250)] | None = None
    online_join_url: Annotated[str, Field(max_length=500, pattern=r"^https://")] | None = None
    notes: Text500 | None = None


class SessionUpdate(PatchModel):
    required_if_sent = ("starts_at", "ends_at", "status")
    version: Version
    starts_at: AwareDatetime | None = None
    ends_at: AwareDatetime | None = None
    venue: Annotated[str, Field(max_length=250)] | None = None
    online_join_url: Annotated[str, Field(max_length=500, pattern=r"^https://")] | None = None
    notes: Text500 | None = None
    status: Literal["scheduled", "cancelled"] | None = None


class EmployeeRef(BaseModel):
    public_id: uuid.UUID
    employee_code: str
    name: str


class EventCounts(BaseModel):
    participants: int
    attended: int
    completed: int


class EventOut(BaseModel):
    public_id: uuid.UUID
    code: str
    title: str
    description: str | None
    status: str
    status_reason: str | None
    timeframe: TimeframeName
    delivery_mode: str | None
    programme: RefOut | None
    category: str | None
    org_unit: RefOut | None
    location: RefOut | None
    calendar_label: str | None
    planned_month: date | None
    planned_start_date: date | None
    planned_end_date: date | None
    actual_start_date: date | None
    actual_end_date: date | None
    planned_duration_minutes: int | None
    venue: str | None
    online_join_url: str | None
    trainer_type: str | None
    trainer_employee: EmployeeRef | None
    trainer_name: str | None
    provider_name: str | None
    capacity: int | None
    planned_participant_count: int | None
    reported_attendance_count: int | None
    planned_manhours: float | None
    reported_manhours: float | None
    target_audience: str | None
    instructions: str | None
    source: str
    published_at: datetime | None
    counts: EventCounts
    sessions: list[SessionOut]
    version: int


class RegisterSummary(BaseModel):
    scope: Literal["global", "team", "own", "none"]
    events_total: int
    events_planned: int
    events_scheduled: int
    events_completed: int
    events_cancelled: int
    events_postponed: int
    events_upcoming: int
    participations: int
    attendance_recorded_present: int
    completions_recorded: int


# -------------------------------------------------------------------- participation


class ParticipantsAdd(BaseModel):
    employees: Annotated[list[uuid.UUID], Field(min_length=1, max_length=500)]
    nomination_status: Literal["nominated", "confirmed"] = "nominated"


class ParticipantsAddResult(BaseModel):
    added: int
    already_participating: list[str]
    employment_status_not_recorded: list[str]


class ParticipationUpdate(PatchModel):
    required_if_sent = ("nomination_status",)
    version: Version
    nomination_status: Literal["nominated", "confirmed", "withdrawn"] | None = None
    attendance_status: Literal["present", "partial", "absent", "excused"] | None = None
    attended_minutes: Annotated[int, Field(ge=0, le=100000)] | None = None
    completion_status: Literal["completed", "not_completed"] | None = None
    assessment_result: Annotated[str, Field(max_length=100)] | None = None
    certificate_number: Annotated[str, Field(max_length=100)] | None = None
    remarks: Annotated[str, Field(max_length=1000)] | None = None


class EventBrief(BaseModel):
    public_id: uuid.UUID
    code: str
    title: str
    status: str
    timeframe: TimeframeName
    start: date | None
    end: date | None


class ParticipationOut(BaseModel):
    public_id: uuid.UUID
    employee: EmployeeRef
    event: EventBrief
    nomination_status: str
    attendance_status: str | None
    attended_minutes: int | None
    completion_status: str | None
    assessment_result: str | None
    certificate_number: str | None
    remarks: str | None
    source: str
    attendance_recorded_at: datetime | None
    completion_recorded_at: datetime | None
    version: int


# ------------------------------------------------------------------------- calendar


class CalendarItem(BaseModel):
    event: EventBrief
    session: SessionOut | None
    all_day: bool
    starts_at: datetime | None
    ends_at: datetime | None
    start_date: date | None
    end_date: date | None
    month_only: bool
    venue: str | None
    online: bool
    delivery_mode: str | None
    org_unit: RefOut | None
    location: RefOut | None
    my_status: str | None = Field(
        default=None, description="The signed-in employee's nomination status, if any."
    )


class CalendarOut(BaseModel):
    scope: Literal["global", "team", "own", "none"]
    start: date
    end: date
    items: list[CalendarItem]


# -------------------------------------------------------------------- notifications


class NotificationOut(BaseModel):
    public_id: uuid.UUID
    notification_type: str
    title: str
    body: str
    link_path: str | None
    created_at: datetime
    read_at: datetime | None


class NotificationList(BaseModel):
    items: list[NotificationOut]
    unread_count: int


class NotificationRead(BaseModel):
    read: bool = True


class PreferenceUpdate(BaseModel):
    notification_type: Annotated[str, Field(max_length=50)]
    in_app_enabled: bool


class PreferencesOut(BaseModel):
    preferences: dict[str, bool]
    mandatory: list[str]


class ChannelOut(BaseModel):
    code: str
    name: str
    connected: bool
    detail: str


class ChannelsOut(BaseModel):
    channels: list[ChannelOut]
    reminder_offsets_days: list[int]
