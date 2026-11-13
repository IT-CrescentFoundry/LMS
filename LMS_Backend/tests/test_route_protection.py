"""Deny-by-default: every API route must require authentication unless allow-listed.

The trusted-origin (CSRF layer 1) behaviour is also tested here because it needs
no database.
"""

from collections.abc import Callable, Iterator

from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from app.api.deps import get_auth_context
from app.api.router import api_router

# Routes that are intentionally reachable without a session.
PUBLIC_ROUTES = {
    ("GET", "/health/live"),
    ("GET", "/health/ready"),
    ("POST", "/auth/login"),
    ("GET", "/auth/session"),
}


def _api_routes(routes: list[object]) -> Iterator[APIRoute]:
    for route in routes:
        if isinstance(route, APIRoute):
            yield route
        else:  # FastAPI keeps included routers as nested router objects
            original = getattr(route, "original_router", None)
            if original is not None:
                yield from _api_routes(list(original.routes))


def _depends_on(dependant: object, target: Callable[..., object]) -> bool:
    for dependency in getattr(dependant, "dependencies", []):
        if dependency.call is target or _depends_on(dependency, target):
            return True
    return False


def test_every_non_public_route_requires_authentication() -> None:
    routes = list(_api_routes(list(api_router.routes)))
    seen: set[tuple[str, str]] = set()
    unprotected: list[str] = []
    for route in routes:
        for method in route.methods or set():
            seen.add((method, route.path))
            if (method, route.path) in PUBLIC_ROUTES:
                continue
            if not _depends_on(route.dependant, get_auth_context):
                unprotected.append(f"{method} {route.path}")

    assert seen >= PUBLIC_ROUTES, "public allow-list refers to routes that do not exist"
    assert len(seen) > len(PUBLIC_ROUTES)
    assert unprotected == []


def test_admin_routes_require_specific_permissions() -> None:
    for route in _api_routes(list(api_router.routes)):
        if not route.path.startswith("/admin"):
            continue
        required = [
            getattr(dependency.call, "required_permissions", None)
            for dependency in route.dependant.dependencies
        ]
        assert any(required), f"{route.path} has no permission requirement"


# --- Trusted origin (CSRF layer 1) ---------------------------------------------------


def test_state_changing_request_without_origin_is_rejected(
    make_client: Callable[..., TestClient],
) -> None:
    client = make_client()

    response = client.post("/api/v1/auth/login", json={}, headers={"Origin": ""})

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "origin_not_allowed"


def test_state_changing_request_from_untrusted_origin_is_rejected(
    make_client: Callable[..., TestClient],
) -> None:
    client = make_client()

    response = client.post(
        "/api/v1/auth/login",
        json={"login_id": "x", "password": "y"},
        headers={"Origin": "https://evil.example"},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "origin_not_allowed"
    assert response.headers["X-Request-ID"]


def test_referer_is_used_when_origin_is_absent(make_client: Callable[..., TestClient]) -> None:
    client = make_client()

    bad = client.post(
        "/api/v1/auth/login",
        json={},
        headers={"Origin": "", "Referer": "https://evil.example/page"},
    )
    good = client.post(
        "/api/v1/auth/login",
        json={},
        headers={"Origin": "", "Referer": "http://testserver/login"},
    )

    assert bad.status_code == 403
    assert good.status_code != 403  # passes the origin check (then fails validation)


def test_safe_methods_are_not_origin_checked(make_client: Callable[..., TestClient]) -> None:
    client = make_client()

    response = client.get("/api/v1/health/live", headers={"Origin": "https://evil.example"})

    assert response.status_code == 200


def test_auth_endpoints_report_unconfigured_database(client: TestClient) -> None:
    response = client.post("/api/v1/auth/login", json={"login_id": "a", "password": "b"})

    assert response.status_code == 503
