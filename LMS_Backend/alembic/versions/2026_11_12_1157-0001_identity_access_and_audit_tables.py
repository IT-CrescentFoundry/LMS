"""Stage B: identity, access-control and audit tables.

Creates eight tables (no data): user_account, access_permission, access_role,
access_role_permission, user_access_role, user_session, login_throttle, audit_event.
No employee or organisation tables (Stage C).

Generated with ``alembic revision --autogenerate`` against the empty test database
and reviewed manually. Column types are rendered as plain MySQL types so this file
never depends on application code.

Revision ID: 0001
Revises:
Create Date: 2026-11-12 11:57:16.525315+00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the Stage B tables, constraints and indexes."""
    op.create_table(
        "access_permission",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("code", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("is_privileged", sa.Boolean(), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_access_permission")),
        sa.UniqueConstraint("code", name=op.f("uq_access_permission_code")),
    )
    op.create_table(
        "login_throttle",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("scope", sa.String(length=20), nullable=False),
        sa.Column("key_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("failure_count", sa.Integer(), nullable=False),
        sa.Column("window_started_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("last_failure_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("locked_until", mysql.DATETIME(fsp=6), nullable=True),
        sa.CheckConstraint(
            "scope IN ('identifier', 'ip')", name=op.f("ck_login_throttle_scope_valid")
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_login_throttle")),
        sa.UniqueConstraint("scope", "key_hash", name=op.f("uq_login_throttle_scope_key_hash")),
    )
    op.create_table(
        "user_account",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("public_id", mysql.BINARY(length=16), nullable=False),
        sa.Column("login_id", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=200), nullable=False),
        sa.Column("email", sa.String(length=254), nullable=True),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("password_created_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("password_changed_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("password_must_change", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("status_changed_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("status_reason", sa.String(length=500), nullable=True),
        sa.Column("activated_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("deactivated_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("last_login_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column(
            "created_by_user_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column(
            "updated_by_user_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(
            "status <> 'active' OR password_hash IS NOT NULL",
            name=op.f("ck_user_account_active_requires_password"),
        ),
        sa.CheckConstraint(
            "status IN ('pending_activation', 'active', 'suspended', 'disabled')",
            name=op.f("ck_user_account_status_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["created_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_user_account_created_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["updated_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_user_account_updated_by_user_id_user_account"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_account")),
        sa.UniqueConstraint("email", name=op.f("uq_user_account_email")),
        sa.UniqueConstraint("login_id", name=op.f("uq_user_account_login_id")),
        sa.UniqueConstraint("public_id", name=op.f("uq_user_account_public_id")),
    )
    op.create_table(
        "access_role",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=500), nullable=False),
        sa.Column("is_system", sa.Boolean(), nullable=False),
        sa.Column("is_api_assignable", sa.Boolean(), nullable=False),
        sa.Column(
            "assign_permission_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("updated_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ["assign_permission_id"],
            ["access_permission.id"],
            name=op.f("fk_access_role_assign_permission_id_access_permission"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_access_role")),
        sa.UniqueConstraint("code", name=op.f("uq_access_role_code")),
    )
    op.create_table(
        "audit_event",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("public_id", mysql.BINARY(length=16), nullable=False),
        sa.Column("occurred_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column("outcome", sa.String(length=20), nullable=False),
        sa.Column(
            "actor_user_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column("target_type", sa.String(length=50), nullable=True),
        sa.Column("target_id", sa.String(length=64), nullable=True),
        sa.Column("request_id", sa.String(length=128), nullable=True),
        sa.Column("source_ip", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=True),
        sa.CheckConstraint(
            "outcome IN ('success', 'failure', 'denied')", name=op.f("ck_audit_event_outcome_valid")
        ),
        sa.ForeignKeyConstraint(
            ["actor_user_id"],
            ["user_account.id"],
            name=op.f("fk_audit_event_actor_user_id_user_account"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_audit_event")),
        sa.UniqueConstraint("public_id", name=op.f("uq_audit_event_public_id")),
    )
    op.create_index(
        "ix_audit_event_actor_user_id_occurred_at",
        "audit_event",
        ["actor_user_id", "occurred_at"],
        unique=False,
    )
    op.create_index(
        "ix_audit_event_event_type_occurred_at",
        "audit_event",
        ["event_type", "occurred_at"],
        unique=False,
    )
    op.create_index("ix_audit_event_occurred_at", "audit_event", ["occurred_at"], unique=False)
    op.create_index(
        "ix_audit_event_target", "audit_event", ["target_type", "target_id"], unique=False
    )
    op.create_table(
        "user_session",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column("public_id", mysql.BINARY(length=16), nullable=False),
        sa.Column(
            "user_account_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.CHAR(length=64), nullable=False),
        sa.Column("created_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("last_seen_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("idle_expires_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("absolute_expires_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column("revoked_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column("revoked_reason", sa.String(length=30), nullable=True),
        sa.Column(
            "revoked_by_user_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column("ip_address", sa.String(length=45), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(
            ["revoked_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_user_session_revoked_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["user_account_id"],
            ["user_account.id"],
            name=op.f("fk_user_session_user_account_id_user_account"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_session")),
        sa.UniqueConstraint("public_id", name=op.f("uq_user_session_public_id")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_user_session_token_hash")),
    )
    op.create_index(
        "ix_user_session_user_account_id_revoked_at",
        "user_session",
        ["user_account_id", "revoked_at"],
        unique=False,
    )
    op.create_table(
        "access_role_permission",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "access_role_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column(
            "access_permission_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column("granted_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column(
            "granted_by_user_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["access_permission_id"],
            ["access_permission.id"],
            name=op.f("fk_access_role_permission_access_permission_id_access_permission"),
        ),
        sa.ForeignKeyConstraint(
            ["access_role_id"],
            ["access_role.id"],
            name=op.f("fk_access_role_permission_access_role_id_access_role"),
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_access_role_permission_granted_by_user_id_user_account"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_access_role_permission")),
        sa.UniqueConstraint(
            "access_role_id",
            "access_permission_id",
            name=op.f("uq_access_role_permission_access_role_id_access_permission_id"),
        ),
    )
    op.create_table(
        "user_access_role",
        sa.Column(
            "id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            autoincrement=True,
            nullable=False,
        ),
        sa.Column(
            "user_account_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column(
            "access_role_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=False,
        ),
        sa.Column("granted_at", mysql.DATETIME(fsp=6), nullable=False),
        sa.Column(
            "granted_by_user_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column("revoked_at", mysql.DATETIME(fsp=6), nullable=True),
        sa.Column(
            "revoked_by_user_id",
            sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql"),
            nullable=True,
        ),
        sa.Column("revoke_reason", sa.String(length=500), nullable=True),
        sa.Column(
            "active_flag",
            sa.SmallInteger(),
            sa.Computed("IF(revoked_at IS NULL, 1, NULL)", persisted=True),
            nullable=True,
        ),
        sa.ForeignKeyConstraint(
            ["access_role_id"],
            ["access_role.id"],
            name=op.f("fk_user_access_role_access_role_id_access_role"),
        ),
        sa.ForeignKeyConstraint(
            ["granted_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_user_access_role_granted_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["revoked_by_user_id"],
            ["user_account.id"],
            name=op.f("fk_user_access_role_revoked_by_user_id_user_account"),
        ),
        sa.ForeignKeyConstraint(
            ["user_account_id"],
            ["user_account.id"],
            name=op.f("fk_user_access_role_user_account_id_user_account"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_user_access_role")),
        sa.UniqueConstraint(
            "user_account_id",
            "access_role_id",
            "active_flag",
            name=op.f("uq_user_access_role_user_account_id_access_role_id_active_flag"),
        ),
    )
    op.create_index(
        "ix_user_access_role_access_role_id", "user_access_role", ["access_role_id"], unique=False
    )


def downgrade() -> None:
    """Drop the Stage B tables (and all their data) in reverse dependency order.

    Indexes are not dropped separately: on MySQL, indexes backing foreign keys
    cannot be dropped before their constraints, and DROP TABLE removes them anyway.
    """
    op.drop_table("user_access_role")
    op.drop_table("access_role_permission")
    op.drop_table("user_session")
    op.drop_table("audit_event")
    op.drop_table("access_role")
    op.drop_table("user_account")
    op.drop_table("login_throttle")
    op.drop_table("access_permission")
