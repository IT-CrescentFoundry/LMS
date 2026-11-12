"""FastAPI application factory.

Run with the factory flag so that configuration is read at startup rather than
at import time::

    uvicorn app.main:create_app --factory --reload
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api.router import api_router
from app.core.config import Settings, get_settings
from app.core.errors import register_exception_handlers
from app.core.logging import configure_logging
from app.core.middleware import REQUEST_ID_HEADER, RequestContextMiddleware
from app.db.session import Database

logger = logging.getLogger("app")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging(settings.log_level, settings.log_format, echo_sql=settings.db_echo_sql)
    database = Database.from_settings(settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        logger.info(
            "application starting",
            extra={
                "environment": settings.environment.value,
                "version": __version__,
                "database_configured": database.is_configured,
                # Host and schema name only - never credentials.
                "database_host": settings.db_host,
                "database_name": settings.db_name,
            },
        )
        if not database.is_configured:
            logger.warning("LMS database is not configured; readiness checks will report not_ready")
        yield
        database.dispose()
        logger.info("application stopped")

    docs_enabled = settings.api_docs_enabled
    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs" if docs_enabled else None,
        redoc_url=None,
        openapi_url=f"{settings.api_v1_prefix}/openapi.json" if docs_enabled else None,
    )
    app.state.settings = settings
    app.state.database = database

    register_exception_handlers(app)

    # Middleware added last runs first: RequestContextMiddleware wraps CORS so
    # that preflight responses also carry a request ID and are logged.
    if settings.cors_allowed_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_allowed_origins,
            allow_credentials=True,
            allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            allow_headers=["Accept", "Accept-Language", "Content-Type", REQUEST_ID_HEADER],
            expose_headers=[REQUEST_ID_HEADER],
            max_age=600,
        )
    app.add_middleware(RequestContextMiddleware)

    app.include_router(api_router, prefix=settings.api_v1_prefix)
    return app
