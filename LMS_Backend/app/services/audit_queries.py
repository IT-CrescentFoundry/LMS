"""Read-only audit queries (there are no write/update/delete counterparts)."""

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent, AuditOutcome
from app.models.identity import UserAccount
from app.services.identity.accounts import decode_cursor, encode_cursor


@dataclass(frozen=True)
class AuditFilters:
    event_type: str | None = None
    outcome: AuditOutcome | None = None
    actor_public_id: uuid.UUID | None = None
    target_type: str | None = None
    target_id: str | None = None
    occurred_from: datetime | None = None
    occurred_to: datetime | None = None


def _as_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def list_audit_events(
    db: Session, filters: AuditFilters, *, limit: int, cursor: str | None
) -> tuple[list[AuditEvent], str | None]:
    query = select(AuditEvent).order_by(AuditEvent.id.desc()).limit(limit + 1)
    if filters.event_type:
        query = query.where(AuditEvent.event_type == filters.event_type)
    if filters.outcome is not None:
        query = query.where(AuditEvent.outcome == filters.outcome.value)
    if filters.actor_public_id is not None:
        query = query.join(UserAccount, UserAccount.id == AuditEvent.actor_user_id).where(
            UserAccount.public_id == filters.actor_public_id
        )
    if filters.target_type:
        query = query.where(AuditEvent.target_type == filters.target_type)
    if filters.target_id:
        query = query.where(AuditEvent.target_id == filters.target_id)
    if filters.occurred_from is not None:
        query = query.where(AuditEvent.occurred_at >= _as_utc(filters.occurred_from))
    if filters.occurred_to is not None:
        query = query.where(AuditEvent.occurred_at < _as_utc(filters.occurred_to))
    before = decode_cursor(cursor)
    if before is not None:
        query = query.where(AuditEvent.id < before)
    rows = list(db.scalars(query))
    next_cursor = encode_cursor(rows[limit - 1].id) if len(rows) > limit else None
    return rows[:limit], next_cursor
