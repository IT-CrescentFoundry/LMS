"""Shared helpers for the organisation services: codes, versions, translations, audit."""

import base64
import binascii
import re
import uuid
from collections.abc import Callable, Mapping
from datetime import UTC, date, datetime, timedelta
from typing import Any, Protocol

from sqlalchemy import Select, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.context import RequestMeta
from app.core.errors import AppError
from app.db.types import utcnow
from app.models.audit import AuditOutcome
from app.models.common import PublicIdMixin, TranslationLocale
from app.services.audit_service import AuditEventType, TargetType, record_audit_event
from app.services.identity.context import Actor

TranslationValues = Mapping[TranslationLocale, str | None]

_CODE = re.compile(r"^[A-Z0-9][A-Z0-9_-]{0,49}$")
_MYSQL_DUPLICATE_KEY = 1062


def normalise_code(raw: str) -> str:
    """Codes are stored upper-case; letters, digits, '-' and '_' (max 50)."""
    code = raw.strip().upper()
    if not _CODE.fullmatch(code):
        raise AppError(
            422,
            "invalid_code",
            "Codes may contain only letters, digits, hyphens and underscores (max 50).",
        )
    return code


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def business_today(settings: Settings) -> date:
    offset = timedelta(minutes=settings.business_utc_offset_minutes)
    return (datetime.now(UTC) + offset).date()


def ensure_version(entity: Any, expected: int) -> None:
    if entity.version != expected:
        raise AppError(
            409,
            "version_conflict",
            "This record was changed by someone else. Reload it and try again.",
        )


def ensure_absent(
    db: Session, statement: Select[Any], code: str, message: str, *, locking: bool = False
) -> None:
    """Raise 409 ``code`` if ``statement`` finds a row.

    ``locking=True`` uses a locking read (FOR SHARE). Use it for dependency checks made
    after taking a row lock: under REPEATABLE READ a plain read may use a snapshot
    taken earlier in the request and miss a row another transaction just committed.
    """
    if locking:
        statement = statement.with_for_update(read=True)
    if db.scalar(statement.limit(1)) is not None:
        raise AppError(409, code, message)


def flush_unique(db: Session, code: str, message: str) -> None:
    """Flush, turning a duplicate-key race into a 409 instead of a 500."""
    try:
        db.flush()
    except IntegrityError as exc:
        args = getattr(exc.orig, "args", ())
        if args and args[0] == _MYSQL_DUPLICATE_KEY:
            raise AppError(409, code, message) from None
        raise


def get_or_404[ModelT: PublicIdMixin](
    db: Session,
    model: type[ModelT],
    public_id: uuid.UUID,
    code: str,
    message: str,
    *,
    for_update: bool = False,
) -> ModelT:
    statement = select(model).where(model.public_id == public_id)
    if for_update:
        statement = statement.with_for_update().execution_options(populate_existing=True)
    entity = db.scalars(statement).unique().one_or_none()
    if entity is None:
        raise AppError(404, code, message)
    return entity


def encode_code_cursor(code: str) -> str:
    return base64.urlsafe_b64encode(code.encode()).decode().rstrip("=")


def decode_code_cursor(cursor: str | None) -> str | None:
    if not cursor:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        code = base64.b64decode(padded, altchars=b"-_", validate=True).decode()
    except (binascii.Error, UnicodeDecodeError, ValueError):
        code = ""
    if not _CODE.fullmatch(code):
        raise AppError(422, "invalid_cursor", "The pagination cursor is invalid.")
    return code


def like_pattern(text: str) -> str:
    escaped = text.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def touch(entity: Any, actor: Actor) -> None:
    """Record who changed a row; always issues an UPDATE, so ``version`` increments."""
    entity.updated_by_user_id = actor.user_id
    entity.updated_at = utcnow()


def jsonable(value: Any) -> Any:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, uuid.UUID):
        return str(value)
    return value


def apply_changes(entity: Any, changes: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """Set changed attributes; return ``{field: {"from": old, "to": new}}`` for audit."""
    diff: dict[str, dict[str, Any]] = {}
    for field, new in changes.items():
        old = getattr(entity, field)
        if old != new:
            diff[field] = {"from": jsonable(old), "to": jsonable(new)}
            setattr(entity, field, new)
    return diff


class TranslationRow(Protocol):
    locale: str
    name: str


def translations_of(rows: list[Any]) -> dict[str, str]:
    return {row.locale: row.name for row in rows}


def apply_translations(
    rows: list[Any],
    factory: Callable[[str, str], Any],
    values: TranslationValues,
) -> dict[str, dict[str, str | None]]:
    """Upsert / remove per-locale display names; a blank value removes the locale."""
    by_locale = {row.locale: row for row in rows}
    diff: dict[str, dict[str, str | None]] = {}
    for locale, raw in values.items():
        value = clean_text(raw)
        current = by_locale.get(locale)
        if value is None:
            if current is not None:
                rows.remove(current)
                diff[locale] = {"from": current.name, "to": None}
        elif current is None:
            rows.append(factory(locale, value))
            diff[locale] = {"from": None, "to": value}
        elif current.name != value:
            diff[locale] = {"from": current.name, "to": value}
            current.name = value
    return diff


def audit(
    db: Session,
    actor: Actor,
    meta: RequestMeta,
    event: AuditEventType,
    target: TargetType,
    public_id: uuid.UUID,
    metadata: Mapping[str, Any],
) -> None:
    record_audit_event(
        db,
        event_type=event,
        outcome=AuditOutcome.SUCCESS,
        meta=meta,
        actor_user_id=actor.user_id,
        target_type=target,
        target_id=str(public_id),
        metadata={key: jsonable(value) for key, value in metadata.items()},
    )
