"""Organisation unit types and their optional parent-type rules.

Rules are optional: a child type with no rules may sit under any parent (or be a
root). When rules exist, a placement outside them is either a warning (``advisory``)
or rejected (``strict``), per the child type's ``parent_rule_mode``.
"""

import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.context import RequestMeta
from app.core.errors import AppError
from app.models.organisation import (
    OrgUnitType,
    OrgUnitTypeRule,
    OrgUnitTypeTranslation,
    ParentRuleMode,
)
from app.services.audit_service import AuditEventType, TargetType
from app.services.identity.context import Actor
from app.services.organisation.support import (
    TranslationValues,
    apply_changes,
    apply_translations,
    audit,
    ensure_absent,
    ensure_version,
    flush_unique,
    get_or_404,
    normalise_code,
    touch,
)


@dataclass(frozen=True)
class OrgWarning:
    """A non-blocking finding returned with a write (e.g. an advisory rule)."""

    code: str
    message: str


def get_unit_type(db: Session, public_id: uuid.UUID, *, for_update: bool = False) -> OrgUnitType:
    return get_or_404(
        db,
        OrgUnitType,
        public_id,
        "unit_type_not_found",
        "Organisation unit type not found.",
        for_update=for_update,
    )


def list_unit_types(db: Session) -> list[OrgUnitType]:
    return list(db.scalars(select(OrgUnitType).order_by(OrgUnitType.sort_order, OrgUnitType.code)))


def rules_for(db: Session, child_type_id: int, *, locking: bool = False) -> list[OrgUnitTypeRule]:
    statement = select(OrgUnitTypeRule).where(OrgUnitTypeRule.child_type_id == child_type_id)
    if locking:
        statement = statement.with_for_update(read=True)
    return list(db.scalars(statement))


def all_rules(db: Session) -> list[OrgUnitTypeRule]:
    return list(db.scalars(select(OrgUnitTypeRule)))


def check_parent_rule(
    db: Session, child_type: OrgUnitType, parent_type: OrgUnitType | None
) -> OrgWarning | None:
    """None if allowed; a warning in advisory mode; raises in strict mode."""
    rules = rules_for(db, child_type.id)
    if not rules:
        return None
    allowed = {rule.parent_type_id for rule in rules}
    if (parent_type.id if parent_type else None) in allowed:
        return None
    where = f"under a {parent_type.name}" if parent_type else "as a top-level (root) unit"
    message = f"A {child_type.name} is not normally placed {where}."
    if child_type.parent_rule_mode == ParentRuleMode.STRICT.value:
        raise AppError(422, "type_rule_violation", message)
    return OrgWarning("type_rule_advisory", message)


def _translation(locale: str, name: str) -> OrgUnitTypeTranslation:
    return OrgUnitTypeTranslation(locale=locale, name=name)


def create_unit_type(
    db: Session,
    *,
    actor: Actor,
    meta: RequestMeta,
    code: str,
    name: str,
    description: str | None,
    sort_order: int,
    allows_employee_assignment: bool,
    parent_rule_mode: ParentRuleMode,
    translations: TranslationValues,
) -> OrgUnitType:
    code = normalise_code(code)
    ensure_absent(
        db,
        select(OrgUnitType.id).where(OrgUnitType.code == code),
        "unit_type_code_taken",
        "This unit type code is already in use.",
    )
    unit_type = OrgUnitType(
        code=code,
        name=name,
        description=description,
        sort_order=sort_order,
        allows_employee_assignment=allows_employee_assignment,
        is_active=True,
        parent_rule_mode=parent_rule_mode.value,
        created_by_user_id=actor.user_id,
        updated_by_user_id=actor.user_id,
    )
    apply_translations(unit_type.translations, _translation, translations)
    db.add(unit_type)
    flush_unique(db, "unit_type_code_taken", "This unit type code is already in use.")
    audit(
        db,
        actor,
        meta,
        AuditEventType.ORG_UNIT_TYPE_CREATED,
        TargetType.ORG_UNIT_TYPE,
        unit_type.public_id,
        {"code": code, "name": name, "parent_rule_mode": parent_rule_mode.value},
    )
    return unit_type


def update_unit_type(
    db: Session,
    public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    changes: Mapping[str, Any],
    translations: TranslationValues | None,
) -> OrgUnitType:
    unit_type = get_unit_type(db, public_id, for_update=True)
    ensure_version(unit_type, version)
    values = dict(changes)
    if "parent_rule_mode" in values:
        values["parent_rule_mode"] = ParentRuleMode(values["parent_rule_mode"]).value
    diff: dict[str, Any] = apply_changes(unit_type, values)
    if translations is not None:
        translation_diff = apply_translations(unit_type.translations, _translation, translations)
        if translation_diff:
            diff["translations"] = translation_diff
    if diff:
        touch(unit_type, actor)
        audit(
            db,
            actor,
            meta,
            AuditEventType.ORG_UNIT_TYPE_UPDATED,
            TargetType.ORG_UNIT_TYPE,
            unit_type.public_id,
            {"code": unit_type.code, "changes": diff},
        )
    return unit_type


def set_parent_rules(
    db: Session,
    public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    allow_root: bool,
    parent_type_ids: list[uuid.UUID],
) -> OrgUnitType:
    """Replace the allowed parent types of a unit type (empty + no root = no rules)."""
    unit_type = get_unit_type(db, public_id, for_update=True)
    ensure_version(unit_type, version)
    parents = {pid: get_unit_type(db, pid) for pid in parent_type_ids}
    by_id = {parent.id: parent for parent in parents.values()}
    desired: set[int | None] = set(by_id) | ({None} if allow_root else set())

    existing = rules_for(db, unit_type.id, locking=True)
    current = {rule.parent_type_id for rule in existing}
    if desired == current:
        return unit_type

    def label(type_ids: set[int | None]) -> list[str]:
        codes = []
        for type_id in type_ids:
            if type_id is None:
                codes.append("(root)")
            else:
                found = by_id.get(type_id) or db.get(OrgUnitType, type_id)
                codes.append(found.code if found else str(type_id))
        return sorted(codes)

    previous = label(current)
    for rule in existing:
        if rule.parent_type_id not in desired:
            db.delete(rule)
    db.flush()
    for type_id in desired - current:
        db.add(
            OrgUnitTypeRule(
                child_type_id=unit_type.id,
                parent_type_id=type_id,
                created_by_user_id=actor.user_id,
            )
        )
    touch(unit_type, actor)
    audit(
        db,
        actor,
        meta,
        AuditEventType.ORG_UNIT_TYPE_RULES_CHANGED,
        TargetType.ORG_UNIT_TYPE,
        unit_type.public_id,
        {"code": unit_type.code, "from": previous, "to": label(desired)},
    )
    return unit_type
