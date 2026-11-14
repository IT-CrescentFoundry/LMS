"""Organisation units and their effective-dated hierarchy.

Concurrency: every structural write first locks the ``org_hierarchy`` row of
``graph_lock`` (SELECT ... FOR UPDATE), then reads the graph with *locking* reads
(FOR SHARE / FOR UPDATE). Under InnoDB REPEATABLE READ, plain reads would use the
transaction's earlier snapshot and could miss a concurrently committed link; locking
reads always see the latest committed rows, so cycle and sibling-name checks are
reliable.

Rules:
* codes are globally unique (case-insensitive); names only among siblings that share a
  parent over overlapping dates — two plants may both have a "Maintenance" department;
* a parent must be active for the whole period of a link; no cycles; type rules apply;
* a move closes the current link and opens a new one (history is kept);
* closing a unit is refused while it has active children or other active dependants;
* nothing is ever deleted.
"""

import uuid
from collections.abc import Mapping
from datetime import date
from typing import Any

from sqlalchemy import ColumnElement, and_, exists, or_, select
from sqlalchemy.orm import Session, aliased

from app.core.context import RequestMeta
from app.core.errors import AppError
from app.db.types import utcnow
from app.models.occupation import DesignationFunctionalRole, FunctionalRole
from app.models.organisation import (
    ORG_HIERARCHY_LOCK,
    GraphLock,
    Location,
    OrgUnit,
    OrgUnitHierarchy,
    OrgUnitTranslation,
    OrgUnitType,
)
from app.schemas.errors import ValidationIssue
from app.services.audit_service import AuditEventType, TargetType
from app.services.identity.context import Actor
from app.services.organisation.graph import creates_cycle
from app.services.organisation.locations import get_location
from app.services.organisation.periods import InvalidPeriodError, Period, fully_covered
from app.services.organisation.support import (
    TranslationValues,
    apply_translations,
    audit,
    clean_text,
    encode_code_cursor,
    ensure_absent,
    ensure_version,
    flush_unique,
    get_or_404,
    jsonable,
    like_pattern,
    normalise_code,
    touch,
)
from app.services.organisation.unit_types import OrgWarning, check_parent_rule, get_unit_type

_CODE_TAKEN = ("unit_code_taken", "This organisation unit code is already in use.")


# --------------------------------------------------------------------------- helpers


def lock_hierarchy(db: Session) -> None:
    db.execute(
        select(GraphLock.name).where(GraphLock.name == ORG_HIERARCHY_LOCK).with_for_update()
    ).one()


def lifetime(unit: OrgUnit) -> Period:
    return Period(unit.effective_from, unit.effective_to)


def link_period(link: OrgUnitHierarchy) -> Period:
    return Period(link.effective_from, link.effective_to)


def _make_period(start: date | None, end: date | None) -> Period:
    try:
        return Period(start, end)
    except InvalidPeriodError:
        raise AppError(
            422, "invalid_period", "The end date must be after the start date."
        ) from None


def active_on(day: date) -> ColumnElement[bool]:
    return and_(
        or_(OrgUnit.effective_from.is_(None), OrgUnit.effective_from <= day),
        or_(OrgUnit.effective_to.is_(None), OrgUnit.effective_to > day),
    )


def _link_covers(link: Any, day: date) -> ColumnElement[bool]:
    return and_(
        or_(link.effective_from.is_(None), link.effective_from <= day),
        or_(link.effective_to.is_(None), link.effective_to > day),
    )


def get_unit(db: Session, public_id: uuid.UUID, *, for_update: bool = False) -> OrgUnit:
    return get_or_404(
        db,
        OrgUnit,
        public_id,
        "org_unit_not_found",
        "Organisation unit not found.",
        for_update=for_update,
    )


def _active_location(db: Session, public_id: uuid.UUID) -> Location:
    # row lock: serialises with a concurrent deactivation of the location
    location = get_location(db, public_id, for_update=True)
    if not location.is_active:
        raise AppError(422, "location_inactive", "This location is inactive.")
    return location


def _links(
    db: Session,
    *,
    period: Period | None = None,
    child_id: int | None = None,
    parent_id: int | None = None,
) -> list[OrgUnitHierarchy]:
    """Hierarchy links (locking read), optionally only those overlapping ``period``."""
    statement = select(OrgUnitHierarchy)
    if child_id is not None:
        statement = statement.where(OrgUnitHierarchy.child_unit_id == child_id)
    if parent_id is not None:
        statement = statement.where(OrgUnitHierarchy.parent_unit_id == parent_id)
    if period is not None:
        if period.end is not None:
            statement = statement.where(
                or_(
                    OrgUnitHierarchy.effective_from.is_(None),
                    OrgUnitHierarchy.effective_from < period.end,
                )
            )
        if period.start is not None:
            statement = statement.where(
                or_(
                    OrgUnitHierarchy.effective_to.is_(None),
                    OrgUnitHierarchy.effective_to > period.start,
                )
            )
    statement = statement.order_by(OrgUnitHierarchy.id).with_for_update(read=True)
    return list(db.scalars(statement.execution_options(populate_existing=True)).unique())


def _ensure_sibling_name_free(
    db: Session, name: str, parent: OrgUnit | None, period: Period, exclude_id: int | None
) -> None:
    statement = select(OrgUnit).where(OrgUnit.name == name)  # collation: case-insensitive
    if exclude_id is not None:
        statement = statement.where(OrgUnit.id != exclude_id)
    candidates = db.scalars(
        statement.with_for_update(read=True).execution_options(populate_existing=True)
    ).unique()
    for candidate in candidates:
        if not lifetime(candidate).overlaps(period):
            continue
        links = _links(db, period=period, child_id=candidate.id)
        if parent is None:
            shared = lifetime(candidate).intersection(period)
            clash = shared is not None and not fully_covered(
                shared, [link_period(link) for link in links]
            )
        else:
            clash = any(link.parent_unit_id == parent.id for link in links)
        if clash:
            where = f"under {parent.name}" if parent else "at the top level"
            raise AppError(
                409,
                "sibling_name_taken",
                f"Another unit named {name!r} already exists {where} for these dates.",
            )


def _validate_placement(
    db: Session,
    unit_type: OrgUnitType,
    parent: OrgUnit | None,
    period: Period,
    name: str,
    exclude_id: int | None,
) -> list[OrgWarning]:
    warnings: list[OrgWarning] = []
    if parent is not None and not lifetime(parent).covers(period):
        raise AppError(
            422,
            "parent_not_active",
            "The parent unit is not active for the whole period (check both start dates).",
        )
    warning = check_parent_rule(db, unit_type, parent.unit_type if parent else None)
    if warning:
        warnings.append(warning)
    _ensure_sibling_name_free(db, name, parent, period, exclude_id)
    return warnings


def _translation(locale: str, name: str) -> OrgUnitTranslation:
    return OrgUnitTranslation(locale=locale, name=name)


def _warning_codes(warnings: list[OrgWarning]) -> list[str]:
    return [warning.code for warning in warnings]


# ---------------------------------------------------------------------------- writes


def create_unit(
    db: Session,
    *,
    actor: Actor,
    meta: RequestMeta,
    code: str,
    name: str,
    short_name: str | None,
    unit_type_id: uuid.UUID,
    location_id: uuid.UUID | None,
    parent_id: uuid.UUID | None,
    effective_from: date | None,
    external_ref: str | None,
    translations: TranslationValues,
) -> tuple[OrgUnit, list[OrgWarning]]:
    lock_hierarchy(db)
    code = normalise_code(code)
    ensure_absent(db, select(OrgUnit.id).where(OrgUnit.code == code), *_CODE_TAKEN)
    unit_type = get_unit_type(db, unit_type_id)
    if not unit_type.is_active:
        raise AppError(422, "unit_type_inactive", "This unit type is inactive.")
    location = _active_location(db, location_id) if location_id else None
    parent = get_unit(db, parent_id, for_update=True) if parent_id else None
    period = Period(effective_from, None)
    warnings = _validate_placement(db, unit_type, parent, period, name, None)

    unit = OrgUnit(
        code=code,
        name=name,
        short_name=clean_text(short_name),
        unit_type_id=unit_type.id,
        location_id=location.id if location else None,
        effective_from=effective_from,
        external_ref=clean_text(external_ref),
        created_by_user_id=actor.user_id,
        updated_by_user_id=actor.user_id,
    )
    apply_translations(unit.translations, _translation, translations)
    db.add(unit)
    flush_unique(db, *_CODE_TAKEN)
    if parent is not None:
        db.add(
            OrgUnitHierarchy(
                child_unit_id=unit.id,
                parent_unit_id=parent.id,
                effective_from=effective_from,
                created_by_user_id=actor.user_id,
            )
        )
        db.flush()
    audit(
        db,
        actor,
        meta,
        AuditEventType.ORG_UNIT_CREATED,
        TargetType.ORG_UNIT,
        unit.public_id,
        {
            "code": code,
            "name": name,
            "unit_type": unit_type.code,
            "parent": parent.code if parent else None,
            "location": location.code if location else None,
            "effective_from": effective_from,
            "warnings": _warning_codes(warnings),
        },
    )
    return unit, warnings


def correct_unit(
    db: Session,
    public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    reason: str | None,
    changes: Mapping[str, Any],
) -> tuple[OrgUnit, list[OrgWarning]]:
    """Fix wrongly recorded data in place (not a business change; audited before/after)."""
    lock_hierarchy(db)
    unit = get_unit(db, public_id, for_update=True)
    ensure_version(unit, version)
    own_links = _links(db, child_id=unit.id)
    child_links = _links(db, parent_id=unit.id)
    warnings: list[OrgWarning] = []
    diff: dict[str, Any] = {}

    if "code" in changes:
        new_code = normalise_code(changes["code"])
        if new_code != unit.code:
            ensure_absent(
                db,
                select(OrgUnit.id).where(OrgUnit.code == new_code, OrgUnit.id != unit.id),
                *_CODE_TAKEN,
            )
            diff["code"] = {"from": unit.code, "to": new_code}
            unit.code = new_code

    if "effective_from" in changes and changes["effective_from"] != unit.effective_from:
        new_start: date | None = changes["effective_from"]
        new_life = _make_period(new_start, unit.effective_to)
        for link in own_links:
            if link.effective_from != unit.effective_from:
                continue
            # the unit's first placement started with the unit: correct it with the unit
            new_link_period = _make_period(new_start, link.effective_to)
            if not lifetime(link.parent).covers(new_link_period):
                raise AppError(
                    422,
                    "parent_not_active",
                    "The parent unit is not active for the corrected start date.",
                )
            edges = [
                (other.child_unit_id, other.parent_unit_id)
                for other in _links(db, period=new_link_period)
                if other.id != link.id
            ]
            if creates_cycle(edges, unit.id, link.parent_unit_id):
                raise AppError(
                    422, "hierarchy_cycle", "This change would create a circular hierarchy."
                )
            link.effective_from = new_start
        for link in [*own_links, *child_links]:
            if not new_life.covers(link_period(link)):
                raise AppError(
                    422,
                    "period_conflict",
                    "The new start date would leave existing parent/child links outside "
                    "the unit's lifetime.",
                )
        diff["effective_from"] = {
            "from": jsonable(unit.effective_from),
            "to": jsonable(changes["effective_from"]),
        }
        unit.effective_from = changes["effective_from"]

    if "unit_type_id" in changes:
        new_type = get_unit_type(db, changes["unit_type_id"])
        if new_type.id != unit.unit_type_id:
            if not new_type.is_active:
                raise AppError(422, "unit_type_inactive", "This unit type is inactive.")
            # rules are checked against the latest placement and the open child links
            latest = next(
                (link for link in own_links if link.effective_to == unit.effective_to), None
            )
            warning = check_parent_rule(db, new_type, latest.parent.unit_type if latest else None)
            if warning:
                warnings.append(warning)
            for link in child_links:
                if link.effective_to is not None:
                    continue
                child = db.get(OrgUnit, link.child_unit_id)
                if child is not None:
                    warning = check_parent_rule(db, child.unit_type, new_type)
                    if warning:
                        warnings.append(warning)
            diff["unit_type"] = {"from": unit.unit_type.code, "to": new_type.code}
            unit.unit_type_id = new_type.id
            unit.unit_type = new_type

    if "name" in changes and changes["name"] != unit.name:
        new_name = changes["name"]
        for link in own_links:
            _ensure_sibling_name_free(db, new_name, link.parent, link_period(link), unit.id)
        if not fully_covered(lifetime(unit), [link_period(link) for link in own_links]):
            _ensure_sibling_name_free(db, new_name, None, lifetime(unit), unit.id)
        diff["name"] = {"from": unit.name, "to": new_name}
        unit.name = new_name

    if "location_id" in changes:
        new_location = (
            _active_location(db, changes["location_id"]) if changes["location_id"] else None
        )
        old_code = unit.location.code if unit.location else None
        new_code_value = new_location.code if new_location else None
        if old_code != new_code_value:
            diff["location"] = {"from": old_code, "to": new_code_value}
            unit.location_id = new_location.id if new_location else None
            unit.location = new_location

    for field in ("short_name", "external_ref"):
        if field in changes:
            value = clean_text(changes[field])
            if value != getattr(unit, field):
                diff[field] = {"from": getattr(unit, field), "to": value}
                setattr(unit, field, value)

    if changes.get("translations") is not None:
        translation_diff = apply_translations(
            unit.translations, _translation, changes["translations"]
        )
        if translation_diff:
            diff["translations"] = translation_diff

    if diff:
        touch(unit, actor)
        flush_unique(db, *_CODE_TAKEN)
        audit(
            db,
            actor,
            meta,
            AuditEventType.ORG_UNIT_CORRECTED,
            TargetType.ORG_UNIT,
            unit.public_id,
            {
                "code": unit.code,
                "reason": reason,
                "changes": diff,
                "warnings": _warning_codes(warnings),
            },
        )
    return unit, warnings


def move_unit(
    db: Session,
    public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    new_parent_id: uuid.UUID | None,
    effective_date: date,
) -> tuple[OrgUnit, list[OrgWarning]]:
    """Business change: from ``effective_date`` the unit sits under a new parent (or root)."""
    lock_hierarchy(db)
    unit = get_unit(db, public_id, for_update=True)
    ensure_version(unit, version)
    if not lifetime(unit).contains(effective_date) or unit.effective_from == effective_date:
        raise AppError(
            422,
            "move_date_invalid",
            "The move date must be after the unit's start date and before its closure.",
        )
    own_links = _links(db, child_id=unit.id)
    if any(link_period(link).starts_after(effective_date) for link in own_links):
        raise AppError(
            409, "later_change_exists", "A later placement change already exists for this unit."
        )
    current = next((link for link in own_links if link_period(link).contains(effective_date)), None)
    if current is not None and current.effective_from == effective_date:
        raise AppError(
            422, "move_date_invalid", "A placement already starts on this date for this unit."
        )
    new_parent = get_unit(db, new_parent_id, for_update=True) if new_parent_id else None
    old_parent_id = current.parent_unit_id if current else None
    if old_parent_id == (new_parent.id if new_parent else None):
        raise AppError(422, "no_change", "The unit is already placed there on that date.")

    new_period = Period(effective_date, unit.effective_to)
    if new_parent is not None:
        edges = [
            (link.child_unit_id, link.parent_unit_id)
            for link in _links(db, period=new_period)
            if current is None or link.id != current.id
        ]
        if creates_cycle(edges, unit.id, new_parent.id):
            raise AppError(
                422,
                "hierarchy_cycle",
                "This move would place the unit inside its own sub-tree.",
            )
    warnings = _validate_placement(db, unit.unit_type, new_parent, new_period, unit.name, unit.id)

    old_parent_code = current.parent.code if current else None
    if current is not None:
        current.effective_to = effective_date
        current.ended_at = utcnow()
        current.ended_by_user_id = actor.user_id
        db.flush()  # free the "one open link per unit" slot before opening the new link
    if new_parent is not None:
        db.add(
            OrgUnitHierarchy(
                child_unit_id=unit.id,
                parent_unit_id=new_parent.id,
                effective_from=effective_date,
                effective_to=unit.effective_to,
                created_by_user_id=actor.user_id,
            )
        )
    touch(unit, actor)
    db.flush()
    audit(
        db,
        actor,
        meta,
        AuditEventType.ORG_UNIT_MOVED,
        TargetType.ORG_UNIT,
        unit.public_id,
        {
            "code": unit.code,
            "from_parent": old_parent_code,
            "to_parent": new_parent.code if new_parent else None,
            "effective_date": effective_date,
            "warnings": _warning_codes(warnings),
        },
    )
    return unit, warnings


def close_unit(
    db: Session,
    public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    effective_date: date,
    reason: str | None,
) -> OrgUnit:
    """Business change: the unit ceases to exist from ``effective_date`` (history kept)."""
    lock_hierarchy(db)
    unit = get_unit(db, public_id, for_update=True)
    ensure_version(unit, version)
    if unit.effective_to is not None:
        raise AppError(409, "unit_already_closed", "This unit is already closed.")
    if unit.effective_from is not None and effective_date <= unit.effective_from:
        raise AppError(422, "invalid_period", "The closure date must be after the start date.")

    remaining = Period(effective_date, None)
    blockers: list[ValidationIssue] = []
    for link in _links(db, parent_id=unit.id, period=remaining):
        child = db.get(OrgUnit, link.child_unit_id)
        blockers.append(
            ValidationIssue(
                location=["children", child.code if child else str(link.child_unit_id)],
                message="Active child unit",
                type="active_child",
            )
        )
    # Locking reads: they see rows committed after this request's snapshot was taken.
    for role in db.scalars(
        select(FunctionalRole)
        .where(FunctionalRole.owner_org_unit_id == unit.id, FunctionalRole.is_active.is_(True))
        .with_for_update(read=True)
    ):
        blockers.append(
            ValidationIssue(
                location=["functional_roles", role.code],
                message="Active functional role owned by this unit",
                type="owned_functional_role",
            )
        )
    for mapping in db.scalars(
        select(DesignationFunctionalRole)
        .with_for_update(read=True)
        .where(
            DesignationFunctionalRole.scope_org_unit_id == unit.id,
            or_(
                DesignationFunctionalRole.effective_to.is_(None),
                DesignationFunctionalRole.effective_to > effective_date,
            ),
        )
    ):
        blockers.append(
            ValidationIssue(
                location=["designation_role_mappings", str(mapping.public_id)],
                message="Open designation-to-role mapping scoped to this unit",
                type="scoped_mapping",
            )
        )
    if blockers:
        raise AppError(
            409,
            "unit_has_dependants",
            "The unit still has active dependants. Move, close or end them first.",
            details=blockers,
        )

    own_links = _links(db, child_id=unit.id, period=remaining)
    if any(
        link.effective_from is not None and link.effective_from >= effective_date
        for link in own_links
    ):
        raise AppError(
            409, "later_change_exists", "A later placement change already exists for this unit."
        )
    for link in own_links:
        link.effective_to = effective_date
        link.ended_at = utcnow()
        link.ended_by_user_id = actor.user_id
    unit.effective_to = effective_date
    touch(unit, actor)
    db.flush()
    audit(
        db,
        actor,
        meta,
        AuditEventType.ORG_UNIT_CLOSED,
        TargetType.ORG_UNIT,
        unit.public_id,
        {"code": unit.code, "effective_date": effective_date, "reason": reason},
    )
    return unit


def reopen_unit(
    db: Session,
    public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    reason: str | None,
) -> OrgUnit:
    """Undo a closure (a correction): the unit and the placement it had are reopened."""
    lock_hierarchy(db)
    unit = get_unit(db, public_id, for_update=True)
    ensure_version(unit, version)
    closed_on = unit.effective_to
    if closed_on is None:
        raise AppError(409, "unit_not_closed", "This unit is not closed.")
    link = next(
        (item for item in _links(db, child_id=unit.id) if item.effective_to == closed_on), None
    )
    parent = link.parent if link else None
    if parent is not None and parent.effective_to is not None:
        raise AppError(409, "parent_closed", "Reopen the parent unit first.")
    _ensure_sibling_name_free(db, unit.name, parent, Period(closed_on, None), unit.id)

    unit.effective_to = None
    if link is not None:
        link.effective_to = None
        link.ended_at = None
        link.ended_by_user_id = None
    touch(unit, actor)
    db.flush()
    audit(
        db,
        actor,
        meta,
        AuditEventType.ORG_UNIT_REOPENED,
        TargetType.ORG_UNIT,
        unit.public_id,
        {"code": unit.code, "previously_closed_on": closed_on, "reason": reason},
    )
    return unit


# ----------------------------------------------------------------------------- reads


def parents_on(db: Session, day: date) -> dict[int, int]:
    """``{child_id: parent_id}`` for links valid on ``day`` (one parent per unit)."""
    rows = db.execute(
        select(OrgUnitHierarchy.child_unit_id, OrgUnitHierarchy.parent_unit_id).where(
            _link_covers(OrgUnitHierarchy, day)
        )
    )
    return {child: parent for child, parent in rows}


def unit_history(db: Session, unit: OrgUnit) -> list[OrgUnitHierarchy]:
    return list(
        db.scalars(
            select(OrgUnitHierarchy)
            .where(OrgUnitHierarchy.child_unit_id == unit.id)
            .order_by(
                OrgUnitHierarchy.effective_from.is_(None).desc(), OrgUnitHierarchy.effective_from
            )
        ).unique()
    )


def org_tree(
    db: Session, *, as_of: date, include_closed: bool
) -> tuple[list[OrgUnit], dict[int, int]]:
    """Units (ordered by code) and ``{child_id: parent_id}`` as of ``as_of``.

    With ``include_closed``, a closed unit is shown under the parent it had when it
    closed.
    """
    statement = select(OrgUnit).order_by(OrgUnit.code)
    if not include_closed:
        statement = statement.where(active_on(as_of))
    units = list(db.scalars(statement).unique())
    parent_of = parents_on(db, as_of)
    if include_closed:
        closed = {unit.id: unit for unit in units if unit.id not in parent_of}
        if closed:
            for link in db.scalars(
                select(OrgUnitHierarchy).where(OrgUnitHierarchy.child_unit_id.in_(closed))
            ).unique():
                unit = closed[link.child_unit_id]
                if unit.effective_to is not None and link.effective_to == unit.effective_to:
                    parent_of[unit.id] = link.parent_unit_id
    known = {unit.id for unit in units}
    return units, {child: parent for child, parent in parent_of.items() if child in known}


def list_units(
    db: Session,
    *,
    as_of: date,
    q: str | None,
    unit_type_id: uuid.UUID | None,
    parent_id: uuid.UUID | None,
    roots_only: bool,
    include_closed: bool,
    limit: int,
    after_code: str | None,
) -> tuple[list[OrgUnit], str | None]:
    statement = select(OrgUnit).order_by(OrgUnit.code).limit(limit + 1)
    if q and q.strip():
        pattern = like_pattern(q)
        statement = statement.where(
            or_(OrgUnit.code.like(pattern, escape="\\"), OrgUnit.name.like(pattern, escape="\\"))
        )
    if unit_type_id is not None:
        statement = statement.where(OrgUnit.unit_type_id == get_unit_type(db, unit_type_id).id)
    if not include_closed:
        statement = statement.where(active_on(as_of))
    link = aliased(OrgUnitHierarchy)
    if parent_id is not None:
        parent = get_unit(db, parent_id)
        statement = statement.where(
            exists().where(
                link.child_unit_id == OrgUnit.id,
                link.parent_unit_id == parent.id,
                _link_covers(link, as_of),
            )
        )
    if roots_only:
        statement = statement.where(
            ~exists().where(link.child_unit_id == OrgUnit.id, _link_covers(link, as_of))
        )
    if after_code is not None:
        statement = statement.where(OrgUnit.code > after_code)
    rows = list(db.scalars(statement).unique())
    next_cursor = encode_code_cursor(rows[limit - 1].code) if len(rows) > limit else None
    return rows[:limit], next_cursor
