"""Environment-based application configuration.

All settings are read from environment variables prefixed with ``LMS_`` (and from
``LMS_Backend/.env`` when present). The prefix is deliberate: generic variables such
as ``DB_HOST`` or ``DATABASE_URL`` that other systems on the same machine (for
example the PMS) might define are never picked up by the LMS.

Blank values (``LMS_X=``) are treated exactly like absent values, so optional
settings fall back to their defaults and required settings produce an explicit
"is required" error rather than a confusing parsing error.

Database credentials are split by purpose:

* ``LMS_DB_USER`` / ``LMS_DB_PASSWORD`` — the restricted runtime account (DML only).
* ``LMS_MIGRATION_DB_USER`` / ``LMS_MIGRATION_DB_PASSWORD`` — the schema-migration
  account used only by Alembic. It must never be the runtime account.

There is intentionally no default database and no fallback database.
"""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, ValidationError, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import URL

BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"
ENV_PREFIX = "LMS_"

MYSQL_DRIVER = "mysql+pymysql"
MYSQL_CHARSET = "utf8mb4"  # Required for Bengali, Hindi and Gujarati text.

MIN_SECRET_KEY_LENGTH = 32
SESSION_COOKIE_BASENAME = "lms_session"

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LogFormat = Literal["json", "console"]
SameSitePolicy = Literal["lax", "strict"]


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


class ConfigurationError(RuntimeError):
    """Raised when settings are missing or invalid. Messages never contain values."""


_REQUIRED_DB_FIELDS = ("db_host", "db_name", "db_user", "db_password")
_MIGRATION_DB_FIELDS = ("migration_db_user", "migration_db_password")


def env_var_name(field_name: str) -> str:
    return f"{ENV_PREFIX}{field_name.upper()}"


def parse_origin_list(value: Any) -> Any:
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    return value


def validate_origin_list(origins: list[str]) -> list[str]:
    for origin in origins:
        if origin == "*":
            raise ValueError("wildcard origins are not permitted; list explicit origins")
        parts = urlsplit(origin)
        if (
            parts.scheme not in {"http", "https"}
            or not parts.netloc
            or parts.path
            or parts.query
            or parts.fragment
        ):
            raise ValueError(
                f"invalid origin {origin!r}; expected scheme://host[:port] with no path"
            )
    return origins


class Settings(BaseSettings):
    """Validated application settings. Instances are immutable."""

    model_config = SettingsConfigDict(
        env_prefix=ENV_PREFIX,
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        case_sensitive=False,
        extra="ignore",
        frozen=True,
    )

    # --- Application -------------------------------------------------------
    app_name: str = "Crescent Foundry LMS API"
    environment: Environment = Environment.DEVELOPMENT
    api_v1_prefix: str = "/api/v1"
    enable_api_docs: bool | None = Field(
        default=None,
        description="Interactive API docs. Defaults to enabled outside production.",
    )

    # --- Logging -----------------------------------------------------------
    log_level: LogLevel = "INFO"
    log_format: LogFormat = "json"

    # --- Browser security ----------------------------------------------------
    # Origins allowed to make cross-origin browser requests (CORS). Only needed
    # when the frontend is served from a different origin than the API.
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)
    # Origins allowed to send state-changing requests (CSRF origin check).
    # Required: with no trusted origin, nobody could sign in.
    trusted_origins: Annotated[list[str], NoDecode]
    # Server-side secret for HMAC-derived values (CSRF tokens, throttle keys).
    secret_key: SecretStr

    # --- Sessions -------------------------------------------------------------
    session_cookie_secure: bool = True
    session_cookie_samesite: SameSitePolicy = "lax"
    session_idle_timeout_minutes: int = Field(default=30, ge=5, le=480)
    session_absolute_timeout_hours: int = Field(default=12, ge=1, le=72)

    # --- Passwords and login throttling --------------------------------------
    password_min_length: int = Field(default=12, ge=10, le=64)
    login_max_failures_per_identifier: int = Field(default=5, ge=1, le=100)
    login_max_failures_per_ip: int = Field(default=20, ge=1, le=10_000)
    login_failure_window_minutes: int = Field(default=15, ge=1, le=1440)
    login_lockout_minutes: int = Field(default=15, ge=1, le=1440)

    # --- Business calendar ---------------------------------------------------
    # Effective dates (organisation changes, assignments) are business dates. "Today"
    # for as-of queries is computed with this fixed UTC offset; default IST (+05:30).
    # A fixed offset avoids a runtime time-zone database dependency.
    business_utc_offset_minutes: int = Field(default=330, ge=-720, le=840)

    # --- Database: runtime account (dedicated LMS MySQL 8 database) --------
    db_host: str | None = None
    db_port: int = Field(default=3306, ge=1, le=65535)
    db_name: str | None = None
    db_user: str | None = None
    db_password: SecretStr | None = None
    db_connect_timeout_seconds: int = Field(default=5, ge=1, le=60)
    db_query_timeout_seconds: int = Field(default=30, ge=1, le=3600)
    db_pool_size: int = Field(default=5, ge=1, le=100)
    db_max_overflow: int = Field(default=10, ge=0, le=100)
    # Recycle connections well before MySQL's wait_timeout closes them.
    db_pool_recycle_seconds: int = Field(default=1800, ge=60)
    db_echo_sql: bool = False

    # --- Database: migration account (Alembic only) ---------------------------
    migration_db_user: str | None = None
    migration_db_password: SecretStr | None = None

    # --- Validators ----------------------------------------------------------
    @field_validator(
        "db_host",
        "db_name",
        "db_user",
        "db_password",
        "migration_db_user",
        "migration_db_password",
        mode="before",
    )
    @classmethod
    def _blank_is_unset(cls, value: Any) -> Any:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("api_v1_prefix")
    @classmethod
    def _validate_prefix(cls, value: str) -> str:
        if not value.startswith("/") or value.endswith("/") or " " in value:
            raise ValueError("must start with '/', must not end with '/' and contain no spaces")
        return value

    @field_validator("cors_allowed_origins", "trusted_origins", mode="before")
    @classmethod
    def _parse_origins(cls, value: Any) -> Any:
        return parse_origin_list(value)

    @field_validator("cors_allowed_origins")
    @classmethod
    def _validate_cors_origins(cls, origins: list[str]) -> list[str]:
        return validate_origin_list(origins)

    @field_validator("trusted_origins")
    @classmethod
    def _validate_trusted_origins(cls, origins: list[str]) -> list[str]:
        if not origins:
            raise ValueError("at least one trusted origin is required")
        return validate_origin_list(origins)

    @field_validator("secret_key")
    @classmethod
    def _validate_secret_key(cls, value: SecretStr) -> SecretStr:
        if len(value.get_secret_value().strip()) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(f"must be at least {MIN_SECRET_KEY_LENGTH} characters long")
        return value

    @model_validator(mode="after")
    def _validate_cross_field_rules(self) -> "Settings":
        provided = [name for name in _REQUIRED_DB_FIELDS if getattr(self, name) is not None]
        if provided and len(provided) != len(_REQUIRED_DB_FIELDS):
            missing = [env_var_name(n) for n in _REQUIRED_DB_FIELDS if n not in provided]
            raise ValueError(
                "Database settings are incomplete. Missing: "
                + ", ".join(missing)
                + ". Either provide all database settings or none."
            )

        migration = [name for name in _MIGRATION_DB_FIELDS if getattr(self, name) is not None]
        if migration and len(migration) != len(_MIGRATION_DB_FIELDS):
            missing = [env_var_name(n) for n in _MIGRATION_DB_FIELDS if n not in migration]
            raise ValueError(
                "Migration database settings are incomplete. Missing: " + ", ".join(missing) + "."
            )
        if migration and not provided:
            raise ValueError(
                "Migration credentials require the database location settings "
                "(LMS_DB_HOST, LMS_DB_NAME, LMS_DB_USER, LMS_DB_PASSWORD)."
            )
        if (
            self.migration_db_user is not None
            and self.db_user is not None
            and self.migration_db_user.strip().casefold() == self.db_user.strip().casefold()
        ):
            raise ValueError(
                "LMS_MIGRATION_DB_USER must differ from LMS_DB_USER: the migration "
                "account must never be the application runtime account."
            )

        if self.environment is Environment.PRODUCTION:
            if not provided:
                raise ValueError("Database settings are required in the production environment.")
            if not self.session_cookie_secure:
                raise ValueError("LMS_SESSION_COOKIE_SECURE must be true in production.")
            if any(not origin.startswith("https://") for origin in self.trusted_origins):
                raise ValueError("LMS_TRUSTED_ORIGINS must use https:// in production.")
        return self

    # --- Derived values ------------------------------------------------------
    @property
    def database_configured(self) -> bool:
        return self.db_host is not None

    @property
    def database_url(self) -> URL | None:
        """Runtime SQLAlchemy URL, or ``None`` when not configured.

        ``URL.create`` escapes special characters in credentials; converting a URL
        to a string renders the password as ``***``.
        """
        if not self.database_configured or self.db_password is None:
            return None
        return self._mysql_url(self.db_user, self.db_password)

    @property
    def migration_configured(self) -> bool:
        return self.database_configured and self.migration_db_user is not None

    @property
    def migration_database_url(self) -> URL | None:
        """Migration SQLAlchemy URL (same database, migration account), or ``None``."""
        if not self.migration_configured or self.migration_db_password is None:
            return None
        return self._mysql_url(self.migration_db_user, self.migration_db_password)

    def _mysql_url(self, user: str | None, password: SecretStr) -> URL:
        return URL.create(
            drivername=MYSQL_DRIVER,
            username=user,
            password=password.get_secret_value(),
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
            query={"charset": MYSQL_CHARSET},
        )

    @property
    def api_docs_enabled(self) -> bool:
        if self.enable_api_docs is not None:
            return self.enable_api_docs
        return self.environment is not Environment.PRODUCTION

    @property
    def session_cookie_name(self) -> str:
        # The __Host- prefix makes browsers enforce Secure, Path=/ and no Domain.
        prefix = "__Host-" if self.session_cookie_secure else ""
        return f"{prefix}{SESSION_COOKIE_BASENAME}"


def describe_validation_error(exc: ValidationError) -> str:
    """Readable, value-free summary of a settings ValidationError."""
    lines: list[str] = []
    for error in exc.errors(include_input=False, include_url=False):
        location = [str(part) for part in error.get("loc", ())]
        message = str(error.get("msg", "invalid value")).removeprefix("Value error, ")
        if not location:
            lines.append(message)
        elif error.get("type") == "missing":
            lines.append(f"{env_var_name(location[0])} is required.")
        else:
            lines.append(f"{env_var_name(location[0])}: {message}")
    return "Invalid LMS configuration:\n  - " + "\n  - ".join(lines)


def load_settings(**overrides: Any) -> Settings:
    """Create Settings, converting validation failures into ConfigurationError."""
    try:
        return Settings(**overrides)
    except ValidationError as exc:
        # `from None`: the original error could echo input values.
        raise ConfigurationError(describe_validation_error(exc)) from None


@lru_cache
def get_settings() -> Settings:
    """Process-wide settings, loaded once from the environment."""
    return load_settings()
