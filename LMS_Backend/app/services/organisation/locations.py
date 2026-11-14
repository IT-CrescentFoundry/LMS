"""Physical locations (sites). A plant is an org unit linked to a location (Q-48 open)."""

import uuid
import zoneinfo
from collections.abc import Mapping
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import RequestMeta
from app.core.errors import AppError
from app.models.organisation import Location, OrgUnit
from app.services.audit_service import AuditEventType, TargetType
from app.services.identity.context import Actor
from app.services.organisation.support import (
    apply_changes,
    audit,
    clean_text,
    ensure_absent,
    ensure_version,
    flush_unique,
    get_or_404,
    normalise_code,
    touch,
)

_CODE_TAKEN = ("location_code_taken", "This location code is already in use.")
_TEXT_FIELDS = ("address_line1", "address_line2", "city", "state", "postal_code")


def get_location(db: Session, public_id: uuid.UUID, *, for_update: bool = False) -> Location:
    return get_or_404(
        db, Location, public_id, "location_not_found", "Location not found.", for_update=for_update
    )


def list_locations(db: Session, *, include_inactive: bool) -> list[Location]:
    statement = select(Location).order_by(Location.code)
    if not include_inactive:
        statement = statement.where(Location.is_active.is_(True))
    return list(db.scalars(statement))


def _country(value: str | None) -> str | None:
    value = clean_text(value)
    return value.upper() if value else None


def _time_zone(value: str | None) -> str | None:
    value = clean_text(value)
    if value is None:
        return None
    try:
        zoneinfo.ZoneInfo(value)
    except (zoneinfo.ZoneInfoNotFoundError, ValueError):
        raise AppError(
            422, "invalid_time_zone", "Unknown time zone (use an IANA name such as Asia/Kolkata)."
        ) from None
    return value


def create_location(
    db: Session,
    *,
    actor: Actor,
    meta: RequestMeta,
    code: str,
    name: str,
    details: Mapping[str, str | None],
) -> Location:
    code = normalise_code(code)
    ensure_absent(db, select(Location.id).where(Location.code == code), *_CODE_TAKEN)
    location = Location(
        code=code,
        name=name,
        country_code=_country(details.get("country_code")),
        time_zone=_time_zone(details.get("time_zone")),
        is_active=True,
        created_by_user_id=actor.user_id,
        updated_by_user_id=actor.user_id,
        **{field: clean_text(details.get(field)) for field in _TEXT_FIELDS},
    )
    db.add(location)
    flush_unique(db, *_CODE_TAKEN)
    audit(
        db,
        actor,
        meta,
        AuditEventType.LOCATION_CREATED,
        TargetType.LOCATION,
        location.public_id,
        {"code": code, "name": name},
    )
    return location


def update_location(
    db: Session,
    public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    changes: Mapping[str, Any],
) -> Location:
    location = get_location(db, public_id, for_update=True)
    ensure_version(location, version)
    values: dict[str, Any] = {}
    for field, raw in changes.items():
        if field == "code":
            values[field] = normalise_code(raw)
        elif field == "country_code":
            values[field] = _country(raw)
        elif field == "time_zone":
            values[field] = _time_zone(raw)
        elif field in _TEXT_FIELDS:
            values[field] = clean_text(raw)
        else:
            values[field] = raw
    if values.get("code", location.code) != location.code:
        ensure_absent(
            db,
            select(Location.id).where(Location.code == values["code"], Location.id != location.id),
            *_CODE_TAKEN,
        )
    if values.get("is_active") is False and location.is_active:
        in_use = select(OrgUnit.id).where(
            OrgUnit.location_id == location.id, OrgUnit.effective_to.is_(None)
        )
        ensure_absent(
            db,
            in_use,
            "location_in_use",
            "Organisation units that are not closed still use this location.",
            locking=True,
        )
    diff = apply_changes(location, values)
    if diff:
        touch(location, actor)
        flush_unique(db, *_CODE_TAKEN)
        audit(
            db,
            actor,
            meta,
            AuditEventType.LOCATION_UPDATED,
            TargetType.LOCATION,
            location.public_id,
            {"code": location.code, "changes": diff},
        )
    return location
