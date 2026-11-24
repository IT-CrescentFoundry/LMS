"""Competency library, proficiency scales, skill matrices and assessments (0011).

* Library, scales and matrix definitions: read with any of ``competency.view``,
  ``competency.manage``, ``team.learning.view``, ``learning.own.view``; change with
  ``competency.manage``.
* Matrix grids and assessment history are narrowed to the caller's scope (all
  employees / own team / self). Recording an assessment needs ``competency.assess``.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    DbSessionDep,
    RequestMetaDep,
    SettingsDep,
    require_any_permission,
    require_permission,
    require_schema,
)
from app.api.routes.training import employee_ref
from app.core.config import Settings
from app.core.errors import AppError
from app.models.competency import (
    Competency,
    CompetencyAssessment,
    ProficiencyLevel,
    ProficiencyScale,
    SkillMatrix,
    SkillMatrixMember,
)
from app.models.employees import Employee
from app.models.occupation import Designation, FunctionalRole
from app.models.organisation import Location, OrgUnit
from app.schemas.competency import (
    AssessmentCreate,
    AssessmentOut,
    BandRequirementOut,
    BandRequirementsUpdate,
    CompetencyCreate,
    CompetencyOut,
    CompetencyStatusChange,
    CompetencyUpdate,
    EmployeeSkillsOut,
    GapOut,
    ItemStatsOut,
    LevelOut,
    MatrixCellOut,
    MatrixCreate,
    MatrixGridOut,
    MatrixItemOut,
    MatrixItemsUpdate,
    MatrixMembersUpdate,
    MatrixOut,
    MatrixRowOut,
    MatrixUpdate,
    ScaleCreate,
    ScaleOut,
    ScaleUpdate,
)
from app.schemas.errors import ErrorResponse
from app.schemas.organisation import RefOut
from app.schemas.training import OffsetPage
from app.services.competency import library
from app.services.identity.context import AuthContext
from app.services.identity.permissions import Permission
from app.services.organisation.support import business_today, get_or_404
from app.services.training.records import unit_ids_for
from app.services.training.scope import RecordScope, record_scope

router = APIRouter(
    prefix="/competency",
    tags=["competency: library and skill matrix"],
    dependencies=[Depends(require_schema("0011"))],
    responses={
        401: {"model": ErrorResponse},
        403: {"model": ErrorResponse},
        404: {"model": ErrorResponse},
        409: {"model": ErrorResponse},
        422: {"model": ErrorResponse},
        503: {"model": ErrorResponse},
    },
)

ViewCompetency = Annotated[
    AuthContext,
    Depends(
        require_any_permission(
            Permission.COMPETENCY_VIEW,
            Permission.COMPETENCY_MANAGE,
            Permission.TEAM_LEARNING_VIEW,
            Permission.LEARNING_OWN_VIEW,
        )
    ),
]
ManageCompetency = Annotated[AuthContext, Depends(require_permission(Permission.COMPETENCY_MANAGE))]
AssessCompetency = Annotated[AuthContext, Depends(require_permission(Permission.COMPETENCY_ASSESS))]


def _scope(db: Session, auth: AuthContext, settings: Settings) -> RecordScope:
    if auth.has(Permission.COMPETENCY_MANAGE) or auth.has(Permission.COMPETENCY_ASSESS):
        return RecordScope(None, "global", auth.user.employee_id)
    return record_scope(
        db, auth, business_today(settings), global_permission=Permission.COMPETENCY_VIEW
    )


# ---------------------------------------------------------------------- presenters


def level_out(level: ProficiencyLevel | None) -> LevelOut | None:
    return None if level is None else LevelOut.model_validate(level, from_attributes=True)


def scale_out(scale: ProficiencyScale) -> ScaleOut:
    return ScaleOut(
        public_id=scale.public_id,
        code=scale.code,
        name=scale.name,
        description=scale.description,
        gap_method=scale.gap_method,
        source_note=scale.source_note,
        competent_rank=scale.competent_rank,
        plan_gap_steps=scale.plan_gap_steps,
        is_active=scale.is_active,
        levels=[LevelOut.model_validate(lvl, from_attributes=True) for lvl in scale.levels],
        version=scale.version,
    )


def _ref(entity: object | None, name_attr: str = "name") -> RefOut | None:
    if entity is None:
        return None
    return RefOut(
        public_id=entity.public_id,  # type: ignore[attr-defined]
        code=entity.code,  # type: ignore[attr-defined]
        name=getattr(entity, name_attr),
    )


def competency_out(db: Session, competency: Competency) -> CompetencyOut:
    unit = db.get(OrgUnit, competency.owner_org_unit_id) if competency.owner_org_unit_id else None
    return CompetencyOut(
        public_id=competency.public_id,
        code=competency.code,
        name=competency.name,
        category=competency.category,
        sub_category=competency.sub_category,
        description=competency.description,
        assessment_criteria=competency.assessment_criteria,
        applicability=competency.applicability,
        scale=_ref(competency.scale),
        owner_org_unit=_ref(unit),
        source_ref=competency.source_ref,
        is_active=competency.is_active,
        status=competency.status,  # type: ignore[arg-type]
        approved_at=competency.approved_at,
        band_requirements=[
            BandRequirementOut(
                band_code=b.band_code,
                band_label=b.band_label,
                required_level=level_out(b.required_level),
            )
            for b in competency.band_requirements
        ],
        version=competency.version,
    )


def matrix_out(db: Session, matrix: SkillMatrix) -> MatrixOut:
    members = db.scalar(
        select(func.count())
        .select_from(SkillMatrixMember)
        .where(SkillMatrixMember.matrix_id == matrix.id)
    )
    return MatrixOut(
        public_id=matrix.public_id,
        code=matrix.code,
        name=matrix.name,
        description=matrix.description,
        org_unit=_ref(db.get(OrgUnit, matrix.org_unit_id) if matrix.org_unit_id else None),
        location=_ref(db.get(Location, matrix.location_id) if matrix.location_id else None),
        designation=_ref(
            db.get(Designation, matrix.designation_id) if matrix.designation_id else None
        ),
        functional_role=_ref(
            db.get(FunctionalRole, matrix.functional_role_id) if matrix.functional_role_id else None
        ),
        scale=scale_out(matrix.scale),
        risk_medium_margin=matrix.risk_medium_margin,
        is_active=matrix.is_active,
        member_count=int(members or 0),
        items=[
            MatrixItemOut(
                competency=RefOut(
                    public_id=item.competency.public_id,
                    code=item.competency.code,
                    name=item.competency.name,
                ),
                category=item.competency.category,
                group_label=item.group_label,
                display_order=item.display_order,
                required_level=level_out(item.required_level),
                required_headcount=item.required_headcount,
            )
            for item in matrix.items
        ],
        version=matrix.version,
    )


def grid_out(db: Session, matrix: SkillMatrix, scope: RecordScope) -> MatrixGridOut:
    rows, summary, stats = library.matrix_grid(db, matrix, scope)
    return MatrixGridOut(
        matrix=matrix_out(db, matrix),
        scope=scope.kind,  # type: ignore[arg-type]
        rows=[
            MatrixRowOut(
                employee=employee_ref(row.employee),
                gaps=sum(1 for c in row.cells if c.gap.is_gap),
                cells=[
                    MatrixCellOut(
                        competency_id=cell.item.competency.public_id,
                        required_level=level_out(cell.item.required_level),
                        assessed_level=level_out(cell.assessment.level)
                        if cell.assessment
                        else None,
                        assessed_on=cell.assessment.assessed_on if cell.assessment else None,
                        gap=GapOut(
                            status=cell.gap.status.value,
                            gap_steps=cell.gap.gap_steps,
                            gap_value=cell.gap.gap_value,
                        ),
                        needs_plan=cell.needs_plan,
                    )
                    for cell in row.cells
                ],
            )
            for row in rows
        ],
        summary=summary,
        item_stats=[
            ItemStatsOut(
                competency_id=s.item.competency.public_id,
                counts_by_rank=s.counts_by_rank,
                not_assessed=s.not_assessed,
                skilled=s.skilled,
                required_headcount=s.item.required_headcount,
                risk=s.risk.value if s.risk else None,
            )
            for s in stats
        ]
        if stats is not None
        else None,
    )


def assessment_out(db: Session, row: CompetencyAssessment) -> AssessmentOut:
    competency = db.get(Competency, row.competency_id)
    if competency is None:  # pragma: no cover - FK guarantees it
        raise AppError(404, "competency_not_found", "Competency not found.")
    assessor = db.get(Employee, row.assessor_employee_id) if row.assessor_employee_id else None
    return AssessmentOut(
        public_id=row.public_id,
        competency=RefOut(
            public_id=competency.public_id, code=competency.code, name=competency.name
        ),
        level=LevelOut.model_validate(row.level, from_attributes=True),
        assessed_on=row.assessed_on,
        method=row.method,
        assessor=employee_ref(assessor) if assessor else None,
        assessor_name=row.assessor_name,
        evidence=row.evidence,
        recorded_at=row.recorded_at,
    )


# -------------------------------------------------------------------------- scales


@router.get("/scales", response_model=list[ScaleOut], summary="Proficiency scales")
def list_scales(_auth: ViewCompetency, db: DbSessionDep) -> list[ScaleOut]:
    return [scale_out(s) for s in library.list_scales(db)]


@router.post(
    "/scales", response_model=ScaleOut, status_code=status.HTTP_201_CREATED, summary="Add a scale"
)
def create_scale(
    body: ScaleCreate, auth: ManageCompetency, db: DbSessionDep, meta: RequestMetaDep
) -> ScaleOut:
    scale = library.create_scale(
        db,
        actor=auth.actor,
        meta=meta,
        values=body.model_dump(exclude={"levels"}),
        levels=[lvl.model_dump() for lvl in body.levels],
    )
    db.commit()
    return scale_out(scale)


@router.patch("/scales/{public_id}", response_model=ScaleOut, summary="Update a scale")
def update_scale(
    public_id: uuid.UUID,
    body: ScaleUpdate,
    auth: ManageCompetency,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> ScaleOut:
    scale = library.update_scale(
        db,
        public_id,
        actor=auth.actor,
        meta=meta,
        version=body.version,
        changes=body.scale_changes(),
        levels=[lvl.model_dump() for lvl in body.levels] if body.levels is not None else None,
    )
    db.commit()
    db.refresh(scale)
    return scale_out(scale)


# -------------------------------------------------------------------- competencies


@router.get("/competencies", response_model=OffsetPage[CompetencyOut], summary="Competency library")
def list_competencies(
    _auth: ViewCompetency,
    db: DbSessionDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    category: Annotated[str | None, Query(max_length=150)] = None,
    include_inactive: bool = False,
    status_filter: Annotated[
        str | None, Query(alias="status", pattern="^(draft|approved)$")
    ] = None,
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> OffsetPage[CompetencyOut]:
    rows, total = library.list_competencies(
        db,
        q=q,
        category=category,
        include_inactive=include_inactive,
        limit=limit,
        offset=offset,
        status=status_filter,
    )
    return OffsetPage[CompetencyOut](
        items=[competency_out(db, c) for c in rows], total=total, limit=limit, offset=offset
    )


@router.get("/categories", response_model=list[str], summary="Competency categories in use")
def categories(_auth: ViewCompetency, db: DbSessionDep) -> list[str]:
    return library.competency_categories(db)


@router.post(
    "/competencies",
    response_model=CompetencyOut,
    status_code=status.HTTP_201_CREATED,
    summary="Add a competency",
)
def create_competency(
    body: CompetencyCreate, auth: ManageCompetency, db: DbSessionDep, meta: RequestMetaDep
) -> CompetencyOut:
    competency = library.create_competency(
        db, actor=auth.actor, meta=meta, values=body.model_dump()
    )
    db.commit()
    return competency_out(db, competency)


@router.get("/competencies/{public_id}", response_model=CompetencyOut, summary="A competency")
def get_competency(public_id: uuid.UUID, _auth: ViewCompetency, db: DbSessionDep) -> CompetencyOut:
    return competency_out(db, library.get_competency(db, public_id))


@router.patch("/competencies/{public_id}", response_model=CompetencyOut, summary="Update")
def update_competency(
    public_id: uuid.UUID,
    body: CompetencyUpdate,
    auth: ManageCompetency,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> CompetencyOut:
    competency = library.update_competency(
        db, public_id, actor=auth.actor, meta=meta, version=body.version, changes=body.changes()
    )
    db.commit()
    db.refresh(competency)
    return competency_out(db, competency)


@router.post(
    "/competencies/{public_id}/status",
    response_model=CompetencyOut,
    summary="Approve a draft competency, or return it to draft (reason required)",
)
def change_competency_status(
    public_id: uuid.UUID,
    body: CompetencyStatusChange,
    auth: ManageCompetency,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> CompetencyOut:
    competency = library.change_competency_status(
        db,
        public_id,
        actor=auth.actor,
        meta=meta,
        version=body.version,
        target=body.status,
        reason=body.reason,
    )
    db.commit()
    db.refresh(competency)
    return competency_out(db, competency)


@router.put(
    "/competencies/{public_id}/band-requirements",
    response_model=CompetencyOut,
    summary="Replace the grade-band required levels of a competency",
)
def set_band_requirements(
    public_id: uuid.UUID,
    body: BandRequirementsUpdate,
    auth: ManageCompetency,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> CompetencyOut:
    competency = library.set_band_requirements(
        db,
        public_id,
        actor=auth.actor,
        meta=meta,
        version=body.version,
        items=[item.model_dump() for item in body.items],
    )
    db.commit()
    db.refresh(competency)
    return competency_out(db, competency)


# ------------------------------------------------------------------------ matrices


@router.get("/matrices", response_model=list[MatrixOut], summary="Skill matrix templates")
def list_matrices(
    _auth: ViewCompetency,
    db: DbSessionDep,
    settings: SettingsDep,
    q: Annotated[str | None, Query(max_length=100)] = None,
    unit: uuid.UUID | None = None,
    include_sub_units: bool = True,
    location: uuid.UUID | None = None,
    include_inactive: bool = False,
) -> list[MatrixOut]:
    unit_ids = (
        unit_ids_for(
            db,
            get_or_404(db, OrgUnit, unit, "org_unit_not_found", "Unit not found.").id,
            business_today(settings),
            include_sub_units,
        )
        if unit
        else None
    )
    location_id = (
        get_or_404(db, Location, location, "location_not_found", "Not found.").id
        if location
        else None
    )
    return [
        matrix_out(db, m)
        for m in library.list_matrices(
            db, q=q, unit_ids=unit_ids, location_id=location_id, include_inactive=include_inactive
        )
    ]


@router.post(
    "/matrices",
    response_model=MatrixOut,
    status_code=status.HTTP_201_CREATED,
    summary="Create a skill matrix template",
)
def create_matrix(
    body: MatrixCreate, auth: ManageCompetency, db: DbSessionDep, meta: RequestMetaDep
) -> MatrixOut:
    matrix = library.create_matrix(db, actor=auth.actor, meta=meta, values=body.model_dump())
    db.commit()
    db.refresh(matrix)
    return matrix_out(db, matrix)


@router.patch("/matrices/{public_id}", response_model=MatrixOut, summary="Update a matrix")
def update_matrix(
    public_id: uuid.UUID,
    body: MatrixUpdate,
    auth: ManageCompetency,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> MatrixOut:
    matrix = library.update_matrix(
        db, public_id, actor=auth.actor, meta=meta, version=body.version, changes=body.changes()
    )
    db.commit()
    db.refresh(matrix)
    return matrix_out(db, matrix)


@router.put(
    "/matrices/{public_id}/items",
    response_model=MatrixOut,
    summary="Replace the competencies and required levels of a matrix",
)
def set_items(
    public_id: uuid.UUID,
    body: MatrixItemsUpdate,
    auth: ManageCompetency,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> MatrixOut:
    matrix = library.set_matrix_items(
        db,
        public_id,
        actor=auth.actor,
        meta=meta,
        version=body.version,
        items=[i.model_dump(exclude_none=True) for i in body.items],
    )
    db.commit()
    db.refresh(matrix)
    return matrix_out(db, matrix)


@router.post(
    "/matrices/{public_id}/members",
    response_model=MatrixOut,
    summary="Apply the matrix to employees (or remove them)",
)
def set_members(
    public_id: uuid.UUID,
    body: MatrixMembersUpdate,
    auth: ManageCompetency,
    db: DbSessionDep,
    meta: RequestMetaDep,
) -> MatrixOut:
    overlap = set(body.add) & set(body.remove)
    if overlap:
        raise AppError(422, "add_and_remove", "An employee cannot be added and removed at once.")
    matrix = library.set_matrix_members(
        db, public_id, actor=auth.actor, meta=meta, add=body.add, remove=body.remove
    )
    db.commit()
    db.refresh(matrix)
    return matrix_out(db, matrix)


@router.get(
    "/matrices/{public_id}/grid",
    response_model=MatrixGridOut,
    summary="Required vs assessed levels for the matrix's employees (your scope)",
)
def matrix_grid(
    public_id: uuid.UUID, auth: ViewCompetency, db: DbSessionDep, settings: SettingsDep
) -> MatrixGridOut:
    matrix = library.get_matrix(db, public_id)
    return grid_out(db, matrix, _scope(db, auth, settings))


# --------------------------------------------------------------------- assessments


@router.post(
    "/assessments",
    response_model=AssessmentOut,
    status_code=status.HTTP_201_CREATED,
    summary="Record an assessed proficiency level",
)
def record_assessment(
    body: AssessmentCreate,
    auth: AssessCompetency,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> AssessmentOut:
    row = library.record_assessment(
        db,
        actor=auth.actor,
        meta=meta,
        today=business_today(settings),
        employee_public_id=body.employee,
        competency_public_id=body.competency,
        level_public_id=body.level,
        assessed_on=body.assessed_on,
        method=body.method,
        assessor_employee_public_id=body.assessor_employee,
        assessor_name=body.assessor_name,
        evidence=body.evidence,
        matrix_public_id=body.matrix,
    )
    db.commit()
    return assessment_out(db, row)


def _employee_in_scope(
    db: Session, auth: AuthContext, settings: Settings, public_id: uuid.UUID | None
) -> tuple[Employee, RecordScope]:
    scope = _scope(db, auth, settings)
    if public_id is None:
        if auth.user.employee_id is None:
            raise AppError(404, "employee_not_linked", "Your account is not linked to an employee.")
        employee = db.get(Employee, auth.user.employee_id)
    else:
        employee = get_or_404(db, Employee, public_id, "employee_not_found", "Employee not found.")
    if employee is None or not scope.allows(employee.id):
        raise AppError(404, "employee_not_found", "Employee not found.")
    return employee, scope


@router.get(
    "/employees/{public_id}/assessments",
    response_model=list[AssessmentOut],
    summary="Assessment history of an employee (your scope)",
)
def employee_assessments(
    public_id: uuid.UUID,
    auth: ViewCompetency,
    db: DbSessionDep,
    settings: SettingsDep,
    competency: uuid.UUID | None = None,
) -> list[AssessmentOut]:
    employee, _ = _employee_in_scope(db, auth, settings, public_id)
    competency_id = library.get_competency(db, competency).id if competency else None
    return [
        assessment_out(db, r) for r in library.assessment_history(db, employee.id, competency_id)
    ]


@router.get(
    "/my-skills",
    response_model=EmployeeSkillsOut,
    summary="The signed-in employee's skill matrices and gaps",
)
def my_skills(auth: ViewCompetency, db: DbSessionDep, settings: SettingsDep) -> EmployeeSkillsOut:
    employee, _ = _employee_in_scope(db, auth, settings, None)
    own = RecordScope(frozenset({employee.id}), "own", employee.id)
    return EmployeeSkillsOut(
        employee=employee_ref(employee),
        matrices=[grid_out(db, m, own) for m in library.employee_matrices(db, employee.id)],
    )


@router.get(
    "/employees/{public_id}/skills",
    response_model=EmployeeSkillsOut,
    summary="An employee's skill matrices and gaps (your scope)",
)
def employee_skills(
    public_id: uuid.UUID, auth: ViewCompetency, db: DbSessionDep, settings: SettingsDep
) -> EmployeeSkillsOut:
    employee, _ = _employee_in_scope(db, auth, settings, public_id)
    own = RecordScope(frozenset({employee.id}), "own", employee.id)
    return EmployeeSkillsOut(
        employee=employee_ref(employee),
        matrices=[grid_out(db, m, own) for m in library.employee_matrices(db, employee.id)],
    )
