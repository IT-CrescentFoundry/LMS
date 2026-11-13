"""Request-context middleware (pure ASGI).

Responsibilities:

* Assign each HTTP request a request ID (accepting a well-formed incoming
  ``X-Request-ID`` header, otherwise generating one) and expose it to logging.
* Return the request ID and baseline security headers on every response.
* Log one structured line per request (method, path, status, duration).
  Query strings are not logged because they may contain personal data.
* Convert unhandled exceptions into the standard 500 error envelope, so no
  stack trace or internal detail ever reaches the client.
"""

import logging
import re
import time
import uuid
from collections.abc import Iterable
from urllib.parse import urlsplit

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.errors import build_error_response
from app.core.logging import request_id_ctx

logger = logging.getLogger("app.request")

REQUEST_ID_HEADER = "X-Request-ID"
_VALID_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")

SECURITY_HEADERS: tuple[tuple[str, str], ...] = (
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "no-referrer"),
    # API responses may contain personal data; never let shared caches keep them.
    ("Cache-Control", "no-store"),
)

# Probes are polled frequently; log them at DEBUG to keep INFO logs useful.
_QUIET_PATH_SUFFIXES = ("/health/live", "/health/ready")


UNSAFE_METHODS = frozenset({"POST", "PUT", "PATCH", "DELETE"})


def _header(scope: Scope, name: bytes) -> str | None:
    for key, value in scope.get("headers", []):
        if key == name:
            return str(value.decode("latin-1"))
    return None


def _request_origin(scope: Scope) -> str | None:
    """The browser-supplied Origin, falling back to the origin part of Referer."""
    origin = _header(scope, b"origin")
    if origin and origin != "null":
        return origin.rstrip("/").lower()
    referer = _header(scope, b"referer")
    if referer:
        parts = urlsplit(referer)
        if parts.scheme and parts.netloc:
            return f"{parts.scheme}://{parts.netloc}".lower()
    return None


class TrustedOriginMiddleware:
    """CSRF layer 1: state-changing requests must come from a trusted origin.

    Applies to every POST/PUT/PATCH/DELETE (including login, which has no session
    yet). Requests without an Origin/Referer, or from any other origin, are
    rejected with 403 ``origin_not_allowed``. Layer 2 (the session-bound CSRF
    token) is enforced by the authentication dependency.
    """

    def __init__(self, app: ASGIApp, *, trusted_origins: Iterable[str]) -> None:
        self.app = app
        self._trusted = frozenset(origin.rstrip("/").lower() for origin in trusted_origins)

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] == "http" and scope.get("method") in UNSAFE_METHODS:
            origin = _request_origin(scope)
            if origin is None or origin not in self._trusted:
                logger.warning(
                    "rejected state-changing request from untrusted origin",
                    extra={"http_path": scope.get("path"), "origin": origin},
                )
                response = build_error_response(
                    403,
                    "The request origin is not allowed.",
                    code="origin_not_allowed",
                )
                await response(scope, receive, send)
                return
        await self.app(scope, receive, send)


def _incoming_request_id(scope: Scope) -> str | None:
    for name, value in scope.get("headers", []):
        if name == b"x-request-id":
            candidate = value.decode("latin-1")
            return candidate if _VALID_REQUEST_ID.fullmatch(candidate) else None
    return None


class RequestContextMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = _incoming_request_id(scope) or uuid.uuid4().hex
        token = request_id_ctx.set(request_id)
        started = time.perf_counter()
        status_code = 500
        response_started = False

        async def send_with_headers(message: Message) -> None:
            nonlocal status_code, response_started
            if message["type"] == "http.response.start":
                response_started = True
                status_code = message["status"]
                headers = MutableHeaders(scope=message)
                headers[REQUEST_ID_HEADER] = request_id
                for name, value in SECURITY_HEADERS:
                    headers.setdefault(name, value)
            await send(message)

        try:
            await self.app(scope, receive, send_with_headers)
        except Exception:
            logger.exception("unhandled error while processing request")
            if response_started:
                raise
            response = build_error_response(500, "An unexpected error occurred.")
            await response(scope, receive, send_with_headers)
        finally:
            path: str = scope.get("path", "")
            level = logging.DEBUG if path.endswith(_QUIET_PATH_SUFFIXES) else logging.INFO
            logger.log(
                level,
                "request completed",
                extra={
                    "http_method": scope.get("method"),
                    "http_path": path,
                    "http_status": status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                },
            )
            request_id_ctx.reset(token)
