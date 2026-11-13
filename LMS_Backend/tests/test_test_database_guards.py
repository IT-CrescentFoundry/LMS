"""The integration-test database guards must make the development database unreachable."""

import re
from pathlib import Path
from typing import Any

import pytest

from tests.support.database import (
    IntegrationDatabaseSettings,
    UnsafeTestDatabaseError,
    assert_connected_to,
    assert_safe_test_target,
    development_database_name,
)

VALID: dict[str, Any] = {
    "host": "127.0.0.1",
    "port": 3306,
    "name": "crescent_lms_test",
    "user": "lms_test",
    "password": "not-a-real-password",
}


def _settings(**overrides: Any) -> IntegrationDatabaseSettings:
    return IntegrationDatabaseSettings(_env_file=None, **{**VALID, **overrides})


def test_valid_test_database_is_accepted() -> None:
    assert assert_safe_test_target(_settings(), "crescent_lms_dev") == "crescent_lms_test"


@pytest.mark.parametrize("name", ["crescent_lms_dev", "crescent_lms", "test_lms", "lms_testing"])
def test_names_not_ending_in_test_are_refused(name: str) -> None:
    with pytest.raises(UnsafeTestDatabaseError, match="must end with '_test'"):
        assert_safe_test_target(_settings(name=name), None)


def test_development_database_name_is_refused_even_if_it_ends_in_test() -> None:
    with pytest.raises(UnsafeTestDatabaseError, match="development database"):
        assert_safe_test_target(_settings(name="shared_test"), "SHARED_TEST")


def test_incomplete_configuration_is_refused() -> None:
    with pytest.raises(UnsafeTestDatabaseError, match="LMS_TEST_DB_PASSWORD"):
        assert_safe_test_target(_settings(password=None), None)


@pytest.mark.parametrize("name", ["other_lms_test", "crescent_lms_test2_test", "Crescent_lms_test"])
def test_only_crescent_lms_test_is_accepted(name: str) -> None:
    with pytest.raises(UnsafeTestDatabaseError, match="may only target 'crescent_lms_test'"):
        assert_safe_test_target(_settings(name=name), "crescent_lms_dev")


@pytest.mark.parametrize("user", ["lms_app", "lms_migrator", "root", "LMS_TEST"])
def test_only_the_lms_test_account_is_accepted(user: str) -> None:
    with pytest.raises(UnsafeTestDatabaseError, match="only 'lms_test' may perform"):
        assert_safe_test_target(_settings(user=user), "crescent_lms_dev")


def test_test_settings_ignore_application_database_variables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LMS_DB_NAME", "crescent_lms_dev")
    monkeypatch.setenv("LMS_DB_USER", "lms_app")

    settings = IntegrationDatabaseSettings(_env_file=None)

    assert settings.configured is False


def test_development_database_name_from_environment_or_env_file(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("LMS_DB_NAME=crescent_lms_dev\nLMS_DB_PASSWORD=x\n", encoding="utf-8")

    assert development_database_name(env_file) == "crescent_lms_dev"
    monkeypatch.setenv("LMS_DB_NAME", "from_environment")
    assert development_database_name(env_file) == "from_environment"
    monkeypatch.delenv("LMS_DB_NAME")
    assert development_database_name(tmp_path / "missing.env") is None


class _FakeResult:
    def __init__(self, row: tuple[str, str]) -> None:
        self._row = row

    def one(self) -> tuple[str, str]:
        return self._row


class _FakeConnection:
    def __init__(self, database: str, account: str = "lms_test@127.0.0.1") -> None:
        self._row = (database, account)

    def execute(self, _statement: object) -> _FakeResult:
        return _FakeResult(self._row)


def test_post_connect_check_rejects_a_different_database() -> None:
    with pytest.raises(UnsafeTestDatabaseError, match="expected the test database"):
        assert_connected_to(_FakeConnection("crescent_lms_dev"), "crescent_lms_test")  # type: ignore[arg-type]

    assert_connected_to(_FakeConnection("crescent_lms_test"), "crescent_lms_test")  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "account",
    [
        "lms_app@127.0.0.1",
        "lms_migrator@127.0.0.1",
        "lms_test@%",
        "lms_test@localhost",
        "root@localhost",
    ],
)
def test_post_connect_check_rejects_an_unexpected_mysql_account(account: str) -> None:
    expected = re.escape("automated tests may only use 'lms_test@127.0.0.1'")
    with pytest.raises(UnsafeTestDatabaseError, match=expected):
        assert_connected_to(_FakeConnection("crescent_lms_test", account), "crescent_lms_test")  # type: ignore[arg-type]


def test_post_connect_check_refuses_any_other_expected_database() -> None:
    with pytest.raises(UnsafeTestDatabaseError, match="may only target 'crescent_lms_test'"):
        assert_connected_to(_FakeConnection("other_test"), "other_test")  # type: ignore[arg-type]
