"""Central training records register (first release; see
docs/product/REVISED_FIRST_RELEASE_SCOPE.md).

Three distinct concepts, never merged:

* ``TrainingProgramme`` — the reusable catalogue definition of a training topic.
* ``TrainingEvent`` — one specific instance (planned or conducted). Planned and actual
  dates are separate columns: a planned event proves nothing about delivery. Whether
  an event is past, ongoing or upcoming is *derived* from its dates (service), never
  stored. ``status`` records what an authorised user has stated:

      planned ─► scheduled ─► completed           (completed needs actual dates)
         └────────┴──► postponed / cancelled      (records are never deleted)

* ``TrainingSession`` — a dated, timed slot of an event (what the calendar shows).
* ``TrainingParticipation`` — one employee's record for one event. Nomination,
  attendance and completion are separate fields: a nomination does not prove
  attendance, and attendance does not prove completion. ``NULL`` attendance or
  completion means "not recorded", never "absent" or "not completed".

The earlier design (LMS_DATABASE_DESIGN §10) also has calendars, planned activities,
batches and per-session attendance; those are deferred (documented in the revised
scope) and can be added without changing these tables' meaning.
"""

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import BigIntKey, UTCDateTime
from app.models.common import PublicIdMixin, TrackedMixin
from app.models.employees import Employee
from app.models.organisation import Location, OrgUnit


class DeliveryMode(StrEnum):
    CLASSROOM = "classroom"
    ONLINE = "online"
    HYBRID = "hybrid"
    OJT = "ojt"


class EventStatus(StrEnum):
    PLANNED = "planned"
    SCHEDULED = "scheduled"
    COMPLETED = "completed"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"


class TrainerType(StrEnum):
    INTERNAL = "internal"
    EXTERNAL = "external"


class RecordSource(StrEnum):
    MANUAL = "manual"
    IMPORT = "import"


class SessionStatus(StrEnum):
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"


class NominationStatus(StrEnum):
    NOMINATED = "nominated"
    CONFIRMED = "confirmed"
    WITHDRAWN = "withdrawn"


class AttendanceStatus(StrEnum):
    PRESENT = "present"
    PARTIAL = "partial"
    ABSENT = "absent"
    EXCUSED = "excused"


class CompletionStatus(StrEnum):
    COMPLETED = "completed"
    NOT_COMPLETED = "not_completed"


def _in(column: str, values: type[StrEnum], *, nullable: bool = False) -> str:
    listed = ", ".join(repr(item.value) for item in values)
    check = f"{column} IN ({listed})"
    return f"{column} IS NULL OR {check}" if nullable else check


class TrainingProgramme(PublicIdMixin, TrackedMixin, Base):
    __tablename__ = "training_programme"
    __table_args__ = (
        CheckConstraint(_in("default_delivery_mode", DeliveryMode, nullable=True), name="mode"),
        CheckConstraint(
            "standard_duration_minutes IS NULL OR standard_duration_minutes > 0", name="duration"
        ),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    title: Mapped[str] = mapped_column(String(250), index=True)
    category: Mapped[str | None] = mapped_column(String(100), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    objectives: Mapped[str | None] = mapped_column(Text)
    target_audience: Mapped[str | None] = mapped_column(String(500))
    default_delivery_mode: Mapped[str | None] = mapped_column(String(20))
    standard_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    competency_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("competency.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class TrainingEvent(PublicIdMixin, TrackedMixin, Base):
    __tablename__ = "training_event"
    __table_args__ = (
        CheckConstraint(_in("status", EventStatus), name="status"),
        CheckConstraint(_in("delivery_mode", DeliveryMode, nullable=True), name="mode"),
        CheckConstraint(_in("trainer_type", TrainerType, nullable=True), name="trainer_type"),
        CheckConstraint(_in("source", RecordSource), name="source"),
        CheckConstraint(
            "planned_end_date IS NULL OR planned_start_date IS NULL "
            "OR planned_end_date >= planned_start_date",
            name="planned_period",
        ),
        CheckConstraint(
            "actual_end_date IS NULL OR actual_start_date IS NULL "
            "OR actual_end_date >= actual_start_date",
            name="actual_period",
        ),
        CheckConstraint(
            "status <> 'completed' OR actual_start_date IS NOT NULL", name="completed_has_dates"
        ),
        CheckConstraint("planned_month IS NULL OR DAY(planned_month) = 1", name="month_first_day"),
        CheckConstraint("capacity IS NULL OR capacity > 0", name="capacity"),
        CheckConstraint(
            "planned_participant_count IS NULL OR planned_participant_count >= 0",
            name="planned_count",
        ),
        CheckConstraint(
            "planned_duration_minutes IS NULL OR planned_duration_minutes > 0", name="duration"
        ),
        CheckConstraint(
            "reported_attendance_count IS NULL OR reported_attendance_count >= 0",
            name="reported_count",
        ),
        Index("ix_training_event_planned_start_date", "planned_start_date"),
        Index("ix_training_event_actual_start_date", "actual_start_date"),
        Index("ix_training_event_planned_month", "planned_month"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    programme_id: Mapped[int | None] = mapped_column(
        BigIntKey, ForeignKey("training_programme.id"), index=True
    )
    title: Mapped[str] = mapped_column(String(250), index=True)
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), index=True)
    delivery_mode: Mapped[str | None] = mapped_column(String(20))
    org_unit_id: Mapped[int | None] = mapped_column(
        BigIntKey, ForeignKey("org_unit.id"), index=True
    )
    location_id: Mapped[int | None] = mapped_column(
        BigIntKey, ForeignKey("location.id"), index=True
    )
    calendar_label: Mapped[str | None] = mapped_column(String(150), index=True)
    planned_month: Mapped[date | None] = mapped_column(Date)
    planned_start_date: Mapped[date | None] = mapped_column(Date)
    planned_end_date: Mapped[date | None] = mapped_column(Date)
    actual_start_date: Mapped[date | None] = mapped_column(Date)
    actual_end_date: Mapped[date | None] = mapped_column(Date)
    planned_duration_minutes: Mapped[int | None] = mapped_column(Integer)
    venue: Mapped[str | None] = mapped_column(String(250))
    online_join_url: Mapped[str | None] = mapped_column(String(500))
    trainer_type: Mapped[str | None] = mapped_column(String(10))
    trainer_employee_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("employee.id"))
    trainer_name: Mapped[str | None] = mapped_column(String(200))
    provider_name: Mapped[str | None] = mapped_column(String(200))
    capacity: Mapped[int | None] = mapped_column(Integer)
    planned_participant_count: Mapped[int | None] = mapped_column(Integer)
    # Headcount reported by the organiser (calendar "Total Attended"). A summary figure
    # only: it is NOT individual attendance and never creates participation records.
    reported_attendance_count: Mapped[int | None] = mapped_column(Integer)
    target_audience: Mapped[str | None] = mapped_column(String(500))
    instructions: Mapped[str | None] = mapped_column(Text)
    status_reason: Mapped[str | None] = mapped_column(String(500))
    source: Mapped[str] = mapped_column(String(10), default=RecordSource.MANUAL.value)
    published_at: Mapped[datetime | None] = mapped_column(UTCDateTime())

    programme: Mapped[TrainingProgramme | None] = relationship(lazy="joined")
    org_unit: Mapped[OrgUnit | None] = relationship(lazy="joined")
    location: Mapped[Location | None] = relationship(lazy="joined")
    trainer_employee: Mapped[Employee | None] = relationship(lazy="joined")
    sessions: Mapped[list["TrainingSession"]] = relationship(
        lazy="selectin", order_by="TrainingSession.starts_at", viewonly=True
    )


class TrainingSession(PublicIdMixin, TrackedMixin, Base):
    __tablename__ = "training_session"
    __table_args__ = (
        CheckConstraint("ends_at > starts_at", name="period"),
        CheckConstraint(_in("status", SessionStatus), name="status"),
        Index("ix_training_session_starts_at", "starts_at"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("training_event.id"), index=True)
    starts_at: Mapped[datetime] = mapped_column(UTCDateTime())
    ends_at: Mapped[datetime] = mapped_column(UTCDateTime())
    venue: Mapped[str | None] = mapped_column(String(250))
    online_join_url: Mapped[str | None] = mapped_column(String(500))
    status: Mapped[str] = mapped_column(String(20), default=SessionStatus.SCHEDULED.value)
    notes: Mapped[str | None] = mapped_column(String(500))


class TrainingParticipation(PublicIdMixin, TrackedMixin, Base):
    __tablename__ = "training_participation"
    __table_args__ = (
        UniqueConstraint("event_id", "employee_id"),
        CheckConstraint(_in("nomination_status", NominationStatus), name="nomination"),
        CheckConstraint(_in("attendance_status", AttendanceStatus, nullable=True), name="attend"),
        CheckConstraint(
            _in("completion_status", CompletionStatus, nullable=True), name="completion"
        ),
        CheckConstraint(_in("source", RecordSource), name="source"),
        CheckConstraint(
            "completion_status IS NULL OR completion_status <> 'completed' "
            "OR attendance_status IN ('present', 'partial')",
            name="completed_attended",
        ),
        CheckConstraint(
            "attended_minutes IS NULL OR attended_minutes >= 0", name="minutes_non_negative"
        ),
        CheckConstraint(
            "certificate_number IS NULL OR completion_status = 'completed'",
            name="certificate_completed",
        ),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    event_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("training_event.id"), index=True)
    employee_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("employee.id"), index=True)
    nomination_status: Mapped[str] = mapped_column(String(20))
    attendance_status: Mapped[str | None] = mapped_column(String(20))
    attended_minutes: Mapped[int | None] = mapped_column(Integer)
    completion_status: Mapped[str | None] = mapped_column(String(20))
    assessment_result: Mapped[str | None] = mapped_column(String(100))
    certificate_number: Mapped[str | None] = mapped_column(String(100))
    remarks: Mapped[str | None] = mapped_column(String(1000))
    source: Mapped[str] = mapped_column(String(10), default=RecordSource.MANUAL.value)
    attendance_recorded_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    attendance_recorded_by_user_id: Mapped[int | None] = mapped_column(
        BigIntKey, ForeignKey("user_account.id")
    )
    completion_recorded_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    completion_recorded_by_user_id: Mapped[int | None] = mapped_column(
        BigIntKey, ForeignKey("user_account.id")
    )

    employee: Mapped[Employee] = relationship(lazy="joined")
    event: Mapped[TrainingEvent] = relationship(lazy="joined")
