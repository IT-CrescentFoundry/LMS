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
