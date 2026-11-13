"""Consistent JSON error responses.

Every error returned by the API uses the same envelope::

    {"error": {"code": "...", "message": "...", "details": [...], "request_id": "..."}}

Internal exception details are never returned to clients; they are logged
server-side together with the request ID so support staff can correlate them.
"""

from collections.abc import Mapping
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.logging import request_id_ctx
from app.schemas.errors import ErrorBody, ErrorResponse, ValidationIssue

_STATUS_CODES: dict[int, str] = {
    400: "bad_request",
    401: "unauthenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    409: "conflict",
    413: "payload_too_large",
    415: "unsupported_media_type",
    422: "validation_error",
    429: "rate_limited",
    500: "internal_error",
    503: "service_unavailable",
}


class AppError(Exception):
    """Expected, client-facing failure raised by services.

    Services raise ``AppError`` instead of FastAPI's ``HTTPException`` so that
    business logic stays independent of the web framework. ``code`` is a stable
    identifier the frontend translates; ``message`` is a safe English fallback.
    """

    def __init__(
        self,
        status_code: int,
        code: str,
        message: str,
        *,
        details: list[ValidationIssue] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        self.headers = headers


def error_code_for_status(status_code: int) -> str:
    return _STATUS_CODES.get(status_code, "http_error")


def build_error_response(
    status_code: int,
    message: str,
    *,
    code: str | None = None,
    details: list[ValidationIssue] | None = None,
    headers: Mapping[str, str] | None = None,
) -> JSONResponse:
    body = ErrorResponse(
        error=ErrorBody(
            code=code or error_code_for_status(status_code),
            message=message,
            details=details,
            request_id=request_id_ctx.get(),
        )
    )
    return JSONResponse(
        status_code=status_code,
        content=body.model_dump(mode="json", exclude_none=True),
        headers=headers,
    )


async def _http_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, StarletteHTTPException):  # pragma: no cover - registration guard
        raise exc
    message = exc.detail if isinstance(exc.detail, str) else HTTPStatus(exc.status_code).phrase
    return build_error_response(exc.status_code, message, headers=exc.headers)


async def _validation_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, RequestValidationError):  # pragma: no cover - registration guard
        raise exc
    # Submitted values are deliberately NOT echoed back: they may contain
    # passwords or personal data.
    issues = [
        ValidationIssue(
            location=[str(part) for part in error.get("loc", ())],
            message=str(error.get("msg", "Invalid value")),
            type=str(error.get("type", "value_error")),
        )
        for error in _as_error_list(exc.errors())
    ]
    return build_error_response(
        422,
        "The request contains invalid data.",
        details=issues,
    )


def _as_error_list(errors: Any) -> list[dict[str, Any]]:
    return [error for error in errors if isinstance(error, dict)]


async def _app_error_handler(request: Request, exc: Exception) -> JSONResponse:
    if not isinstance(exc, AppError):  # pragma: no cover - registration guard
        raise exc
    return build_error_response(
        exc.status_code, exc.message, code=exc.code, details=exc.details, headers=exc.headers
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
