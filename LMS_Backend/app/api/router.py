"""Central API router. Every feature router is registered here, under the API version prefix."""

from fastapi import APIRouter

from app.api.routes import health

api_router = APIRouter()
api_router.include_router(health.router)
