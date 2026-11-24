"""Shared FastAPI dependencies: settings, database, request metadata, authentication.

Access control is deny-by-default: every route under the API prefix must depend
on :func:`get_auth_context` (directly or through :func:`require_permission`),
except the explicit public allow-list checked by ``tests/test_route_protection.py``.
"""

from collections.abc import Callable, Iterator
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.api.cookies import cleared_session_cookie_header
from app.core.config import Settings
from app.core.context import RequestMeta
from app.core.errors import AppError
from app.core.middleware import UNSAFE_METHODS
from app.core.security.tokens import csrf_token_matches, hash_session_token
from app.db.session import Database
from app.db.types import utcnow
from app.models.audit import AuditOutcome
from app.services.audit_service import AuditEventType, record_audit_event
from app.services.identity.authentication import resolve_auth_context
from app.services.identity.context import AuthContext
from app.services.identity.sessions import touch_session

CSRF_HEADER = "X-CSRF-Token"


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


def get_request_meta(request: Request) -> RequestMeta:
    return RequestMeta.from_request(request)


RequestMetaDep = Annotated[RequestMeta, Depends(get_request_meta)]


def session_token(request: Request, settings: Settings) -> str | None:
    return request.cookies.get(settings.session_cookie_name) or None


def get_optional_auth_context(
    request: Request, db: DbSessionDep, settings: SettingsDep
) -> AuthContext | None:
    """Resolve the session without enforcing CSRF or extending the idle window."""
    token = session_token(request, settings)
    return resolve_auth_context(db, token, utcnow()) if token else None


def get_auth_context(request: Request, db: DbSessionDep, settings: SettingsDep) -> AuthContext:
    token = session_token(request, settings)
    now = utcnow()
    context = resolve_auth_context(db, token, now) if token else None
    if context is None:
        headers = {"Set-Cookie": cleared_session_cookie_header(settings)} if token else None
        raise AppError(401, "unauthenticated", "Please sign in to continue.", headers=headers)

    if request.method in UNSAFE_METHODS:
        candidate = request.headers.get(CSRF_HEADER, "")
        expected_hash = hash_session_token(token or "")
        if not candidate or not csrf_token_matches(settings.secret_key, expected_hash, candidate):
            raise AppError(403, "csrf_failed", "The security token is missing or invalid.")

    if touch_session(settings, context.session, now):
        db.commit()
    return context


AuthContextDep = Annotated[AuthContext, Depends(get_auth_context)]
OptionalAuthContextDep = Annotated[AuthContext | None, Depends(get_optional_auth_context)]


def require_permission(*permissions: str) -> Callable[..., AuthContext]:
    """Dependency factory: the user must hold *all* of ``permissions``.

    Users who must change their password are limited to the session, logout and
    password endpoints until they do.
    """

    def dependency(
        request: Request, auth: AuthContextDep, db: DbSessionDep, meta: RequestMetaDep
    ) -> AuthContext:
        if auth.user.password_must_change:
            raise AppError(
                403,
                "password_change_required",
                "You must change your password before continuing.",
            )
        missing = sorted(code for code in permissions if code not in auth.permissions)
        if missing:
            route = request.scope.get("route")
            record_audit_event(
                db,
                event_type=AuditEventType.AUTHORIZATION_DENIED,
                outcome=AuditOutcome.DENIED,
                meta=meta,
                actor_user_id=auth.user.id,
                metadata={
                    "required": missing,
                    "method": request.method,
                    "route": getattr(route, "path", request.url.path),
                },
            )
            db.commit()
            raise AppError(403, "forbidden", "You do not have permission to perform this action.")
        return auth

    dependency.required_permissions = permissions  # type: ignore[attr-defined]
    return dependency


def require_any_permission(*permissions: str) -> Callable[..., AuthContext]:
    """Dependency factory: the user must hold *at least one* of ``permissions``.

    Used where the data returned depends on which permission is held (global, team or
    own records); the service narrows the result accordingly.
    """

    def dependency(
        request: Request, auth: AuthContextDep, db: DbSessionDep, meta: RequestMetaDep
    ) -> AuthContext:
        if auth.user.password_must_change:
            raise AppError(
                403,
                "password_change_required",
                "You must change your password before continuing.",
            )
        if not any(code in auth.permissions for code in permissions):
            route = request.scope.get("route")
            record_audit_event(
                db,
                event_type=AuditEventType.AUTHORIZATION_DENIED,
                outcome=AuditOutcome.DENIED,
                meta=meta,
                actor_user_id=auth.user.id,
                metadata={
                    "required_any": sorted(permissions),
                    "method": request.method,
                    "route": getattr(route, "path", request.url.path),
                },
            )
            db.commit()
            raise AppError(403, "forbidden", "You do not have permission to perform this action.")
        return auth

    dependency.required_permissions = permissions  # type: ignore[attr-defined]
    return dependency


def require_schema(revision: str) -> Callable[..., None]:
    """Dependency factory: the database must be at ``revision`` or later.

    Feature tables are created by reviewed migrations that an operator applies
    explicitly. Until then the feature's endpoints answer 503
    ``schema_migration_pending`` instead of failing on a missing table. A successful
    check is remembered for the life of the app; a failed one is re-checked on every
    request, so the feature works as soon as the migration is applied.
    """
    required = int(revision)

    def dependency(request: Request, db: DbSessionDep, _auth: AuthContextDep) -> None:
        # Authentication is resolved first: anonymous callers get 401, not feature status.
        verified: set[str] | None = getattr(request.app.state, "verified_schema", None)
        if verified is None:
            verified = set()
            request.app.state.verified_schema = verified
        if revision in verified:
            return
        try:
            current = db.execute(text("SELECT version_num FROM alembic_version")).scalar()
        except SQLAlchemyError:
            db.rollback()
            current = None
        if current is None or not str(current).isdigit() or int(current) < required:
            raise AppError(
                503,
                "schema_migration_pending",
                f"This feature needs database migration {revision}, which has not been "
                "applied yet. An administrator must approve and apply it.",
            )
        verified.add(revision)

    return dependency
