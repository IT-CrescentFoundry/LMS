"""In-app notification centre and the boundary for future external channels.

Notifications are created only from real business events (nomination, schedule
published / changed / cancelled, completion recorded, due reminders). Every
notification has a deterministic ``dedupe_key``; inserting a key twice is a no-op
(savepoint + UNIQUE constraint), so retries and concurrent generation never
duplicate a message.

Recipients are the *user accounts* linked to the affected employees. Employees without
a linked, non-disabled account receive nothing (and nothing pretends otherwise).

External channels: ``EXTERNAL_CHANNELS`` lists Outlook calendar and Microsoft Teams as
**not connected**. They require a Microsoft Entra app registration, admin-consented
Graph permissions (Calendars.ReadWrite, ChannelMessage.Send / Chat.ReadWrite or
TeamsActivity.Send) and tenant configuration - none of which exist yet. No code here
calls Microsoft Graph or records anything as sent externally.
"""

import uuid
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.errors import AppError
from app.db.types import utcnow
from app.models.identity import AccountStatus, UserAccount
from app.models.notifications import Notification, NotificationPreference
from app.models.training import (
    EventStatus,
    NominationStatus,
    SessionStatus,
    TrainingEvent,
    TrainingParticipation,
    TrainingSession,
)


class NotificationType:
    NOMINATED = "training.nominated"
    PUBLISHED = "training.schedule_published"
    SCHEDULE_CHANGED = "training.schedule_changed"
    CANCELLED = "training.cancelled"
    REMINDER = "training.reminder"
    COMPLETED = "training.completed"
    CERTIFICATE = "training.certificate_recorded"


ALL_TYPES = (
    NotificationType.NOMINATED,
    NotificationType.PUBLISHED,
    NotificationType.SCHEDULE_CHANGED,
    NotificationType.CANCELLED,
    NotificationType.REMINDER,
    NotificationType.COMPLETED,
    NotificationType.CERTIFICATE,
)
# Operational messages a user may not switch off.
MANDATORY_TYPES = frozenset({NotificationType.SCHEDULE_CHANGED, NotificationType.CANCELLED})


@dataclass(frozen=True)
class ChannelStatus:
    code: str
    name: str
    connected: bool
    detail: str


IN_APP_CHANNEL = ChannelStatus(
    "in_app", "Portal notification centre", True, "Notifications appear in the portal."
)
EXTERNAL_CHANNELS = (
    ChannelStatus(
        "outlook",
        "Outlook calendar",
        False,
        "Not connected. Requires a Microsoft 365 app registration and IT approval.",
    ),
    ChannelStatus(
        "teams",
        "Microsoft Teams",
        False,
        "Not connected. Requires a Microsoft 365 app registration and IT approval.",
    ),
)


# ----------------------------------------------------------------------- creation


def _recipients(db: Session, employee_ids: Iterable[int]) -> dict[int, int]:
    """employee_id -> user_account_id for linked, non-disabled accounts."""
    ids = sorted(set(employee_ids))
    if not ids:
        return {}
    rows = db.execute(
        select(UserAccount.employee_id, UserAccount.id).where(
            UserAccount.employee_id.in_(ids),
            UserAccount.status != AccountStatus.DISABLED.value,
        )
    ).all()
    return {employee_id: user_id for employee_id, user_id in rows if employee_id is not None}


def _muted(db: Session, user_ids: Iterable[int], kind: str) -> set[int]:
    if kind in MANDATORY_TYPES:
        return set()
    return set(
        db.scalars(
            select(NotificationPreference.user_account_id).where(
                NotificationPreference.user_account_id.in_(list(user_ids) or [0]),
                NotificationPreference.notification_type == kind,
                NotificationPreference.in_app_enabled.is_(False),
            )
        )
    )


def _insert(db: Session, notification: Notification) -> bool:
    """Insert unless the dedupe key exists. Returns True when created."""
    exists = db.scalar(
        select(Notification.id).where(Notification.dedupe_key == notification.dedupe_key)
    )
    if exists is not None:
        return False
    try:
        with db.begin_nested():
            db.add(notification)
    except IntegrityError:
        return False  # created concurrently: the UNIQUE key did its job
    return True


def notify_employees(
    db: Session,
    *,
    kind: str,
    employee_ids: Iterable[int],
    title: str,
    body: str,
    key: str,
    event: TrainingEvent | None = None,
    link_path: str | None = None,
) -> int:
    """Create one notification per recipient; ``key`` is suffixed with the employee id."""
    recipients = _recipients(db, employee_ids)
    muted = _muted(db, recipients.values(), kind)
    created = 0
    for employee_id, user_id in recipients.items():
        if user_id in muted:
            continue
        created += _insert(
            db,
            Notification(
                recipient_user_id=user_id,
                notification_type=kind,
                title=title[:200],
                body=body[:1000],
                link_path=link_path,
                training_event_id=event.id if event is not None else None,
                employee_id=employee_id,
                dedupe_key=f"{key}:e{employee_id}"[:200],
            ),
        )
    return created


def active_participant_ids(db: Session, event: TrainingEvent) -> list[int]:
    return list(
        db.scalars(
            select(TrainingParticipation.employee_id).where(
                TrainingParticipation.event_id == event.id,
                TrainingParticipation.nomination_status != NominationStatus.WITHDRAWN.value,
            )
        )
    )


def event_link(event: TrainingEvent) -> str:
    return f"/training/events/{event.public_id}"


# ---------------------------------------------------------------------- reminders


def _due_reminder_rows(
    db: Session, now: datetime, offsets: tuple[int, ...], employee_id: int | None
) -> list[tuple[TrainingSession, TrainingEvent, int]]:
    if not offsets:
        return []
    horizon = now + timedelta(days=max(offsets))
    statement = (
        select(TrainingSession, TrainingEvent, TrainingParticipation.employee_id)
        .join(TrainingEvent, TrainingEvent.id == TrainingSession.event_id)
        .join(TrainingParticipation, TrainingParticipation.event_id == TrainingEvent.id)
        .where(
            TrainingSession.status == SessionStatus.SCHEDULED.value,
            TrainingEvent.status == EventStatus.SCHEDULED.value,
            TrainingSession.starts_at > now,
            TrainingSession.starts_at <= horizon,
            TrainingParticipation.nomination_status != NominationStatus.WITHDRAWN.value,
        )
    )
    if employee_id is not None:
        statement = statement.where(TrainingParticipation.employee_id == employee_id)
    return [(row[0], row[1], row[2]) for row in db.execute(statement).unique().all()]


def local_time_text(moment: datetime, utc_offset_minutes: int) -> str:
    """``moment`` (UTC) as business-calendar local time, e.g. ``2026-11-25 10:00 IST``.

    The business calendar has a fixed UTC offset (``LMS_BUSINESS_UTC_OFFSET_MINUTES``;
    India has no daylight saving), so no DST conversion is needed."""
    local = moment + timedelta(minutes=utc_offset_minutes)
    if utc_offset_minutes == 330:
        label = "IST"
    else:
        sign = "+" if utc_offset_minutes >= 0 else "-"
        hours, minutes = divmod(abs(utc_offset_minutes), 60)
        label = f"UTC{sign}{hours:02d}:{minutes:02d}"
    return f"{local:%Y-%m-%d %H:%M} {label}"


def generate_due_reminders(
    db: Session,
    *,
    offsets: tuple[int, ...],
    settings: Settings | None = None,
    now: datetime | None = None,
    employee_id: int | None = None,
) -> int:
    """Create reminders whose time has come. Idempotent (dedupe keys).

    Triggered by ``python -m app.jobs training-reminders`` (OS scheduler), by the
    administrator endpoint, and - for the signed-in user only - when the notification
    centre is opened. Session times are stored in UTC; the text shows business-calendar
    local time. The de-duplication key uses the UTC start, so a rescheduled session gets
    new reminders and the old time's reminders are never re-sent."""
    now = now or utcnow()
    offset_minutes = settings.business_utc_offset_minutes if settings is not None else 0
    created = 0
    for session, event, participant_id in _due_reminder_rows(db, now, offsets, employee_id):
        # Only the nearest due offset: a reminder generated late (e.g. 1 day before)
        # does not also produce the 7-day reminder.
        due = [days for days in offsets if session.starts_at - timedelta(days=days) <= now]
        if not due:
            continue
        days = min(due)
        when = local_time_text(session.starts_at, offset_minutes)
        place = session.venue or event.venue or ("Online" if session.online_join_url else None)
        body = f"'{event.title}' starts {when}" + (f" at {place}." if place else ".")
        created += notify_employees(
            db,
            kind=NotificationType.REMINDER,
            employee_ids=[participant_id],
            title=f"Reminder: {event.title}",
            body=body,
            key=f"reminder:{session.public_id}:{session.starts_at.isoformat()}:{days}d",
            event=event,
            link_path=event_link(event),
        )
    return created


# ------------------------------------------------------------------ user's centre


def list_for_user(
    db: Session, user_id: int, *, unread_only: bool, limit: int
) -> tuple[list[Notification], int]:
    statement = select(Notification).where(Notification.recipient_user_id == user_id)
    if unread_only:
        statement = statement.where(Notification.read_at.is_(None))
    items = list(
        db.scalars(
            statement.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(limit)
        )
    )
    unread = db.scalar(
        select(func.count())
        .select_from(Notification)
        .where(Notification.recipient_user_id == user_id, Notification.read_at.is_(None))
    )
    return items, int(unread or 0)


def mark_read(db: Session, user_id: int, public_id: uuid.UUID, *, read: bool) -> Notification:
    item = db.scalar(
        select(Notification).where(
            Notification.public_id == public_id, Notification.recipient_user_id == user_id
        )
    )
    if item is None:  # someone else's notification is indistinguishable from none
        raise AppError(404, "notification_not_found", "Notification not found.")
    item.read_at = (item.read_at or utcnow()) if read else None
    return item


def mark_all_read(db: Session, user_id: int) -> int:
    result = db.execute(
        update(Notification)
        .where(Notification.recipient_user_id == user_id, Notification.read_at.is_(None))
        .values(read_at=utcnow())
    )
    return int(getattr(result, "rowcount", 0) or 0)


def preferences(db: Session, user_id: int) -> dict[str, bool]:
    stored = {
        row.notification_type: row.in_app_enabled
        for row in db.scalars(
            select(NotificationPreference).where(NotificationPreference.user_account_id == user_id)
        )
    }
    return {
        kind: (True if kind in MANDATORY_TYPES else stored.get(kind, True)) for kind in ALL_TYPES
    }


def set_preference(db: Session, user_id: int, kind: str, enabled: bool) -> dict[str, bool]:
    if kind not in ALL_TYPES:
        raise AppError(422, "unknown_notification_type", "Unknown notification type.")
    if kind in MANDATORY_TYPES and not enabled:
        raise AppError(
            409,
            "notification_mandatory",
            "Schedule changes and cancellations are always shown.",
        )
    row = db.scalar(
        select(NotificationPreference).where(
            NotificationPreference.user_account_id == user_id,
            NotificationPreference.notification_type == kind,
        )
    )
    if row is None:
        db.add(
            NotificationPreference(
                user_account_id=user_id, notification_type=kind, in_app_enabled=enabled
            )
        )
    else:
        row.in_app_enabled = enabled
    db.flush()
    return preferences(db, user_id)
