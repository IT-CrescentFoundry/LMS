"""API contract tests: error envelope, request validation, CORS and API docs."""

from collections.abc import Callable

from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field

from app.main import create_app
from tests.conftest import DUMMY_DB, TEST_ORIGIN, SettingsFactory

BROWSER_HEADERS = {"Origin": TEST_ORIGIN}


class _ExamplePayload(BaseModel):
    """Test-only payload used to exercise the validation error handler."""

    code: str = Field(min_length=2, max_length=20)
    quantity: int = Field(ge=1)


def _app_with_test_routes(make_settings: SettingsFactory) -> FastAPI:
    app = create_app(make_settings())

    @app.post("/api/v1/_test/validate")
    def validate(payload: _ExamplePayload) -> dict[str, str]:
        return {"code": payload.code}

    @app.get("/api/v1/_test/boom")
    def boom() -> None:
        raise RuntimeError("internal secret detail")

    return app


def test_unknown_route_returns_error_envelope(client: TestClient) -> None:
    response = client.get("/api/v1/does-not-exist")

    assert response.status_code == 404
    error = response.json()["error"]
    assert error["code"] == "not_found"
    assert error["message"]
    assert error["request_id"] == response.headers["X-Request-ID"]


def test_wrong_method_returns_error_envelope(client: TestClient) -> None:
    response = client.post("/api/v1/health/live")

    assert response.status_code == 405
    assert response.json()["error"]["code"] == "method_not_allowed"


def test_invalid_payload_returns_validation_envelope(make_settings: SettingsFactory) -> None:
    with TestClient(_app_with_test_routes(make_settings), headers=BROWSER_HEADERS) as client:
        response = client.post(
            "/api/v1/_test/validate", json={"code": "x", "quantity": 0, "secret": "hunter2"}
        )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_error"
    locations = {tuple(issue["location"]) for issue in error["details"]}
    assert locations == {("body", "code"), ("body", "quantity")}
    # Submitted values must not be echoed back.
    assert "hunter2" not in response.text
    assert '"x"' not in response.text


def test_malformed_json_returns_validation_envelope(make_settings: SettingsFactory) -> None:
    with TestClient(_app_with_test_routes(make_settings), headers=BROWSER_HEADERS) as client:
        response = client.post(
            "/api/v1/_test/validate",
            content=b"{not json",
            headers={"Content-Type": "application/json"},
        )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_valid_payload_is_accepted(make_settings: SettingsFactory) -> None:
    with TestClient(_app_with_test_routes(make_settings), headers=BROWSER_HEADERS) as client:
        response = client.post("/api/v1/_test/validate", json={"code": "AB", "quantity": 2})

    assert response.status_code == 200
    assert response.json() == {"code": "AB"}


def test_unhandled_error_returns_generic_500(make_settings: SettingsFactory) -> None:
    with TestClient(_app_with_test_routes(make_settings), headers=BROWSER_HEADERS) as client:
        response = client.get("/api/v1/_test/boom")

    assert response.status_code == 500
    error = response.json()["error"]
    assert error["code"] == "internal_error"
    assert error["request_id"] == response.headers["X-Request-ID"]
    assert "internal secret detail" not in response.text
    assert "Traceback" not in response.text


def test_cors_preflight_allows_configured_origin(make_client: Callable[..., TestClient]) -> None:
    client = make_client(cors_allowed_origins=["http://localhost:5173"])

    response = client.options(
        "/api/v1/health/live",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert response.headers["access-control-allow-credentials"] == "true"


def test_cors_rejects_unlisted_origin(make_client: Callable[..., TestClient]) -> None:
    client = make_client(cors_allowed_origins=["http://localhost:5173"])

    response = client.get("/api/v1/health/live", headers={"Origin": "https://evil.example"})

    assert "access-control-allow-origin" not in response.headers


def test_api_docs_available_in_development(client: TestClient) -> None:
    assert client.get("/api/docs").status_code == 200
    schema = client.get("/api/v1/openapi.json").json()
    assert "/api/v1/health/live" in schema["paths"]
    assert "/api/v1/health/ready" in schema["paths"]


def test_api_docs_disabled_in_production(make_client: Callable[..., TestClient]) -> None:
    client = make_client(
        environment="production",
        session_cookie_secure=True,
        trusted_origins=["https://lms.example.test"],
        **DUMMY_DB,
    )

    assert client.get("/api/docs").status_code == 404
    assert client.get("/api/v1/openapi.json").status_code == 404
