"""Structured application logging built on the standard library.

* ``json`` format (default) emits one JSON object per line - suitable for log
  shipping and searching in production.
* ``console`` format is a readable single-line format for local development.

Every record emitted while a request is being handled carries that request's
``request_id`` (see :mod:`app.core.middleware`). Extra fields passed through
``logger.info("...", extra={...})`` are included as structured fields.

Never log secrets, session tokens, passwords or personal data.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import UTC, datetime
from typing import Any

request_id_ctx: ContextVar[str | None] = ContextVar("request_id", default=None)

# Attributes present on every LogRecord; anything else came from ``extra=``.
# ``color_message`` is uvicorn's ANSI-coloured duplicate of the message.
_STANDARD_RECORD_ATTRS = frozenset(
    vars(logging.LogRecord("", logging.INFO, "", 0, "", None, None)).keys()
) | {"message", "asctime", "taskName", "color_message"}

_HANDLER_MARKER = "_lms_handler"


def _extra_fields(record: logging.LogRecord) -> dict[str, Any]:
    return {
        key: value
        for key, value in record.__dict__.items()
        if key not in _STANDARD_RECORD_ATTRS and not key.startswith("_")
    }


class JsonFormatter(logging.Formatter):
    """Formats log records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        request_id = request_id_ctx.get()
        if request_id:
            payload["request_id"] = request_id
        payload.update(_extra_fields(record))
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str, ensure_ascii=False)


class ConsoleFormatter(logging.Formatter):
    """Readable single-line format for local development."""

    def format(self, record: logging.LogRecord) -> str:
        timestamp = datetime.fromtimestamp(record.created, tz=UTC).strftime("%H:%M:%S.%f")[:-3]
        parts = [f"{timestamp} {record.levelname:<8} {record.name}: {record.getMessage()}"]
        request_id = request_id_ctx.get()
        if request_id:
            parts.append(f"request_id={request_id}")
        parts.extend(f"{key}={value}" for key, value in _extra_fields(record).items())
        line = " ".join(parts)
        if record.exc_info:
            line += "\n" + self.formatException(record.exc_info)
        return line


def configure_logging(level: str, log_format: str, *, echo_sql: bool = False) -> None:
    """Install the LMS log handler on the root logger.

    Idempotent: calling it again replaces the previously installed LMS handler
    without touching handlers installed by other tools (e.g. pytest).
    """
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter() if log_format == "json" else ConsoleFormatter())
    setattr(handler, _HANDLER_MARKER, True)

    root = logging.getLogger()
    for existing in list(root.handlers):
        if getattr(existing, _HANDLER_MARKER, False):
            root.removeHandler(existing)
    root.addHandler(handler)
    root.setLevel(level)

    # Route uvicorn's own logs through the LMS formatter.
    for name in ("uvicorn", "uvicorn.error"):
        uvicorn_logger = logging.getLogger(name)
        uvicorn_logger.handlers.clear()
        uvicorn_logger.propagate = True
    # Request logging is done by RequestContextMiddleware, which includes the
    # request ID and duration; uvicorn's access log would duplicate it.
    access_logger = logging.getLogger("uvicorn.access")
    access_logger.handlers.clear()
    access_logger.propagate = False
    access_logger.disabled = True

    logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO if echo_sql else logging.WARNING)
