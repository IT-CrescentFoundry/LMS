"""Shared FastAPI dependencies."""

from collections.abc import Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.db.session import Database


def get_app_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


def get_database(request: Request) -> Database:
    database: Database = request.app.state.database
    return database


SettingsDep = Annotated[Settings, Depends(get_app_settings)]
DatabaseDep = Annotated[Database, Depends(get_database)]


def get_db_session(database: DatabaseDep) -> Iterator[Session]:
    """Request-scoped database session.

    Services decide when to commit. Anything left uncommitted is rolled back
    when the session closes at the end of the request.
    """
    if not database.is_configured:
        raise HTTPException(status_code=503, detail="The LMS database is not configured.")
    with database.session() as session:
        yield session


DbSessionDep = Annotated[Session, Depends(get_db_session)]
