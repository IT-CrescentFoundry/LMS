"""In-application notifications (first release: training calendar events).

* ``Notification`` — one message for one user account. ``dedupe_key`` is UNIQUE, so the
  same business event (e.g. "reminder 1 day before session X starting at T for
  employee E") can never produce two notifications, even if generation runs twice or
  concurrently. A rescheduled session gets a different key (the start time is part of
  it), so reminders follow the new schedule; reminders for the old time are not
  re-sent.
* ``NotificationPreference`` — per-user opt-out of a notification type for the in-app
  channel. Mandatory operational messages (cancellation, schedule change) cannot be
  muted (service rule).

External channels (Outlook calendar, Microsoft Teams) are NOT implemented: they need
an approved Microsoft 365 app registration (see
docs/reference-analysis/05_SOURCE_TO_SYSTEM_MAPPING_AND_OPEN_DECISIONS.md). Nothing
here records a message as "sent" to an external system.
"""

from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base
from app.db.types import BigIntKey, UTCDateTime, utcnow
from app.models.common import PublicIdMixin


class Notification(PublicIdMixin, Base):
    __tablename__ = "notification"
    __table_args__ = (
        Index("ix_notification_recipient_created", "recipient_user_id", "created_at"),
        Index("ix_notification_recipient_read", "recipient_user_id", "read_at"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    recipient_user_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("user_account.id"))
    notification_type: Mapped[str] = mapped_column(String(50))
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(String(1000))
    link_path: Mapped[str | None] = mapped_column(String(300))
    training_event_id: Mapped[int | None] = mapped_column(
        BigIntKey, ForeignKey("training_event.id"), index=True
    )
    employee_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("employee.id"))
    dedupe_key: Mapped[str] = mapped_column(String(200), unique=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    read_at: Mapped[datetime | None] = mapped_column(UTCDateTime())


class NotificationPreference(Base):
    __tablename__ = "notification_preference"
    __table_args__ = (UniqueConstraint("user_account_id", "notification_type"),)

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    user_account_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("user_account.id"))
    notification_type: Mapped[str] = mapped_column(String(50))
    in_app_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow, onupdate=utcnow)
