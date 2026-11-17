"""Concurrency: two simultaneous commits of the same import job (Stage D).

Commits take the ``imports`` graph lock, then the job row, and check the status inside
the transaction. The second commit therefore waits, sees the committed job and is
refused - the records are created exactly once.

These tests COMMIT (on crescent_lms_test only, as lms_test@127.0.0.1); the schema is
rebuilt afterwards. Synthetic data only.
"""

import threading
import uuid
from collections.abc import Iterator

import pytest
from sqlalchemy import Engine, func, select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.context import RequestMeta
from app.core.errors import AppError
from app.models.employees import Employee
from app.models.imports import ImportJob, RecordProvenance
from app.services.identity.access_control import load_permission_codes
from app.services.identity.context import Actor
from app.services.imports import jobs
from tests.integration.helpers import make_user
from tests.support.database import assert_connected_to
from tests.support.schema_reset import rebuild_test_schema
from tests.support.workbooks import standard

pytestmark = pytest.mark.db
META = RequestMeta(request_id="import-concurrency")


@pytest.fixture
def committing_engine(test_engine: Engine, test_database_name: str) -> Iterator[Engine]:
    try:
        yield test_engine
    finally:
        rebuild_test_schema(test_engine, test_database_name)


def _session(engine: Engine, name: str) -> Session:
    session = Session(bind=engine, autoflush=False, expire_on_commit=False)
    assert_connected_to(session.connection(), name)
    return session


def _ready_job(engine: Engine, name: str, settings: Settings) -> tuple[Actor, uuid.UUID]:
    with _session(engine, name) as db:
        admin = make_user(db, "race.import.admin", roles=("hr_admin",))
        actor = Actor(user_id=admin.id, permissions=load_permission_codes(db, admin.id))
        data = standard(
            employees=[
                [f"RACE-{n}", f"Race Person {n}", "Active", "2025-04-01", None]
                for n in range(1, 21)
            ]
        )
        job = jobs.upload(
            db,
            settings,
            actor=actor,
            meta=META,
            profile_code="employees",
            filename="race.xlsx",
            data=data,
        )
        db.commit()
        sections = [
            {k: m[k] for k in ("section", "sheet", "header_row", "columns")}
            for m in job.column_mapping or []
        ]
        jobs.set_mapping(
            db, settings, job, actor=actor, meta=META, version=job.version, sections=sections
        )
        db.commit()
        job = jobs.validate(db, settings, job, actor=actor, meta=META, version=job.version)
        db.commit()
        assert job.status == "ready_for_approval", job.summary
        return actor, job.public_id


def test_two_simultaneous_commits_create_the_records_once(
    committing_engine: Engine, test_database_name: str, app_settings: Settings
) -> None:
    actor, job_id = _ready_job(committing_engine, test_database_name, app_settings)
    with _session(committing_engine, test_database_name) as db:
        version = db.scalars(select(ImportJob.version).where(ImportJob.public_id == job_id)).one()
    barrier = threading.Barrier(2)
    outcomes: list[str] = []

    def commit() -> None:
        with _session(committing_engine, test_database_name) as db:
            barrier.wait()
            try:
                jobs.commit(
                    db,
                    app_settings,
                    job_id,
                    actor=actor,
                    meta=META,
                    version=version,
                    apply_updates=False,
                )
                db.commit()
                outcomes.append("committed")
            except AppError as error:
                db.rollback()
                outcomes.append(error.code)

    threads = [threading.Thread(target=commit) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert sorted(outcomes) in (
        ["committed", "import_not_ready"],
        ["committed", "version_conflict"],
    ), outcomes
    with _session(committing_engine, test_database_name) as db:
        assert (
            db.scalar(
                select(func.count())
                .select_from(Employee)
                .where(Employee.employee_code.like("RACE-%"))
            )
            == 20
        )
        assert db.scalar(select(func.count()).select_from(RecordProvenance)) == 20
        assert (
            db.scalars(select(ImportJob.status).where(ImportJob.public_id == job_id)).one()
            == "completed"
        )
