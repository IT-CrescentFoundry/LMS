"""Competency library and skill matrices (first release).

* ``ProficiencyScale`` / ``ProficiencyLevel`` — administrator-configured scales. The
  sources disagree (company workbooks vs. the current third-party LMS), so no scale is
  hard-coded: each competency names its scale and levels are ordered by ``rank``.
  ``numeric_value`` is optional; ``gap_method`` says whether arithmetic differences
  are meaningful (``numeric``) or only the order is (``ordinal``).
* ``Competency`` — one library entry (code, name, category, description, criteria).
  ``CompetencyLevelDescriptor`` holds what a level means for that competency.
* ``SkillMatrix`` — a reusable template for a scope (any combination of org unit,
  location, designation, functional role; none is mandatory). ``SkillMatrixItem``
  lists the competencies and the **required** level (NULL = requirement pending).
  ``SkillMatrixMember`` lists the employees the matrix is applied to.
* ``CompetencyAssessment`` — the **assessed** level of one employee for one competency
  on a date. Append-only: a re-assessment is a new row; the current level is the
  latest by ``assessed_on`` (then id). Required and assessed levels are never mixed.
"""

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import BigIntKey, UTCDateTime, utcnow
from app.models.common import PublicIdMixin, TrackedMixin


class GapMethod(StrEnum):
    ORDINAL = "ordinal"
    NUMERIC = "numeric"


class CompetencyStatus(StrEnum):
    """Governance state of a library entry. New entries start as ``draft``; only an
    explicit, audited approval makes them ``approved`` (never silently published)."""

    DRAFT = "draft"
    APPROVED = "approved"


class AssessmentMethod(StrEnum):
    ASSESSOR = "assessor_rating"
    MANAGER = "manager_rating"
    PRACTICAL = "practical_evaluation"
    IMPORTED = "imported_matrix"


class ProficiencyScale(PublicIdMixin, TrackedMixin, Base):
    __tablename__ = "proficiency_scale"
    __table_args__ = (CheckConstraint("gap_method IN ('ordinal', 'numeric')", name="gap_method"),)

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(String(1000))
    gap_method: Mapped[str] = mapped_column(String(10), default=GapMethod.ORDINAL.value)
    source_note: Mapped[str | None] = mapped_column(String(500))
    # Rank at or above which an employee counts as "skilled" for headcount and risk
    # (company skill matrices: score >= 3). NULL = not configured.
    competent_rank: Mapped[int | None] = mapped_column(SmallInteger)
    # Gap (in ranks) at or above which an individual development plan is required
    # (competency library Read Me: gap >= 2). NULL = not configured.
    plan_gap_steps: Mapped[int | None] = mapped_column(SmallInteger)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    levels: Mapped[list["ProficiencyLevel"]] = relationship(
        lazy="selectin", order_by="ProficiencyLevel.rank", cascade="all, delete-orphan"
    )


class ProficiencyLevel(PublicIdMixin, Base):
    __tablename__ = "proficiency_level"
    __table_args__ = (
        UniqueConstraint("scale_id", "rank"),
        UniqueConstraint("scale_id", "code"),
        CheckConstraint("`rank` >= 0", name="rank_non_negative"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    scale_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("proficiency_scale.id"))
    rank: Mapped[int] = mapped_column(SmallInteger)
    code: Mapped[str] = mapped_column(String(30))
    label: Mapped[str] = mapped_column(String(150))
    numeric_value: Mapped[float | None] = mapped_column(Numeric(6, 2, asdecimal=False))
    description: Mapped[str | None] = mapped_column(String(1000))


class Competency(PublicIdMixin, TrackedMixin, Base):
    __tablename__ = "competency"
    __table_args__ = (
        CheckConstraint("status IN ('draft', 'approved')", name="status"),
        CheckConstraint(
            "status <> 'approved' OR approved_at IS NOT NULL", name="approved_has_time"
        ),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(250), index=True)
    category: Mapped[str | None] = mapped_column(String(150), index=True)
    sub_category: Mapped[str | None] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(Text)
    assessment_criteria: Mapped[str | None] = mapped_column(Text)
    applicability: Mapped[str | None] = mapped_column(String(1000))
    scale_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("proficiency_scale.id"))
    owner_org_unit_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("org_unit.id"))
    source_ref: Mapped[str | None] = mapped_column(String(200))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    # Draft / approved (see CompetencyStatus). The source library marks some entries as
    # drafts; they are imported as drafts and stay so until an authorised approval.
    status: Mapped[str] = mapped_column(
        String(20), default=CompetencyStatus.DRAFT.value, index=True
    )
    approved_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    approved_by_user_id: Mapped[int | None] = mapped_column(
        BigIntKey, ForeignKey("user_account.id")
    )

    scale: Mapped[ProficiencyScale | None] = relationship(lazy="joined")
    descriptors: Mapped[list["CompetencyLevelDescriptor"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan"
    )
    band_requirements: Mapped[list["CompetencyBandRequirement"]] = relationship(
        lazy="selectin", cascade="all, delete-orphan"
    )


class CompetencyLevelDescriptor(Base):
    __tablename__ = "competency_level_descriptor"
    __table_args__ = (UniqueConstraint("competency_id", "level_id"),)

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    competency_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("competency.id"))
    level_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("proficiency_level.id"))
    description: Mapped[str] = mapped_column(String(2000))


class CompetencyBandRequirement(Base):
    """Required level of a library competency for a grade band (library columns J-M).

    ``band_code`` is the band as written in the library (e.g. ``L6-L5``); how bands map
    to designations/grades is an open business question, so it is stored verbatim.
    """

    __tablename__ = "competency_band_requirement"
    __table_args__ = (UniqueConstraint("competency_id", "band_code"),)

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    competency_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("competency.id"))
    band_code: Mapped[str] = mapped_column(String(30))
    band_label: Mapped[str | None] = mapped_column(String(150))
    required_level_id: Mapped[int | None] = mapped_column(
        BigIntKey, ForeignKey("proficiency_level.id")
    )

    required_level: Mapped["ProficiencyLevel | None"] = relationship(lazy="joined")


class SkillMatrix(PublicIdMixin, TrackedMixin, Base):
    __tablename__ = "skill_matrix"

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(250))
    description: Mapped[str | None] = mapped_column(String(1000))
    org_unit_id: Mapped[int | None] = mapped_column(
        BigIntKey, ForeignKey("org_unit.id"), index=True
    )
    location_id: Mapped[int | None] = mapped_column(
        BigIntKey, ForeignKey("location.id"), index=True
    )
    designation_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("designation.id"))
    functional_role_id: Mapped[int | None] = mapped_column(
        BigIntKey, ForeignKey("functional_role.id")
    )
    scale_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("proficiency_scale.id"))
    # Staffing risk per item (company matrices): High when skilled headcount <= required,
    # Medium when <= required + margin, else Low. Source formula uses margin 1.
    risk_medium_margin: Mapped[int] = mapped_column(SmallInteger, default=1)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    scale: Mapped[ProficiencyScale] = relationship(lazy="joined")
    items: Mapped[list["SkillMatrixItem"]] = relationship(
        lazy="selectin", order_by="SkillMatrixItem.display_order", viewonly=True
    )


class SkillMatrixItem(Base):
    __tablename__ = "skill_matrix_item"
    __table_args__ = (UniqueConstraint("matrix_id", "competency_id"),)

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    matrix_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("skill_matrix.id"))
    competency_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("competency.id"))
    required_level_id: Mapped[int | None] = mapped_column(
        BigIntKey, ForeignKey("proficiency_level.id")
    )
    # "Required Skilled Manpower": people needed at or above the scale's competent rank.
    required_headcount: Mapped[int | None] = mapped_column(Integer)
    group_label: Mapped[str | None] = mapped_column(String(150))
    display_order: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)

    competency: Mapped[Competency] = relationship(lazy="joined")
    required_level: Mapped[ProficiencyLevel | None] = relationship(lazy="joined")


class SkillMatrixMember(Base):
    __tablename__ = "skill_matrix_member"
    __table_args__ = (UniqueConstraint("matrix_id", "employee_id"),)

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    matrix_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("skill_matrix.id"))
    employee_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("employee.id"), index=True)
    added_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    added_by_user_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("user_account.id"))


class CompetencyAssessment(PublicIdMixin, Base):
    __tablename__ = "competency_assessment"
    __table_args__ = (
        CheckConstraint(
            "method IN ('assessor_rating', 'manager_rating', 'practical_evaluation', "
            "'imported_matrix')",
            name="method",
        ),
        Index("ix_competency_assessment_current", "employee_id", "competency_id", "assessed_on"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("employee.id"))
    competency_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("competency.id"), index=True)
    level_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("proficiency_level.id"))
    assessed_on: Mapped[date] = mapped_column(Date)
    method: Mapped[str] = mapped_column(String(30))
    assessor_employee_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("employee.id"))
    assessor_name: Mapped[str | None] = mapped_column(String(200))
    evidence: Mapped[str | None] = mapped_column(String(2000))
    matrix_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("skill_matrix.id"))
    recorded_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    recorded_by_user_id: Mapped[int | None] = mapped_column(
        BigIntKey, ForeignKey("user_account.id")
    )

    level: Mapped[ProficiencyLevel] = relationship(lazy="joined")
