"""Non-interactive scheduled jobs (run by an operating-system scheduler).

Usage (from LMS_Backend, virtual environment active)::

    python -m app.jobs training-reminders [--dry-run]

``training-reminders`` creates every in-app training reminder that has fallen due
(``LMS_TRAINING_REMINDER_OFFSETS_DAYS`` before each scheduled session) for all
participants, so reminders exist even for people who have not signed in. It is
idempotent - each reminder has a unique de-duplication key - so running it every
15 minutes, re-running it after a failure, or running it while users also open their
notification centre never produces duplicates. Cancelled or postponed events,
cancelled sessions, withdrawn participants and past sessions never get reminders; a
rescheduled session gets reminders for its new start time only.

Exit codes: 0 success; 1 failure (nothing committed - the next run retries);
2 configuration missing; 3 database not yet migrated to revision 0011.

Safety: uses the restricted runtime account (``LMS_DB_USER``), never the migration
account; writes only ``notification`` rows; ``--dry-run`` counts what would be created
and rolls back. No external message (e-mail, Outlook, Teams) is sent.

Windows Task Scheduler example (every 15 minutes)::

    Program:   <repo>\\LMS_Backend\\.venv\\Scripts\\python.exe
    Arguments: -m app.jobs training-reminders
    Start in:  <repo>\\LMS_Backend
"""

import argparse
import logging
import sys
from collections.abc import Sequence

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import ConfigurationError, Settings, get_settings
from app.db.session import Database
from app.services import notifications

REQUIRED_REVISION = 11
logger = logging.getLogger("app.jobs")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.jobs", description="Crescent Foundry LMS scheduled jobs."
    )
    commands = parser.add_subparsers(dest="command", required=True)
    reminders = commands.add_parser(
        "training-reminders", help="Create due in-app training reminders (idempotent)."
    )
    reminders.add_argument(
        "--dry-run", action="store_true", help="Count due reminders, then roll back."
    )
    return parser


def main(
    argv: Sequence[str] | None = None,
    *,
    database: Database | None = None,
    settings: Settings | None = None,
) -> int:
    args = _parser().parse_args(argv)
    try:
        settings = settings or get_settings()
    except ConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if database is None and not settings.database_configured:
        print("The LMS database is not configured (LMS_DB_*).", file=sys.stderr)
        return 2
    database = database or Database.from_settings(settings)
    session = database.session()
    try:
        try:
            current = session.execute(text("SELECT version_num FROM alembic_version")).scalar()
        except SQLAlchemyError:
            session.rollback()
            current = None
        if current is None or not str(current).isdigit() or int(current) < REQUIRED_REVISION:
            print(
                f"Refused: the database is at revision {current}; training reminders need "
                "migration 0011, which has not been applied.",
                file=sys.stderr,
            )
            return 3
        created = notifications.generate_due_reminders(
            session, offsets=settings.reminder_offsets, settings=settings
        )
        if args.dry_run:
            session.rollback()
            print(f"Dry run: {created} reminder(s) would be created (nothing saved).")
        else:
            session.commit()
            print(f"Created {created} reminder(s).")
        return 0
    except Exception:
        session.rollback()
        logger.exception("training reminder job failed; nothing was committed")
        print("Failed: nothing was committed; the next run will retry.", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
