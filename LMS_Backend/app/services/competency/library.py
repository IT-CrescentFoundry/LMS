"""Competency library, proficiency scales, skill matrices and assessments.

* Scales are configuration: levels are ordered by ``rank`` and may be added or
  relabelled, but a level already used by a requirement or an assessment cannot be
  removed (its meaning is history).
* Matrix requirements must use a level of the matrix's scale; a competency may use a
  matrix only if its own scale (when set) is the matrix's scale.
* Assessments are append-only and must use a level of the competency's scale (or the
  matrix's scale when the competency has none).
* Library entries are created as ``draft``; only an explicit, audited status change by
  an authorised user approves them (or returns them to draft, with a reason).
* Grade-band requirements (library columns J-M) are configuration of the competency:
  changing them never alters recorded assessments; every change is audited with the
  previous and new values. How bands map to employees' grades is an open business
  decision, so no employee gap is derived from bands.
"""

import uuid
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.core.context import RequestMeta
from app.core.errors import AppError
from app.db.types import utcnow
from app.models.competency import (
    AssessmentMethod,
    Competency,
    CompetencyAssessment,
    CompetencyBandRequirement,
    CompetencyStatus,
    GapMethod,
    ProficiencyLevel,
    ProficiencyScale,
    SkillMatrix,
    SkillMatrixItem,
    SkillMatrixMember,
)
from app.models.employees import Employee
from app.models.occupation import Designation, FunctionalRole
from app.models.organisation import Location, OrgUnit
from app.services.audit_service import AuditEventType, TargetType
from app.services.competency.gap import (
    Gap,
    LevelRef,
    StaffingRisk,
    compute_gap,
    needs_development_plan,
    staffing_risk,
    summarise,
)
from app.services.identity.context import Actor
from app.services.organisation.support import (
    apply_changes,
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
from app.services.training.scope import RecordScope

_SCALE_TAKEN = ("proficiency_scale_code_taken", "This scale code is already in use.")
_COMPETENCY_TAKEN = ("competency_code_taken", "This competency code is already in use.")
_MATRIX_TAKEN = ("skill_matrix_code_taken", "This matrix code is already in use.")


def _clean(values: Mapping[str, Any]) -> dict[str, Any]:
    return {k: (clean_text(v) if isinstance(v, str) else v) for k, v in values.items()}


# --------------------------------------------------------------------------- scales


def get_scale(db: Session, public_id: uuid.UUID, *, for_update: bool = False) -> ProficiencyScale:
    return get_or_404(
        db,
        ProficiencyScale,
        public_id,
        "proficiency_scale_not_found",
        "Proficiency scale not found.",
        for_update=for_update,
    )


def list_scales(db: Session) -> list[ProficiencyScale]:
    return list(db.scalars(select(ProficiencyScale).order_by(ProficiencyScale.name)))


def _check_rank_settings(ranks: set[int], competent_rank: int | None) -> None:
    if competent_rank is not None and competent_rank not in ranks:
        raise AppError(
            422, "competent_rank_invalid", "The competent rank must be one of the levels."
        )


def _validate_levels(levels: Sequence[Mapping[str, Any]]) -> None:
    if not levels:
        raise AppError(422, "levels_required", "A scale needs at least one level.")
    ranks = [lvl["rank"] for lvl in levels]
    codes = [str(lvl["code"]).strip().upper() for lvl in levels]
    if len(set(ranks)) != len(ranks) or len(set(codes)) != len(codes):
        raise AppError(
            422, "levels_not_unique", "Level ranks and codes must be unique within a scale."
        )


def create_scale(
    db: Session,
    *,
    actor: Actor,
    meta: RequestMeta,
    values: Mapping[str, Any],
    levels: Sequence[Mapping[str, Any]],
) -> ProficiencyScale:
    data = _clean(values)
    data["code"] = normalise_code(data["code"])
    if data.get("gap_method", GapMethod.ORDINAL.value) not in {m.value for m in GapMethod}:
        raise AppError(422, "invalid_gap_method", "Gap method must be ordinal or numeric.")
    _validate_levels(levels)
    _check_rank_settings({lvl["rank"] for lvl in levels}, data.get("competent_rank"))
    ensure_absent(
        db, select(ProficiencyScale.id).where(ProficiencyScale.code == data["code"]), *_SCALE_TAKEN
    )
    scale = ProficiencyScale(
        **data, is_active=True, created_by_user_id=actor.user_id, updated_by_user_id=actor.user_id
    )
    scale.levels = [
        ProficiencyLevel(
            rank=lvl["rank"],
            code=str(lvl["code"]).strip().upper(),
            label=str(lvl["label"]).strip(),
            numeric_value=lvl.get("numeric_value"),
            description=clean_text(lvl.get("description")),
        )
        for lvl in levels
    ]
    db.add(scale)
    flush_unique(db, *_SCALE_TAKEN)
    audit(
        db,
        actor,
        meta,
        AuditEventType.PROFICIENCY_SCALE_CREATED,
        TargetType.PROFICIENCY_SCALE,
        scale.public_id,
        {"code": scale.code, "levels": [lvl.code for lvl in scale.levels]},
    )
    return scale


def _level_in_use(db: Session, level_id: int) -> bool:
    for statement in (
        select(SkillMatrixItem.id).where(SkillMatrixItem.required_level_id == level_id),
        select(CompetencyAssessment.id).where(CompetencyAssessment.level_id == level_id),
    ):
        if db.scalar(statement.limit(1)) is not None:
            return True
    return False


def update_scale(
    db: Session,
    public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    changes: Mapping[str, Any],
    levels: Sequence[Mapping[str, Any]] | None,
) -> ProficiencyScale:
    scale = get_scale(db, public_id, for_update=True)
    ensure_version(scale, version)
    data = _clean(changes)
    if "code" in data:
        data["code"] = normalise_code(data["code"])
        if data["code"] != scale.code:
            ensure_absent(
                db,
                select(ProficiencyScale.id).where(
                    ProficiencyScale.code == data["code"], ProficiencyScale.id != scale.id
                ),
                *_SCALE_TAKEN,
            )
    if data.get("gap_method") and data["gap_method"] not in {m.value for m in GapMethod}:
        raise AppError(422, "invalid_gap_method", "Gap method must be ordinal or numeric.")
    diff: dict[str, Any] = dict(apply_changes(scale, data))
    if levels is not None:
        _validate_levels(levels)
        by_id = {str(lvl.public_id): lvl for lvl in scale.levels}
        keep: list[ProficiencyLevel] = []
        for item in levels:
            existing = by_id.pop(str(item["public_id"]), None) if item.get("public_id") else None
            target = existing or ProficiencyLevel(scale_id=scale.id)
            if (
                existing is not None
                and existing.rank != item["rank"]
                and _level_in_use(db, existing.id)
            ):
                raise AppError(
                    409,
                    "level_in_use",
                    f"Level {existing.code} is in use; its order cannot change.",
                )
            target.rank = item["rank"]
            target.code = str(item["code"]).strip().upper()
            target.label = str(item["label"]).strip()
            target.numeric_value = item.get("numeric_value")
            target.description = clean_text(item.get("description"))
            keep.append(target)
        for removed in by_id.values():
            if _level_in_use(db, removed.id):
                raise AppError(
                    409, "level_in_use", f"Level {removed.code} is in use and cannot be removed."
                )
        # Two-phase rank update avoids transient UNIQUE(scale, rank) collisions.
        for offset, lvl in enumerate(scale.levels):
            lvl.rank = 10000 + offset
        db.flush()
        scale.levels = keep
        diff["levels"] = [f"{lvl.rank}:{lvl.code}" for lvl in keep]
    _check_rank_settings({lvl.rank for lvl in scale.levels}, scale.competent_rank)
    if diff:
        touch(scale, actor)
        flush_unique(
            db, "levels_not_unique", "Level ranks and codes must be unique within a scale."
        )
        audit(
            db,
            actor,
            meta,
            AuditEventType.PROFICIENCY_SCALE_UPDATED,
            TargetType.PROFICIENCY_SCALE,
            scale.public_id,
            {"code": scale.code, "changes": diff},
        )
    return scale


# ---------------------------------------------------------------------- competencies


def get_competency(db: Session, public_id: uuid.UUID, *, for_update: bool = False) -> Competency:
    return get_or_404(
        db,
        Competency,
        public_id,
        "competency_not_found",
        "Competency not found.",
        for_update=for_update,
    )


def list_competencies(
    db: Session,
    *,
    q: str | None,
    category: str | None,
    include_inactive: bool,
    limit: int,
    offset: int,
    status: str | None = None,
) -> tuple[list[Competency], int]:
    statement = select(Competency)
    if not include_inactive:
        statement = statement.where(Competency.is_active.is_(True))
    if status:
        statement = statement.where(Competency.status == status)
    if q and q.strip():
        pattern = like_pattern(q)
        statement = statement.where(
            or_(Competency.name.like(pattern), Competency.code.like(pattern))
        )
    if category:
        statement = statement.where(Competency.category == category)
    total = db.scalar(select(func.count()).select_from(statement.subquery())) or 0
    rows = db.scalars(
        statement.order_by(Competency.category, Competency.code).limit(limit).offset(offset)
    ).unique()
    return list(rows), int(total)


def competency_categories(db: Session) -> list[str]:
    return [
        row
        for row in db.scalars(
            select(Competency.category)
            .where(Competency.category.is_not(None))
            .distinct()
            .order_by(Competency.category)
        )
        if row
    ]


def _competency_values(db: Session, values: Mapping[str, Any]) -> dict[str, Any]:
    data = _clean(values)
    if "code" in data:
        data["code"] = normalise_code(data["code"])
    if "scale" in data:
        scale = data.pop("scale")
        data["scale_id"] = get_scale(db, scale).id if scale else None
    if "owner_org_unit" in data:
        unit = data.pop("owner_org_unit")
        data["owner_org_unit_id"] = (
            get_or_404(db, OrgUnit, unit, "org_unit_not_found", "Organisation unit not found.").id
            if unit
            else None
        )
    if "name" in data and not data["name"]:
        raise AppError(422, "name_required", "A name is required.")
    return data


def create_competency(
    db: Session, *, actor: Actor, meta: RequestMeta, values: Mapping[str, Any]
) -> Competency:
    data = _competency_values(db, values)
    data.pop("status", None)  # never set on creation: every new entry starts as a draft
    ensure_absent(
        db, select(Competency.id).where(Competency.code == data["code"]), *_COMPETENCY_TAKEN
    )
    competency = Competency(
        **data,
        is_active=True,
        status=CompetencyStatus.DRAFT.value,
        created_by_user_id=actor.user_id,
        updated_by_user_id=actor.user_id,
    )
    db.add(competency)
    flush_unique(db, *_COMPETENCY_TAKEN)
    audit(
        db,
        actor,
        meta,
        AuditEventType.COMPETENCY_CREATED,
        TargetType.COMPETENCY,
        competency.public_id,
        {"code": competency.code, "name": competency.name, "status": competency.status},
    )
    return competency


def update_competency(
    db: Session,
    public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    changes: Mapping[str, Any],
) -> Competency:
    competency = get_competency(db, public_id, for_update=True)
    ensure_version(competency, version)
    data = _competency_values(db, changes)
    if data.get("code", competency.code) != competency.code:
        ensure_absent(
            db,
            select(Competency.id).where(
                Competency.code == data["code"], Competency.id != competency.id
            ),
            *_COMPETENCY_TAKEN,
        )
    if "scale_id" in data and data["scale_id"] != competency.scale_id:
        used = db.scalar(
            select(CompetencyAssessment.id)
            .where(CompetencyAssessment.competency_id == competency.id)
            .limit(1)
        )
        if used is not None:
            raise AppError(
                409, "competency_assessed", "The scale cannot change once assessments exist."
            )
    diff = apply_changes(competency, data)
    if diff:
        touch(competency, actor)
        flush_unique(db, *_COMPETENCY_TAKEN)
        audit(
            db,
            actor,
            meta,
            AuditEventType.COMPETENCY_UPDATED,
            TargetType.COMPETENCY,
            competency.public_id,
            {"code": competency.code, "changes": diff},
        )
    return competency


def change_competency_status(
    db: Session,
    public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    target: str,
    reason: str | None,
) -> Competency:
    """Approve a draft, or return an approved entry to draft (a reason is required)."""
    competency = get_competency(db, public_id, for_update=True)
    ensure_version(competency, version)
    if target not in {s.value for s in CompetencyStatus}:
        raise AppError(422, "invalid_competency_status", "Unknown competency status.")
    if target == competency.status:
        raise AppError(409, "status_unchanged", "The competency already has this status.")
    reason = clean_text(reason)
    if target == CompetencyStatus.DRAFT.value and not reason:
        raise AppError(422, "reason_required", "Give a reason for returning it to draft.")
    if target == CompetencyStatus.APPROVED.value and not competency.is_active:
        raise AppError(409, "competency_inactive", "An inactive competency cannot be approved.")
    before = competency.status
    competency.status = target
    if target == CompetencyStatus.APPROVED.value:
        competency.approved_at = utcnow()
        competency.approved_by_user_id = actor.user_id
    else:
        competency.approved_at = None
        competency.approved_by_user_id = None
    touch(competency, actor)
    db.flush()
    audit(
        db,
        actor,
        meta,
        AuditEventType.COMPETENCY_STATUS_CHANGED,
        TargetType.COMPETENCY,
        competency.public_id,
        {"code": competency.code, "from": before, "to": target, "reason": reason},
    )
    return competency


def set_band_requirements(
    db: Session,
    public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    items: Sequence[Mapping[str, Any]],
) -> Competency:
    """Replace the competency's grade-band requirements (band code -> required level).

    Bands are stored verbatim in upper case (e.g. ``L6-L5``); the required level must
    belong to the competency's own scale; a band without a level is "requirement
    pending". Recorded assessments are never changed."""
    competency = get_competency(db, public_id, for_update=True)
    ensure_version(competency, version)
    scale = competency.scale
    levels = {str(level.public_id): level for level in (scale.levels if scale else [])}
    wanted: dict[str, tuple[str | None, ProficiencyLevel | None]] = {}
    for item in items:
        band = clean_text(item.get("band_code"))
        if not band:
            raise AppError(422, "band_code_required", "Each requirement needs a band code.")
        band = band.upper()
        if band in wanted:
            raise AppError(422, "duplicate_band", f"Band {band} is listed twice.")
        level = None
        if item.get("required_level"):
            if scale is None:
                raise AppError(
                    422,
                    "scale_unknown",
                    "Set the competency's proficiency scale before recording band levels.",
                )
            level = levels.get(str(item["required_level"]))
            if level is None:
                raise AppError(
                    422,
                    "level_not_in_scale",
                    "The required level must belong to the competency's proficiency scale.",
                )
        wanted[band] = (clean_text(item.get("band_label")), level)

    def snapshot() -> dict[str, dict[str, str | None]]:
        return {
            r.band_code: {
                "label": r.band_label,
                "level": r.required_level.code if r.required_level else None,
            }
            for r in competency.band_requirements
        }

    before = snapshot()
    current = {r.band_code: r for r in competency.band_requirements}
    for band, row in current.items():
        if band not in wanted:
            competency.band_requirements.remove(row)  # configuration, not a record of fact
    for band, (label, level) in wanted.items():
        existing = current.get(band)
        if existing is None:
            competency.band_requirements.append(
                CompetencyBandRequirement(
                    band_code=band,
                    band_label=label,
                    required_level_id=level.id if level else None,
                )
            )
        else:
            existing.band_label = label
            existing.required_level_id = level.id if level else None
    db.flush()
    db.refresh(competency, ["band_requirements"])
    after = snapshot()
    if before != after:
        touch(competency, actor)
        db.flush()
        audit(
            db,
            actor,
            meta,
            AuditEventType.COMPETENCY_BAND_REQUIREMENTS_CHANGED,
            TargetType.COMPETENCY,
            competency.public_id,
            {"code": competency.code, "from": before, "to": after},
        )
    return competency


# ------------------------------------------------------------------------- matrices


def get_matrix(db: Session, public_id: uuid.UUID, *, for_update: bool = False) -> SkillMatrix:
    return get_or_404(
        db,
        SkillMatrix,
        public_id,
        "skill_matrix_not_found",
        "Skill matrix not found.",
        for_update=for_update,
    )


def list_matrices(
    db: Session,
    *,
    q: str | None,
    unit_ids: set[int] | None,
    location_id: int | None,
    include_inactive: bool,
) -> list[SkillMatrix]:
    statement = select(SkillMatrix).order_by(SkillMatrix.name)
    if not include_inactive:
        statement = statement.where(SkillMatrix.is_active.is_(True))
    if q and q.strip():
        pattern = like_pattern(q)
        statement = statement.where(
            or_(SkillMatrix.name.like(pattern), SkillMatrix.code.like(pattern))
        )
    if unit_ids is not None:
        statement = statement.where(SkillMatrix.org_unit_id.in_(sorted(unit_ids)))
    if location_id is not None:
        statement = statement.where(SkillMatrix.location_id == location_id)
    return list(db.scalars(statement).unique())


def _matrix_values(db: Session, values: Mapping[str, Any]) -> dict[str, Any]:
    data = _clean(values)
    if "code" in data:
        data["code"] = normalise_code(data["code"])
    for field, model, code, label in (
        ("org_unit", OrgUnit, "org_unit_not_found", "Organisation unit"),
        ("location", Location, "location_not_found", "Location"),
        ("designation", Designation, "designation_not_found", "Designation"),
        ("functional_role", FunctionalRole, "functional_role_not_found", "Functional role"),
        ("scale", ProficiencyScale, "proficiency_scale_not_found", "Proficiency scale"),
    ):
        if field in data:
            public_id = data.pop(field)
            data[f"{field}_id"] = (
                get_or_404(db, model, public_id, code, f"{label} not found.").id  # type: ignore[attr-defined]
                if public_id
                else None
            )
    if "scale_id" in data and data["scale_id"] is None:
        raise AppError(422, "scale_required", "A skill matrix needs a proficiency scale.")
    return data


def create_matrix(
    db: Session, *, actor: Actor, meta: RequestMeta, values: Mapping[str, Any]
) -> SkillMatrix:
    data = _matrix_values(db, values)
    ensure_absent(
        db, select(SkillMatrix.id).where(SkillMatrix.code == data["code"]), *_MATRIX_TAKEN
    )
    matrix = SkillMatrix(
        **data, is_active=True, created_by_user_id=actor.user_id, updated_by_user_id=actor.user_id
    )
    db.add(matrix)
    flush_unique(db, *_MATRIX_TAKEN)
    audit(
        db,
        actor,
        meta,
        AuditEventType.SKILL_MATRIX_CREATED,
        TargetType.SKILL_MATRIX,
        matrix.public_id,
        {"code": matrix.code, "name": matrix.name},
    )
    return matrix


def update_matrix(
    db: Session,
    public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    changes: Mapping[str, Any],
) -> SkillMatrix:
    matrix = get_matrix(db, public_id, for_update=True)
    ensure_version(matrix, version)
    data = _matrix_values(db, changes)
    if data.get("code", matrix.code) != matrix.code:
        ensure_absent(
            db,
            select(SkillMatrix.id).where(
                SkillMatrix.code == data["code"], SkillMatrix.id != matrix.id
            ),
            *_MATRIX_TAKEN,
        )
    if "scale_id" in data and data["scale_id"] != matrix.scale_id and matrix.items:
        raise AppError(
            409, "matrix_has_items", "Remove the requirements before changing the matrix's scale."
        )
    diff = apply_changes(matrix, data)
    if diff:
        touch(matrix, actor)
        flush_unique(db, *_MATRIX_TAKEN)
        audit(
            db,
            actor,
            meta,
            AuditEventType.SKILL_MATRIX_UPDATED,
            TargetType.SKILL_MATRIX,
            matrix.public_id,
            {"code": matrix.code, "changes": diff},
        )
    return matrix


def set_matrix_items(
    db: Session,
    public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    version: int,
    items: Sequence[Mapping[str, Any]],
) -> SkillMatrix:
    """Replace the matrix's requirement list (competency, required level, group, order)."""
    matrix = get_matrix(db, public_id, for_update=True)
    ensure_version(matrix, version)
    levels = {str(lvl.public_id): lvl for lvl in matrix.scale.levels}
    seen: set[int] = set()
    wanted: list[tuple[Competency, ProficiencyLevel | None, str | None, int]] = []
    headcounts: dict[int, int | None] = {}
    for position, item in enumerate(items):
        competency = get_competency(db, item["competency"])
        if competency.id in seen:
            raise AppError(422, "duplicate_competency", f"{competency.code} is listed twice.")
        seen.add(competency.id)
        if competency.scale_id is not None and competency.scale_id != matrix.scale_id:
            raise AppError(
                422, "scale_mismatch", f"{competency.code} uses a different proficiency scale."
            )
        level = None
        if item.get("required_level"):
            level = levels.get(str(item["required_level"]))
            if level is None:
                raise AppError(
                    422,
                    "level_not_in_scale",
                    "The required level must belong to the matrix's scale.",
                )
        headcounts[competency.id] = item.get("required_headcount")
        wanted.append(
            (
                competency,
                level,
                clean_text(item.get("group_label")),
                item.get("display_order", position),
            )
        )
    current = {
        row.competency_id: row
        for row in db.scalars(select(SkillMatrixItem).where(SkillMatrixItem.matrix_id == matrix.id))
    }
    for competency_id, row in current.items():
        if competency_id not in seen:
            db.delete(row)
    for competency, level, group, order in wanted:
        existing_item = current.get(competency.id)
        if existing_item is None:
            db.add(
                SkillMatrixItem(
                    matrix_id=matrix.id,
                    competency_id=competency.id,
                    required_level_id=level.id if level else None,
                    required_headcount=headcounts[competency.id],
                    group_label=group,
                    display_order=order,
                )
            )
        else:
            existing_item.required_level_id = level.id if level else None
            existing_item.group_label, existing_item.display_order = group, order
            existing_item.required_headcount = headcounts[competency.id]
    touch(matrix, actor)
    db.flush()
    db.refresh(matrix, ["items"])
    audit(
        db,
        actor,
        meta,
        AuditEventType.SKILL_MATRIX_ITEMS_CHANGED,
        TargetType.SKILL_MATRIX,
        matrix.public_id,
        {
            "code": matrix.code,
            "items": [
                {"competency": c.code, "required": lv.code if lv else None}
                for c, lv, _g, _o in wanted
            ],
        },
    )
    return matrix


def set_matrix_members(
    db: Session,
    public_id: uuid.UUID,
    *,
    actor: Actor,
    meta: RequestMeta,
    add: Sequence[uuid.UUID],
    remove: Sequence[uuid.UUID],
) -> SkillMatrix:
    matrix = get_matrix(db, public_id, for_update=True)
    ids = list(dict.fromkeys([*add, *remove]))
    employees = {
        e.public_id: e for e in db.scalars(select(Employee).where(Employee.public_id.in_(ids)))
    }
    if len(employees) != len(ids):
        raise AppError(404, "employee_not_found", "One or more employees were not found.")
    existing = {
        row.employee_id: row
        for row in db.scalars(
            select(SkillMatrixMember).where(SkillMatrixMember.matrix_id == matrix.id)
        )
    }
    added, removed = [], []
    for pid in add:
        emp = employees[pid]
        if emp.id not in existing:
            db.add(
                SkillMatrixMember(
                    matrix_id=matrix.id, employee_id=emp.id, added_by_user_id=actor.user_id
                )
            )
            added.append(emp.employee_code)
    for pid in remove:
        emp = employees[pid]
        if emp.id in existing:
            db.delete(existing[emp.id])  # membership is a mapping, not a record of fact
            removed.append(emp.employee_code)
    if added or removed:
        touch(matrix, actor)
        db.flush()
        audit(
            db,
            actor,
            meta,
            AuditEventType.SKILL_MATRIX_MEMBERS_CHANGED,
            TargetType.SKILL_MATRIX,
            matrix.public_id,
            {"code": matrix.code, "added": added, "removed": removed},
        )
    return matrix


def member_ids(db: Session, matrix: SkillMatrix) -> list[int]:
    return list(
        db.scalars(
            select(SkillMatrixMember.employee_id).where(SkillMatrixMember.matrix_id == matrix.id)
        )
    )


# ---------------------------------------------------------------------- assessments


def record_assessment(
    db: Session,
    *,
    actor: Actor,
    meta: RequestMeta,
    today: date,
    employee_public_id: uuid.UUID,
    competency_public_id: uuid.UUID,
    level_public_id: uuid.UUID,
    assessed_on: date,
    method: str,
    assessor_employee_public_id: uuid.UUID | None,
    assessor_name: str | None,
    evidence: str | None,
    matrix_public_id: uuid.UUID | None,
) -> CompetencyAssessment:
    employee = get_or_404(
        db, Employee, employee_public_id, "employee_not_found", "Employee not found."
    )
    competency = get_competency(db, competency_public_id)
    matrix = get_matrix(db, matrix_public_id) if matrix_public_id else None
    scale_id = competency.scale_id or (matrix.scale_id if matrix else None)
    if scale_id is None:
        raise AppError(
            422,
            "scale_unknown",
            "This competency has no proficiency scale; assess it within a skill matrix.",
        )
    level = db.scalar(select(ProficiencyLevel).where(ProficiencyLevel.public_id == level_public_id))
    if level is None or level.scale_id != scale_id:
        raise AppError(
            422,
            "level_not_in_scale",
            "The level must belong to the competency's proficiency scale.",
        )
    if method not in {m.value for m in AssessmentMethod}:
        raise AppError(422, "invalid_method", "Unknown assessment method.")
    if assessed_on > today:
        raise AppError(422, "assessed_in_future", "The assessment date cannot be in the future.")
    assessor_id = None
    if assessor_employee_public_id:
        assessor_id = get_or_404(
            db, Employee, assessor_employee_public_id, "employee_not_found", "Assessor not found."
        ).id
        if assessor_id == employee.id:
            raise AppError(
                422, "self_assessment", "An employee cannot record their own official assessment."
            )
    row = CompetencyAssessment(
        employee_id=employee.id,
        competency_id=competency.id,
        level_id=level.id,
        assessed_on=assessed_on,
        method=method,
        assessor_employee_id=assessor_id,
        assessor_name=clean_text(assessor_name),
        evidence=clean_text(evidence),
        matrix_id=matrix.id if matrix else None,
        recorded_by_user_id=actor.user_id,
    )
    db.add(row)
    db.flush()
    audit(
        db,
        actor,
        meta,
        AuditEventType.COMPETENCY_ASSESSMENT_RECORDED,
        TargetType.COMPETENCY,
        competency.public_id,
        {
            "employee": employee.employee_code,
            "competency": competency.code,
            "level": level.code,
            "assessed_on": assessed_on,
            "method": method,
        },
    )
    return row


def assessment_history(
    db: Session, employee_id: int, competency_id: int | None = None
) -> list[CompetencyAssessment]:
    statement = select(CompetencyAssessment).where(CompetencyAssessment.employee_id == employee_id)
    if competency_id is not None:
        statement = statement.where(CompetencyAssessment.competency_id == competency_id)
    return list(
        db.scalars(
            statement.order_by(
                CompetencyAssessment.assessed_on.desc(), CompetencyAssessment.id.desc()
            )
        )
    )


def latest_assessments(
    db: Session, employee_ids: Sequence[int], competency_ids: Sequence[int]
) -> dict[tuple[int, int], CompetencyAssessment]:
    """Latest assessment per (employee, competency): max assessed_on, then max id."""
    if not employee_ids or not competency_ids:
        return {}
    rows = db.scalars(
        select(CompetencyAssessment)
        .where(
            CompetencyAssessment.employee_id.in_(list(employee_ids)),
            CompetencyAssessment.competency_id.in_(list(competency_ids)),
        )
        .order_by(CompetencyAssessment.assessed_on, CompetencyAssessment.id)
    )
    latest: dict[tuple[int, int], CompetencyAssessment] = {}
    for row in rows:
        latest[(row.employee_id, row.competency_id)] = row  # later rows win
    return latest


# ---------------------------------------------------------------------- matrix view


@dataclass(frozen=True)
class MatrixCell:
    item: SkillMatrixItem
    assessment: CompetencyAssessment | None
    gap: Gap
    needs_plan: bool


@dataclass(frozen=True)
class MatrixRow:
    employee: Employee
    cells: list[MatrixCell]


@dataclass(frozen=True)
class ItemStats:
    """Per-competency headcounts over all matrix members (workbook column formulas)."""

    item: SkillMatrixItem
    counts_by_rank: dict[int, int]
    not_assessed: int
    skilled: int | None  # members at or above the scale's competent rank
    risk: StaffingRisk | None


def _ref(level: ProficiencyLevel | None) -> LevelRef | None:
    return None if level is None else LevelRef(level.scale_id, level.rank, level.numeric_value)


def item_stats(
    matrix: SkillMatrix,
    items: list[SkillMatrixItem],
    member_list: list[int],
    latest: dict[tuple[int, int], CompetencyAssessment],
) -> list[ItemStats]:
    competent = matrix.scale.competent_rank
    stats: list[ItemStats] = []
    for item in items:
        counts: dict[int, int] = {lvl.rank: 0 for lvl in matrix.scale.levels}
        missing = 0
        for employee_id in member_list:
            assessment = latest.get((employee_id, item.competency_id))
            if assessment is None or assessment.level.scale_id != matrix.scale_id:
                missing += 1
            else:
                counts[assessment.level.rank] = counts.get(assessment.level.rank, 0) + 1
        skilled = (
            sum(n for rank, n in counts.items() if rank >= competent)
            if competent is not None
            else None
        )
        risk = (
            staffing_risk(skilled, item.required_headcount, matrix.risk_medium_margin)
            if skilled is not None
            else None
        )
        stats.append(ItemStats(item, counts, missing, skilled, risk))
    return stats


def matrix_grid(
    db: Session, matrix: SkillMatrix, scope: RecordScope
) -> tuple[list[MatrixRow], dict[str, int], list[ItemStats] | None]:
    """Rows are narrowed to ``scope``; headcount statistics (which summarise every
    member) are returned only to users who may see every employee."""
    all_members = member_ids(db, matrix)
    ids = [i for i in all_members if scope.allows(i)]
    employees = list(
        db.scalars(
            select(Employee).where(Employee.id.in_(ids or [0])).order_by(Employee.employee_code)
        )
    )
    items = list(matrix.items)
    stat_ids = all_members if scope.is_global else [e.id for e in employees]
    latest = latest_assessments(db, stat_ids, [i.competency_id for i in items])
    rows: list[MatrixRow] = []
    gaps: list[Gap] = []
    for employee in employees:
        cells = []
        for item in items:
            assessment = latest.get((employee.id, item.competency_id))
            gap = compute_gap(
                _ref(item.required_level),
                _ref(assessment.level) if assessment else None,
                gap_method=matrix.scale.gap_method,
            )
            gaps.append(gap)
            cells.append(
                MatrixCell(
                    item, assessment, gap, needs_development_plan(gap, matrix.scale.plan_gap_steps)
                )
            )
        rows.append(MatrixRow(employee, cells))
    stats = item_stats(matrix, items, all_members, latest) if scope.is_global else None
    summary = summarise(gaps)
    if stats is not None:
        summary["risk_high"] = sum(1 for s in stats if s.risk is StaffingRisk.HIGH)
        summary["risk_medium"] = sum(1 for s in stats if s.risk is StaffingRisk.MEDIUM)
        summary["risk_low"] = sum(1 for s in stats if s.risk is StaffingRisk.LOW)
    summary["needs_plan"] = sum(1 for r in rows for c in r.cells if c.needs_plan)
    return rows, summary, stats


def employee_matrices(db: Session, employee_id: int) -> list[SkillMatrix]:
    return list(
        db.scalars(
            select(SkillMatrix)
            .join(SkillMatrixMember, SkillMatrixMember.matrix_id == SkillMatrix.id)
            .where(SkillMatrixMember.employee_id == employee_id, SkillMatrix.is_active.is_(True))
            .order_by(SkillMatrix.name)
        ).unique()
    )
