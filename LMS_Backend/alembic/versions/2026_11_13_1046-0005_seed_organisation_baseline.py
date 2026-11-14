"""Stage C1: seed the confirmed organisation baseline (data only).

Business-confirmed baseline (Stage C instructions; codes approved in C0):

    ACC_COM      Accounts & Commercial
    HR_ADMIN_IT  HR, Admin & IT
    OPERATION    Operation
    PURCHASE     Purchase
    SALES_BD     Sales & BD

* Unit types FUNCTION, SUB_FUNCTION and DEPARTMENT, plus ADVISORY parent rules
  (root -> FUNCTION, FUNCTION -> SUB_FUNCTION, SUB_FUNCTION -> DEPARTMENT,
  FUNCTION -> DEPARTMENT). Advisory rules only warn; the rule set is open (Q-47).
* The five functions as ROOT units of type FUNCTION, names exactly as supplied. Their
  start dates were not supplied, so ``effective_from`` stays NULL ("not recorded")
  rather than inventing a date.
* NO sub-functions, departments, plants, locations or company root are seeded: their
  names and placement are not yet confirmed (Q-47, Q-48).

Functions are organisational units. They are not functional roles, not Technical
Competency Library functions, and grant no LMS permissions.

Identity: every seeded row has a FIXED, migration-owned UUIDv7 ``public_id``. Codes and
names can be corrected by administrators; ``public_id`` is never changed by the
application, so the downgrade identifies the seeded rows by ``public_id`` only.

Downgrade safety: the downgrade removes the seeded rows only when they are exactly as
seeded (unmodified, version 1) and nothing else refers to them - no translations,
hierarchy links, other units of the seeded types, extra parent rules, or any other
foreign-key reference. Otherwise it refuses and changes nothing. It never deletes
administrator-created data. Development/production downgrades additionally require
explicit human approval and a verified backup.

This file does not import application code (frozen snapshot).

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-13 10:46:00.000000+00:00
"""

import re
import uuid
from collections.abc import Iterable, Sequence
from typing import Any

import sqlalchemy as sa
from alembic import context, op

# revision identifiers, used by Alembic.
revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

NOW = sa.func.utc_timestamp(6)

# (fixed public_id, code, name, sort_order, description)
UNIT_TYPES: list[tuple[str, str, str, int, str]] = [
    (
        "01a1d85c-46c6-7507-becf-6a138d42d30b",
        "FUNCTION",
        "Function",
        10,
        "Top-level company function",
    ),
    (
        "01a1d85c-46c8-7728-b174-5b36176a084d",
        "SUB_FUNCTION",
        "Sub-function",
        20,
        "Sub-function within a function",
    ),
    ("01a1d85c-46cb-7140-914e-86ed5dce1f1f", "DEPARTMENT", "Department", 30, "Department"),
]
# (child type, parent type or None for "may be a root")
PARENT_RULES: list[tuple[str, str | None]] = [
    ("FUNCTION", None),
    ("SUB_FUNCTION", "FUNCTION"),
    ("DEPARTMENT", "SUB_FUNCTION"),
    ("DEPARTMENT", "FUNCTION"),
]
# (fixed public_id, code, name) - all of type FUNCTION, roots, no dates.
FUNCTIONS: list[tuple[str, str, str]] = [
    ("01a1d85c-46cd-7b58-9a7e-9a2d7c0de618", "ACC_COM", "Accounts & Commercial"),
    ("01a1d85c-46d0-7630-a633-bf0222e6c701", "HR_ADMIN_IT", "HR, Admin & IT"),
    ("01a1d85c-46d3-7cce-834b-a055ef122b53", "OPERATION", "Operation"),
    ("01a1d85c-46d5-740b-8518-f6d3a7f8cd97", "PURCHASE", "Purchase"),
    ("01a1d85c-46d8-73ff-b636-ff5fea63dee9", "SALES_BD", "Sales & BD"),
]
FUNCTION_TYPE_CODE = "FUNCTION"

unit_type = sa.table(
    "org_unit_type",
    sa.column("id", sa.BigInteger),
    sa.column("public_id", sa.LargeBinary),
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("description", sa.String),
    sa.column("sort_order", sa.Integer),
    sa.column("allows_employee_assignment", sa.Boolean),
    sa.column("is_active", sa.Boolean),
    sa.column("parent_rule_mode", sa.String),
    sa.column("created_at", sa.DateTime),
    sa.column("updated_at", sa.DateTime),
    sa.column("version", sa.Integer),
)
type_rule = sa.table(
    "org_unit_type_rule",
    sa.column("child_type_id", sa.BigInteger),
    sa.column("parent_type_id", sa.BigInteger),
    sa.column("created_at", sa.DateTime),
)
org_unit = sa.table(
    "org_unit",
    sa.column("id", sa.BigInteger),
    sa.column("public_id", sa.LargeBinary),
    sa.column("code", sa.String),
    sa.column("name", sa.String),
    sa.column("unit_type_id", sa.BigInteger),
    sa.column("created_at", sa.DateTime),
    sa.column("updated_at", sa.DateTime),
    sa.column("version", sa.Integer),
)

_IDENTIFIER = re.compile(r"^[A-Za-z0-9_]+$")


def _public_id(value: str) -> sa.Function[bytes]:
    """``UNHEX('<hex>')`` of a fixed UUID: a SQL expression, so --sql output can render it."""
    return sa.func.unhex(uuid.UUID(value).hex)


def _uuid_bytes(value: str) -> bytes:
    return uuid.UUID(value).bytes


def _type_id(code: str) -> sa.ScalarSelect[int]:
    return sa.select(unit_type.c.id).where(unit_type.c.code == code).scalar_subquery()


def upgrade() -> None:
    """Insert the baseline unit types, advisory parent rules and the five functions."""
    for public_id, code, name, sort_order, description in UNIT_TYPES:
        op.execute(
            unit_type.insert().values(
                public_id=_public_id(public_id),
                code=code,
                name=name,
                description=description,
                sort_order=sort_order,
                allows_employee_assignment=True,
                is_active=True,
                parent_rule_mode="advisory",
                created_at=NOW,
                updated_at=NOW,
                version=1,
            )
        )
    for child, parent in PARENT_RULES:
        op.execute(
            type_rule.insert().from_select(
                ["child_type_id", "parent_type_id", "created_at"],
                sa.select(
                    _type_id(child),
                    _type_id(parent) if parent else sa.null(),
                    NOW,
                ),
            )
        )
    for public_id, code, name in FUNCTIONS:
        op.execute(
            org_unit.insert().from_select(
                ["public_id", "code", "name", "unit_type_id"]
                + ["created_at", "updated_at", "version"],
                sa.select(
                    _public_id(public_id),
                    sa.literal(code),
                    sa.literal(name),
                    _type_id(FUNCTION_TYPE_CODE),
                    NOW,
                    NOW,
                    sa.literal(1),
                ),
            )
        )
    if context.is_offline_mode():
        op.execute("-- 0005: seed verification runs only in online mode")
    else:
        problems = baseline_problems(op.get_bind())
        if problems:
            raise RuntimeError(
                "Revision 0005 could not establish the organisation baseline: "
                + "; ".join(problems)
            )


# --------------------------------------------------------------------------- checks


def _rows(connection: sa.Connection, sql: str, **params: Any) -> list[sa.Row[Any]]:
    statement = sa.text(sql)
    expanding = [name for name, value in params.items() if isinstance(value, list | tuple)]
    if expanding:
        statement = statement.bindparams(*(sa.bindparam(n, expanding=True) for n in expanding))
    return list(connection.execute(statement, params))


def _seeded_types(connection: sa.Connection) -> dict[str, sa.Row[Any]]:
    """Seeded unit types by code, located by their fixed public_id."""
    rows = _rows(
        connection,
        "SELECT id, public_id, code, name, description, sort_order, "
        "allows_employee_assignment, is_active, parent_rule_mode, version, "
        "created_by_user_id, updated_by_user_id "
        "FROM org_unit_type WHERE public_id IN :ids",
        ids=[_uuid_bytes(public_id) for public_id, *_ in UNIT_TYPES],
    )
    by_public_id = {bytes(row.public_id): row for row in rows}
    return {
        code: by_public_id[_uuid_bytes(public_id)]
        for public_id, code, *_ in UNIT_TYPES
        if _uuid_bytes(public_id) in by_public_id
    }


def _seeded_units(connection: sa.Connection) -> dict[str, sa.Row[Any]]:
    """Seeded functions keyed by their ORIGINAL code, located by fixed public_id."""
    rows = _rows(
        connection,
        "SELECT id, public_id, code, name, short_name, unit_type_id, location_id, "
        "effective_from, effective_to, external_ref, version, "
        "created_by_user_id, updated_by_user_id "
        "FROM org_unit WHERE public_id IN :ids",
        ids=[_uuid_bytes(public_id) for public_id, *_ in FUNCTIONS],
    )
    by_public_id = {bytes(row.public_id): row for row in rows}
    return {
        code: by_public_id[_uuid_bytes(public_id)]
        for public_id, code, _ in FUNCTIONS
        if _uuid_bytes(public_id) in by_public_id
    }


def _seeded_rules(
    connection: sa.Connection, types: dict[str, sa.Row[Any]]
) -> tuple[dict[int, tuple[str, str | None]], list[str]]:
    """Rules touching the seeded types: ({rule id: (child, parent)}, problems)."""
    code_of = {row.id: code for code, row in types.items()}
    ids = list(code_of) or [0]
    rows = _rows(
        connection,
        "SELECT id, child_type_id, parent_type_id, created_by_user_id FROM org_unit_type_rule "
        "WHERE child_type_id IN :ids OR parent_type_id IN :ids",
        ids=ids,
    )
    expected = set(PARENT_RULES)
    owned: dict[int, tuple[str, str | None]] = {}
    problems = []
    for row in rows:
        child = code_of.get(row.child_type_id)
        parent = code_of.get(row.parent_type_id) if row.parent_type_id is not None else None
        pair = (child, parent)
        known_parent = row.parent_type_id is None or row.parent_type_id in code_of
        seeded = known_parent and row.created_by_user_id is None
        if child is not None and seeded and pair in expected:
            owned[row.id] = (child, parent)
        else:
            problems.append(f"org_unit_type_rule {row.id} is not a seeded rule")
    missing = expected - set(owned.values())
    if missing:
        problems.append(f"seeded parent rules missing: {sorted(missing, key=str)}")
    return owned, problems


def baseline_problems(connection: sa.Connection) -> list[str]:
    """Differences between the database and the exact seeded baseline (empty = intact)."""
    problems: list[str] = []
    types = _seeded_types(connection)
    for public_id, code, name, sort_order, description in UNIT_TYPES:
        row = types.get(code)
        if row is None:
            problems.append(f"seeded unit type {code} ({public_id}) is missing")
            continue
        expected = {
            "code": code,
            "name": name,
            "description": description,
            "sort_order": sort_order,
            "allows_employee_assignment": 1,
            "is_active": 1,
            "parent_rule_mode": "advisory",
            "version": 1,
            "created_by_user_id": None,
            "updated_by_user_id": None,
        }
        changed = sorted(k for k, v in expected.items() if getattr(row, k) != v)
        if changed:
            problems.append(f"seeded unit type {code} was modified ({', '.join(changed)})")
    function_type = types.get(FUNCTION_TYPE_CODE)
    units = _seeded_units(connection)
    for public_id, code, name in FUNCTIONS:
        row = units.get(code)
        if row is None:
            problems.append(f"seeded function {code} ({public_id}) is missing")
            continue
        expected = {
            "code": code,
            "name": name,
            "short_name": None,
            "unit_type_id": function_type.id if function_type is not None else -1,
            "location_id": None,
            "effective_from": None,
            "effective_to": None,
            "external_ref": None,
            "version": 1,
            "created_by_user_id": None,
            "updated_by_user_id": None,
        }
        changed = sorted(k for k, v in expected.items() if getattr(row, k) != v)
        if changed:
            problems.append(
                f"seeded function {code} ({public_id}) was modified ({', '.join(changed)})"
            )
    _, rule_problems = _seeded_rules(connection, types)
    problems.extend(rule_problems)
    return problems


def foreign_references(
    connection: sa.Connection,
    table: str,
    ids: Iterable[int],
    allowed: dict[tuple[str, str], set[int]],
) -> list[str]:
    """Rows in ANY table whose foreign key points at ``table.id`` in ``ids``.

    ``allowed`` maps (referencing table, column) to the referencing row ids that are
    themselves migration-owned and will be removed. Every other reference is reported.
    """
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
        exempt = sorted(allowed.get((ref_table, ref_column), set())) or [0]
        sql = f"SELECT COUNT(*) FROM `{ref_table}` WHERE `{ref_column}` IN :ids"  # noqa: S608
        if (ref_table, ref_column) in allowed:
            sql += " AND id NOT IN :exempt"
            count = _rows(connection, sql, ids=id_list, exempt=exempt)[0][0]
        else:
            count = _rows(connection, sql, ids=id_list)[0][0]
        if count:
            found.append(f"{count} row(s) in {ref_table}.{ref_column} refer to seeded {table} rows")
    return found


def downgrade() -> None:
    """Remove the seeded baseline - only if it is exactly as seeded and unreferenced."""
    if context.is_offline_mode():
        raise RuntimeError(
            "Revision 0005 cannot be downgraded in offline (--sql) mode: it must first "
            "verify the live database."
        )
    connection = op.get_bind()
    problems = baseline_problems(connection)
    types = _seeded_types(connection)
    units = _seeded_units(connection)
    rules, _ = _seeded_rules(connection, types)
    unit_ids = {row.id for row in units.values()}
    type_ids = {row.id for row in types.values()}
    problems += foreign_references(connection, "org_unit", unit_ids, allowed={})
    problems += foreign_references(
        connection,
        "org_unit_type",
        type_ids,
        allowed={
            ("org_unit", "unit_type_id"): unit_ids,
            ("org_unit_type_rule", "child_type_id"): set(rules),
            ("org_unit_type_rule", "parent_type_id"): set(rules),
        },
    )
    if problems:
        raise RuntimeError(
            "Refusing to downgrade revision 0005 (organisation baseline); nothing was "
            "changed: " + "; ".join(problems) + ". Data created after the seed is never "
            "deleted by a migration."
        )

    expected_counts = (
        ("org_unit_type_rule", set(rules), len(PARENT_RULES)),
        ("org_unit", unit_ids, len(FUNCTIONS)),
        ("org_unit_type", type_ids, len(UNIT_TYPES)),
    )
    for table, ids, expected in expected_counts:
        statement = sa.text(f"DELETE FROM `{table}` WHERE id IN :ids").bindparams(  # noqa: S608
            sa.bindparam("ids", expanding=True)
        )
        deleted = connection.execute(statement, {"ids": sorted(ids)}).rowcount
        if deleted != expected:
            raise RuntimeError(
                f"Revision 0005 downgrade deleted {deleted} {table} rows, expected {expected}."
            )
