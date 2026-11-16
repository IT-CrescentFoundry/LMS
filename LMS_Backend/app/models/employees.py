"""Employee master models (Stage C3).

* ``Employee`` — the person employed by Crescent Foundry, independent of any login
  account (ADR-040). Minimal data only: no compensation, bank, identity-number, date
  of birth, gender, address, health, family or personal contact fields. A NULL
  ``employment_status`` means "not recorded" and is never treated as active.
* ``EmployeeAssignment`` — effective-dated placement in an organisation unit with
  optional designation, grade, level and location (C1 reference data). A business
  change closes one row and opens another; history is never overwritten.
* ``EmployeeFunctionalRole`` — explicit (manual) functional roles and exclusions.
  Roles derived from the designation mapping are computed on read, never stored.
* ``EmployeeResponsibility`` — duties with optional unit/location context.
* ``ReportingRelationshipType`` / ``ReportingRelationship`` — typed, effective-dated
  employee-to-employee relationships (seeded type: LINE_MANAGER).

None of these records grant LMS permissions: being a manager, holding a functional
role or a responsibility changes nothing in access control (ADR-023).
"""

from datetime import date, datetime
from enum import StrEnum

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    ForeignKey,
    Index,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base
from app.db.types import BigIntKey, UTCDateTime, utcnow
from app.models.common import (
    LOCALE_CHECK,
    OPEN_FLAG,
    PERIOD_CHECK,
    PublicIdMixin,
    TrackedMixin,
)
from app.models.occupation import Designation, FunctionalRole, Grade, JobLevel, Responsibility
from app.models.organisation import Location, OrgUnit


class EmploymentStatus(StrEnum):
    ACTIVE = "active"
    ON_LEAVE = "on_leave"
    SEPARATED = "separated"


class AssignmentType(StrEnum):
    PRIMARY = "primary"
    ADDITIONAL = "additional"
    ACTING = "acting"
    DEPUTATION = "deputation"


class AssignmentSource(StrEnum):
    MANUAL = "manual"
    IMPORT = "import"


class FunctionalRoleKind(StrEnum):
    MANUAL = "manual"
    EXCLUSION = "exclusion"


LINE_MANAGER = "LINE_MANAGER"
REPORTING_LOCK = "reporting"


def _in(column: str, values: type[StrEnum]) -> str:
    return f"{column} IN ({', '.join(repr(item.value) for item in values)})"


class _EndedMixin:
    """Who ended an effective-dated row and when (business end is ``effective_to``)."""

    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    ended_by_user_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("user_account.id"))


class Employee(PublicIdMixin, TrackedMixin, Base):
    __tablename__ = "employee"
    __table_args__ = (
        CheckConstraint(
            f"employment_status IS NULL OR {_in('employment_status', EmploymentStatus)}",
            name="status_valid",
        ),
        CheckConstraint(
            "preferred_language IS NULL OR preferred_language IN ('en', 'bn', 'hi', 'gu')",
            name="language_valid",
        ),
        CheckConstraint(
            "date_of_separation IS NULL OR date_of_joining IS NULL "
            "OR date_of_separation >= date_of_joining",
            name="separation_after_joining",
        ),
        CheckConstraint(
            "employment_status IS NULL OR employment_status <> 'separated' "
            "OR date_of_separation IS NOT NULL",
            name="separated_has_date",
        ),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    employee_code: Mapped[str] = mapped_column(String(30), unique=True)
    full_name: Mapped[str] = mapped_column(String(200))
    display_name: Mapped[str | None] = mapped_column(String(200))
    preferred_language: Mapped[str | None] = mapped_column(CHAR(2))
    work_email: Mapped[str | None] = mapped_column(String(254))
    employment_status: Mapped[str | None] = mapped_column(String(20), index=True)
    date_of_joining: Mapped[date | None] = mapped_column(Date)
    date_of_separation: Mapped[date | None] = mapped_column(Date)
    external_ref: Mapped[str | None] = mapped_column(String(100), index=True)


class EmployeeAssignment(PublicIdMixin, TrackedMixin, _EndedMixin, Base):
    __tablename__ = "employee_assignment"
    __table_args__ = (
        CheckConstraint(_in("assignment_type", AssignmentType), name="type_valid"),
        CheckConstraint(_in("source", AssignmentSource), name="source_valid"),
        CheckConstraint(PERIOD_CHECK, name="valid_period"),
        UniqueConstraint("employee_id", "primary_open"),
        UniqueConstraint("employee_id", "org_unit_id", "open_flag"),
        Index("ix_employee_assignment_org_unit_id_effective_to", "org_unit_id", "effective_to"),
        Index("ix_employee_assignment_employee_id_effective_from", "employee_id", "effective_from"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("employee.id"))
    org_unit_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("org_unit.id"))
    designation_id: Mapped[int | None] = mapped_column(
        BigIntKey, ForeignKey("designation.id"), index=True
    )
    grade_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("grade.id"))
    job_level_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("job_level.id"))
    location_id: Mapped[int | None] = mapped_column(
        BigIntKey, ForeignKey("location.id"), index=True
    )
    assignment_type: Mapped[str] = mapped_column(String(20))
    is_primary: Mapped[bool] = mapped_column(
        Boolean, Computed("assignment_type = 'primary'", persisted=True)
    )
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    source: Mapped[str] = mapped_column(String(20), default=AssignmentSource.MANUAL.value)
    reason: Mapped[str | None] = mapped_column(String(500))
    primary_open: Mapped[int | None] = mapped_column(
        SmallInteger,
        Computed(
            "IF(assignment_type = 'primary' AND effective_to IS NULL, 1, NULL)", persisted=True
        ),
    )
    open_flag: Mapped[int | None] = mapped_column(SmallInteger, Computed(OPEN_FLAG, persisted=True))

    org_unit: Mapped[OrgUnit] = relationship(lazy="joined")
    designation: Mapped[Designation | None] = relationship(lazy="joined")
    grade: Mapped[Grade | None] = relationship(lazy="joined")
    job_level: Mapped[JobLevel | None] = relationship(lazy="joined")
    location: Mapped[Location | None] = relationship(lazy="joined")


class EmployeeFunctionalRole(PublicIdMixin, _EndedMixin, Base):
    """A manually assigned functional role, or an exclusion of a derived one."""

    __tablename__ = "employee_functional_role"
    __table_args__ = (
        CheckConstraint(_in("kind", FunctionalRoleKind), name="kind_valid"),
        CheckConstraint(PERIOD_CHECK, name="valid_period"),
        UniqueConstraint(
            "employee_id",
            "functional_role_id",
            "open_flag",
            name="uq_employee_functional_role_open",
        ),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("employee.id"))
    functional_role_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("functional_role.id"))
    kind: Mapped[str] = mapped_column(String(20))
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    reason: Mapped[str | None] = mapped_column(String(500))
    open_flag: Mapped[int | None] = mapped_column(SmallInteger, Computed(OPEN_FLAG, persisted=True))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("user_account.id"))

    functional_role: Mapped[FunctionalRole] = relationship(lazy="joined")


class EmployeeResponsibility(PublicIdMixin, _EndedMixin, Base):
    """A responsibility held by an employee, optionally for a unit and/or location."""

    __tablename__ = "employee_responsibility"
    __table_args__ = (
        CheckConstraint(PERIOD_CHECK, name="valid_period"),
        UniqueConstraint(
            "employee_id",
            "responsibility_id",
            "context_unit_key",
            "context_location_key",
            "open_flag",
            name="uq_employee_responsibility_open",
        ),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("employee.id"))
    responsibility_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("responsibility.id"))
    context_org_unit_id: Mapped[int | None] = mapped_column(
        BigIntKey, ForeignKey("org_unit.id"), index=True
    )
    context_location_id: Mapped[int | None] = mapped_column(
        BigIntKey, ForeignKey("location.id"), index=True
    )
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    reason: Mapped[str | None] = mapped_column(String(500))
    context_unit_key: Mapped[int] = mapped_column(
        BigIntKey, Computed("COALESCE(context_org_unit_id, 0)", persisted=True)
    )
    context_location_key: Mapped[int] = mapped_column(
        BigIntKey, Computed("COALESCE(context_location_id, 0)", persisted=True)
    )
    open_flag: Mapped[int | None] = mapped_column(SmallInteger, Computed(OPEN_FLAG, persisted=True))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("user_account.id"))

    responsibility: Mapped[Responsibility] = relationship(lazy="joined")
    context_org_unit: Mapped[OrgUnit | None] = relationship(lazy="joined")
    context_location: Mapped[Location | None] = relationship(lazy="joined")


class ReportingRelationshipType(PublicIdMixin, TrackedMixin, Base):
    __tablename__ = "reporting_relationship_type"

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    allows_multiple: Mapped[bool] = mapped_column(Boolean, default=False)
    is_hierarchical: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    translations: Mapped[list["ReportingRelationshipTypeTranslation"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class ReportingRelationshipTypeTranslation(Base):
    __tablename__ = "reporting_relationship_type_translation"
    __table_args__ = (
        UniqueConstraint("relationship_type_id", "locale"),
        CheckConstraint(LOCALE_CHECK, name="locale_valid"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    relationship_type_id: Mapped[int] = mapped_column(
        BigIntKey, ForeignKey("reporting_relationship_type.id")
    )
    locale: Mapped[str] = mapped_column(CHAR(2))
    name: Mapped[str] = mapped_column(String(150))


class ReportingRelationship(PublicIdMixin, _EndedMixin, Base):
    __tablename__ = "reporting_relationship"
    __table_args__ = (
        CheckConstraint("employee_id <> manager_employee_id", name="not_self"),
        CheckConstraint(PERIOD_CHECK, name="valid_period"),
        UniqueConstraint(
            "employee_id",
            "relationship_type_id",
            "manager_employee_id",
            "open_flag",
            name="uq_reporting_relationship_open",
        ),
        Index(
            "ix_reporting_relationship_manager_employee_id_effective_to",
            "manager_employee_id",
            "effective_to",
        ),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    employee_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("employee.id"))
    manager_employee_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("employee.id"))
    relationship_type_id: Mapped[int] = mapped_column(
        BigIntKey, ForeignKey("reporting_relationship_type.id")
    )
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    reason: Mapped[str | None] = mapped_column(String(500))
    open_flag: Mapped[int | None] = mapped_column(SmallInteger, Computed(OPEN_FLAG, persisted=True))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("user_account.id"))

    relationship_type: Mapped[ReportingRelationshipType] = relationship(lazy="joined")
    manager: Mapped[Employee] = relationship(foreign_keys=[manager_employee_id], lazy="joined")
    employee: Mapped[Employee] = relationship(foreign_keys=[employee_id], lazy="joined")
