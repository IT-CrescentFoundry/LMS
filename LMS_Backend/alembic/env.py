"""Alembic migration environment for the Crescent Foundry LMS.

Safety rules enforced here:

* Migrations connect with the **migration account** only
  (``LMS_MIGRATION_DB_USER`` / ``LMS_MIGRATION_DB_PASSWORD``), never with the
  application runtime account. Missing migration credentials stop with an error.
* The database location comes only from the LMS settings (``LMS_DB_HOST``,
  ``LMS_DB_PORT``, ``LMS_DB_NAME``). There is no fallback database.
* After connecting, the server-reported ``DATABASE()`` must equal ``LMS_DB_NAME``.
* Online migrations against an environment configured as ``production`` require
  an explicit opt-in: ``python -m alembic -x allow_production=true upgrade head``.
* The automated test harness passes an already-verified connection to the
  dedicated test database through ``config.attributes["connection"]``.
"""

import logging
from logging.config import fileConfig
from typing import Any, Literal

from alembic import context
from alembic.autogenerate.api import AutogenContext
from sqlalchemy import Connection, text

import app.models  # noqa: F401  (registers every model on Base.metadata)
from app.core import config as app_config
from app.db.base import Base
from app.db.session import create_mysql_engine
from app.db.types import UTCDateTime, UUIDBinary

alembic_config = context.config
# The test harness keeps its own logging configuration (pytest log capture).
if alembic_config.config_file_name is not None and "connection" not in alembic_config.attributes:
    fileConfig(alembic_config.config_file_name, disable_existing_loggers=False)

logger = logging.getLogger("alembic.env")
target_metadata = Base.metadata


def _load_settings() -> app_config.Settings:
    settings = app_config.get_settings()
    if settings.database_url is None:
        raise RuntimeError(
            "The LMS database is not configured. Set LMS_DB_HOST, LMS_DB_NAME, "
            "LMS_DB_USER and LMS_DB_PASSWORD (see LMS_Backend/.env.example). "
            "Alembic will not fall back to any other database."
        )
    if settings.migration_database_url is None:
        raise RuntimeError(
            "Migration credentials are not configured. Set LMS_MIGRATION_DB_USER and "
            "LMS_MIGRATION_DB_PASSWORD. Alembic never uses the application runtime "
            "account (LMS_DB_USER)."
        )
    return settings


def render_item(type_: str, obj: Any, autogen_context: AutogenContext) -> str | Literal[False]:
    """Render project column types as plain MySQL types in generated migrations.

    Migrations must stay valid even if application code changes later, so they
    must not import ``app.db.types``.
    """
    if type_ == "type" and isinstance(obj, UTCDateTime | UUIDBinary):
        autogen_context.imports.add("from sqlalchemy.dialects import mysql")
        if isinstance(obj, UTCDateTime):
            return "mysql.DATETIME(fsp=6)"
        return "mysql.BINARY(length=16)"
    return False


def _run(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        render_item=render_item,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting to the database."""
    settings = _load_settings()
    context.configure(
        url=settings.migration_database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    injected = alembic_config.attributes.get("connection")
    if injected is not None:
        # Test harness: the target database was verified before this call.
        _run(injected)
        return

    settings = _load_settings()
    if settings.environment is app_config.Environment.PRODUCTION:
        x_args = context.get_x_argument(as_dictionary=True)
        if x_args.get("allow_production", "").lower() != "true":
            raise RuntimeError(
                "Refusing to migrate a production database without explicit approval. "
                "Take a backup, then re-run with: -x allow_production=true"
            )

    engine = create_mysql_engine(settings, url=settings.migration_database_url, use_null_pool=True)
    try:
        with engine.connect() as connection:
            database, current_user = connection.execute(
                text("SELECT DATABASE(), CURRENT_USER()")
            ).one()
            if database != settings.db_name:
                raise RuntimeError(
                    f"Connected to database {database!r}, but LMS_DB_NAME is "
                    f"{settings.db_name!r}. Refusing to migrate."
                )
            logger.info("Connected to database %s as %s", database, current_user)
            # End the transaction that the check above auto-began (SQLAlchemy 2.x).
            # Otherwise Alembic treats the connection as externally managed and never
            # commits: MySQL DDL commits implicitly, but the final alembic_version
            # update (DML after the last DDL) would be rolled back on close.
            connection.commit()
            _run(connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
