"""Append-only audit trail.

Audit events are inserted in the same transaction as the change they describe and
are never updated or deleted by the application. Three layers protect them:

1. no update/delete code paths or API routes exist;
2. the ``before_flush`` guard below raises if any loaded audit event is modified
   or deleted through an ORM session;
3. MySQL ``BEFORE UPDATE`` / ``BEFORE DELETE`` triggers reject changes at the
   database level (Alembic revision ``0003``).

Limitations — the audit trail is append-only for the application, NOT tamper-proof:

* ``TRUNCATE TABLE`` and ``DROP TABLE`` do not fire row triggers, so any account
  with DROP privilege (the migration account, DBAs) can still remove audit data.
* An account with TRIGGER privilege (the migration account) can drop the triggers.
* The runtime account (``lms_app``) has no DROP, ALTER or TRIGGER privilege, and the
  migration account must remain tightly controlled. Production protection
  (e.g. a separate audit schema with insert-only grants, off-server log shipping)
  requires a separate DBA decision.
"""

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import JSON, CheckConstraint, ForeignKey, Index, String, event
from sqlalchemy.orm import Mapped, Session, UOWTransaction, mapped_column

from app.core.ids import uuid7
from app.db.base import Base
from app.db.types import BigIntKey, UTCDateTime, UUIDBinary, utcnow


class AuditOutcome(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    DENIED = "denied"


class AuditImmutableError(RuntimeError):
    """Raised when code attempts to modify or delete an audit event."""


class AuditEvent(Base):
    __tablename__ = "audit_event"
    __table_args__ = (
        CheckConstraint("outcome IN ('success', 'failure', 'denied')", name="outcome_valid"),
        Index("ix_audit_event_occurred_at", "occurred_at"),
        Index("ix_audit_event_event_type_occurred_at", "event_type", "occurred_at"),
        Index("ix_audit_event_actor_user_id_occurred_at", "actor_user_id", "occurred_at"),
        Index("ix_audit_event_target", "target_type", "target_id"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    public_id: Mapped[uuid.UUID] = mapped_column(UUIDBinary(), unique=True, default=uuid7)
    occurred_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    event_type: Mapped[str] = mapped_column(String(100))
    outcome: Mapped[str] = mapped_column(String(20))
    actor_user_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("user_account.id"))
    target_type: Mapped[str | None] = mapped_column(String(50))
    target_id: Mapped[str | None] = mapped_column(String(64))
    request_id: Mapped[str | None] = mapped_column(String(128))
    source_ip: Mapped[str | None] = mapped_column(String(45))
    user_agent: Mapped[str | None] = mapped_column(String(255))
    # "metadata" is reserved on declarative classes, hence the attribute name.
    event_metadata: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSON)


@event.listens_for(Session, "before_flush")
def _reject_audit_changes(session: Session, _context: UOWTransaction, _instances: Any) -> None:
    for instance in (*session.dirty, *session.deleted):
        if isinstance(instance, AuditEvent) and (
            instance in session.deleted or session.is_modified(instance)
        ):
            raise AuditImmutableError("Audit events are append-only and cannot be changed.")
