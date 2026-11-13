"""Regression: the real CLI migration path (env.py settings path) must commit its work.

The test harness applies migrations through an injected connection inside
``engine.begin()``, which commits. ``python -m alembic ...`` instead goes through
env.py's own connection. A defect there once left the final ``alembic_version``
update uncommitted: MySQL DDL commits implicitly, so tables and triggers were
created, but the last revision bump (DML after the last DDL) was rolled back.

This test drives that exact path against the TEST database only.
"""

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from pydantic import SecretStr
from sqlalchemy import Engine, text

from app.core import config as app_config
from app.core.config import BACKEND_DIR, Settings
from app.db.session import create_mysql_engine
from tests.conftest import BASE_TEST_SETTINGS
from tests.support.database import IntegrationDatabaseSettings, assert_connected_to

pytestmark = pytest.mark.db


def _cli_settings(integration: IntegrationDatabaseSettings, database_name: str) -> Settings:
    password = integration.password
    assert password is not None
    return Settings(
        _env_file=None,
        **BASE_TEST_SETTINGS,
        db_host=integration.host,
        db_port=integration.port,
        db_name=database_name,
        # Runtime credentials are never used by Alembic; placeholders keep the
        # "migration account must differ from runtime account" rule satisfied.
        db_user="runtime_placeholder",
        db_password=SecretStr("not-used-by-alembic"),
        migration_db_user=integration.user,
        migration_db_password=password,
    )


def _version_and_triggers(engine: Engine) -> tuple[list[str], int]:
    with engine.connect() as connection:  # fresh connection: sees committed state only
        version = list(
            connection.execute(text("SELECT version_num FROM alembic_version")).scalars()
        )
        triggers = connection.execute(
            text(
                "SELECT COUNT(*) FROM information_schema.TRIGGERS "
                "WHERE TRIGGER_SCHEMA = DATABASE() AND EVENT_OBJECT_TABLE = 'audit_event'"
            )
        ).scalar_one()
    return version, int(triggers)


def test_cli_migration_path_commits_every_revision(
    monkeypatch: pytest.MonkeyPatch,
    integration_settings: IntegrationDatabaseSettings,
    test_database_name: str,
    test_engine: Engine,
) -> None:
    settings = _cli_settings(integration_settings, test_database_name)
    # Pre-flight: env.py checks only DATABASE(); verify that these exact migration
    # credentials resolve to crescent_lms_test AS lms_test@127.0.0.1 before the CLI
    # path runs any DDL.
    preflight = create_mysql_engine(
        settings, url=settings.migration_database_url, use_null_pool=True
    )
    try:
        with preflight.connect() as connection:
            assert_connected_to(connection, test_database_name)
    finally:
        preflight.dispose()
    monkeypatch.setattr(app_config, "get_settings", lambda: settings)
    alembic_config = Config(str(BACKEND_DIR / "alembic.ini"))
    head = ScriptDirectory.from_config(alembic_config).get_current_head()
    assert _version_and_triggers(test_engine) == ([head], 2)

    # Downgrade the last revision through the CLI path: drops the triggers and
    # must COMMIT the version change as well.
    command.downgrade(alembic_config, "-1")
    previous, triggers = _version_and_triggers(test_engine)
    assert triggers == 0
    assert previous != [head], "downgrade did not commit its alembic_version change"

    # Upgrade back to head through the CLI path.
    command.upgrade(alembic_config, "head")
    assert _version_and_triggers(test_engine) == ([head], 2), (
        "upgrade did not commit the final alembic_version change"
    )
