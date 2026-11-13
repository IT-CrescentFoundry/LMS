"""Configuration and safety guards for the dedicated automated-test database.

Integration tests run **only** against the database configured with the
``LMS_TEST_DB_*`` variables (normally in ``LMS_Backend/.env.test``). Before any
statement is executed the target is checked:

1. all five settings are present;
2. the database name ends with ``_test``;
3. the name differs from the development database name (``LMS_DB_NAME``);
4. the name is exactly ``crescent_lms_test`` and the configured user is ``lms_test``;
5. immediately after connecting, ``SELECT DATABASE(), CURRENT_USER()`` must return
   exactly ``crescent_lms_test`` and ``lms_test@127.0.0.1`` - on every connection,
   before any query, migration, reset or DDL.

Any failure aborts with :class:`UnsafeTestDatabaseError`. These settings are never
read by the application itself.
"""

import os
import re
from pathlib import Path

from dotenv import dotenv_values
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy import Connection, text
from sqlalchemy.engine import URL

from app.core.config import BACKEND_DIR, ENV_FILE, MYSQL_CHARSET, MYSQL_DRIVER

TEST_ENV_FILE = BACKEND_DIR / ".env.test"
_SAFE_TEST_DATABASE_NAME = re.compile(r"^[A-Za-z0-9_]+_test$")

# The only database and MySQL account automated tests may ever use. Allowing any
# other target requires a reviewed change here.
REQUIRED_TEST_DATABASE_NAME = "crescent_lms_test"
REQUIRED_TEST_DATABASE_USER = "lms_test"
REQUIRED_TEST_ACCOUNT = "lms_test@127.0.0.1"


class UnsafeTestDatabaseError(RuntimeError):
    """The configured test database failed a safety check."""


class IntegrationDatabaseSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_prefix="LMS_TEST_DB_",
        env_file=TEST_ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore",
        frozen=True,
    )

    host: str | None = None
    port: int = Field(default=3306, ge=1, le=65535)
    name: str | None = None
    user: str | None = None
    password: SecretStr | None = None

    @property
    def configured(self) -> bool:
        return None not in (self.host, self.name, self.user, self.password)

    def url(self) -> URL:
        if not self.configured or self.password is None:
            raise UnsafeTestDatabaseError("The test database is not fully configured.")
        return URL.create(
            drivername=MYSQL_DRIVER,
            username=self.user,
            password=self.password.get_secret_value(),
            host=self.host,
            port=self.port,
            database=self.name,
            query={"charset": MYSQL_CHARSET},
        )


def development_database_name(env_file: Path = ENV_FILE) -> str | None:
    """``LMS_DB_NAME`` from the environment or the developer ``.env`` (nothing else is read)."""
    from_environment = os.environ.get("LMS_DB_NAME", "").strip()
    if from_environment:
        return from_environment
    if env_file.exists():
        value = dotenv_values(env_file).get("LMS_DB_NAME") or ""
        return value.strip() or None
    return None


def assert_safe_test_target(
    settings: IntegrationDatabaseSettings, development_name: str | None
) -> str:
    """Validate the configured target before connecting. Returns the database name."""
    if not settings.configured or settings.name is None:
        raise UnsafeTestDatabaseError(
            "Set LMS_TEST_DB_HOST, LMS_TEST_DB_NAME, LMS_TEST_DB_USER and "
            "LMS_TEST_DB_PASSWORD (see LMS_Backend/.env.test.example)."
        )
    name = settings.name.strip()
    if not _SAFE_TEST_DATABASE_NAME.fullmatch(name):
        raise UnsafeTestDatabaseError(
            f"Refusing to run automated tests against {name!r}: "
            "the test database name must end with '_test'."
        )
    if development_name and name.casefold() == development_name.strip().casefold():
        raise UnsafeTestDatabaseError(
            f"Refusing to run automated tests against {name!r}: "
            "it is the development database (LMS_DB_NAME)."
        )
    if name != REQUIRED_TEST_DATABASE_NAME:
        raise UnsafeTestDatabaseError(
            f"Refusing to run automated tests against {name!r}: automated database "
            f"tests may only target {REQUIRED_TEST_DATABASE_NAME!r}."
        )
    if (settings.user or "").strip() != REQUIRED_TEST_DATABASE_USER:
        raise UnsafeTestDatabaseError(
            "Refusing to run automated tests with the configured account: only "
            f"{REQUIRED_TEST_DATABASE_USER!r} may perform automated database operations."
        )
    return name


def assert_connected_to(connection: Connection, expected_name: str) -> None:
    """Confirm the server-side database AND MySQL account right after connecting.

    Call before any other statement on the connection. Raises before anything
    else is executed when either value is unexpected.
    """
    if expected_name != REQUIRED_TEST_DATABASE_NAME:
        raise UnsafeTestDatabaseError(
            f"Refusing to use {expected_name!r}: automated database tests may only "
            f"target {REQUIRED_TEST_DATABASE_NAME!r}."
        )
    database, account = connection.execute(text("SELECT DATABASE(), CURRENT_USER()")).one()
    if database != expected_name:
        raise UnsafeTestDatabaseError(
            f"Connected to {database!r} but expected the test database {expected_name!r}."
        )
    if account != REQUIRED_TEST_ACCOUNT:
        raise UnsafeTestDatabaseError(
            f"Connected as MySQL account {account!r}, but automated tests may only use "
            f"{REQUIRED_TEST_ACCOUNT!r}."
        )
