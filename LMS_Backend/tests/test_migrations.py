"""Alembic infrastructure tests. These never connect to a database."""

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from app.core import config as app_config
from app.core.config import BACKEND_DIR
from tests.conftest import DUMMY_DB, SettingsFactory


def _alembic_config() -> Config:
    return Config(str(BACKEND_DIR / "alembic.ini"))


def test_alembic_config_does_not_contain_a_database_url() -> None:
    assert _alembic_config().get_main_option("sqlalchemy.url") is None


def test_stage_a_has_no_migrations() -> None:
    script = ScriptDirectory.from_config(_alembic_config())

    assert script.get_heads() == []


def test_alembic_refuses_to_run_without_database_settings(
    monkeypatch: pytest.MonkeyPatch, make_settings: SettingsFactory
) -> None:
    monkeypatch.setattr(app_config, "get_settings", lambda: make_settings())

    with pytest.raises(RuntimeError, match="will not fall back"):
        command.upgrade(_alembic_config(), "head", sql=True)


def test_alembic_offline_mode_runs_against_mysql_dialect_without_connecting(
    monkeypatch: pytest.MonkeyPatch,
    make_settings: SettingsFactory,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # DUMMY_DB points at a closed port: any connection attempt would fail.
    monkeypatch.setattr(app_config, "get_settings", lambda: make_settings(**DUMMY_DB))

    command.upgrade(_alembic_config(), "head", sql=True)

    captured = capsys.readouterr()
    assert "Context impl MySQLImpl" in captured.err
    assert "Generating static SQL" in captured.err
    # Stage A has no revisions, so no DDL is produced.
    assert "CREATE TABLE" not in captured.out


def test_alembic_refuses_production_online_migration_without_opt_in(
    monkeypatch: pytest.MonkeyPatch, make_settings: SettingsFactory
) -> None:
    monkeypatch.setattr(
        app_config, "get_settings", lambda: make_settings(environment="production", **DUMMY_DB)
    )

    with pytest.raises(RuntimeError, match="allow_production=true"):
        command.upgrade(_alembic_config(), "head")
