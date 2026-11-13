"""Engine and session management for the dedicated LMS MySQL database.

The application uses synchronous SQLAlchemy 2 with the PyMySQL driver. FastAPI
runs synchronous (``def``) endpoints in a worker thread pool, so blocking database
calls do not stall the event loop.

``Database`` wraps an optional engine: when database settings are absent the
object exists but is "not configured" - nothing silently falls back to another
database.
"""

from typing import Any

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import Settings


class DatabaseNotConfiguredError(RuntimeError):
    """Raised when database access is attempted without database settings."""

    def __init__(self) -> None:
        super().__init__(
            "The LMS database is not configured. Set LMS_DB_HOST, LMS_DB_NAME, "
            "LMS_DB_USER and LMS_DB_PASSWORD (see LMS_Backend/.env.example)."
        )


def create_mysql_engine(
    settings: Settings, *, url: URL | None = None, use_null_pool: bool = False
) -> Engine:
    """Create (but do not connect) an engine for the configured LMS database.

    ``url`` defaults to the runtime account. Alembic passes the migration URL so
    that both share the same timeouts, charset and UTC session time zone.
    """
    url = url if url is not None else settings.database_url
    if url is None:
        raise DatabaseNotConfiguredError()

    connect_args: dict[str, Any] = {
        "connect_timeout": settings.db_connect_timeout_seconds,
        "read_timeout": settings.db_query_timeout_seconds,
        "write_timeout": settings.db_query_timeout_seconds,
        # Store and compare all timestamps in UTC; convert for display only.
        "init_command": "SET time_zone = '+00:00'",
    }
    if use_null_pool:
        # Used for short-lived processes such as Alembic migrations.
        return create_engine(url, poolclass=NullPool, connect_args=connect_args)
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle_seconds,
        pool_timeout=settings.db_connect_timeout_seconds,
        connect_args=connect_args,
    )


class Database:
    """Holds the engine and session factory for the application's lifetime."""

    def __init__(self, engine: Engine | None) -> None:
        self._engine = engine
        self._session_factory: sessionmaker[Session] | None = (
            sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
            if engine is not None
            else None
        )

    @classmethod
    def from_settings(cls, settings: Settings) -> "Database":
        if not settings.database_configured:
            return cls(None)
        return cls(create_mysql_engine(settings))

    @property
    def is_configured(self) -> bool:
        return self._engine is not None

    @property
    def engine(self) -> Engine:
        if self._engine is None:
            raise DatabaseNotConfiguredError()
        return self._engine

    def session(self) -> Session:
        if self._session_factory is None:
            raise DatabaseNotConfiguredError()
        return self._session_factory()

    def ping(self) -> None:
        """Open a connection and run a trivial query. Raises on failure."""
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    def dispose(self) -> None:
        if self._engine is not None:
            self._engine.dispose()
