"""Helpers for the organisation API tests. All names and codes are synthetic."""

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from tests.integration.helpers import csrf, login, make_user

ORG = "/api/v1/org"


class OrgClient:
    """A signed-in API client with small helpers for organisation calls."""

    def __init__(self, api: TestClient, token: str) -> None:
        self.api = api
        self.token = token

    def get(self, path: str, **params: Any) -> Any:
        response = self.api.get(f"{ORG}{path}", params=params)
        assert response.status_code == 200, response.text
        return response.json()

    def send(self, method: str, path: str, body: dict[str, Any], expect: int = 200) -> Any:
        response = self.api.request(method, f"{ORG}{path}", json=body, headers=csrf(self.token))
        assert response.status_code == expect, response.text
        return response.json()

    def post(self, path: str, body: dict[str, Any], expect: int = 201) -> Any:
        return self.send("POST", path, body, expect)

    def patch(self, path: str, body: dict[str, Any], expect: int = 200) -> Any:
        return self.send("PATCH", path, body, expect)

    def error(self, method: str, path: str, body: dict[str, Any], status: int) -> str:
        """Send a request that must fail; return the error code."""
        response = self.api.request(method, f"{ORG}{path}", json=body, headers=csrf(self.token))
        assert response.status_code == status, response.text
        return str(response.json()["error"]["code"])

    # -- lookups ------------------------------------------------------------------------

    def unit_type(self, code: str) -> dict[str, Any]:
        types = {item["code"]: item for item in self.get("/unit-types")}
        return dict(types[code])

    def unit(self, public_id: str, **params: Any) -> dict[str, Any]:
        return dict(self.get(f"/units/{public_id}", **params))

    def function(self, code: str) -> dict[str, Any]:
        items = self.get("/units", q=code, roots_only=True)["items"]
        return dict(next(item for item in items if item["code"] == code))

    def create_unit(
        self,
        code: str,
        name: str,
        unit_type: str,
        parent: str | None = None,
        **extra: Any,
    ) -> dict[str, Any]:
        body = {
            "code": code,
            "name": name,
            "unit_type_id": self.unit_type(unit_type)["public_id"],
            "parent_id": parent,
            **extra,
        }
        return dict(self.post("/units", body))


def org_admin(api: TestClient, db: Session, login_id: str = "org.hr.admin") -> OrgClient:
    make_user(db, login_id, roles=("hr_admin",))
    return OrgClient(api, login(api, login_id))


def org_user(api: TestClient, db: Session, login_id: str, role: str) -> OrgClient:
    make_user(db, login_id, roles=(role,))
    return OrgClient(api, login(api, login_id))
