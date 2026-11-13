"""Configuration tests: database boundaries, blank handling, security settings."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from app.core.config import ConfigurationError, Environment, Settings, load_settings
from tests.conftest import (
    DUMMY_DB,
    DUMMY_MIGRATION,
    TEST_ORIGIN,
    TEST_SECRET_KEY,
    SettingsFactory,
)

REQUIRED_ENV = {"LMS_SECRET_KEY": TEST_SECRET_KEY, "LMS_TRUSTED_ORIGINS": TEST_ORIGIN}


def _set_env(monkeypatch: pytest.MonkeyPatch, values: dict[str, str]) -> None:
    for key, value in values.items():
        monkeypatch.setenv(key, value)


# --- Defaults and runtime database -------------------------------------------


def test_defaults_without_database(make_settings: SettingsFactory) -> None:
    settings = make_settings()

    assert settings.api_v1_prefix == "/api/v1"
    assert settings.database_configured is False
    assert settings.database_url is None
    assert settings.migration_database_url is None
    assert settings.cors_allowed_origins == []


def test_complete_database_settings_build_a_mysql_url(make_settings: SettingsFactory) -> None:
    settings = make_settings(**DUMMY_DB)

    url = settings.database_url
    assert url is not None
    assert url.drivername == "mysql+pymysql"
    assert url.host == "127.0.0.1"
    assert url.database == "lms_test_dummy"
    assert url.username == "lms_test_user"
    assert url.query["charset"] == "utf8mb4"
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


# --- Migration credentials -----------------------------------------------------


def test_migration_url_uses_migration_account_on_the_same_database(
    make_settings: SettingsFactory,
) -> None:
    settings = make_settings(**DUMMY_DB, **DUMMY_MIGRATION)

    runtime = settings.database_url
    migration = settings.migration_database_url
    assert runtime is not None and migration is not None
    assert runtime.username == "lms_test_user"
    assert migration.username == "lms_test_migrator"
    assert (migration.host, migration.port, migration.database) == (
        runtime.host,
        runtime.port,
        runtime.database,
    )
    assert migration.password == DUMMY_MIGRATION["migration_db_password"]
    assert DUMMY_MIGRATION["migration_db_password"] not in str(migration)
    assert DUMMY_MIGRATION["migration_db_password"] not in repr(settings)


def test_migration_password_special_characters_are_escaped(
    make_settings: SettingsFactory,
) -> None:
    settings = make_settings(
        **DUMMY_DB, migration_db_user="lms_migrator", migration_db_password="m!g@r:t/r#$%"
    )

    url = settings.migration_database_url
    assert url is not None
    assert url.password == "m!g@r:t/r#$%"


def test_migration_credentials_are_optional_for_the_runtime(
    make_settings: SettingsFactory,
) -> None:
    settings = make_settings(**DUMMY_DB)

    assert settings.database_url is not None
    assert settings.migration_configured is False
    assert settings.migration_database_url is None


@pytest.mark.parametrize(
    "partial",
    [{"migration_db_user": "lms_migrator"}, {"migration_db_password": "secret-value"}],
)
def test_partial_migration_credentials_are_rejected(
    make_settings: SettingsFactory, partial: dict[str, str]
) -> None:
    with pytest.raises(ValidationError, match="Migration database settings are incomplete"):
        make_settings(**DUMMY_DB, **partial)


@pytest.mark.parametrize("same_user", ["lms_test_user", "LMS_TEST_USER", " lms_test_user "])
def test_migration_account_must_differ_from_runtime_account(
    make_settings: SettingsFactory, same_user: str
) -> None:
    with pytest.raises(ValidationError, match="must never be the application runtime account"):
        make_settings(
            **DUMMY_DB, migration_db_user=same_user, migration_db_password="other-password"
        )


def test_migration_credentials_require_database_location(make_settings: SettingsFactory) -> None:
    with pytest.raises(ValidationError, match="require the database location"):
        make_settings(**DUMMY_MIGRATION)


# --- Blank environment values ----------------------------------------------------


def test_blank_optional_environment_values_use_defaults(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_env(monkeypatch, REQUIRED_ENV)
    _set_env(
        monkeypatch,
        {
            "LMS_ENABLE_API_DOCS": "",
            "LMS_DB_PORT": "",
            "LMS_SESSION_IDLE_TIMEOUT_MINUTES": "",
            "LMS_LOG_LEVEL": "",
            "LMS_CORS_ALLOWED_ORIGINS": "",
            "LMS_MIGRATION_DB_USER": "",
            "LMS_MIGRATION_DB_PASSWORD": "",
        },
    )

    settings = Settings(_env_file=None)

    assert settings.enable_api_docs is None
    assert settings.db_port == 3306
    assert settings.session_idle_timeout_minutes == 30
    assert settings.log_level == "INFO"
    assert settings.cors_allowed_origins == []
    assert settings.migration_configured is False


def test_blank_values_in_env_file_use_defaults(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        f"LMS_SECRET_KEY={TEST_SECRET_KEY}\nLMS_TRUSTED_ORIGINS={TEST_ORIGIN}\n"
        "LMS_ENABLE_API_DOCS=\nLMS_DB_PORT=\nLMS_DB_HOST=\nLMS_LOG_LEVEL=ERROR\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert settings.enable_api_docs is None
    assert settings.db_port == 3306
    assert settings.database_configured is False
    assert settings.log_level == "ERROR"


@pytest.mark.parametrize("missing", ["LMS_SECRET_KEY", "LMS_TRUSTED_ORIGINS"])
def test_blank_required_setting_gives_explicit_error(
    monkeypatch: pytest.MonkeyPatch, missing: str
) -> None:
    _set_env(monkeypatch, {**REQUIRED_ENV, missing: ""})

    with pytest.raises(ConfigurationError) as excinfo:
        load_settings(_env_file=None)

    assert f"{missing} is required." in str(excinfo.value)


def test_configuration_errors_never_contain_values(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_env(
        monkeypatch,
        {
            "LMS_SECRET_KEY": "too-short-secret-VALUE",
            "LMS_TRUSTED_ORIGINS": TEST_ORIGIN,
            "LMS_DB_HOST": "127.0.0.1",
            "LMS_DB_PASSWORD": "visible-db-PASSWORD",
        },
    )

    with pytest.raises(ConfigurationError) as excinfo:
        load_settings(_env_file=None)

    message = str(excinfo.value)
    assert "LMS_SECRET_KEY" in message
    assert "at least 32 characters" in message
    assert "too-short-secret-VALUE" not in message
    assert "visible-db-PASSWORD" not in message
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__suppress_context__ is True


# --- Security settings ------------------------------------------------------------


@pytest.mark.parametrize("origins", [[], ["*"], ["http://localhost:5173/"]])
def test_invalid_trusted_origins_are_rejected(
    make_settings: SettingsFactory, origins: list[str]
) -> None:
    with pytest.raises(ValidationError):
        make_settings(trusted_origins=origins)


def test_trusted_origins_parse_comma_separated_values(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_env(
        monkeypatch,
        {
            "LMS_SECRET_KEY": TEST_SECRET_KEY,
            "LMS_TRUSTED_ORIGINS": "http://localhost:5173, http://127.0.0.1:5173",
        },
    )

    settings = Settings(_env_file=None)

    assert settings.trusted_origins == ["http://localhost:5173", "http://127.0.0.1:5173"]


def test_session_cookie_name_depends_on_secure_flag(make_settings: SettingsFactory) -> None:
    assert make_settings(session_cookie_secure=True).session_cookie_name == "__Host-lms_session"
    assert make_settings(session_cookie_secure=False).session_cookie_name == "lms_session"


def test_production_requires_a_database(make_settings: SettingsFactory) -> None:
    with pytest.raises(ValidationError, match="required in the production environment"):
        make_settings(
            environment="production",
            session_cookie_secure=True,
            trusted_origins=["https://lms.example.test"],
        )


def test_production_requires_secure_cookies(make_settings: SettingsFactory) -> None:
    with pytest.raises(ValidationError, match="LMS_SESSION_COOKIE_SECURE must be true"):
        make_settings(
            environment="production",
            session_cookie_secure=False,
            trusted_origins=["https://lms.example.test"],
            **DUMMY_DB,
        )


def test_production_requires_https_trusted_origins(make_settings: SettingsFactory) -> None:
    with pytest.raises(ValidationError, match="must use https"):
        make_settings(
            environment="production",
            session_cookie_secure=True,
            trusted_origins=["http://lms.example.test"],
            **DUMMY_DB,
        )


def test_api_docs_disabled_by_default_in_production(make_settings: SettingsFactory) -> None:
    production = {
        "environment": "production",
        "session_cookie_secure": True,
        "trusted_origins": ["https://lms.example.test"],
        **DUMMY_DB,
    }
    assert make_settings(environment="development").api_docs_enabled is True
    assert make_settings(**production).api_docs_enabled is False
    assert make_settings(**production, enable_api_docs=True).api_docs_enabled is True


# --- Environment isolation ------------------------------------------------------


def test_environment_variables_with_lms_prefix_are_read(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_env(monkeypatch, REQUIRED_ENV)
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
    _set_env(monkeypatch, REQUIRED_ENV)
    monkeypatch.setenv("DATABASE_URL", "mysql+pymysql://pms:secret@pms-host/pms")
    monkeypatch.setenv("DB_HOST", "pms-host")
    monkeypatch.setenv("DB_NAME", "pms")
    monkeypatch.setenv("MYSQL_PASSWORD", "secret")
    monkeypatch.setenv("MIGRATION_DB_USER", "root")

    settings = Settings(_env_file=None)

    assert settings.database_configured is False
    assert settings.database_url is None
    assert settings.migration_database_url is None


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
