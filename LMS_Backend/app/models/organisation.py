"""Organisation structure models (Stage C1).

* ``OrgUnitType`` — administrator-configured unit types (Function, Department, Plant,
  Team, ...). No type, level count or depth is hardcoded.
* ``OrgUnitTypeRule`` — optional allowed (parent type -> child type) pairs; a NULL
  parent type means "may be a root". Enforced as warnings (advisory) or errors
  (strict) per child type.
* ``OrgUnit`` — a unit with a lifetime ``[effective_from, effective_to)``. Names are
  NOT globally unique (two plants may each have a "Maintenance" department); codes are.
* ``OrgUnitHierarchy`` — effective-dated parent links, so past structures can be
  reconstructed. At most one open link per unit (generated ``open_flag``); overlap
  and cycle rules are enforced in the service under the ``org_hierarchy`` graph lock.
* ``Location`` — a physical site, kept separate from organisational units.
* ``GraphLock`` — rows locked with SELECT ... FOR UPDATE to serialise graph changes.

Organisational units are not access roles and grant no permissions (ADR-023).
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


class ParentRuleMode(StrEnum):
    ADVISORY = "advisory"
    STRICT = "strict"


ORG_HIERARCHY_LOCK = "org_hierarchy"


class OrgUnitType(PublicIdMixin, TrackedMixin, Base):
    __tablename__ = "org_unit_type"
    __table_args__ = (
        CheckConstraint("parent_rule_mode IN ('advisory', 'strict')", name="rule_mode_valid"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(150))
    description: Mapped[str | None] = mapped_column(String(500))
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    allows_employee_assignment: Mapped[bool] = mapped_column(Boolean, default=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    parent_rule_mode: Mapped[str] = mapped_column(String(10), default=ParentRuleMode.ADVISORY.value)

    translations: Mapped[list["OrgUnitTypeTranslation"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class OrgUnitTypeTranslation(Base):
    __tablename__ = "org_unit_type_translation"
    __table_args__ = (
        UniqueConstraint("org_unit_type_id", "locale"),
        CheckConstraint(LOCALE_CHECK, name="locale_valid"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    org_unit_type_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("org_unit_type.id"))
    locale: Mapped[str] = mapped_column(CHAR(2))
    name: Mapped[str] = mapped_column(String(150))


class OrgUnitTypeRule(Base):
    """Allowed parent type for a child type. ``parent_type_id`` NULL = may be a root."""

    __tablename__ = "org_unit_type_rule"
    __table_args__ = (UniqueConstraint("child_type_id", "parent_key"),)

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    child_type_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("org_unit_type.id"))
    parent_type_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("org_unit_type.id"))
    parent_key: Mapped[int] = mapped_column(
        BigIntKey, Computed("COALESCE(parent_type_id, 0)", persisted=True)
    )
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("user_account.id"))


class Location(PublicIdMixin, TrackedMixin, Base):
    """A physical site. A plant is an org unit of a "Plant" type linked to a location."""

    __tablename__ = "location"

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    address_line1: Mapped[str | None] = mapped_column(String(200))
    address_line2: Mapped[str | None] = mapped_column(String(200))
    city: Mapped[str | None] = mapped_column(String(100))
    state: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    country_code: Mapped[str | None] = mapped_column(CHAR(2))
    time_zone: Mapped[str | None] = mapped_column(String(64))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)


class OrgUnit(PublicIdMixin, TrackedMixin, Base):
    __tablename__ = "org_unit"
    __table_args__ = (CheckConstraint(PERIOD_CHECK, name="valid_period"),)

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    short_name: Mapped[str | None] = mapped_column(String(50))
    unit_type_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("org_unit_type.id"))
    location_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("location.id"))
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    external_ref: Mapped[str | None] = mapped_column(String(100), index=True)

    unit_type: Mapped[OrgUnitType] = relationship(lazy="joined")
    location: Mapped[Location | None] = relationship(lazy="joined")
    translations: Mapped[list["OrgUnitTranslation"]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class OrgUnitTranslation(Base):
    __tablename__ = "org_unit_translation"
    __table_args__ = (
        UniqueConstraint("org_unit_id", "locale"),
        CheckConstraint(LOCALE_CHECK, name="locale_valid"),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    org_unit_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("org_unit.id"))
    locale: Mapped[str] = mapped_column(CHAR(2))
    name: Mapped[str] = mapped_column(String(200))


class OrgUnitHierarchy(Base):
    """Effective-dated parent link. Moving a unit closes one link and opens another."""

    __tablename__ = "org_unit_hierarchy"
    __table_args__ = (
        UniqueConstraint("child_unit_id", "open_flag"),
        CheckConstraint("child_unit_id <> parent_unit_id", name="not_self"),
        CheckConstraint(PERIOD_CHECK, name="valid_period"),
        Index(
            "ix_org_unit_hierarchy_parent_unit_id_effective_to", "parent_unit_id", "effective_to"
        ),
    )

    id: Mapped[int] = mapped_column(BigIntKey, primary_key=True, autoincrement=True)
    child_unit_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("org_unit.id"))
    parent_unit_id: Mapped[int] = mapped_column(BigIntKey, ForeignKey("org_unit.id"))
    effective_from: Mapped[date | None] = mapped_column(Date)
    effective_to: Mapped[date | None] = mapped_column(Date)
    open_flag: Mapped[int | None] = mapped_column(SmallInteger, Computed(OPEN_FLAG, persisted=True))
    created_at: Mapped[datetime] = mapped_column(UTCDateTime(), default=utcnow)
    created_by_user_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("user_account.id"))
    ended_at: Mapped[datetime | None] = mapped_column(UTCDateTime())
    ended_by_user_id: Mapped[int | None] = mapped_column(BigIntKey, ForeignKey("user_account.id"))

    parent: Mapped[OrgUnit] = relationship(foreign_keys=[parent_unit_id], lazy="joined")


class GraphLock(Base):
    """One row per independently serialised graph (e.g. ``org_hierarchy``)."""

    __tablename__ = "graph_lock"

    name: Mapped[str] = mapped_column(String(50), primary_key=True)
    description: Mapped[str] = mapped_column(String(200))
