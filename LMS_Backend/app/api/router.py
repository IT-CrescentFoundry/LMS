"""Central API router. Every feature router is registered here, under the API version prefix."""

from fastapi import APIRouter

from app.api.routes import admin_access, admin_audit, admin_users, auth, health

api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(admin_users.router)
api_router.include_router(admin_access.router)
api_router.include_router(admin_audit.router)
