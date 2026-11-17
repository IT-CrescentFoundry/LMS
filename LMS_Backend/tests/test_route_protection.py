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


def _required_permissions(route: APIRoute) -> set[str]:
    found: set[str] = set()
    for dependency in route.dependant.dependencies:
        found.update(getattr(dependency.call, "required_permissions", ()))
    return found


def test_admin_organisation_and_employee_routes_require_specific_permissions() -> None:
    checked = 0
    for route in _api_routes(list(api_router.routes)):
        if not route.path.startswith(("/admin", "/org", "/employees")):
            continue
        checked += 1
        assert _required_permissions(route), f"{route.path} has no permission requirement"
    assert checked > 0


def test_organisation_writes_need_a_manage_permission() -> None:
    writes = 0
    for route in _api_routes(list(api_router.routes)):
        if not route.path.startswith("/org"):
            continue
        required = _required_permissions(route)
        if route.methods and route.methods & {"POST", "PUT", "PATCH", "DELETE"}:
            writes += 1
            assert required and all(code.endswith(".manage") for code in required), route.path
        else:
            assert required == {"organisation.view"}, route.path
    assert writes > 0


EMPLOYEE_PERMISSIONS = {
    "employees.view",
    "employees.history.view",
    "employees.manage",
    "reporting_lines.manage",
}


def test_employee_routes_use_only_the_interim_employee_permissions() -> None:
    """C3 (Q-51): global employee codes only; account links also need user_accounts.manage."""
    writes = 0
    for route in _api_routes(list(api_router.routes)):
        if not route.path.startswith("/employees"):
            continue
        required = _required_permissions(route)
        methods = route.methods or set()
        is_write = bool(methods & {"POST", "PUT", "PATCH", "DELETE"})
        if is_write and route.path.endswith(("/account", "/account/unlink")):
            assert required == {"employees.manage", "user_accounts.manage"}, route.path
            continue
        assert required <= EMPLOYEE_PERMISSIONS and len(required) == 1, route.path
        if is_write:
            writes += 1
            assert required & {"employees.manage", "reporting_lines.manage"}, route.path
            if "/reporting" in route.path:
                assert required == {"reporting_lines.manage"}, route.path
    assert writes > 0


def test_import_routes_require_import_permissions() -> None:
    """Stage D: every import route needs imports.view; mapping decisions also need
    imports.mappings.manage. Profile-specific run/commit permissions (and the domain
    permissions a commit writes with) are checked in the handlers - integration tests."""
    checked = 0
    for route in _api_routes(list(api_router.routes)):
        if not route.path.startswith("/imports"):
            continue
        checked += 1
        required = _required_permissions(route)
        if route.path.startswith("/imports/mappings/") and (route.methods or set()) & {"POST"}:
            assert required == {"imports.view", "imports.mappings.manage"}, route.path
        else:
            assert required == {"imports.view"}, route.path
    assert checked == 17


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
