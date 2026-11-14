"""Stage C1: occupational reference tables.

Creates job families (optional parent), grades and job levels (two separate optional
lists; their relationship is open, Q-45), designations (+ translations), functional
roles (+ translations), the effective-dated, optionally unit-scoped designation ->
functional-role mapping, and responsibilities (+ translations).

None of these tables grant LMS permissions or hold competency / proficiency data
(Technical Competency Library and proficiency scales are Stage F). No rows are created.

Downgrade safety: the downgrade refuses, dropping nothing, while any of its tables
holds data. Development/production downgrades additionally require explicit human
approval and a verified backup.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-13 10:47:00.000000+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "0006"
down_revision: str | Sequence[str] | None = "0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Every table this revision creates; all must be empty before a downgrade.
DATA_TABLES = (
    "functional_role_translation",
    "designation_functional_role",
    "functional_role",
    "designation_translation",
    "responsibility_translation",
    "designation",
    "responsibility",
    "job_level",
    "job_family",
    "grade",
)


def upgrade() -> None:
    """Create the occupational reference tables."""
    op.create_table(
        "grade",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
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
            name=op.f("fk_grade_created_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_grade_updated_by_user_id_user_account"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_grade")),
        sa.UniqueConstraint("code", name=op.f("uq_grade_code")),
        sa.UniqueConstraint("public_id", name=op.f("uq_grade_public_id")),
    )
    op.create_table(
        "job_family",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column(
            "parent_job_family_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
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
            name=op.f("fk_job_family_created_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_job_family_id"],
            ["job_family.id"],
            name=op.f("fk_job_family_parent_job_family_id_job_family"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_job_family_updated_by_user_id_user_account"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_family")),
        sa.UniqueConstraint("code", name=op.f("uq_job_family_code")),
        sa.UniqueConstraint("public_id", name=op.f("uq_job_family_public_id")),
    )
    op.create_table(
        "job_level",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=True),
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
            name=op.f("fk_job_level_created_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_job_level_updated_by_user_id_user_account"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_job_level")),
        sa.UniqueConstraint("code", name=op.f("uq_job_level_code")),
        sa.UniqueConstraint("public_id", name=op.f("uq_job_level_public_id")),
    )
    op.create_table(
        "responsibility",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column("category", sa.String(length=50), nullable=True),
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
            name=op.f("fk_responsibility_created_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_responsibility_updated_by_user_id_user_account"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_responsibility")),
        sa.UniqueConstraint("code", name=op.f("uq_responsibility_code")),
        sa.UniqueConstraint("public_id", name=op.f("uq_responsibility_public_id")),
    )
    op.create_table(
        "designation",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column(
            "job_family_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
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
            name=op.f("fk_designation_created_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["job_family_id"],
            ["job_family.id"],
            name=op.f("fk_designation_job_family_id_job_family"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_designation_updated_by_user_id_user_account"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_designation")),
        sa.UniqueConstraint("code", name=op.f("uq_designation_code")),
        sa.UniqueConstraint("public_id", name=op.f("uq_designation_public_id")),
    )
    op.create_table(
        "responsibility_translation",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "responsibility_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column("locale", sa.CHAR(length=2), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.CheckConstraint(
            "locale IN ('bn', 'hi', 'gu')", name=op.f("ck_responsibility_translation_locale_valid")
        ),
        sa.ForeignKeyConstraint(
            ["responsibility_id"],
            ["responsibility.id"],
            name=op.f("fk_responsibility_translation_responsibility_id_responsibility"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_responsibility_translation")),
        sa.UniqueConstraint(
            "responsibility_id",
            "locale",
            name=op.f("uq_responsibility_translation_responsibility_id_locale"),
        ),
    )
    op.create_table(
        "designation_translation",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "designation_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column("locale", sa.CHAR(length=2), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.CheckConstraint(
            "locale IN ('bn', 'hi', 'gu')", name=op.f("ck_designation_translation_locale_valid")
        ),
        sa.ForeignKeyConstraint(
            ["designation_id"],
            ["designation.id"],
            name=op.f("fk_designation_translation_designation_id_designation"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_designation_translation")),
        sa.UniqueConstraint(
            "designation_id",
            "locale",
            name=op.f("uq_designation_translation_designation_id_locale"),
        ),
    )
    op.create_table(
        "functional_role",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("description", sa.String(length=1000), nullable=True),
        sa.Column(
            "job_family_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column(
            "owner_org_unit_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
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
            name=op.f("fk_functional_role_created_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["job_family_id"],
            ["job_family.id"],
            name=op.f("fk_functional_role_job_family_id_job_family"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_org_unit_id"],
            ["org_unit.id"],
            name=op.f("fk_functional_role_owner_org_unit_id_org_unit"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_functional_role_updated_by_user_id_user_account"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_functional_role")),
        sa.UniqueConstraint("code", name=op.f("uq_functional_role_code")),
        sa.UniqueConstraint("public_id", name=op.f("uq_functional_role_public_id")),
    )
    op.create_table(
        "designation_functional_role",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "designation_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column(
            "functional_role_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column(
            "scope_org_unit_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column("scope_include_descendants", sa.Boolean(), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
        sa.Column(
            "scope_key",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            sa.Computed("COALESCE(scope_org_unit_id, 0)", persisted=True),
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
        sa.Column("ended_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column(
            "ended_by_user_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column("public_id", mysql.BINARY(length=16), nullable=False),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from",
            name=op.f("ck_designation_functional_role_valid_period"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_designation_functional_role_created_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["designation_id"],
            ["designation.id"],
            name=op.f("fk_designation_functional_role_designation_id_designation"),
        ),
        sa.ForeignKeyConstraint(
            ["ended_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_designation_functional_role_ended_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["functional_role_id"],
            ["functional_role.id"],
            name=op.f("fk_designation_functional_role_functional_role_id_functional_role"),
        ),
        sa.ForeignKeyConstraint(
            ["scope_org_unit_id"],
            ["org_unit.id"],
            name=op.f("fk_designation_functional_role_scope_org_unit_id_org_unit"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_designation_functional_role")),
        sa.UniqueConstraint(
            "designation_id",
            "functional_role_id",
            "scope_key",
            "open_flag",
            name="uq_designation_functional_role_open",
        ),
        sa.UniqueConstraint("public_id", name=op.f("uq_designation_functional_role_public_id")),
    )
    op.create_table(
        "functional_role_translation",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "functional_role_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column("locale", sa.CHAR(length=2), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.CheckConstraint(
            "locale IN ('bn', 'hi', 'gu')", name=op.f("ck_functional_role_translation_locale_valid")
        ),
        sa.ForeignKeyConstraint(
            ["functional_role_id"],
            ["functional_role.id"],
            name=op.f("fk_functional_role_translation_functional_role_id_functional_role"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_functional_role_translation")),
        sa.UniqueConstraint(
            "functional_role_id",
            "locale",
            name=op.f("uq_functional_role_translation_functional_role_id_locale"),
        ),
    )


def downgrade() -> None:
    """Drop the occupational reference tables, dependants first - only when empty."""
    if context.is_offline_mode():
        raise RuntimeError(
            "Revision 0006 cannot be downgraded in offline (--sql) mode: it must first "
            "verify that its tables hold no data."
        )
    connection = op.get_bind()
    populated = [
        f"{table} ({count} row(s))"
        for table in DATA_TABLES
        if (count := connection.execute(sa.text(f"SELECT COUNT(*) FROM `{table}`")).scalar_one())
    ]
    if populated:
        raise RuntimeError(
            "Refusing to downgrade revision 0006 (occupational reference data); nothing "
            "was dropped. These tables contain data: " + ", ".join(populated) + ". "
            "Remove or archive it deliberately (with approval and a verified backup) "
            "before downgrading."
        )

    op.drop_table("functional_role_translation")
    op.drop_table("designation_functional_role")
    op.drop_table("functional_role")
    op.drop_table("designation_translation")
    op.drop_table("responsibility_translation")
    op.drop_table("designation")
    op.drop_table("responsibility")
    op.drop_table("job_level")
    op.drop_table("job_family")
    op.drop_table("grade")
