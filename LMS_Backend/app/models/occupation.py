"""Occupational reference models (Stage C1).

These concepts stay separate (ADR-023, Stage C plan section 4):

* ``JobFamily`` — a broad occupational grouping (optional parent).
* ``Grade`` and ``JobLevel`` — two independent, optional classification lists. Their
  relationship to each other is unresolved (Q-45), so neither has built-in meaning.
* ``Designation`` — the official title held by an employee.
* ``FunctionalRole`` — the work an employee performs; competency requirements attach
  here in Stage F. NOT an organisational sub-function and NOT an access role.
* ``DesignationFunctionalRole`` — effective-dated many-to-many mapping, optionally
  scoped to an org-unit subtree (the same designation can imply different roles in
  different departments).
* ``Responsibility`` — a discrete duty (e.g. fire warden). Never grants permissions
  or practical authorisation.

None of these tables grant LMS permissions, and none hold competency or proficiency
data (Technical Competency Library and proficiency scales are Stage F).
"""

from datetime import date, datetime

from sqlalchemy import (
    CHAR,
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    ForeignKey,
    Integer,
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
from app.models.organisation import OrgUnit


class JobFamily(PublicIdMixin, TrackedMixin, Base):
    __tablename__ = "job_family"

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(500))
    parent_job_family_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("job_family.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Grade(PublicIdMixin, TrackedMixin, Base):
    __tablename__ = "grade"

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    rank: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class JobLevel(PublicIdMixin, TrackedMixin, Base):
    __tablename__ = "job_level"

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(100))
    rank: Mapped[int | None] = mapped_column(Integer)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class Designation(PublicIdMixin, TrackedMixin, Base):
    __tablename__ = "designation"

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    title: Mapped[str] = mapped_column(String(200))
    job_family_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("job_family.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    job_family: Mapped[JobFamily | None] = relationship(lazy="joined")
    translations: Mapped[list["DesignationTranslation"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class DesignationTranslation(Base):
    __tablename__ = "designation_translation"
    __table_args__ = (
        UniqueConstraint("designation_id", "locale"),
        CheckConstraint(LOCALE_CHECK, name="locale_valid"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    designation_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("designation.id"))
    locale: Mapped[str] = mapped_column(CHAR(2))
    name: Mapped[str] = mapped_column(String(200))


class FunctionalRole(PublicIdMixin, TrackedMixin, Base):
    __tablename__ = "functional_role"

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(1000))
    job_family_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("job_family.id"))
    owner_org_unit_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("org_unit.id"))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    job_family: Mapped[JobFamily | None] = relationship(lazy="joined")
    owner_org_unit: Mapped[OrgUnit | None] = relationship(lazy="joined")
    translations: Mapped[list["FunctionalRoleTranslation"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class FunctionalRoleTranslation(Base):
    __tablename__ = "functional_role_translation"
    __table_args__ = (
        UniqueConstraint("functional_role_id", "locale"),
        CheckConstraint(LOCALE_CHECK, name="locale_valid"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    functional_role_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("functional_role.id"))
    locale: Mapped[str] = mapped_column(CHAR(2))
    name: Mapped[str] = mapped_column(String(200))


class DesignationFunctionalRole(PublicIdMixin, Base):
    """Designation -> functional role mapping (effective-dated, optionally unit-scoped)."""

    __tablename__ = "designation_functional_role"
    __table_args__ = (
        UniqueConstraint(
            "designation_id",
            "functional_role_id",
            "scope_key",
            "open_flag",
            name="uq_designation_functional_role_open",
        ),
        CheckConstraint(PERIOD_CHECK, name="valid_period"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    designation_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("designation.id"))
    functional_role_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("functional_role.id"))
    scope_org_unit_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("org_unit.id"))
    scope_include_descendants: Mapped[bool] = mapped_column(Boolean, default=True)
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    scope_key: Mapped[int] = mapped_column(
        BigIntKey, Computed("COALESCE(scope_org_unit_id, 0)", persisted=True)
    )
    open_flag: Mapped[int | None] = mapped_column(SmallInteger, Computed(OPEN_FLAG, persisted=True))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("user_account.id"))
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    ended_by_user_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("user_account.id"))

    designation: Mapped[Designation] = relationship(lazy="joined")
    functional_role: Mapped[FunctionalRole] = relationship(lazy="joined")
    scope_org_unit: Mapped[OrgUnit | None] = relationship(lazy="joined")


class Responsibility(PublicIdMixin, TrackedMixin, Base):
    __tablename__ = "responsibility"

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(String(1000))
    category: Mapped[str | None] = mapped_column(String(50))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    translations: Mapped[list["ResponsibilityTranslation"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class ResponsibilityTranslation(Base):
    __tablename__ = "responsibility_translation"
    __table_args__ = (
        UniqueConstraint("responsibility_id", "locale"),
        CheckConstraint(LOCALE_CHECK, name="locale_valid"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    responsibility_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("responsibility.id"))
    locale: Mapped[str] = mapped_column(CHAR(2))
    name: Mapped[str] = mapped_column(String(200))
