"""Occupational reference lists: job families, grades, levels, designations, responsibilities.

All are configurable catalogues with an upper-case ``code``, a display name (``title``
for designations), an ``is_active`` flag and optimistic ``version``. Nothing is deleted;
entries are deactivated. None of them grant LMS permissions (ADR-023), and
responsibilities never establish practical authorisation.
"""

import uuid
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.context import RequestMeta
from app.core.errors import AppError
from app.models.common import PublicIdMixin
from app.models.occupation import (
    Designation,
    DesignationFunctionalRole,
    DesignationTranslation,
    Grade,
    JobFamily,
    JobLevel,
    Responsibility,
    ResponsibilityTranslation,
)
from app.services.audit_service import AuditEventType, TargetType
from app.services.identity.context import Actor
from app.services.organisation.graph import creates_cycle
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


@dataclass(frozen=True)
class ReferenceKind[M: PublicIdMixin]:
    model: type[M]
    key: str  # error-code prefix, e.g. "grade" -> grade_not_found / grade_code_taken
    label: str  # human label for messages
    name_field: str
    target: TargetType
    created: AuditEventType
    updated: AuditEventType
    translation: Callable[[str, str], Any] | None = None
    ranked: bool = False


JOB_FAMILY = ReferenceKind(
    JobFamily,
    "job_family",
    "job family",
    "name",
    TargetType.JOB_FAMILY,
    AuditEventType.JOB_FAMILY_CREATED,
    AuditEventType.JOB_FAMILY_UPDATED,
)
GRADE = ReferenceKind(
    Grade,
    "grade",
    "grade",
    "name",
    TargetType.GRADE,
    AuditEventType.GRADE_CREATED,
    AuditEventType.GRADE_UPDATED,
    ranked=True,
)
JOB_LEVEL = ReferenceKind(
    JobLevel,
    "job_level",
    "level",
    "name",
    TargetType.JOB_LEVEL,
    AuditEventType.JOB_LEVEL_CREATED,
    AuditEventType.JOB_LEVEL_UPDATED,
    ranked=True,
)
DESIGNATION = ReferenceKind(
    Designation,
    "designation",
    "designation",
    "title",
    TargetType.DESIGNATION,
    AuditEventType.DESIGNATION_CREATED,
    AuditEventType.DESIGNATION_UPDATED,
    translation=lambda locale, name: DesignationTranslation(locale=locale, name=name),
)
RESPONSIBILITY = ReferenceKind(
    Responsibility,
    "responsibility",
    "responsibility",
    "name",
    TargetType.RESPONSIBILITY,
    AuditEventType.RESPONSIBILITY_CREATED,
    AuditEventType.RESPONSIBILITY_UPDATED,
    translation=lambda locale, name: ResponsibilityTranslation(locale=locale, name=name),
)


def _code_taken(kind: ReferenceKind[Any]) -> tuple[str, str]:
    return f"{kind.key}_code_taken", f"This {kind.label} code is already in use."


def get_reference[M: PublicIdMixin](
    db: Session, kind: ReferenceKind[M], public_id: uuid.UUID, *, for_update: bool = False
) -> M:
    return get_or_404(
        db,
        kind.model,
        public_id,
        f"{kind.key}_not_found",
        f"{kind.label.capitalize()} not found.",
        for_update=for_update,
    )


def list_reference[M: PublicIdMixin](
    db: Session,
    kind: ReferenceKind[M],
    *,
    include_inactive: bool,
    q: str | None = None,
    after_code: str | None = None,
    limit: int | None = None,
) -> list[M]:
    model: Any = kind.model
    statement = select(kind.model)
    if kind.ranked:
        statement = statement.order_by(model.rank.is_(None), model.rank, model.code)
    else:
        statement = statement.order_by(model.code)
    if not include_inactive:
        statement = statement.where(model.is_active.is_(True))
    if q and q.strip():
        pattern = like_pattern(q)
        name_column = getattr(model, kind.name_field)
        statement = statement.where(
            or_(model.code.like(pattern, escape="\\"), name_column.like(pattern, escape="\\"))
        )
    if after_code is not None:
        statement = statement.where(model.code > after_code)
    if limit is not None:
        statement = statement.limit(limit)
    return list(db.scalars(statement).unique())


def _normalise(values: Mapping[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for field, value in values.items():
        if field == "code":
            result[field] = normalise_code(value)
        elif isinstance(value, str):
            result[field] = clean_text(value)
        else:
            result[field] = value
    return result


def create_reference[M: PublicIdMixin](
    db: Session,
    kind: ReferenceKind[M],
    *,
    actor: Actor,
    meta: RequestMeta,
    values: Mapping[str, Any],
    translations: TranslationValues | None = None,
) -> M:
    model: Any = kind.model
    fields = _normalise(values)
    ensure_absent(db, select(model.id).where(model.code == fields["code"]), *_code_taken(kind))
    factory: Any = kind.model
    entity: Any = factory(
        **fields,
        is_active=True,
        created_by_user_id=actor.user_id,
        updated_by_user_id=actor.user_id,
    )
    if translations and kind.translation is not None:
        apply_translations(entity.translations, kind.translation, translations)
    db.add(entity)
    flush_unique(db, *_code_taken(kind))
    audit(
        db,
        actor,
        meta,
        kind.created,
        kind.target,
        entity.public_id,
        {"code": entity.code, kind.name_field: getattr(entity, kind.name_field)},
    )
    result: M = entity
    return result


def update_reference[M: PublicIdMixin](
    db: Session,
    kind: ReferenceKind[M],
    entity: M,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    changes: Mapping[str, Any],
    translations: TranslationValues | None = None,
    labels: Mapping[str, dict[str, Any]] | None = None,
) -> M:
    """Apply changes to an entity already loaded FOR UPDATE.

    ``labels`` replaces raw foreign-key ids in the audit diff with readable codes.
    """
    model: Any = kind.model
    target: Any = entity
    ensure_version(target, version)
    fields = _normalise(changes)
    if fields.get("code", target.code) != target.code:
        ensure_absent(
            db,
            select(model.id).where(model.code == fields["code"], model.id != target.id),
            *_code_taken(kind),
        )
    diff: dict[str, Any] = apply_changes(target, fields)
    for field, label in (labels or {}).items():
        if field in diff:
            diff[field] = label
    if translations is not None and kind.translation is not None:
        translation_diff = apply_translations(target.translations, kind.translation, translations)
        if translation_diff:
            diff["translations"] = translation_diff
    if diff:
        touch(target, actor)
        flush_unique(db, *_code_taken(kind))
        audit(
            db,
            actor,
            meta,
            kind.updated,
            kind.target,
            target.public_id,
            {"code": target.code, "changes": diff},
        )
    return entity


# ------------------------------------------------------------------------ job families


def _active_job_family(db: Session, public_id: uuid.UUID) -> JobFamily:
    family = get_reference(db, JOB_FAMILY, public_id)
    if not family.is_active:
        raise AppError(422, "job_family_inactive", "This job family is inactive.")
    return family


def resolve_job_family(db: Session, public_id: uuid.UUID | None) -> JobFamily | None:
    return _active_job_family(db, public_id) if public_id else None


def create_job_family(
    db: Session,
    *,
    actor: Actor,
    meta: RequestMeta,
    code: str,
    name: str,
    description: str | None,
    parent_id: uuid.UUID | None,
) -> JobFamily:
    parent = resolve_job_family(db, parent_id)
    return create_reference(
        db,
        JOB_FAMILY,
        actor=actor,
        meta=meta,
        values={
            "code": code,
            "name": name,
            "description": description,
            "parent_job_family_id": parent.id if parent else None,
        },
    )


def update_job_family(
    db: Session,
    public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    changes: Mapping[str, Any],
) -> JobFamily:
    # Lock every family row: parent changes are serialised, so two concurrent edits
    # cannot each pass the cycle check and together form a loop.
    edges = {
        family_id: parent_id
        for family_id, parent_id in db.execute(
            select(JobFamily.id, JobFamily.parent_job_family_id).with_for_update()
        )
    }
    family = get_reference(db, JOB_FAMILY, public_id, for_update=True)
    values = dict(changes)
    labels: dict[str, dict[str, Any]] = {}
    if "parent_id" in values:
        parent = resolve_job_family(db, values.pop("parent_id"))
        if parent is not None:
            others = [
                (child, up) for child, up in edges.items() if up is not None and child != family.id
            ]
            if creates_cycle(others, family.id, parent.id):
                raise AppError(
                    422, "job_family_cycle", "A job family cannot sit under its own descendant."
                )
        old_id = family.parent_job_family_id
        old_parent = db.get(JobFamily, old_id) if old_id is not None else None
        labels["parent_job_family_id"] = {
            "from": old_parent.code if old_parent else None,
            "to": parent.code if parent else None,
        }
        values["parent_job_family_id"] = parent.id if parent else None
    return update_reference(
        db,
        JOB_FAMILY,
        family,
        actor=actor,
        meta=meta,
        version=version,
        changes=values,
        labels=labels,
    )


# ------------------------------------------------------------------------ designations


def update_designation(
    db: Session,
    public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    changes: Mapping[str, Any],
    translations: TranslationValues | None,
) -> Designation:
    designation = get_reference(db, DESIGNATION, public_id, for_update=True)
    values = dict(changes)
    labels: dict[str, dict[str, Any]] = {}
    if "job_family_id" in values:
        family = resolve_job_family(db, values.pop("job_family_id"))
        labels["job_family_id"] = {
            "from": designation.job_family.code if designation.job_family else None,
            "to": family.code if family else None,
        }
        values["job_family_id"] = family.id if family else None
    if values.get("is_active") is False and designation.is_active:
        ensure_absent(
            db,
            select(DesignationFunctionalRole.id).where(
                DesignationFunctionalRole.designation_id == designation.id,
                DesignationFunctionalRole.effective_to.is_(None),
            ),
            "designation_in_use",
            "End this designation's open functional-role mappings before deactivating it.",
            locking=True,
        )
    return update_reference(
        db,
        DESIGNATION,
        designation,
        actor=actor,
        meta=meta,
        version=version,
        changes=values,
        translations=translations,
        labels=labels,
    )
