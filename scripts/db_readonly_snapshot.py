"""Read-only snapshot of the configured LMS database (for migration before/after checks).

Usage (PowerShell, from LMS_Backend):

    $Before = 'C:\\LMS_Backups\\before_0011.json'
    .venv\\Scripts\\python ..\\scripts\\db_readonly_snapshot.py |
        Out-File -Encoding utf8 -NoClobber $Before
    .venv\\Scripts\\python ..\\scripts\\db_readonly_snapshot.py --compare $Before

Do not use ``>``: in Windows PowerShell 5.1 it writes UTF-16, which ``--compare`` cannot read.
``Out-File -Encoding utf8`` writes UTF-8 with a BOM, which ``--compare`` accepts (utf-8-sig).

Connects with the restricted RUNTIME account (LMS_DB_*, SELECT/INSERT/UPDATE/DELETE
only) inside ``START TRANSACTION READ ONLY`` and issues SELECT / CHECKSUM TABLE
statements only, then rolls back. Prints: database name, MySQL version, Alembic
revision, base-table count, foreign-key count, trigger names, per-table row counts and
CHECKSUM TABLE values, the 0011 permission codes and their role grants. Never prints
credentials. With ``--compare`` it reports what changed against an earlier snapshot.

Note: MySQL lists triggers in information_schema only for accounts holding the TRIGGER
privilege. The runtime account deliberately lacks it, so ``triggers`` is empty here even
though migration 0003's audit triggers exist; check triggers with the migration account
(``SHOW TRIGGERS``) if needed.
"""

import argparse
import json
import os
import sys
from typing import Any

sys.path.insert(0, os.getcwd())  # run from LMS_Backend

from sqlalchemy import bindparam, create_engine, text

from app.core.config import Settings

NEW_0011_PERMISSIONS = (
    "training.records.view",
    "competency.view",
    "competency.manage",
    "competency.assess",
    "imports.organisation.run",
    "imports.organisation.commit",
)


def snapshot() -> dict[str, Any]:
    settings = Settings()
    if settings.database_url is None:
        raise SystemExit("LMS_DB_* is not configured.")
    engine = create_engine(settings.database_url)
    with engine.connect() as c:
        c.execute(text("START TRANSACTION READ ONLY"))
        name, version = c.execute(text("SELECT DATABASE(), VERSION()")).one()
        tables = [
            r[0]
            for r in c.execute(
                text(
                    "SELECT table_name FROM information_schema.tables "
                    "WHERE table_schema = DATABASE() AND table_type = 'BASE TABLE' "
                    "ORDER BY table_name"
                )
            )
        ]
        counts = {
            # table names come from information_schema, not from user input
            t: int(c.execute(text(f"SELECT COUNT(*) FROM `{t}`")).scalar() or 0)  # noqa: S608
            for t in tables
        }
        checksums = {
            str(r[0]).split(".")[-1]: r[1]
            for r in c.execute(text("CHECKSUM TABLE " + ", ".join(f"`{t}`" for t in tables)))
        }
        fks = c.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.referential_constraints "
                "WHERE constraint_schema = DATABASE()"
            )
        ).scalar()
        triggers = sorted(
            r[0]
            for r in c.execute(
                text(
                    "SELECT trigger_name FROM information_schema.triggers "
                    "WHERE trigger_schema = DATABASE()"
                )
            )
        )
        revision = c.execute(text("SELECT version_num FROM alembic_version")).scalar()
        grants = [
            f"{r[0]}:{r[1]}"
            for r in c.execute(
                text(
                    "SELECT r.code, p.code FROM access_role_permission m "
                    "JOIN access_role r ON r.id = m.access_role_id "
                    "JOIN access_permission p ON p.id = m.access_permission_id "
                    "WHERE p.code IN :codes ORDER BY r.code, p.code"
                ).bindparams(bindparam("codes", expanding=True)),
                {"codes": list(NEW_0011_PERMISSIONS)},
            )
        ]
        c.execute(text("ROLLBACK"))
    return {
        "database": name,
        "mysql_version": version,
        "alembic_revision": revision,
        "table_count": len(tables),
        "foreign_key_count": int(fks or 0),
        "triggers": triggers,
        "row_counts": counts,
        "checksums": checksums,
        "grants_0011": grants,
    }


def compare(before: dict[str, Any], after: dict[str, Any]) -> list[str]:
    lines = [
        f"database: {after['database']}",
        f"revision: {before['alembic_revision']} -> {after['alembic_revision']}",
        f"tables: {before['table_count']} -> {after['table_count']}",
        f"foreign keys: {before['foreign_key_count']} -> {after['foreign_key_count']}",
        f"triggers unchanged: {before['triggers'] == after['triggers']}",
        f"0011 grants now: {len(after['grants_0011'])}",
    ]
    added = sorted(set(after["row_counts"]) - set(before["row_counts"]))
    removed = sorted(set(before["row_counts"]) - set(after["row_counts"]))
    lines.append(f"tables added ({len(added)}): {', '.join(added) or '-'}")
    lines.append(f"tables removed ({len(removed)}): {', '.join(removed) or '-'}")
    for table in sorted(set(before["row_counts"]) & set(after["row_counts"])):
        b, a = before["row_counts"][table], after["row_counts"][table]
        same_sum = before["checksums"].get(table) == after["checksums"].get(table)
        if b != a or not same_sum:
            lines.append(f"CHANGED {table}: rows {b} -> {a}, checksum same: {same_sum}")
    return lines


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--compare", help="earlier snapshot JSON file to compare against")
    args = parser.parse_args()
    current = snapshot()
    if args.compare:
        with open(args.compare, encoding="utf-8-sig") as handle:
            before = json.load(handle)
        print("\n".join(compare(before, current)))
    else:
        print(json.dumps(current, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
