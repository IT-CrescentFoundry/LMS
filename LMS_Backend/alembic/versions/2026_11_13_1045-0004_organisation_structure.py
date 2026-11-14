"""Stage C1: organisation structure tables.

Creates configurable organisation unit types (+ translations and optional parent-type
rules), locations, organisation units (+ translations), effective-dated parent links
and the ``graph_lock`` table, seeded with the ``org_hierarchy`` row that serialises
hierarchy changes (cycle checks run under SELECT ... FOR UPDATE on it).

No business rows are created here; the confirmed baseline (five functions) is seeded
by revision 0005. Organisational units grant no permissions.

Downgrade safety: the downgrade refuses, dropping nothing, unless every table is
empty and graph_lock holds only its own row. Development/production downgrades
additionally require explicit human approval and a verified backup.

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-13 10:45:07.507295+00:00
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

graph_lock = sa.table(
    "graph_lock", sa.column("name", sa.String), sa.column("description", sa.String)
)
OWNED_LOCK_ROWS = ("org_hierarchy",)
# Tables that must be empty before this revision may drop them (graph_lock is checked
# separately: it must hold exactly the migration-owned row).
DATA_TABLES = (
    "org_unit_translation",
    "org_unit_hierarchy",
    "org_unit_type_translation",
    "org_unit_type_rule",
    "org_unit",
    "org_unit_type",
    "location",
)


def upgrade() -> None:
    """Create the organisation structure tables."""
    op.create_table(
        "graph_lock",
        sa.Column("name", sa.String(length=50), nullable=False),
        sa.Column("description", sa.String(length=200), nullable=False),
        sa.PrimaryKeyConstraint("name", name=op.f("pk_graph_lock")),
    )
    op.create_table(
        "location",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("address_line1", sa.String(length=200), nullable=True),
        sa.Column("address_line2", sa.String(length=200), nullable=True),
        sa.Column("city", sa.String(length=100), nullable=True),
        sa.Column("state", sa.String(length=100), nullable=True),
        sa.Column("postal_code", sa.String(length=20), nullable=True),
        sa.Column("country_code", sa.CHAR(length=2), nullable=True),
        sa.Column("time_zone", sa.String(length=64), nullable=True),
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
            name=op.f("fk_location_created_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_location_updated_by_user_id_user_account"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_location")),
        sa.UniqueConstraint("code", name=op.f("uq_location_code")),
        sa.UniqueConstraint("public_id", name=op.f("uq_location_public_id")),
    )
    op.create_table(
        "org_unit_type",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("allows_employee_assignment", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("parent_rule_mode", sa.String(length=10), nullable=False),
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
            "parent_rule_mode IN ('advisory', 'strict')",
            name=op.f("ck_org_unit_type_rule_mode_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_org_unit_type_created_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_org_unit_type_updated_by_user_id_user_account"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_org_unit_type")),
        sa.UniqueConstraint("code", name=op.f("uq_org_unit_type_code")),
        sa.UniqueConstraint("public_id", name=op.f("uq_org_unit_type_public_id")),
    )
    op.create_table(
        "org_unit",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("short_name", sa.String(length=50), nullable=True),
        sa.Column(
            "unit_type_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column(
            "location_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
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
            "effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from",
            name=op.f("ck_org_unit_valid_period"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_org_unit_created_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["location_id"], ["location.id"], name=op.f("fk_org_unit_location_id_location")
        ),
        sa.ForeignKeyConstraint(
            ["unit_type_id"],
            ["org_unit_type.id"],
            name=op.f("fk_org_unit_unit_type_id_org_unit_type"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_org_unit_updated_by_user_id_user_account"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_org_unit")),
        sa.UniqueConstraint("code", name=op.f("uq_org_unit_code")),
        sa.UniqueConstraint("public_id", name=op.f("uq_org_unit_public_id")),
    )
    op.create_index(op.f("ix_org_unit_external_ref"), "org_unit", ["external_ref"], unique=False)
    op.create_table(
        "org_unit_type_rule",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "child_type_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column(
            "parent_type_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column(
            "parent_key",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            sa.Computed("COALESCE(parent_type_id, 0)", persisted=True),
            nullable=False,
        ),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column(
            "created_by_user_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["child_type_id"],
            ["org_unit_type.id"],
            name=op.f("fk_org_unit_type_rule_child_type_id_org_unit_type"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_org_unit_type_rule_created_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_type_id"],
            ["org_unit_type.id"],
            name=op.f("fk_org_unit_type_rule_parent_type_id_org_unit_type"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_org_unit_type_rule")),
        sa.UniqueConstraint(
            "child_type_id",
            "parent_key",
            name=op.f("uq_org_unit_type_rule_child_type_id_parent_key"),
        ),
    )
    op.create_table(
        "org_unit_type_translation",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "org_unit_type_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column("locale", sa.CHAR(length=2), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.CheckConstraint(
            "locale IN ('bn', 'hi', 'gu')", name=op.f("ck_org_unit_type_translation_locale_valid")
        ),
        sa.ForeignKeyConstraint(
            ["org_unit_type_id"],
            ["org_unit_type.id"],
            name=op.f("fk_org_unit_type_translation_org_unit_type_id_org_unit_type"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_org_unit_type_translation")),
        sa.UniqueConstraint(
            "org_unit_type_id",
            "locale",
            name=op.f("uq_org_unit_type_translation_org_unit_type_id_locale"),
        ),
    )
    op.create_table(
        "org_unit_hierarchy",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "child_unit_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column(
            "parent_unit_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column("effective_from", sa.Date(), nullable=True),
        sa.Column("effective_to", sa.Date(), nullable=True),
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
        sa.CheckConstraint(
            "child_unit_id <> parent_unit_id", name=op.f("ck_org_unit_hierarchy_not_self")
        ),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_from IS NULL OR effective_to > effective_from",
            name=op.f("ck_org_unit_hierarchy_valid_period"),
        ),
        sa.ForeignKeyConstraint(
            ["child_unit_id"],
            ["org_unit.id"],
            name=op.f("fk_org_unit_hierarchy_child_unit_id_org_unit"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_org_unit_hierarchy_created_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["ended_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_org_unit_hierarchy_ended_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["parent_unit_id"],
            ["org_unit.id"],
            name=op.f("fk_org_unit_hierarchy_parent_unit_id_org_unit"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_org_unit_hierarchy")),
        sa.UniqueConstraint(
            "child_unit_id", "open_flag", name=op.f("uq_org_unit_hierarchy_child_unit_id_open_flag")
        ),
    )
    op.create_index(
        "ix_org_unit_hierarchy_parent_unit_id_effective_to",
        "org_unit_hierarchy",
        ["parent_unit_id", "effective_to"],
        unique=False,
    )
    op.create_table(
        "org_unit_translation",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "org_unit_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column("locale", sa.CHAR(length=2), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.CheckConstraint(
            "locale IN ('bn', 'hi', 'gu')", name=op.f("ck_org_unit_translation_locale_valid")
        ),
        sa.ForeignKeyConstraint(
            ["org_unit_id"],
            ["org_unit.id"],
            name=op.f("fk_org_unit_translation_org_unit_id_org_unit"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_org_unit_translation")),
        sa.UniqueConstraint(
            "org_unit_id", "locale", name=op.f("uq_org_unit_translation_org_unit_id_locale")
        ),
    )
    op.bulk_insert(
        graph_lock,
        [{"name": "org_hierarchy", "description": "Serialises organisation hierarchy changes"}],
    )


def downgrade() -> None:
    """Drop the organisation structure tables in reverse dependency order.

    Refuses (and changes nothing) unless every table is empty and ``graph_lock`` holds
    only its migration-owned row: after revision 0005's downgrade has removed the
    seeded baseline, any remaining row was created by someone and must not be lost.

    Indexes are not dropped separately: on MySQL an index backing a foreign key cannot
    be dropped before its constraint, and DROP TABLE removes indexes anyway.
    """
    if context.is_offline_mode():
        raise RuntimeError(
            "Revision 0004 cannot be downgraded in offline (--sql) mode: it must first "
            "verify that its tables hold no data."
        )
    connection = op.get_bind()
    problems = [
        f"{table} has {count} row(s)"
        for table in DATA_TABLES
        if (count := connection.execute(sa.text(f"SELECT COUNT(*) FROM `{table}`")).scalar_one())
    ]
    locks = set(connection.execute(sa.text("SELECT name FROM graph_lock")).scalars())
    if locks != set(OWNED_LOCK_ROWS):
        problems.append(f"graph_lock holds {sorted(locks)}, expected {sorted(OWNED_LOCK_ROWS)}")
    if problems:
        raise RuntimeError(
            "Refusing to downgrade revision 0004 (organisation structure); nothing was "
            "dropped: " + "; ".join(problems) + ". Remove or archive this data deliberately "
            "(with approval and a verified backup) before downgrading."
        )

    op.drop_table("org_unit_translation")
    op.drop_table("org_unit_hierarchy")
    op.drop_table("org_unit_type_translation")
    op.drop_table("org_unit_type_rule")
    op.drop_table("org_unit")
    op.drop_table("org_unit_type")
    op.drop_table("location")
    op.drop_table("graph_lock")
