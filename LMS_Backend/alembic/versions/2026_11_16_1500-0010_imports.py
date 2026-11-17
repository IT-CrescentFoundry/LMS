"""Stage D: import framework tables, import permissions and the import commit lock.

Tables:

* ``import_job`` - uploaded workbook metadata (name, size, SHA-256 - never the file),
  profile code and version, lifecycle status, inspection result, confirmed column
  mapping, summary counts, who uploaded / validated / committed and when;
* ``import_row`` - staged rows of mapped sections (mapped fields only), outcome,
  explicit decisions (skip / distinct) and the target record;
* ``import_issue`` - file, row and cell issues (code, severity, source text);
* ``import_value_mapping`` - reviewed label -> canonical record decisions (review queue
  ``pending``; ``approved`` decisions are superseded, never edited). Generated
  ``current_flag`` (UNIQUE with kind + normalised label) allows one current decision;
* ``record_provenance`` - business record <- import row links.

Permissions (none privileged), granted to hr_admin and super_admin only (exactly 8
mappings; Q-31 - second approver - remains open):

    imports.view               import profiles, jobs, history, issues and reports
    imports.employees.run      upload, map, validate, decide rows and cancel (profile 1)
    imports.employees.commit   approve and commit a validated profile-1 import
    imports.mappings.manage    approve or reject reference mappings (labels -> records)

Committing additionally needs the domain permissions (``employees.manage``,
``reporting_lines.manage``), so an import never grants more than the screens do.

Seed: ``graph_lock`` row ``imports`` serialises import commits.

Downgrade safety: refuses, changing nothing, while any import table holds rows, the
permission seed or its mappings were changed, or anything else refers to them.

This file does not import application code (frozen snapshot).

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-16 15:00:00.000000+00:00
"""

import re
from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import context, op
from sqlalchemy.dialects import mysql

revision: str = "0010"
down_revision: str | Sequence[str] | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOW = sa.func.utc_timestamp(6)
BIGINT = sa.BigInteger().with_variant(mysql.BIGINT(unsigned=True), "mysql")
UUID_BIN = mysql.BINARY(length=16)
TS = mysql.DATETIME(fsp=6)

STATUSES = (
    "uploaded",
    "mapping_required",
    "validating",
    "validation_failed",
    "ready_for_approval",
    "committing",
    "completed",
    "completed_with_skips",
    "failed",
    "expired",
    "cancelled",
)
OUTCOMES = ("new", "update", "unchanged", "error", "skipped")
DECISIONS = ("skip", "distinct")
SEVERITIES = ("error", "warning")
KINDS = ("org_unit", "designation", "location", "grade", "job_level")
MAPPING_STATUSES = ("pending", "approved", "rejected", "superseded")
ACTIONS = ("created", "updated", "unchanged")
DATA_TABLES = (
    "record_provenance",
    "import_issue",
    "import_row",
    "import_value_mapping",
    "import_job",
)

PERMISSIONS: list[tuple[str, str]] = [
    ("imports.view", "View import profiles, import jobs, history, issues and reports"),
    ("imports.employees.run", "Upload, map, validate and prepare employee imports"),
    ("imports.employees.commit", "Approve and commit validated employee imports"),
    ("imports.mappings.manage", "Approve or reject reference mappings used by imports"),
]
ALL_CODES = [code for code, _ in PERMISSIONS]
ROLE_GRANTS: dict[str, list[str]] = {"hr_admin": ALL_CODES, "super_admin": ALL_CODES}
EXPECTED_MAPPINGS = frozenset((r, c) for r, codes in ROLE_GRANTS.items() for c in codes)
if len(EXPECTED_MAPPINGS) != 8:  # guards edits to ROLE_GRANTS above
    raise RuntimeError("0010 must define exactly 8 role-permission mappings")
LOCK_NAME = "imports"
LOCK_DESCRIPTION = "Serialises import commits"

permission = sa.table(
    "access_permission",
    sa.column("id", sa.BigInteger),
    sa.column("code", sa.String),
    sa.column("description", sa.String),
    sa.column("is_privileged", sa.Boolean),
    sa.column("created_at", sa.DateTime),
)
role = sa.table("access_role", sa.column("id", sa.BigInteger), sa.column("code", sa.String))
role_permission = sa.table(
    "access_role_permission",
    sa.column("access_role_id", sa.BigInteger),
    sa.column("access_permission_id", sa.BigInteger),
    sa.column("granted_at", sa.DateTime),
)
graph_lock = sa.table(
    "graph_lock", sa.column("name", sa.String), sa.column("description", sa.String)
)
_IDENTIFIER = re.compile(r"^[A-Za-z0-9_]+$")


def _in(column: str, values: Sequence[str]) -> str:
    return f"{column} IN ({', '.join(repr(v) for v in values)})"


def _rows(connection: sa.Connection, sql: str, **params: Any) -> list[sa.Row[Any]]:
    statement = sa.text(sql)
    expanding = [name for name, value in params.items() if isinstance(value, list | tuple)]
    if expanding:
        statement = statement.bindparams(*(sa.bindparam(n, expanding=True) for n in expanding))
    return list(connection.execute(statement, params))


def _user_fk(column: str, table: str) -> sa.ForeignKeyConstraint:
    return sa.ForeignKeyConstraint(
        [column], ["user_account.id"], name=f"fk_{table}_{column}_user_account"
    )


def upgrade() -> None:
    online = not context.is_offline_mode()
    if online:
        connection = op.get_bind()
        roles = {
            r.code
            for r in _rows(
                connection, "SELECT code FROM access_role WHERE code IN :c", c=list(ROLE_GRANTS)
            )
        }
        missing = sorted(set(ROLE_GRANTS) - roles)
        existing = sorted(
            r.code
            for r in _rows(
                connection, "SELECT code FROM access_permission WHERE code IN :c", c=ALL_CODES
            )
        )
        if missing or existing:
            raise RuntimeError(
                "Revision 0010 cannot seed the import permissions: "
                + (f"missing roles {missing}; " if missing else "")
                + (f"permission codes already exist {existing}" if existing else "")
            )

    op.create_table(
        "import_job",
        sa.Column("id", BIGINT, primary_key=True, autoincrement=True),
        sa.Column("public_id", UUID_BIN, nullable=False),
        sa.Column("profile_code", sa.String(50), nullable=False),
        sa.Column("profile_version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("original_filename", sa.String(255), nullable=False),
        sa.Column("file_sha256", sa.String(64), nullable=False),
        sa.Column("file_size", sa.BigInteger(), nullable=False),
        sa.Column("file_stored", sa.Boolean(), nullable=False),
        sa.Column("workbook", sa.JSON(), nullable=False),
        sa.Column("column_mapping", sa.JSON(), nullable=True),
        sa.Column("summary", sa.JSON(), nullable=True),
        sa.Column("failure_code", sa.String(80), nullable=True),
        sa.Column("uploaded_by_user_id", BIGINT, nullable=False),
        sa.Column("uploaded_at", TS, nullable=False),
        sa.Column("validated_by_user_id", BIGINT, nullable=True),
        sa.Column("validated_at", TS, nullable=True),
        sa.Column("committed_by_user_id", BIGINT, nullable=True),
        sa.Column("committed_at", TS, nullable=True),
        sa.Column("finished_at", TS, nullable=True),
        sa.Column("updated_at", TS, nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(_in("status", STATUSES), name=op.f("ck_import_job_status_valid")),
        sa.CheckConstraint("file_size > 0", name=op.f("ck_import_job_file_size_positive")),
        _user_fk("uploaded_by_user_id", "import_job"),
        _user_fk("validated_by_user_id", "import_job"),
        _user_fk("committed_by_user_id", "import_job"),
        sa.UniqueConstraint("public_id", name=op.f("uq_import_job_public_id")),
    )
    op.create_index("ix_import_job_status", "import_job", ["status"])
    op.create_index("ix_import_job_profile_sha", "import_job", ["profile_code", "file_sha256"])

    op.create_table(
        "import_row",
        sa.Column("id", BIGINT, primary_key=True, autoincrement=True),
        sa.Column("job_id", BIGINT, nullable=False),
        sa.Column("section", sa.String(30), nullable=False),
        sa.Column("sheet", sa.String(100), nullable=False),
        sa.Column("row_number", sa.Integer(), nullable=False),
        sa.Column("natural_key", sa.String(400), nullable=False),
        sa.Column("values", sa.JSON(), nullable=False),
        sa.Column("source", sa.JSON(), nullable=False),
        sa.Column("outcome", sa.String(20), nullable=False),
        sa.Column("changes", sa.JSON(), nullable=True),
        sa.Column("decision", sa.String(20), nullable=True),
        sa.Column("decision_reason", sa.String(500), nullable=True),
        sa.Column("decided_by_user_id", BIGINT, nullable=True),
        sa.Column("decided_at", TS, nullable=True),
        sa.Column("target_public_id", UUID_BIN, nullable=True),
        sa.CheckConstraint(_in("outcome", OUTCOMES), name=op.f("ck_import_row_outcome_valid")),
        sa.CheckConstraint(
            f"decision IS NULL OR {_in('decision', DECISIONS)}",
            name=op.f("ck_import_row_decision_valid"),
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["import_job.id"], name="fk_import_row_job_id_import_job"
        ),
        _user_fk("decided_by_user_id", "import_row"),
        sa.UniqueConstraint(
            "job_id",
            "section",
            "sheet",
            "row_number",
            name=op.f("uq_import_row_job_id_section_sheet_row_number"),
        ),
    )
    op.create_index("ix_import_row_job_outcome", "import_row", ["job_id", "outcome"])

    op.create_table(
        "import_issue",
        sa.Column("id", BIGINT, primary_key=True, autoincrement=True),
        sa.Column("job_id", BIGINT, nullable=False),
        sa.Column("row_id", BIGINT, nullable=True),
        sa.Column("section", sa.String(30), nullable=True),
        sa.Column("sheet", sa.String(100), nullable=True),
        sa.Column("row_number", sa.Integer(), nullable=True),
        sa.Column("column", sa.String(10), nullable=True),
        sa.Column("field", sa.String(50), nullable=True),
        sa.Column("code", sa.String(80), nullable=False),
        sa.Column("severity", sa.String(10), nullable=False),
        sa.Column("source_value", sa.String(200), nullable=True),
        sa.Column("params", sa.JSON(), nullable=True),
        sa.CheckConstraint(
            _in("severity", SEVERITIES), name=op.f("ck_import_issue_severity_valid")
        ),
        sa.ForeignKeyConstraint(
            ["job_id"], ["import_job.id"], name="fk_import_issue_job_id_import_job"
        ),
        sa.ForeignKeyConstraint(
            ["row_id"], ["import_row.id"], name="fk_import_issue_row_id_import_row"
        ),
    )
    op.create_index("ix_import_issue_job_severity", "import_issue", ["job_id", "severity"])

    op.create_table(
        "import_value_mapping",
        sa.Column("id", BIGINT, primary_key=True, autoincrement=True),
        sa.Column("public_id", UUID_BIN, nullable=False),
        sa.Column("kind", sa.String(30), nullable=False),
        sa.Column("source_text", sa.String(200), nullable=False),
        sa.Column("normalised_text", sa.String(200), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("target_public_id", UUID_BIN, nullable=True),
        sa.Column("decision_reason", sa.String(500), nullable=True),
        sa.Column("decided_by_user_id", BIGINT, nullable=True),
        sa.Column("decided_at", TS, nullable=True),
        sa.Column("first_job_id", BIGINT, nullable=True),
        sa.Column("created_at", TS, nullable=False),
        sa.Column(
            "current_flag",
            sa.Integer(),
            sa.Computed("IF(status <> 'superseded', 1, NULL)", persisted=True),
            nullable=True,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.CheckConstraint(_in("kind", KINDS), name=op.f("ck_import_value_mapping_kind_valid")),
        sa.CheckConstraint(
            _in("status", MAPPING_STATUSES), name=op.f("ck_import_value_mapping_status_valid")
        ),
        sa.CheckConstraint(
            "status <> 'approved' OR target_public_id IS NOT NULL",
            name=op.f("ck_import_value_mapping_approved_has_target"),
        ),
        sa.CheckConstraint(
            "status <> 'pending' OR target_public_id IS NULL",
            name=op.f("ck_import_value_mapping_pending_has_no_target"),
        ),
        _user_fk("decided_by_user_id", "import_value_mapping"),
        sa.ForeignKeyConstraint(
            ["first_job_id"],
            ["import_job.id"],
            name="fk_import_value_mapping_first_job_id_import_job",
        ),
        sa.UniqueConstraint("public_id", name=op.f("uq_import_value_mapping_public_id")),
        sa.UniqueConstraint(
            "kind",
            "normalised_text",
            "current_flag",
            name=op.f("uq_import_value_mapping_kind_normalised_text_current_flag"),
        ),
    )
    op.create_index("ix_import_value_mapping_status", "import_value_mapping", ["status"])

    op.create_table(
        "record_provenance",
        sa.Column("id", BIGINT, primary_key=True, autoincrement=True),
        sa.Column("job_id", BIGINT, nullable=False),
        sa.Column("row_id", BIGINT, nullable=False),
        sa.Column("target_type", sa.String(40), nullable=False),
        sa.Column("target_public_id", UUID_BIN, nullable=False),
        sa.Column("action", sa.String(20), nullable=False),
        sa.Column("recorded_at", TS, nullable=False),
        sa.CheckConstraint(_in("action", ACTIONS), name=op.f("ck_record_provenance_action_valid")),
        sa.ForeignKeyConstraint(
            ["job_id"], ["import_job.id"], name="fk_record_provenance_job_id_import_job"
        ),
        sa.ForeignKeyConstraint(
            ["row_id"], ["import_row.id"], name="fk_record_provenance_row_id_import_row"
        ),
    )
    op.create_index(
        "ix_record_provenance_target", "record_provenance", ["target_type", "target_public_id"]
    )
    op.create_index("ix_record_provenance_job", "record_provenance", ["job_id"])

    for code, description in PERMISSIONS:
        op.execute(
            permission.insert().values(
                code=code, description=description, is_privileged=False, created_at=NOW
            )
        )
    for role_code, codes in ROLE_GRANTS.items():
        op.execute(
            role_permission.insert().from_select(
                ["access_role_id", "access_permission_id", "granted_at"],
                sa.select(role.c.id, permission.c.id, NOW)
                .select_from(role.join(permission, sa.true()))
                .where(role.c.code == role_code, permission.c.code.in_(codes)),
            )
        )
    op.execute(graph_lock.insert().values(name=LOCK_NAME, description=LOCK_DESCRIPTION))

    if online:
        problems = seed_problems(op.get_bind())
        if problems:
            raise RuntimeError(
                "Revision 0010 did not establish the expected seed: " + "; ".join(problems)
            )
    else:
        op.execute("-- 0010: seed verification runs only in online mode")


def _permission_rows(connection: sa.Connection) -> list[sa.Row[Any]]:
    return _rows(
        connection,
        "SELECT id, code, description, is_privileged FROM access_permission WHERE code IN :c",
        c=ALL_CODES,
    )


def _mapping_rows(connection: sa.Connection, permission_ids: list[int]) -> list[sa.Row[Any]]:
    return _rows(
        connection,
        "SELECT m.id, r.code AS role_code, p.code AS permission_code, m.granted_by_user_id "
        "FROM access_role_permission m JOIN access_role r ON r.id = m.access_role_id "
        "JOIN access_permission p ON p.id = m.access_permission_id "
        "WHERE m.access_permission_id IN :ids",
        ids=permission_ids or [0],
    )


def seed_problems(connection: sa.Connection) -> list[str]:
    problems: list[str] = []
    expected = dict(PERMISSIONS)
    permissions = _permission_rows(connection)
    if {row.code for row in permissions} != set(ALL_CODES) or len(permissions) != len(ALL_CODES):
        problems.append(
            f"permissions present {sorted(row.code for row in permissions)}, "
            f"expected {sorted(ALL_CODES)}"
        )
    for row in permissions:
        if row.description != expected.get(row.code) or row.is_privileged:
            problems.append(f"permission {row.code} was modified")
    mappings = _mapping_rows(connection, [row.id for row in permissions])
    actual = [(row.role_code, row.permission_code) for row in mappings]
    if set(actual) != EXPECTED_MAPPINGS or len(actual) != len(set(actual)):
        problems.append(f"role-permission mappings differ: {sorted(actual)}")
    if any(row.granted_by_user_id for row in mappings):
        problems.append("mappings modified (granted by a user)")
    locks = [
        r.description
        for r in _rows(
            connection, "SELECT description FROM graph_lock WHERE name = :n", n=LOCK_NAME
        )
    ]
    if locks != [LOCK_DESCRIPTION]:
        problems.append("graph_lock row 'imports' is missing or modified")
    return problems


def _foreign_references(connection: sa.Connection, ids: list[int], exempt: set[int]) -> list[str]:
    if not ids:
        return []
    columns = _rows(
        connection,
        "SELECT TABLE_NAME AS ref_table, COLUMN_NAME AS ref_column "
        "FROM information_schema.KEY_COLUMN_USAGE "
        "WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_SCHEMA = DATABASE() "
        "AND REFERENCED_TABLE_NAME = 'access_permission' AND REFERENCED_COLUMN_NAME = 'id'",
    )
    found = []
    for row in columns:
        table, column = str(row.ref_table), str(row.ref_column)
        if not (_IDENTIFIER.fullmatch(table) and _IDENTIFIER.fullmatch(column)):
            raise RuntimeError(f"Unexpected identifier {table}.{column}")
        sql = f"SELECT COUNT(*) FROM `{table}` WHERE `{column}` IN :ids AND id NOT IN :exempt"  # noqa: S608
        if _rows(connection, sql, ids=ids, exempt=sorted(exempt) or [0])[0][0]:
            found.append(f"{table}.{column} refers to the import permissions")
    return found


def downgrade() -> None:
    """Drop the import tables and remove the seed - only when nothing would be lost."""
    if context.is_offline_mode():
        raise RuntimeError(
            "Revision 0010 cannot be downgraded in offline (--sql) mode: it must first verify "
            "that no import data exists."
        )
    connection = op.get_bind()
    problems = [
        f"{table} has {count} row(s)"
        for table in DATA_TABLES
        if (count := connection.execute(sa.text(f"SELECT COUNT(*) FROM `{table}`")).scalar_one())  # noqa: S608
    ]
    problems += seed_problems(connection)
    permission_ids = [row.id for row in _permission_rows(connection)]
    mapping_ids = {row.id for row in _mapping_rows(connection, permission_ids)}
    problems += _foreign_references(connection, permission_ids, mapping_ids)
    if problems:
        raise RuntimeError(
            "Refusing to downgrade revision 0010 (imports); nothing was changed: "
            + "; ".join(problems)
            + ". Import history is never deleted by a migration."
        )
    for table, ids, expected_count in (
        ("access_role_permission", sorted(mapping_ids), len(EXPECTED_MAPPINGS)),
        ("access_permission", sorted(permission_ids), len(PERMISSIONS)),
    ):
        statement = sa.text(f"DELETE FROM `{table}` WHERE id IN :ids").bindparams(  # noqa: S608
            sa.bindparam("ids", expanding=True)
        )
        deleted = connection.execute(statement, {"ids": ids}).rowcount
        if deleted != expected_count:
            raise RuntimeError(
                f"Revision 0010 downgrade deleted {deleted} {table} rows, "
                f"expected {expected_count}."
            )
    connection.execute(sa.text("DELETE FROM graph_lock WHERE name = :n"), {"n": LOCK_NAME})
    for table in DATA_TABLES:
        op.drop_table(table)
