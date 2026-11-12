"""Structured logging tests."""

import json
import logging

from app.core.logging import ConsoleFormatter, JsonFormatter, request_id_ctx


def _record(message: str, **extra: object) -> logging.LogRecord:
    record = logging.LogRecord("app.test", logging.INFO, __file__, 1, message, None, None)
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_json_formatter_emits_structured_fields() -> None:
    token = request_id_ctx.set("req-123")
    try:
        line = JsonFormatter().format(_record("request completed", http_status=200))
    finally:
        request_id_ctx.reset(token)

    payload = json.loads(line)
    assert payload["message"] == "request completed"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "app.test"
    assert payload["request_id"] == "req-123"
    assert payload["http_status"] == 200
    assert payload["timestamp"].endswith("+00:00")


def test_json_formatter_keeps_non_latin_text_readable() -> None:
    payload = json.loads(JsonFormatter().format(_record("স্বাগতম · स्वागत · સ્વાગત")))

    assert payload["message"] == "স্বাগতম · स्वागत · સ્વાગત"


def test_uvicorn_color_message_is_not_duplicated() -> None:
    record = _record("Started server", color_message="\x1b[36mStarted server\x1b[0m")

    payload = json.loads(JsonFormatter().format(record))

    assert "color_message" not in payload


def test_console_formatter_includes_extras() -> None:
    line = ConsoleFormatter().format(_record("hello", duration_ms=1.5))

    assert "hello" in line
    assert "duration_ms=1.5" in line
