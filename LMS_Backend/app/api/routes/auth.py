"""Authentication endpoints: login, logout, session status, current user, password change."""

from typing import Any

from fastapi import APIRouter, Request, Response, status

from app.api.cookies import clear_session_cookie, set_session_cookie
from app.api.deps import (
    AuthContextDep,
    DbSessionDep,
    OptionalAuthContextDep,
    RequestMetaDep,
    SettingsDep,
    session_token,
)
from app.api.presenters import current_user, session_response
from app.db.types import utcnow
from app.schemas.auth import ChangePasswordRequest, CurrentUser, LoginRequest, SessionResponse
from app.schemas.errors import ErrorResponse
from app.services.identity import authentication

router = APIRouter(prefix="/auth", tags=["authentication"])

_ERRORS: dict[int | str, dict[str, Any]] = {
    401: {"model": ErrorResponse},
    403: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
}


@router.post(
    "/login",
    response_model=SessionResponse,
    summary="Sign in with login ID and password",
    responses=_ERRORS,
)
def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> SessionResponse:
    signed_in = authentication.authenticate(
        db,
        settings,
        login_id=body.login_id,
        password=body.password.get_secret_value(),
        meta=meta,
        presented_token=session_token(request, settings),
        now=utcnow(),
    )
    set_session_cookie(response, settings, signed_in.token)
    return session_response(signed_in.context, settings)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Sign out and revoke the current session",
)
def logout(
    auth: AuthContextDep, db: DbSessionDep, settings: SettingsDep, meta: RequestMetaDep
) -> Response:
    authentication.logout(db, auth, meta, utcnow())
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    clear_session_cookie(response, settings)
    return response


@router.get(
    "/session",
    response_model=SessionResponse,
    summary="Current session status (public; used to restore the UI after a refresh)",
)
def session_status(
    request: Request, response: Response, auth: OptionalAuthContextDep, settings: SettingsDep
) -> SessionResponse:
    if auth is None:
        if session_token(request, settings):
            clear_session_cookie(response, settings)
        return SessionResponse(authenticated=False)
    return session_response(auth, settings)


@router.get("/me", response_model=CurrentUser, summary="The signed-in user")
def me(auth: AuthContextDep) -> CurrentUser:
    return current_user(auth)


@router.post(
    "/password",
    response_model=SessionResponse,
    summary="Change own password (rotates the session and revokes all others)",
    responses=_ERRORS,
)
def change_password(
    body: ChangePasswordRequest,
    response: Response,
    auth: AuthContextDep,
    db: DbSessionDep,
    settings: SettingsDep,
    meta: RequestMetaDep,
) -> SessionResponse:
    signed_in = authentication.change_password(
        db,
        settings,
        auth=auth,
        current_password=body.current_password.get_secret_value(),
        new_password=body.new_password.get_secret_value(),
        meta=meta,
        now=utcnow(),
    )
    set_session_cookie(response, settings, signed_in.token)
    return session_response(signed_in.context, settings)
