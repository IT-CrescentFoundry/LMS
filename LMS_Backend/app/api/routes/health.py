"""Health-check endpoints used by load balancers, monitoring and the frontend."""

from fastapi import APIRouter, Response, status

from app.api.deps import DatabaseDep
from app.schemas.health import LivenessResponse, ReadinessResponse
from app.services import health_service

router = APIRouter(prefix="/health", tags=["health"])


@router.get(
    "/live",
    response_model=LivenessResponse,
    summary="Liveness probe",
    description="Reports that the API process is running. Does not check dependencies.",
)
async def liveness() -> LivenessResponse:
    return health_service.get_liveness()


@router.get(
    "/ready",
    response_model=ReadinessResponse,
    summary="Readiness probe",
    description=(
        "Reports whether the API can serve requests that need its dependencies. "
        "Returns 200 when ready and 503 when any check fails."
    ),
    responses={status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ReadinessResponse}},
)
def readiness(database: DatabaseDep, response: Response) -> ReadinessResponse:
    # Synchronous on purpose: the database ping blocks, so FastAPI runs it in
    # the thread pool instead of on the event loop.
    report = health_service.get_readiness(database)
    if report.status != "ready":
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return report
