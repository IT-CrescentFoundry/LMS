"""Session cookie helpers.

The cookie is HttpOnly (never readable by JavaScript), host-only (no Domain),
``Path=/``, SameSite Lax/Strict, and Secure when configured (always in
production; the ``__Host-`` name prefix then enforces these attributes).
"""

from datetime import timedelta

from fastapi import Response

from app.core.config import Settings


def set_session_cookie(response: Response, settings: Settings, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie_name,
        value=token,
        max_age=int(timedelta(hours=settings.session_absolute_timeout_hours).total_seconds()),
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite=settings.session_cookie_samesite,
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    response.delete_cookie(
        key=settings.session_cookie_name,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite=settings.session_cookie_samesite,
    )


def cleared_session_cookie_header(settings: Settings) -> str:
    """``Set-Cookie`` value that removes the session cookie (for error responses)."""
    response = Response()
    clear_session_cookie(response, settings)
    return response.headers["set-cookie"]
