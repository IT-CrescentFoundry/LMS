"""Liveness and readiness logic.

* Liveness answers "is the process running and able to serve HTTP?" and never
  touches external dependencies, so a database outage cannot cause the process
  to be restarted needlessly.
* Readiness answers "can this instance do useful work?" and checks the
  dependencies the LMS needs (currently the database).
"""

import logging
import time
from datetime import UTC, datetime

from app import __version__
from app.db.session import Database
from app.schemas.health import (
    CheckStatus,
    ComponentCheck,
    LivenessResponse,
    ReadinessResponse,
)

logger = logging.getLogger(__name__)

SERVICE_NAME = "crescent-lms-api"


def get_liveness() -> LivenessResponse:
    return LivenessResponse(service=SERVICE_NAME, version=__version__, timestamp=datetime.now(UTC))


def check_database(database: Database) -> ComponentCheck:
    if not database.is_configured:
        return ComponentCheck(
            status=CheckStatus.NOT_CONFIGURED,
            detail="The LMS database connection has not been configured.",
        )
    started = time.perf_counter()
    try:
        database.ping()
    except Exception:
        # Full error (driver message, host) goes to the server log only.
        logger.warning("database readiness check failed", exc_info=True)
        return ComponentCheck(
            status=CheckStatus.UNAVAILABLE,
            detail="The LMS database could not be reached.",
            duration_ms=_elapsed_ms(started),
        )
    return ComponentCheck(status=CheckStatus.OK, duration_ms=_elapsed_ms(started))


def get_readiness(database: Database) -> ReadinessResponse:
    checks = {"database": check_database(database)}
    ready = all(check.status is CheckStatus.OK for check in checks.values())
    return ReadinessResponse(
        status="ready" if ready else "not_ready",
        checks=checks,
        timestamp=datetime.now(UTC),
    )


def _elapsed_ms(started: float) -> float:
    return round((time.perf_counter() - started) * 1000, 2)
