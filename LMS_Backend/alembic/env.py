"""Alembic migration environment for the Crescent Foundry LMS.

Safety rules enforced here:

* The database URL comes only from the LMS settings (``LMS_DB_*``). There is no
  fallback: missing settings stop the migration with a clear error.
* Online migrations against an environment configured as ``production`` require
  an explicit opt-in: ``python -m alembic -x allow_production=true upgrade head``.
  Offline SQL generation (``--sql``) never connects and is always allowed.
"""

from logging.config import fileConfig

from alembic import context

import app.models  # noqa: F401  (registers every model on Base.metadata)
from app.core import config as app_config
from app.db.base import Base
from app.db.session import create_mysql_engine

alembic_config = context.config
if alembic_config.config_file_name is not None:
    fileConfig(alembic_config.config_file_name, disable_existing_loggers=False)

target_metadata = Base.metadata


def _load_settings() -> app_config.Settings:
    settings = app_config.get_settings()
    if settings.database_url is None:
        raise RuntimeError(
            "The LMS database is not configured. Set LMS_DB_HOST, LMS_DB_NAME, "
            "LMS_DB_USER and LMS_DB_PASSWORD (see LMS_Backend/.env.example). "
            "Alembic will not fall back to any other database."
        )
    return settings


def run_migrations_offline() -> None:
    """Emit SQL to stdout without connecting to the database."""
    settings = _load_settings()
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    settings = _load_settings()
    if settings.environment is app_config.Environment.PRODUCTION:
        x_args = context.get_x_argument(as_dictionary=True)
        if x_args.get("allow_production", "").lower() != "true":
            raise RuntimeError(
                "Refusing to migrate a production database without explicit approval. "
                "Take a backup, then re-run with: -x allow_production=true"
            )

    engine = create_mysql_engine(settings, use_null_pool=True)
    with engine.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
