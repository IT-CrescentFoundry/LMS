"""Database infrastructure tests. No test connects to a real MySQL server."""

from collections.abc import Callable

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import Column, ForeignKey, Integer, MetaData, String, Table, create_engine
from sqlalchemy.dialects import mysql
from sqlalchemy.schema import CreateTable

from app.api.deps import DbSessionDep
from app.db.base import NAMING_CONVENTION, Base
from app.db.session import Database, DatabaseNotConfiguredError, create_mysql_engine
from app.main import create_app
from tests.conftest import DUMMY_DB, SettingsFactory


def test_base_metadata_uses_naming_convention() -> None:
    assert Base.metadata.naming_convention == NAMING_CONVENTION


STAGE_B_TABLES = {
    "user_account",
    "access_permission",
    "access_role",
    "access_role_permission",
    "user_access_role",
    "user_session",
    "login_throttle",
    "audit_event",
}
STAGE_C1_TABLES = {
    "graph_lock",
    "location",
    "org_unit_type",
    "org_unit_type_translation",
    "org_unit_type_rule",
    "org_unit",
    "org_unit_translation",
    "org_unit_hierarchy",
    "job_family",
    "grade",
    "job_level",
    "designation",
    "designation_translation",
    "functional_role",
    "functional_role_translation",
    "designation_functional_role",
    "responsibility",
    "responsibility_translation",
}
STAGE_C3_TABLES = {
    "employee",
    "employee_assignment",
    "employee_functional_role",
    "employee_responsibility",
    "reporting_relationship_type",
    "reporting_relationship_type_translation",
    "reporting_relationship",
}


def test_models_define_only_the_tables_of_completed_stages() -> None:
    import app.models  # noqa: F401

    assert set(Base.metadata.tables) == STAGE_B_TABLES | STAGE_C1_TABLES | STAGE_C3_TABLES
    # Competency and proficiency data belong to Stage F, not to C3.
    for fragment in ("competenc", "proficien"):
        assert not any(fragment in name for name in Base.metadata.tables), fragment


def test_naming_convention_produces_deterministic_names() -> None:
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
    Table("org_unit_type", metadata, Column("id", Integer, primary_key=True))
    unit = Table(
        "org_unit",
        metadata,
        Column("id", Integer, primary_key=True),
        Column("code", String(50), nullable=False, unique=True),
        Column("type_id", ForeignKey("org_unit_type.id"), nullable=False, index=True),
    )

    ddl = str(CreateTable(unit).compile(dialect=mysql.dialect()))

    assert "CONSTRAINT pk_org_unit PRIMARY KEY" in ddl
    assert "CONSTRAINT uq_org_unit_code UNIQUE" in ddl
    assert "CONSTRAINT fk_org_unit_type_id_org_unit_type FOREIGN KEY" in ddl
    assert {index.name for index in unit.indexes} == {"ix_org_unit_type_id"}


def test_unconfigured_database_raises_on_use() -> None:
    database = Database(None)

    assert database.is_configured is False
    with pytest.raises(DatabaseNotConfiguredError):
        database.session()
    with pytest.raises(DatabaseNotConfiguredError):
        database.ping()
    database.dispose()  # must be a safe no-op


def test_from_settings_without_database_settings(make_settings: SettingsFactory) -> None:
    assert Database.from_settings(make_settings()).is_configured is False


def test_engine_uses_pymysql_and_does_not_connect_on_creation(
    make_settings: SettingsFactory,
) -> None:
    # Creating the engine must not open a connection (the dummy port is closed).
    engine = create_mysql_engine(make_settings(**DUMMY_DB))

    assert engine.dialect.name == "mysql"
    assert engine.dialect.driver == "pymysql"
    assert engine.url.query["charset"] == "utf8mb4"
    engine.dispose()


def test_create_engine_without_settings_raises(make_settings: SettingsFactory) -> None:
    with pytest.raises(DatabaseNotConfiguredError):
        create_mysql_engine(make_settings())


def test_ping_and_session_with_an_explicit_engine() -> None:
    """Exercises Database mechanics with an explicitly supplied in-memory engine.

    This is test-only wiring; the application itself never falls back to SQLite.
    """
    database = Database(create_engine("sqlite://"))

    database.ping()
    with database.session() as session:
        assert session.bind is database.engine
    database.dispose()


def _app_with_session_route(make_settings: SettingsFactory) -> FastAPI:
    app = create_app(make_settings())

    @app.get("/api/v1/_test/session")
    def uses_session(session: DbSessionDep) -> dict[str, bool]:
        return {"active": session.is_active}

    return app


def test_session_dependency_returns_503_when_not_configured(
    make_settings: SettingsFactory,
) -> None:
    with TestClient(_app_with_session_route(make_settings)) as client:
        response = client.get("/api/v1/_test/session")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"


def test_session_dependency_yields_session_when_configured(
    make_settings: SettingsFactory,
) -> None:
    app = _app_with_session_route(make_settings)
    app.state.database = Database(create_engine("sqlite://"))

    with TestClient(app) as client:
        response = client.get("/api/v1/_test/session")

    assert response.status_code == 200
    assert response.json() == {"active": True}


def test_app_starts_and_stays_live_when_database_is_unreachable(
    make_client: Callable[..., TestClient],
) -> None:
    # Startup must not require a database connection; only readiness reflects it.
    client = make_client(**DUMMY_DB)

    assert client.get("/api/v1/health/live").status_code == 200
    assert client.get("/api/v1/health/ready").status_code == 503
