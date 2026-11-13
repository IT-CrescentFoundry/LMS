"""Administrative command-line interface.

Usage (from LMS_Backend, virtual environment active)::

    python -m app.cli create-super-admin --login-id <ID> --display-name "<Name>" [--email <addr>]
    python -m app.cli grant-super-admin  --login-id <ID>
    python -m app.cli revoke-super-admin --login-id <ID>

Safety measures:

* The target host/database is shown and must be confirmed by typing its name.
* Passwords are read with ``getpass`` (no echo) and never printed or logged.
* An interactive terminal is required; passwords cannot be piped in.
* Uses the restricted runtime account (``LMS_DB_USER``); never the migration account.
"""

import argparse
import getpass
import sys
from collections.abc import Callable, Sequence

from app.core.config import ConfigurationError, Settings, get_settings
from app.db.session import Database
from app.db.types import utcnow
from app.services.identity import bootstrap

InputFn = Callable[[str], str]
PasswordFn = Callable[[str], str]


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.cli", description="Crescent Foundry LMS administrative commands."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create-super-admin", help="Create the first Super Admin.")
    create.add_argument("--login-id", required=True)
    create.add_argument("--display-name", required=True)
    create.add_argument("--email", default=None)

    for name, help_text in (
        ("grant-super-admin", "Grant Super Admin to an existing active account."),
        ("revoke-super-admin", "Revoke Super Admin (never the last one)."),
    ):
        command = commands.add_parser(name, help=help_text)
        command.add_argument("--login-id", required=True)
    return parser


def _confirm_target(settings: Settings, input_fn: InputFn) -> bool:
    print(
        f"Target database: {settings.db_name} on {settings.db_host}:{settings.db_port} "
        f"(environment: {settings.environment.value}, account: {settings.db_user})"
    )
    answer = input_fn("Type the database name to confirm: ").strip()
    return answer == settings.db_name


def _read_new_password(password_fn: PasswordFn) -> str | None:
    first = password_fn("New Super Admin password: ")
    second = password_fn("Repeat password: ")
    if first != second:
        print("The passwords do not match.", file=sys.stderr)
        return None
    return first


def main(
    argv: Sequence[str] | None = None,
    *,
    database: Database | None = None,
    settings: Settings | None = None,
    input_fn: InputFn = input,
    password_fn: PasswordFn = getpass.getpass,
    is_interactive: Callable[[], bool] = lambda: sys.stdin.isatty(),
    operator: str | None = None,
) -> int:
    args = _parser().parse_args(argv)
    if not is_interactive():
        print("This command must be run from an interactive terminal.", file=sys.stderr)
        return 2
    try:
        settings = settings or get_settings()
    except ConfigurationError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if not settings.database_configured:
        print("The LMS database is not configured (LMS_DB_*).", file=sys.stderr)
        return 2
    if not _confirm_target(settings, input_fn):
        print("Cancelled: the database name did not match.", file=sys.stderr)
        return 1

    operator = operator or getpass.getuser()
    database = database or Database.from_settings(settings)
    session = database.session()
    try:
        if args.command == "create-super-admin":
            password = _read_new_password(password_fn)
            if password is None:
                return 1
            account = bootstrap.create_initial_super_admin(
                session,
                settings,
                login_id=args.login_id,
                display_name=args.display_name,
                email=args.email,
                password=password,
                operator=operator,
                now=utcnow(),
            )
            print(f"Created Super Admin '{account.login_id}'.")
        elif args.command == "grant-super-admin":
            account = bootstrap.grant_super_admin(
                session, login_id=args.login_id, operator=operator, now=utcnow()
            )
            print(f"Granted Super Admin to '{account.login_id}'.")
        else:
            account = bootstrap.revoke_super_admin(
                session, login_id=args.login_id, operator=operator, now=utcnow()
            )
            print(f"Revoked Super Admin from '{account.login_id}'.")
        return 0
    except bootstrap.BootstrapError as exc:
        print(f"Refused: {exc}", file=sys.stderr)
        return 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
