"""Stage C3: employee permissions and their role mappings (data only).

New permission codes (none privileged):

    employees.view           employee directory, profile, roles, responsibilities,
                             reporting lines and account summary
    employees.history.view   assignment timelines and the employee change history
    employees.manage         employee records, employment status, assignments,
                             functional roles, responsibilities, data-quality view
    reporting_lines.manage   reporting relationships (line managers)

Interim mappings (Stage C3 plan section 7; provisional, final policy Q-51 / C4) -
exactly 8: hr_admin and super_admin receive all four; no other role receives any.
Grants are global. Being a line manager, holding a functional role or a
responsibility never grants these permissions. Linking an account to an employee
additionally requires the existing ``user_accounts.manage``.

Seed integrity: the upgrade refuses if a required role is missing or a permission code
already exists, and afterwards verifies exactly the four permissions and exactly the
8 expected mappings (online mode).

Downgrade safety: removes only the verified migration-owned rows; refuses, changing
nothing, if mappings were added, removed or re-granted, a permission record was
modified, or anything else refers to these permissions. Development/production
downgrades additionally require explicit human approval and a verified backup.

This file does not import application code (frozen snapshot).

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-14 08:30:00.000000+00:00
"""

import re
from collections.abc import Iterable, Sequence
from typing import Any

import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision: str = "0009"
down_revision: str | Sequence[str] | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOW = sa.func.utc_timestamp(6)

PERMISSIONS: list[tuple[str, str]] = [
    (
        "employees.view",
        "View employees: directory, profile, functional roles, responsibilities, "
        "reporting lines and account summary",
    ),
    ("employees.history.view", "View employee assignment timelines and change history"),
    (
        "employees.manage",
        "Manage employee records, employment status, assignments, functional roles, "
        "responsibilities and the data-quality view",
    ),
    ("reporting_lines.manage", "Manage employee reporting relationships"),
]
ALL_CODES = [code for code, _ in PERMISSIONS]
ROLE_GRANTS: dict[str, list[str]] = {
    "hr_admin": ALL_CODES,
    "super_admin": ALL_CODES,
}
EXPECTED_MAPPINGS: frozenset[tuple[str, str]] = frozenset(
    (role_code, code) for role_code, codes in ROLE_GRANTS.items() for code in codes
)
if len(EXPECTED_MAPPINGS) != 8:  # guards edits to ROLE_GRANTS above
    raise RuntimeError("0009 must define exactly 8 role-permission mappings")

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

_IDENTIFIER = re.compile(r"^[A-Za-z0-9_]+$")


def _rows(connection: sa.Connection, sql: str, **params: Any) -> list[sa.Row[Any]]:
    statement = sa.text(sql)
    expanding = [name for name, value in params.items() if isinstance(value, list | tuple)]
    if expanding:
        statement = statement.bindparams(*(sa.bindparam(n, expanding=True) for n in expanding))
    return list(connection.execute(statement, params))


def upgrade() -> None:
    """Insert the employee permissions and grant them to the seeded roles."""
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
                "Revision 0009 cannot seed the employee permissions: "
                + (f"missing roles {missing}; " if missing else "")
                + (f"permission codes already exist {existing}" if existing else "")
            )
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
    if online:
        problems = seed_problems(op.get_bind())
        if problems:
            raise RuntimeError(
                "Revision 0009 did not establish the expected seed: " + "; ".join(problems)
            )
    else:
        op.execute("-- 0009: seed verification runs only in online mode")


# --------------------------------------------------------------------------- checks


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
        "FROM access_role_permission m "
        "JOIN access_role r ON r.id = m.access_role_id "
        "JOIN access_permission p ON p.id = m.access_permission_id "
        "WHERE m.access_permission_id IN :ids",
        ids=permission_ids or [0],
    )


def seed_problems(connection: sa.Connection) -> list[str]:
    """Differences from the exact migration-owned seed (empty list = intact)."""
    problems: list[str] = []
    expected_permissions = {code: description for code, description in PERMISSIONS}
    permissions = _permission_rows(connection)
    found = {row.code for row in permissions}
    if found != set(ALL_CODES) or len(permissions) != len(ALL_CODES):
        problems.append(f"permissions present {sorted(found)}, expected {sorted(ALL_CODES)}")
    for row in permissions:
        if row.description != expected_permissions.get(row.code) or row.is_privileged:
            problems.append(f"permission {row.code} was modified")
    mappings = _mapping_rows(connection, [row.id for row in permissions])
    actual = [(row.role_code, row.permission_code) for row in mappings]
    extra = sorted(set(actual) - EXPECTED_MAPPINGS)
    missing = sorted(EXPECTED_MAPPINGS - set(actual))
    if extra:
        problems.append(f"additional role-permission mappings {extra}")
    if missing:
        problems.append(f"missing role-permission mappings {missing}")
    if len(actual) != len(set(actual)):
        problems.append("duplicate role-permission mappings")
    regranted = sorted(
        (row.role_code, row.permission_code) for row in mappings if row.granted_by_user_id
    )
    if regranted:
        problems.append(f"mappings modified (granted by a user) {regranted}")
    return problems


def foreign_references(
    connection: sa.Connection,
    table: str,
    ids: Iterable[int],
    allowed: dict[tuple[str, str], set[int]],
) -> list[str]:
    """Rows in ANY table whose foreign key points at ``table.id`` in ``ids``, except the
    migration-owned referencing rows listed in ``allowed``."""
    id_list = sorted(set(ids))
    if not id_list:
        return []
    columns = _rows(
        connection,
        "SELECT TABLE_NAME AS ref_table, COLUMN_NAME AS ref_column "
        "FROM information_schema.KEY_COLUMN_USAGE "
        "WHERE TABLE_SCHEMA = DATABASE() AND REFERENCED_TABLE_SCHEMA = DATABASE() "
        "AND REFERENCED_TABLE_NAME = :table AND REFERENCED_COLUMN_NAME = 'id' "
        "ORDER BY TABLE_NAME, COLUMN_NAME",
        table=table,
    )
    found = []
    for row in columns:
        ref_table, ref_column = str(row.ref_table), str(row.ref_column)
        if not (_IDENTIFIER.fullmatch(ref_table) and _IDENTIFIER.fullmatch(ref_column)):
            raise RuntimeError(f"Unexpected identifier {ref_table}.{ref_column}")
        sql = f"SELECT COUNT(*) FROM `{ref_table}` WHERE `{ref_column}` IN :ids"  # noqa: S608
        if (ref_table, ref_column) in allowed:
            sql += " AND id NOT IN :exempt"
            exempt = sorted(allowed[(ref_table, ref_column)]) or [0]
            count = _rows(connection, sql, ids=id_list, exempt=exempt)[0][0]
        else:
            count = _rows(connection, sql, ids=id_list)[0][0]
        if count:
            found.append(f"{count} row(s) in {ref_table}.{ref_column} refer to these permissions")
    return found


def downgrade() -> None:
    """Remove exactly the verified migration-owned permissions and mappings."""
    if context.is_offline_mode():
        raise RuntimeError(
            "Revision 0009 cannot be downgraded in offline (--sql) mode: it must first "
            "verify the live database."
        )
    connection = op.get_bind()
    problems = seed_problems(connection)
    permission_ids = [row.id for row in _permission_rows(connection)]
    mapping_ids = {row.id for row in _mapping_rows(connection, permission_ids)}
    problems += foreign_references(
        connection,
        "access_permission",
        permission_ids,
        allowed={("access_role_permission", "access_permission_id"): mapping_ids},
    )
    if problems:
        raise RuntimeError(
            "Refusing to downgrade revision 0009 (employee permissions); nothing was "
            "changed: " + "; ".join(problems) + ". Administrator changes are never deleted "
            "by a migration."
        )

    for table, ids, expected in (
        ("access_role_permission", mapping_ids, len(EXPECTED_MAPPINGS)),
        ("access_permission", set(permission_ids), len(PERMISSIONS)),
    ):
        statement = sa.text(f"DELETE FROM `{table}` WHERE id IN :ids").bindparams(  # noqa: S608
            sa.bindparam("ids", expanding=True)
        )
        deleted = connection.execute(statement, {"ids": sorted(ids)}).rowcount
        if deleted != expected:
            raise RuntimeError(
                f"Revision 0009 downgrade deleted {deleted} {table} rows, expected {expected}."
            )
