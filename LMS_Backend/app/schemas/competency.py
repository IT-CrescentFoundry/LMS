"""Competency library, proficiency scale and skill matrix schemas (first release)."""

import uuid
from datetime import date, datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field

from app.schemas.organisation import Code, PatchModel, RefOut, Version
from app.schemas.training import EmployeeRef

GapMethod = Literal["ordinal", "numeric"]
Method = Literal["assessor_rating", "manager_rating", "practical_evaluation", "imported_matrix"]
GapStatusName = Literal[
    "requirement_pending", "not_assessed", "scale_mismatch", "below", "met", "exceeds"
]


class LevelIn(BaseModel):
    public_id: uuid.UUID | None = None
    rank: Annotated[int, Field(ge=0, le=100)]
    code: Annotated[str, Field(min_length=1, max_length=30)]
    label: Annotated[str, Field(min_length=1, max_length=150)]
    numeric_value: Annotated[float, Field(ge=-9999, le=9999)] | None = None
    description: Annotated[str, Field(max_length=1000)] | None = None


class LevelOut(BaseModel):
    public_id: uuid.UUID
    rank: int
    code: str
    label: str
    numeric_value: float | None
    description: str | None


class ScaleCreate(BaseModel):
    code: Code
    name: Annotated[str, Field(min_length=1, max_length=150)]
    description: Annotated[str, Field(max_length=1000)] | None = None
    gap_method: GapMethod = "ordinal"
    source_note: Annotated[str, Field(max_length=500)] | None = None
    competent_rank: Annotated[int, Field(ge=0, le=100)] | None = None
    plan_gap_steps: Annotated[int, Field(ge=1, le=100)] | None = None
    levels: Annotated[list[LevelIn], Field(min_length=1, max_length=20)]


class ScaleUpdate(PatchModel):
    required_if_sent = ("code", "name", "gap_method", "is_active")
    version: Version
    code: Code | None = None
    name: Annotated[str, Field(min_length=1, max_length=150)] | None = None
    description: Annotated[str, Field(max_length=1000)] | None = None
    gap_method: GapMethod | None = None
    source_note: Annotated[str, Field(max_length=500)] | None = None
    is_active: bool | None = None
    competent_rank: Annotated[int, Field(ge=0, le=100)] | None = None
    plan_gap_steps: Annotated[int, Field(ge=1, le=100)] | None = None
    levels: Annotated[list[LevelIn], Field(min_length=1, max_length=20)] | None = None

    def scale_changes(self) -> dict[str, object]:
        return self.changes("levels")


class ScaleOut(BaseModel):
    public_id: uuid.UUID
    code: str
    name: str
    description: str | None
    gap_method: str
    source_note: str | None
    competent_rank: int | None
    plan_gap_steps: int | None
    is_active: bool
    levels: list[LevelOut]
    version: int


class CompetencyFields(BaseModel):
    category: Annotated[str, Field(max_length=150)] | None = None
    sub_category: Annotated[str, Field(max_length=150)] | None = None
    description: Annotated[str, Field(max_length=10000)] | None = None
    assessment_criteria: Annotated[str, Field(max_length=10000)] | None = None
    applicability: Annotated[str, Field(max_length=1000)] | None = None
    scale: uuid.UUID | None = None
    owner_org_unit: uuid.UUID | None = None
    source_ref: Annotated[str, Field(max_length=200)] | None = None


class CompetencyCreate(CompetencyFields):
    code: Code
    name: Annotated[str, Field(min_length=1, max_length=250)]


class CompetencyUpdate(CompetencyFields, PatchModel):
    required_if_sent = ("code", "name", "is_active")
    version: Version
    code: Code | None = None
    name: Annotated[str, Field(min_length=1, max_length=250)] | None = None
    is_active: bool | None = None


class BandRequirementOut(BaseModel):
    band_code: str
    band_label: str | None
    required_level: LevelOut | None


CompetencyStatusValue = Literal["draft", "approved"]


class CompetencyStatusChange(BaseModel):
    version: Version
    status: CompetencyStatusValue
    reason: Annotated[str, Field(max_length=500)] | None = None


# Band codes as written in the company library, which uses an en dash (U+2013), e.g. L6\u2013L5.
BAND_CODE_PATTERN = "^[A-Za-z0-9 ._/+\u2013-]+$"


class BandRequirementIn(BaseModel):
    band_code: Annotated[str, Field(min_length=1, max_length=30, pattern=BAND_CODE_PATTERN)]
    band_label: Annotated[str, Field(max_length=150)] | None = None
    required_level: uuid.UUID | None = None


class BandRequirementsUpdate(BaseModel):
    version: Version
    items: Annotated[list[BandRequirementIn], Field(max_length=20)]


class CompetencyOut(BaseModel):
    public_id: uuid.UUID
    code: str
    name: str
    category: str | None
    sub_category: str | None
    description: str | None
    assessment_criteria: str | None
    applicability: str | None
    scale: RefOut | None
    owner_org_unit: RefOut | None
    source_ref: str | None
    is_active: bool
    status: CompetencyStatusValue
    approved_at: datetime | None
    band_requirements: list[BandRequirementOut]
    version: int


class MatrixFields(BaseModel):
    description: Annotated[str, Field(max_length=1000)] | None = None
    org_unit: uuid.UUID | None = None
    location: uuid.UUID | None = None
    designation: uuid.UUID | None = None
    functional_role: uuid.UUID | None = None
    risk_medium_margin: Annotated[int, Field(ge=0, le=100)] | None = None


class MatrixCreate(MatrixFields):
    code: Code
    name: Annotated[str, Field(min_length=1, max_length=250)]
    scale: uuid.UUID


class MatrixUpdate(MatrixFields, PatchModel):
    required_if_sent = ("code", "name", "scale", "is_active")
    version: Version
    code: Code | None = None
    name: Annotated[str, Field(min_length=1, max_length=250)] | None = None
    scale: uuid.UUID | None = None
    is_active: bool | None = None


class MatrixItemIn(BaseModel):
    competency: uuid.UUID
    required_level: uuid.UUID | None = None
    required_headcount: Annotated[int, Field(ge=0, le=100000)] | None = None
    group_label: Annotated[str, Field(max_length=150)] | None = None
    display_order: Annotated[int, Field(ge=0, le=100000)] | None = None


class MatrixItemsUpdate(BaseModel):
    version: Version
    items: Annotated[list[MatrixItemIn], Field(max_length=500)]


class MatrixMembersUpdate(BaseModel):
    add: Annotated[list[uuid.UUID], Field(max_length=500)] = []
    remove: Annotated[list[uuid.UUID], Field(max_length=500)] = []


class MatrixItemOut(BaseModel):
    competency: RefOut
    category: str | None
    group_label: str | None
    display_order: int
    required_level: LevelOut | None
    required_headcount: int | None


class MatrixOut(BaseModel):
    public_id: uuid.UUID
    code: str
    name: str
    description: str | None
    org_unit: RefOut | None
    location: RefOut | None
    designation: RefOut | None
    functional_role: RefOut | None
    scale: ScaleOut
    risk_medium_margin: int
    is_active: bool
    member_count: int
    items: list[MatrixItemOut]
    version: int


class AssessmentCreate(BaseModel):
    employee: uuid.UUID
    competency: uuid.UUID
    level: uuid.UUID
    assessed_on: date
    method: Method = "assessor_rating"
    assessor_employee: uuid.UUID | None = None
    assessor_name: Annotated[str, Field(max_length=200)] | None = None
    evidence: Annotated[str, Field(max_length=2000)] | None = None
    matrix: uuid.UUID | None = None


class AssessmentOut(BaseModel):
    public_id: uuid.UUID
    competency: RefOut
    level: LevelOut
    assessed_on: date
    method: str
    assessor: EmployeeRef | None
    assessor_name: str | None
    evidence: str | None
    recorded_at: datetime


class GapOut(BaseModel):
    status: GapStatusName
    gap_steps: int | None
    gap_value: float | None


class MatrixCellOut(BaseModel):
    competency_id: uuid.UUID
    required_level: LevelOut | None
    assessed_level: LevelOut | None
    assessed_on: date | None
    gap: GapOut
    needs_plan: bool


class MatrixRowOut(BaseModel):
    employee: EmployeeRef
    cells: list[MatrixCellOut]
    gaps: int


class ItemStatsOut(BaseModel):
    competency_id: uuid.UUID
    counts_by_rank: dict[int, int]
    not_assessed: int
    skilled: int | None
    required_headcount: int | None
    risk: Literal["high", "medium", "low"] | None


class MatrixGridOut(BaseModel):
    matrix: MatrixOut
    scope: Literal["global", "team", "own", "none"]
    rows: list[MatrixRowOut]
    summary: dict[str, int]
    item_stats: list[ItemStatsOut] | None = Field(
        default=None, description="Headcounts over all members; only for full-access users."
    )


class EmployeeSkillsOut(BaseModel):
    employee: EmployeeRef
    matrices: list[MatrixGridOut]
