"""Stage C3: employee master, assignments, functional roles, responsibilities,
reporting relationships and the user-account link.

* ``employee`` - minimal employee record, independent of any login account
  (ADR-040). NULL ``employment_status`` = "not recorded" (never treated as active).
  No compensation, bank, identity-number, birth date, gender, address, health,
  family or personal contact columns exist - by design.
* ``employee_assignment`` - effective-dated placement in an org unit with optional
  C1 designation / grade / level / location. Generated ``primary_open`` and
  ``open_flag`` back the one-open-primary and one-open-per-unit rules; the services
  check full period overlaps under an employee-row lock.
* ``employee_functional_role`` - manual roles and exclusions (derived roles are
  computed on read). ``employee_responsibility`` - duties with optional context.
* ``reporting_relationship_type`` (+ translations) and ``reporting_relationship`` -
  typed, effective-dated employee-to-employee relationships.
* ``user_account.employee_id`` plus generated ``linked_employee_active`` (UNIQUE):
  at most one non-disabled account per employee; disabled accounts keep the link.

Seeds (fixed, migration-owned identities): reporting type ``LINE_MANAGER`` and the
``graph_lock`` row ``reporting`` that serialises reporting-line changes. The upgrade
verifies them.

Downgrade safety: refuses - changing nothing - unless every employee table is empty,
no account is linked, the seeds are exactly as seeded and nothing else refers to
them. Development/production downgrades additionally require explicit human
approval and a verified backup. None of these tables grant LMS permissions.

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-14 08:05:09.384844+00:00
"""

import uuid
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "0008"
down_revision: str | Sequence[str] | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOW = sa.func.utc_timestamp(6)
LINE_MANAGER_ID = "01a1d916-fe06-7227-bb32-8c8712475ee2"
LINE_MANAGER = {
    "code": "LINE_MANAGER",
    "name": "Line manager",
    "allows_multiple": 0,
    "is_hierarchical": 1,
    "is_active": 1,
}
LOCK_NAME = "reporting"
LOCK_DESCRIPTION = "Serialises reporting-relationship changes (cycle checks)"
KNOWN_LOCKS = {"org_hierarchy", LOCK_NAME}  # org_hierarchy belongs to revision 0004
# Tables this revision creates that must be empty before it may drop them.
DATA_TABLES = (
    "employee_functional_role",
    "employee_responsibility",
    "employee_assignment",
    "reporting_relationship",
    "reporting_relationship_type_translation",
    "employee",
)

relationship_type = sa.table(
    "reporting_relationship_type",
    sa.column("public_id", sa.LargeBinary),
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("allows_multiple", sa.Boolean),
    sa.column("is_hierarchical", sa.Boolean),
    sa.column("is_active", sa.Boolean),
    sa.column("created_at", sa.DateTime),
    sa.column("updated_at", sa.DateTime),
    sa.column("version", sa.Integer),
)
graph_lock = sa.table(
    "graph_lock", sa.column("name", sa.String), sa.column("description", sa.String)
)


def _rows(connection: sa.Connection, sql: str, **params: Any) -> list[sa.Row[Any]]:
    return list(connection.execute(sa.text(sql), params))


def seed_problems(connection: sa.Connection) -> list[str]:
    """Differences from the exact migration-owned seed (empty list = intact)."""
    problems = []
    rows = _rows(
        connection,
        "SELECT code, name, allows_multiple, is_hierarchical, is_active, version, "
        "created_by_user_id, updated_by_user_id FROM reporting_relationship_type "
        "WHERE public_id = :pid",
        pid=uuid.UUID(LINE_MANAGER_ID).bytes,
    )
    if len(rows) != 1:
        problems.append("seeded reporting type LINE_MANAGER is missing")
    else:
        row = rows[0]
        expected = {
            **LINE_MANAGER,
            "version": 1,
            "created_by_user_id": None,
            "updated_by_user_id": None,
        }
        changed = sorted(k for k, v in expected.items() if getattr(row, k) != v)
        if changed:
            problems.append(
                f"seeded reporting type LINE_MANAGER was modified ({', '.join(changed)})"
            )
    others = _rows(
        connection,
        "SELECT code FROM reporting_relationship_type WHERE public_id <> :pid",
        pid=uuid.UUID(LINE_MANAGER_ID).bytes,
    )
    if others:
        problems.append(f"other reporting types exist {sorted(r.code for r in others)}")
    locks = {r.name for r in _rows(connection, "SELECT name FROM graph_lock")}
    if LOCK_NAME not in locks:
        problems.append("graph_lock row 'reporting' is missing")
    return problems


def upgrade() -> None:
    """Create the employee tables and the account link; seed LINE_MANAGER and the lock."""
    op.create_table(
        "employee",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("employee_code", sa.String(length=30), nullable=False),
        sa.Column("full_name", sa.String(length=200), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=True),
        sa.Column("preferred_language", sa.CHAR(length=2), nullable=True),
        sa.Column("work_email", sa.String(length=254), nullable=True),
        sa.Column("employment_status", sa.String(length=20), nullable=True),
        sa.Column("date_of_joining", sa.Date(), nullable=True),
        sa.Column("date_of_separation", sa.Date(), nullable=True),
        sa.Column("external_ref", sa.String(length=100), nullable=True),
        sa.Column("public_id", mysql.BINARY(length=16), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_by_user_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column(
            "updated_by_user_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "employment_status IS NULL OR employment_status <> 'separated' "
            "OR date_of_separation IS NOT NULL",
            name=op.f("ck_employee_separated_has_date"),
        ),
        sa.CheckConstraint(
            "employment_status IS NULL OR employment_status IN ('active', 'on_leave', 'separated')",
            name=op.f("ck_employee_status_valid"),
        ),
        sa.CheckConstraint(
            "preferred_language IS NULL OR preferred_language IN ('en', 'bn', 'hi', 'gu')",
            name=op.f("ck_employee_language_valid"),
        ),
        sa.CheckConstraint(
            "date_of_separation IS NULL OR date_of_joining IS NULL "
            "OR date_of_separation >= date_of_joining",
            name=op.f("ck_employee_separation_after_joining"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_employee_created_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_employee_updated_by_user_id_user_account"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employee")),
        sa.UniqueConstraint("employee_code", name=op.f("uq_employee_employee_code")),
        sa.UniqueConstraint("public_id", name=op.f("uq_employee_public_id")),
    )
    op.create_index(
        op.f("ix_employee_employment_status"), "employee", ["employment_status"], unique=False
    )
    op.create_index(op.f("ix_employee_external_ref"), "employee", ["external_ref"], unique=False)
    op.create_table(
        "reporting_relationship_type",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("allows_multiple", sa.Boolean(), nullable=False),
        sa.Column("is_hierarchical", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("public_id", mysql.BINARY(length=16), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_by_user_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column(
            "updated_by_user_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_reporting_relationship_type_created_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_reporting_relationship_type_updated_by_user_id_user_account"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reporting_relationship_type")),
        sa.UniqueConstraint("code", name=op.f("uq_reporting_relationship_type_code")),
        sa.UniqueConstraint("public_id", name=op.f("uq_reporting_relationship_type_public_id")),
    )
    op.create_table(
        "reporting_relationship",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "employee_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column(
            "manager_employee_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column(
            "relationship_type_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column(
            "open_flag",
            sa.SmallInteger(),
            sa.Computed("IF(effective_to IS NULL, 1, NULL)", persisted=True),
            nullable=True,
        ),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column(
            "created_by_user_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column("public_id", mysql.BINARY(length=16), nullable=False),
        sa.Column("ended_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column(
            "ended_by_user_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from",
            name=op.f("ck_reporting_relationship_valid_period"),
        ),
        sa.CheckConstraint(
            "employee_id <> manager_employee_id", name=op.f("ck_reporting_relationship_not_self")
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_reporting_relationship_created_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee.id"],
            name=op.f("fk_reporting_relationship_employee_id_employee"),
        ),
        sa.ForeignKeyConstraint(
            ["ended_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_reporting_relationship_ended_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["manager_employee_id"],
            ["employee.id"],
            name=op.f("fk_reporting_relationship_manager_employee_id_employee"),
        ),
        sa.ForeignKeyConstraint(
            ["relationship_type_id"],
            ["reporting_relationship_type.id"],
            name=op.f("fk_reporting_relationship_relationship_type_id_reporting_relationship_type"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reporting_relationship")),
        sa.UniqueConstraint(
            "employee_id",
            "relationship_type_id",
            "manager_employee_id",
            "open_flag",
            name="uq_reporting_relationship_open",
        ),
        sa.UniqueConstraint("public_id", name=op.f("uq_reporting_relationship_public_id")),
    )
    op.create_index(
        "ix_reporting_relationship_manager_employee_id_effective_to",
        "reporting_relationship",
        ["manager_employee_id", "effective_to"],
        unique=False,
    )
    op.create_table(
        "reporting_relationship_type_translation",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "relationship_type_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column("locale", sa.CHAR(length=2), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.CheckConstraint(
            "locale IN ('bn', 'hi', 'gu')",
            name=op.f("ck_reporting_relationship_type_translation_locale_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["relationship_type_id"],
            ["reporting_relationship_type.id"],
            name=op.f(
                "fk_reporting_relationship_type_translation_relationship_type_id_reporting_relationship_type"
            ),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reporting_relationship_type_translation")),
        sa.UniqueConstraint(
            "relationship_type_id",
            "locale",
            name=op.f("uq_reporting_relationship_type_translation_relationship_type_id_locale"),
        ),
    )
    op.create_table(
        "employee_assignment",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "employee_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column(
            "org_unit_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column(
            "designation_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column(
            "grade_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column(
            "job_level_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column(
            "location_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column("assignment_type", sa.String(length=20), nullable=False),
        sa.Column(
            "is_primary",
            sa.Boolean(),
            sa.Computed("assignment_type = 'primary'", persisted=True),
            nullable=False,
        ),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("source", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column(
            "primary_open",
            sa.SmallInteger(),
            sa.Computed(
                "IF(assignment_type = 'primary' AND effective_to IS NULL, 1, NULL)", persisted=True
            ),
            nullable=True,
        ),
        sa.Column(
            "open_flag",
            sa.SmallInteger(),
            sa.Computed("IF(effective_to IS NULL, 1, NULL)", persisted=True),
            nullable=True,
        ),
        sa.Column("public_id", mysql.BINARY(length=16), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column(
            "created_by_user_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column(
            "updated_by_user_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column("ended_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column(
            "ended_by_user_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "assignment_type IN ('primary', 'additional', 'acting', 'deputation')",
            name=op.f("ck_employee_assignment_type_valid"),
        ),
        sa.CheckConstraint(
            "source IN ('manual', 'import')", name=op.f("ck_employee_assignment_source_valid")
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from",
            name=op.f("ck_employee_assignment_valid_period"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_employee_assignment_created_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["designation_id"],
            ["designation.id"],
            name=op.f("fk_employee_assignment_designation_id_designation"),
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee.id"],
            name=op.f("fk_employee_assignment_employee_id_employee"),
        ),
        sa.ForeignKeyConstraint(
            ["ended_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_employee_assignment_ended_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["grade_id"], ["grade.id"], name=op.f("fk_employee_assignment_grade_id_grade")
        ),
        sa.ForeignKeyConstraint(
            ["job_level_id"],
            ["job_level.id"],
            name=op.f("fk_employee_assignment_job_level_id_job_level"),
        ),
        sa.ForeignKeyConstraint(
            ["location_id"],
            ["location.id"],
            name=op.f("fk_employee_assignment_location_id_location"),
        ),
        sa.ForeignKeyConstraint(
            ["org_unit_id"],
            ["org_unit.id"],
            name=op.f("fk_employee_assignment_org_unit_id_org_unit"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_employee_assignment_updated_by_user_id_user_account"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employee_assignment")),
        sa.UniqueConstraint(
            "employee_id",
            "org_unit_id",
            "open_flag",
            name=op.f("uq_employee_assignment_employee_id_org_unit_id_open_flag"),
        ),
        sa.UniqueConstraint(
            "employee_id",
            "primary_open",
            name=op.f("uq_employee_assignment_employee_id_primary_open"),
        ),
        sa.UniqueConstraint("public_id", name=op.f("uq_employee_assignment_public_id")),
    )
    op.create_index(
        op.f("ix_employee_assignment_designation_id"),
        "employee_assignment",
        ["designation_id"],
        unique=False,
    )
    op.create_index(
        "ix_employee_assignment_employee_id_effective_from",
        "employee_assignment",
        ["employee_id", "effective_from"],
        unique=False,
    )
    op.create_index(
        op.f("ix_employee_assignment_location_id"),
        "employee_assignment",
        ["location_id"],
        unique=False,
    )
    op.create_index(
        "ix_employee_assignment_org_unit_id_effective_to",
        "employee_assignment",
        ["org_unit_id", "effective_to"],
        unique=False,
    )
    op.create_table(
        "employee_responsibility",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "employee_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column(
            "responsibility_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column(
            "context_org_unit_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column(
            "context_location_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column(
            "context_unit_key",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            sa.Computed("COALESCE(context_org_unit_id, 0)", persisted=True),
            nullable=False,
        ),
        sa.Column(
            "context_location_key",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            sa.Computed("COALESCE(context_location_id, 0)", persisted=True),
            nullable=False,
        ),
        sa.Column(
            "open_flag",
            sa.SmallInteger(),
            sa.Computed("IF(effective_to IS NULL, 1, NULL)", persisted=True),
            nullable=True,
        ),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column(
            "created_by_user_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column("public_id", mysql.BINARY(length=16), nullable=False),
        sa.Column("ended_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column(
            "ended_by_user_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from",
            name=op.f("ck_employee_responsibility_valid_period"),
        ),
        sa.ForeignKeyConstraint(
            ["context_location_id"],
            ["location.id"],
            name=op.f("fk_employee_responsibility_context_location_id_location"),
        ),
        sa.ForeignKeyConstraint(
            ["context_org_unit_id"],
            ["org_unit.id"],
            name=op.f("fk_employee_responsibility_context_org_unit_id_org_unit"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_employee_responsibility_created_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee.id"],
            name=op.f("fk_employee_responsibility_employee_id_employee"),
        ),
        sa.ForeignKeyConstraint(
            ["ended_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_employee_responsibility_ended_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["responsibility_id"],
            ["responsibility.id"],
            name=op.f("fk_employee_responsibility_responsibility_id_responsibility"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employee_responsibility")),
        sa.UniqueConstraint(
            "employee_id",
            "responsibility_id",
            "context_unit_key",
            "context_location_key",
            "open_flag",
            name="uq_employee_responsibility_open",
        ),
        sa.UniqueConstraint("public_id", name=op.f("uq_employee_responsibility_public_id")),
    )
    op.create_index(
        op.f("ix_employee_responsibility_context_location_id"),
        "employee_responsibility",
        ["context_location_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_employee_responsibility_context_org_unit_id"),
        "employee_responsibility",
        ["context_org_unit_id"],
        unique=False,
    )
    op.create_table(
        "employee_functional_role",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "employee_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column(
            "functional_role_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column("reason", sa.String(length=500), nullable=True),
        sa.Column(
            "open_flag",
            sa.SmallInteger(),
            sa.Computed("IF(effective_to IS NULL, 1, NULL)", persisted=True),
            nullable=True,
        ),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column(
            "created_by_user_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column("public_id", mysql.BINARY(length=16), nullable=False),
        sa.Column("ended_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column(
            "ended_by_user_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.CheckConstraint(
            "kind IN ('manual', 'exclusion')", name=op.f("ck_employee_functional_role_kind_valid")
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from",
            name=op.f("ck_employee_functional_role_valid_period"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_employee_functional_role_created_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["employee_id"],
            ["employee.id"],
            name=op.f("fk_employee_functional_role_employee_id_employee"),
        ),
        sa.ForeignKeyConstraint(
            ["ended_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_employee_functional_role_ended_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["functional_role_id"],
            ["functional_role.id"],
            name=op.f("fk_employee_functional_role_functional_role_id_functional_role"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_employee_functional_role")),
        sa.UniqueConstraint(
            "employee_id",
            "functional_role_id",
            "open_flag",
            name="uq_employee_functional_role_open",
        ),
        sa.UniqueConstraint("public_id", name=op.f("uq_employee_functional_role_public_id")),
    )
    op.add_column(
        "user_account",
        sa.Column(
            "employee_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
    )
    op.add_column(
        "user_account",
        sa.Column(
            "linked_employee_active",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            sa.Computed(
                "IF(employee_id IS NOT NULL AND status <> 'disabled', employee_id, NULL)",
                persisted=True,
            ),
            nullable=True,
        ),
    )
    op.create_index("ix_user_account_employee_id", "user_account", ["employee_id"], unique=False)
    op.create_unique_constraint(
        op.f("uq_user_account_linked_employee_active"), "user_account", ["linked_employee_active"]
    )
    op.create_foreign_key(
        "fk_user_account_employee_id_employee",
        "user_account",
        "employee",
        ["employee_id"],
        ["id"],
        use_alter=True,
    )
    op.execute(
        relationship_type.insert().values(
            public_id=sa.func.unhex(uuid.UUID(LINE_MANAGER_ID).hex),
            **LINE_MANAGER,
            created_at=NOW,
            updated_at=NOW,
            version=1,
        )
    )
    op.execute(graph_lock.insert().values(name=LOCK_NAME, description=LOCK_DESCRIPTION))
    if context.is_offline_mode():
        op.execute("-- 0008: seed verification runs only in online mode")
    else:
        problems = seed_problems(op.get_bind())
        if problems:
            raise RuntimeError("Revision 0008 could not establish its seed: " + "; ".join(problems))


def downgrade() -> None:
    """Drop the employee tables and the account link - only when nothing would be lost."""
    if context.is_offline_mode():
        raise RuntimeError(
            "Revision 0008 cannot be downgraded in offline (--sql) mode: it must first "
            "verify that no employee data or account link exists."
        )
    connection = op.get_bind()
    problems = [
        f"{table} has {count} row(s)"
        for table in DATA_TABLES
        if (count := connection.execute(sa.text(f"SELECT COUNT(*) FROM `{table}`")).scalar_one())
    ]
    linked = connection.execute(
        sa.text("SELECT COUNT(*) FROM user_account WHERE employee_id IS NOT NULL")
    ).scalar_one()
    if linked:
        problems.append(f"{linked} user account(s) are linked to employees")
    problems += seed_problems(connection)
    unknown_locks = sorted(
        {r.name for r in _rows(connection, "SELECT name FROM graph_lock")} - KNOWN_LOCKS
    )
    if unknown_locks:
        problems.append(f"graph_lock holds rows of later revisions {unknown_locks}")
    if problems:
        raise RuntimeError(
            "Refusing to downgrade revision 0008 (employees); nothing was changed: "
            + "; ".join(problems)
            + ". Remove or archive this data deliberately (with approval and a verified "
            "backup) before downgrading."
        )

    deleted = connection.execute(
        sa.text("DELETE FROM reporting_relationship_type WHERE public_id = :pid"),
        {"pid": uuid.UUID(LINE_MANAGER_ID).bytes},
    ).rowcount
    if deleted != 1:
        raise RuntimeError(
            f"Revision 0008 downgrade deleted {deleted} reporting types, expected 1."
        )
    connection.execute(sa.text("DELETE FROM graph_lock WHERE name = :name"), {"name": LOCK_NAME})

    # Indexes are not dropped separately: on MySQL an index backing a foreign key
    # cannot be dropped before its constraint, and DROP TABLE removes indexes anyway.
    op.drop_constraint("fk_user_account_employee_id_employee", "user_account", type_="foreignkey")
    op.drop_constraint(
        op.f("uq_user_account_linked_employee_active"), "user_account", type_="unique"
    )
    op.drop_index("ix_user_account_employee_id", table_name="user_account")
    op.drop_column("user_account", "linked_employee_active")
    op.drop_column("user_account", "employee_id")
    op.drop_table("employee_functional_role")
    op.drop_table("employee_responsibility")
    op.drop_table("employee_assignment")
    op.drop_table("reporting_relationship_type_translation")
    op.drop_table("reporting_relationship")
    op.drop_table("reporting_relationship_type")
    op.drop_table("employee")
