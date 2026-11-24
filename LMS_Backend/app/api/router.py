"""Central API router. Every feature router is registered here, under the API version prefix."""

from fastapi import APIRouter

from app.api.routes import (
    admin_access,
    admin_audit,
    admin_users,
    auth,
    competency,
    employees,
    health,
    imports,
    notifications,
    org_reference,
    org_structure,
    training,
)

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(admin_users.router)
api_router.include_router(admin_access.router)
api_router.include_router(admin_audit.router)
api_router.include_router(org_structure.router)
api_router.include_router(org_reference.router)
api_router.include_router(employees.router)
api_router.include_router(imports.router)
api_router.include_router(training.router)
api_router.include_router(competency.router)
api_router.include_router(notifications.router)
