"""Functional roles and the designation -> functional role mapping.

A functional role describes the work someone performs; Stage F attaches competency
requirements to it. It is NOT an organisational sub-function (those are org units)
and NOT an access role: holding one grants no LMS permission (ADR-023).

Mappings are many-to-many and effective-dated. A mapping may be scoped to an org
unit (optionally including its descendants), so the same designation can imply
different roles in different departments. Employees' derived roles are computed
from these mappings in Stage C3.
"""

import uuid
from collections.abc import Mapping
from datetime import date
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.context import RequestMeta
from app.core.errors import AppError
from app.db.types import utcnow
from app.models.occupation import (
    DesignationFunctionalRole,
    FunctionalRole,
    FunctionalRoleTranslation,
)
from app.models.organisation import OrgUnit
from app.services.audit_service import AuditEventType, TargetType
from app.services.identity.context import Actor
from app.services.organisation.periods import Period
from app.services.organisation.reference import DESIGNATION, get_reference, resolve_job_family
from app.services.organisation.support import (
    TranslationValues,
    apply_changes,
    apply_translations,
    audit,
    clean_text,
    ensure_absent,
    ensure_version,
    flush_unique,
    get_or_404,
    like_pattern,
    normalise_code,
    touch,
)
from app.services.organisation.units import get_unit

_CODE_TAKEN = ("functional_role_code_taken", "This functional role code is already in use.")


def _translation(locale: str, name: str) -> FunctionalRoleTranslation:
    return FunctionalRoleTranslation(locale=locale, name=name)


def get_role(db: Session, public_id: uuid.UUID, *, for_update: bool = False) -> FunctionalRole:
    return get_or_404(
        db,
        FunctionalRole,
        public_id,
        "functional_role_not_found",
        "Functional role not found.",
        for_update=for_update,
    )


def _open_unit(db: Session, public_id: uuid.UUID) -> OrgUnit:
    """A unit that is not closed, row-locked so a concurrent closure waits for us."""
    unit = get_unit(db, public_id, for_update=True)
    if unit.effective_to is not None:
        raise AppError(422, "unit_closed", "This organisation unit is closed.")
    return unit


def list_roles(
    db: Session,
    *,
    q: str | None,
    include_inactive: bool,
    owner_unit_id: uuid.UUID | None,
    after_code: str | None,
    limit: int,
) -> list[FunctionalRole]:
    statement = select(FunctionalRole).order_by(FunctionalRole.code).limit(limit)
    if not include_inactive:
        statement = statement.where(FunctionalRole.is_active.is_(True))
    if q and q.strip():
        pattern = like_pattern(q)
        statement = statement.where(
            or_(
                FunctionalRole.code.like(pattern, escape="\\"),
                FunctionalRole.name.like(pattern, escape="\\"),
            )
        )
    if owner_unit_id is not None:
        statement = statement.where(
            FunctionalRole.owner_org_unit_id == get_unit(db, owner_unit_id).id
        )
    if after_code is not None:
        statement = statement.where(FunctionalRole.code > after_code)
    return list(db.scalars(statement).unique())


def create_role(
    db: Session,
    *,
    actor: Actor,
    meta: RequestMeta,
    code: str,
    name: str,
    description: str | None,
    job_family_id: uuid.UUID | None,
    owner_unit_id: uuid.UUID | None,
    translations: TranslationValues,
) -> FunctionalRole:
    code = normalise_code(code)
    ensure_absent(db, select(FunctionalRole.id).where(FunctionalRole.code == code), *_CODE_TAKEN)
    family = resolve_job_family(db, job_family_id)
    owner = _open_unit(db, owner_unit_id) if owner_unit_id else None
    role = FunctionalRole(
        code=code,
        name=name,
        description=clean_text(description),
        job_family_id=family.id if family else None,
        owner_org_unit_id=owner.id if owner else None,
        is_active=True,
        created_by_user_id=actor.user_id,
        updated_by_user_id=actor.user_id,
    )
    apply_translations(role.translations, _translation, translations)
    db.add(role)
    flush_unique(db, *_CODE_TAKEN)
    audit(
        db,
        actor,
        meta,
        AuditEventType.FUNCTIONAL_ROLE_CREATED,
        TargetType.FUNCTIONAL_ROLE,
        role.public_id,
        {
            "code": code,
            "name": name,
            "job_family": family.code if family else None,
            "owner_unit": owner.code if owner else None,
        },
    )
    return role


def update_role(
    db: Session,
    public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    changes: Mapping[str, Any],
    translations: TranslationValues | None,
) -> FunctionalRole:
    role = get_role(db, public_id, for_update=True)
    ensure_version(role, version)
    values: dict[str, Any] = {}
    diff: dict[str, Any] = {}
    for field, raw in changes.items():
        if field == "code":
            values["code"] = normalise_code(raw)
        elif field in ("name",):
            values[field] = raw
        elif field == "description":
            values[field] = clean_text(raw)
        elif field == "is_active":
            values[field] = raw
        elif field == "job_family_id":
            family = resolve_job_family(db, raw)
            new_code = family.code if family else None
            old_code = role.job_family.code if role.job_family else None
            if new_code != old_code:
                diff["job_family"] = {"from": old_code, "to": new_code}
                role.job_family_id = family.id if family else None
                role.job_family = family
        elif field == "owner_unit_id":
            owner = _open_unit(db, raw) if raw else None
            new_code = owner.code if owner else None
            old_code = role.owner_org_unit.code if role.owner_org_unit else None
            if new_code != old_code:
                diff["owner_unit"] = {"from": old_code, "to": new_code}
                role.owner_org_unit_id = owner.id if owner else None
                role.owner_org_unit = owner
    if values.get("code", role.code) != role.code:
        ensure_absent(
            db,
            select(FunctionalRole.id).where(
                FunctionalRole.code == values["code"], FunctionalRole.id != role.id
            ),
            *_CODE_TAKEN,
        )
    if values.get("is_active") is False and role.is_active:
        ensure_absent(
            db,
            select(DesignationFunctionalRole.id).where(
                DesignationFunctionalRole.functional_role_id == role.id,
                DesignationFunctionalRole.effective_to.is_(None),
            ),
            "functional_role_in_use",
            "End the open designation mappings of this role before deactivating it.",
            locking=True,
        )
    diff.update(apply_changes(role, values))
    if translations is not None:
        translation_diff = apply_translations(role.translations, _translation, translations)
        if translation_diff:
            diff["translations"] = translation_diff
    if diff:
        touch(role, actor)
        flush_unique(db, *_CODE_TAKEN)
        audit(
            db,
            actor,
            meta,
            AuditEventType.FUNCTIONAL_ROLE_UPDATED,
            TargetType.FUNCTIONAL_ROLE,
            role.public_id,
            {"code": role.code, "changes": diff},
        )
    return role


# ---------------------------------------------------------------------------- mappings


def list_mappings(
    db: Session, designation_id: uuid.UUID, *, include_ended: bool
) -> list[DesignationFunctionalRole]:
    designation = get_reference(db, DESIGNATION, designation_id)
    statement = (
        select(DesignationFunctionalRole)
        .where(DesignationFunctionalRole.designation_id == designation.id)
        .order_by(DesignationFunctionalRole.id)
    )
    if not include_ended:
        statement = statement.where(DesignationFunctionalRole.effective_to.is_(None))
    return list(db.scalars(statement).unique())


def create_mapping(
    db: Session,
    designation_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    functional_role_id: uuid.UUID,
    scope_unit_id: uuid.UUID | None,
    include_descendants: bool,
    effective_from: date,
) -> DesignationFunctionalRole:
    # The designation row lock serialises mapping changes for that designation.
    designation = get_reference(db, DESIGNATION, designation_id, for_update=True)
    if not designation.is_active:
        raise AppError(422, "designation_inactive", "This designation is inactive.")
    # Row lock: serialises with a concurrent deactivation of the role.
    role = get_role(db, functional_role_id, for_update=True)
    if not role.is_active:
        raise AppError(422, "functional_role_inactive", "This functional role is inactive.")
    scope = _open_unit(db, scope_unit_id) if scope_unit_id else None
    if scope is not None and scope.effective_from and effective_from < scope.effective_from:
        raise AppError(
            422, "unit_not_active", "The scope unit does not exist yet on the start date."
        )

    new_period = Period(effective_from, None)
    existing = db.scalars(
        select(DesignationFunctionalRole)
        .with_for_update(read=True)
        .where(
            DesignationFunctionalRole.designation_id == designation.id,
            DesignationFunctionalRole.functional_role_id == role.id,
            DesignationFunctionalRole.scope_org_unit_id.is_(None)
            if scope is None
            else DesignationFunctionalRole.scope_org_unit_id == scope.id,
        )
    ).unique()
    for mapping in existing:
        if Period(mapping.effective_from, mapping.effective_to).overlaps(new_period):
            raise AppError(
                409,
                "mapping_overlap",
                "This designation is already mapped to this role, with the same scope, "
                "for overlapping dates.",
            )
    mapping = DesignationFunctionalRole(
        designation_id=designation.id,
        functional_role_id=role.id,
        scope_org_unit_id=scope.id if scope else None,
        scope_include_descendants=include_descendants if scope else False,
        effective_from=effective_from,
        created_by_user_id=actor.user_id,
    )
    db.add(mapping)
    flush_unique(db, "mapping_overlap", "This mapping is already open.")
    db.refresh(mapping)
    audit(
        db,
        actor,
        meta,
        AuditEventType.DESIGNATION_ROLE_MAPPED,
        TargetType.DESIGNATION_ROLE_MAPPING,
        mapping.public_id,
        {
            "designation": designation.code,
            "functional_role": role.code,
            "scope_unit": scope.code if scope else None,
            "include_descendants": mapping.scope_include_descendants,
            "effective_from": effective_from,
        },
    )
    return mapping


def end_mapping(
    db: Session,
    designation_id: uuid.UUID,
    mapping_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    effective_to: date,
    reason: str | None,
) -> DesignationFunctionalRole:
    designation = get_reference(db, DESIGNATION, designation_id, for_update=True)
    mapping = (
        db.scalars(
            select(DesignationFunctionalRole)
            .where(
                DesignationFunctionalRole.public_id == mapping_id,
                DesignationFunctionalRole.designation_id == designation.id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        .unique()
        .one_or_none()
    )
    if mapping is None:
        raise AppError(404, "mapping_not_found", "Designation mapping not found.")
    if mapping.effective_to is not None:
        raise AppError(409, "mapping_already_ended", "This mapping has already ended.")
    if mapping.effective_from is not None and effective_to <= mapping.effective_from:
        raise AppError(422, "invalid_period", "The end date must be after the start date.")
    mapping.effective_to = effective_to
    mapping.ended_at = utcnow()
    mapping.ended_by_user_id = actor.user_id
    db.flush()
    audit(
        db,
        actor,
        meta,
        AuditEventType.DESIGNATION_ROLE_MAPPING_ENDED,
        TargetType.DESIGNATION_ROLE_MAPPING,
        mapping.public_id,
        {
            "designation": designation.code,
            "functional_role": mapping.functional_role.code,
            "effective_to": effective_to,
            "reason": reason,
        },
    )
    return mapping
