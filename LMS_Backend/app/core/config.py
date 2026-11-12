"""Environment-based application configuration.

All settings are read from environment variables prefixed with ``LMS_`` (and from
``LMS_Backend/.env`` when present). The prefix is deliberate: generic variables such
as ``DB_HOST`` or ``DATABASE_URL`` that other systems on the same machine (for
example the PMS) might define are never picked up by the LMS.

There is intentionally no default database. When the database settings are absent
the application still starts (so the liveness probe works) but reports itself as
not ready. A *partially* configured database is treated as a configuration error.
"""

from enum import StrEnum
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any, Literal
from urllib.parse import urlsplit

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict
from sqlalchemy.engine import URL

BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"

MYSQL_DRIVER = "mysql+pymysql"
MYSQL_CHARSET = "utf8mb4"  # Required for Bengali, Hindi and Gujarati text.

LogLevel = Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
LogFormat = Literal["json", "console"]


class Environment(StrEnum):
    DEVELOPMENT = "development"
    TEST = "test"
    STAGING = "staging"
    PRODUCTION = "production"


_REQUIRED_DB_FIELDS = ("db_host", "db_name", "db_user", "db_password")


class Settings(BaseSettings):
    """Validated application settings. Instances are immutable."""

    model_config = SettingsConfigDict(
        env_prefix="LMS_",
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
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

    # --- CORS --------------------------------------------------------------
    # Only needed when the frontend is served from a different origin than the
    # API. The recommended deployment is same-origin (see docs/architecture).
    cors_allowed_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    # --- Database (dedicated LMS MySQL 8 database) -------------------------
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

    # --- Validators ----------------------------------------------------------
    @field_validator("db_host", "db_name", "db_user", "db_password", mode="before")
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

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _parse_origins(cls, value: Any) -> Any:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("cors_allowed_origins")
    @classmethod
    def _validate_origins(cls, origins: list[str]) -> list[str]:
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

    @model_validator(mode="after")
    def _validate_database_settings(self) -> "Settings":
        provided = [name for name in _REQUIRED_DB_FIELDS if getattr(self, name) is not None]
        if provided and len(provided) != len(_REQUIRED_DB_FIELDS):
            missing = [
                f"LMS_{name.upper()}" for name in _REQUIRED_DB_FIELDS if name not in provided
            ]
            raise ValueError(
                "Database settings are incomplete. Missing: "
                + ", ".join(missing)
                + ". Either provide all database settings or none."
            )
        if self.environment is Environment.PRODUCTION and not provided:
            raise ValueError("Database settings are required in the production environment.")
        return self

    # --- Derived values ------------------------------------------------------
    @property
    def database_configured(self) -> bool:
        return self.db_host is not None

    @property
    def database_url(self) -> URL | None:
        """SQLAlchemy URL for the LMS database, or ``None`` when not configured.

        ``URL`` objects escape special characters in credentials and render the
        password as ``***`` when converted to a string.
        """
        if not self.database_configured or self.db_password is None:
            return None
        return URL.create(
            drivername=MYSQL_DRIVER,
            username=self.db_user,
            password=self.db_password.get_secret_value(),
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


@lru_cache
def get_settings() -> Settings:
    """Process-wide settings, loaded once from the environment."""
    return Settings()
