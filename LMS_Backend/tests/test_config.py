"""Configuration tests."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import Environment, Settings
from tests.conftest import DUMMY_DB, SettingsFactory


def test_defaults_without_database(make_settings: SettingsFactory) -> None:
    settings = make_settings()

    assert settings.api_v1_prefix == "/api/v1"
    assert settings.database_configured is False
    assert settings.database_url is None
    assert settings.cors_allowed_origins == []


def test_complete_database_settings_build_a_mysql_url(make_settings: SettingsFactory) -> None:
    settings = make_settings(**DUMMY_DB)

    url = settings.database_url
    assert url is not None
    assert url.drivername == "mysql+pymysql"
    assert url.host == "127.0.0.1"
    assert url.database == "lms_test_dummy"
    assert url.query["charset"] == "utf8mb4"
    # The password must never appear when the URL is rendered or logged.
    assert DUMMY_DB["db_password"] not in str(url)
    assert DUMMY_DB["db_password"] not in repr(settings)


def test_password_with_special_characters_is_escaped(make_settings: SettingsFactory) -> None:
    settings = make_settings(**{**DUMMY_DB, "db_password": "p@ss:w/rd#1"})

    url = settings.database_url
    assert url is not None
    assert url.password == "p@ss:w/rd#1"
    assert "p%40ss%3Aw%2Frd%231" in url.render_as_string(hide_password=False)


def test_partial_database_settings_are_rejected(make_settings: SettingsFactory) -> None:
    with pytest.raises(ValidationError) as excinfo:
        make_settings(db_host="127.0.0.1", db_name="lms_test_dummy")

    message = str(excinfo.value)
    assert "LMS_DB_USER" in message
    assert "LMS_DB_PASSWORD" in message


def test_blank_database_values_count_as_unset(make_settings: SettingsFactory) -> None:
    settings = make_settings(db_host="", db_name=" ", db_user="", db_password="")

    assert settings.database_configured is False


def test_production_requires_a_database(make_settings: SettingsFactory) -> None:
    with pytest.raises(ValidationError, match="required in the production environment"):
        make_settings(environment="production")


def test_api_docs_disabled_by_default_in_production(make_settings: SettingsFactory) -> None:
    assert make_settings(environment="development").api_docs_enabled is True
    production = make_settings(environment="production", **DUMMY_DB)
    assert production.api_docs_enabled is False
    overridden = make_settings(environment="production", enable_api_docs=True, **DUMMY_DB)
    assert overridden.api_docs_enabled is True


def test_environment_variables_with_lms_prefix_are_read(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LMS_ENVIRONMENT", "staging")
    monkeypatch.setenv("LMS_LOG_LEVEL", "WARNING")
    monkeypatch.setenv(
        "LMS_CORS_ALLOWED_ORIGINS", "http://localhost:5173, https://lms.example.test"
    )

    settings = Settings(_env_file=None)

    assert settings.environment is Environment.STAGING
    assert settings.log_level == "WARNING"
    assert settings.cors_allowed_origins == ["http://localhost:5173", "https://lms.example.test"]


def test_generic_database_variables_are_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    """Variables another system (e.g. the PMS) might define must not be used."""
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://pms:secret@pms-host/pms")
    monkeypatch.setenv("DB_HOST", "pms-host")
    monkeypatch.setenv("DB_NAME", "pms")
    monkeypatch.setenv("MYSQL_PASSWORD", "secret")

    settings = Settings(_env_file=None)

    assert settings.database_configured is False
    assert settings.database_url is None


def test_env_file_is_read_when_present(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("LMS_LOG_LEVEL=ERROR\nLMS_DB_HOST=\n", encoding="utf-8")

    settings = Settings(_env_file=env_file)

    assert settings.log_level == "ERROR"
    assert settings.database_configured is False


@pytest.mark.parametrize(
    "origin",
    ["*", "localhost:5173", "http://localhost:5173/", "http://localhost:5173/path", "ftp://x"],
)
def test_invalid_cors_origins_are_rejected(make_settings: SettingsFactory, origin: str) -> None:
    with pytest.raises(ValidationError):
        make_settings(cors_allowed_origins=[origin])


@pytest.mark.parametrize("prefix", ["api/v1", "/api/v1/", "/api v1"])
def test_invalid_api_prefix_is_rejected(make_settings: SettingsFactory, prefix: str) -> None:
    with pytest.raises(ValidationError):
        make_settings(api_v1_prefix=prefix)


def test_settings_are_immutable(make_settings: SettingsFactory) -> None:
    settings = make_settings()
    with pytest.raises(ValidationError):
        settings.environment = Environment.PRODUCTION  # type: ignore[misc]
