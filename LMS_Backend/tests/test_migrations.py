"""Alembic infrastructure tests. These never connect to a database."""

from typing import Any

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

import app.db.session as session_module
from app.core import config as app_config
from app.core.config import BACKEND_DIR
from tests.conftest import DUMMY_DB, DUMMY_MIGRATION, SettingsFactory


def _alembic_config() -> Config:
    return Config(str(BACKEND_DIR / "alembic.ini"))


def test_alembic_config_does_not_contain_a_database_url() -> None:
    assert _alembic_config().get_main_option("sqlalchemy.url") is None


def test_migration_history_has_a_single_head() -> None:
    script = ScriptDirectory.from_config(_alembic_config())

    assert len(script.get_heads()) <= 1


def test_alembic_refuses_to_run_without_database_settings(
    monkeypatch: pytest.MonkeyPatch, make_settings: SettingsFactory
) -> None:
    monkeypatch.setattr(app_config, "get_settings", lambda: make_settings())

    with pytest.raises(RuntimeError, match="will not fall back"):
        command.upgrade(_alembic_config(), "head", sql=True)


def test_alembic_refuses_to_use_the_runtime_account(
    monkeypatch: pytest.MonkeyPatch, make_settings: SettingsFactory
) -> None:
    # Runtime credentials present, migration credentials absent.
    monkeypatch.setattr(app_config, "get_settings", lambda: make_settings(**DUMMY_DB))

    with pytest.raises(RuntimeError, match="never uses the application runtime account"):
        command.upgrade(_alembic_config(), "head")
    with pytest.raises(RuntimeError, match="LMS_MIGRATION_DB_USER"):
        command.upgrade(_alembic_config(), "head", sql=True)


def test_online_migrations_connect_with_the_migration_account(
    monkeypatch: pytest.MonkeyPatch, make_settings: SettingsFactory
) -> None:
    settings = make_settings(**DUMMY_DB, **DUMMY_MIGRATION)
    monkeypatch.setattr(app_config, "get_settings", lambda: settings)
    captured: dict[str, Any] = {}

    class _StopBeforeConnectingError(Exception):
        pass

    def fake_engine(*_args: Any, **kwargs: Any) -> None:
        captured.update(kwargs)
        raise _StopBeforeConnectingError

    monkeypatch.setattr(session_module, "create_mysql_engine", fake_engine)

    with pytest.raises(_StopBeforeConnectingError):
        command.upgrade(_alembic_config(), "head")

    url = captured["url"]
    assert url.username == DUMMY_MIGRATION["migration_db_user"]
    assert url.username != DUMMY_DB["db_user"]
    assert url.database == DUMMY_DB["db_name"]
    assert captured["use_null_pool"] is True


def test_alembic_offline_mode_runs_against_mysql_dialect_without_connecting(
    monkeypatch: pytest.MonkeyPatch,
    make_settings: SettingsFactory,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # DUMMY_DB points at a closed port: any connection attempt would fail.
    monkeypatch.setattr(
        app_config, "get_settings", lambda: make_settings(**DUMMY_DB, **DUMMY_MIGRATION)
    )

    command.upgrade(_alembic_config(), "head", sql=True)

    captured = capsys.readouterr()
    assert "Context impl MySQLImpl" in captured.err
    assert "Generating static SQL" in captured.err


def test_alembic_refuses_production_online_migration_without_opt_in(
    monkeypatch: pytest.MonkeyPatch, make_settings: SettingsFactory
) -> None:
    production = make_settings(
        environment="production",
        session_cookie_secure=True,
        trusted_origins=["https://lms.example.test"],
        **DUMMY_DB,
        **DUMMY_MIGRATION,
    )
    monkeypatch.setattr(app_config, "get_settings", lambda: production)

    with pytest.raises(RuntimeError, match="allow_production=true"):
        command.upgrade(_alembic_config(), "head")
