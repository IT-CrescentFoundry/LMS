"""Helpers for the employee API tests. Every employee, code and name is synthetic."""

from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from tests.integration.helpers import csrf, login, make_user
from tests.integration.org_helpers import OrgClient

EMP = "/api/v1/employees"


class EmployeeClient:
    """A signed-in client with helpers for employee calls (and ``org`` for set-up)."""

    def __init__(self, api: TestClient, token: str) -> None:
        self.api = api
        self.token = token
        self.org = OrgClient(api, token)

    def get(self, path: str = "", **params: Any) -> Any:
        response = self.api.get(f"{EMP}{path}", params=params)
        assert response.status_code == 200, response.text
        return response.json()

    def send(self, method: str, path: str, body: dict[str, Any], expect: int) -> Any:
        response = self.api.request(method, f"{EMP}{path}", json=body, headers=csrf(self.token))
        assert response.status_code == expect, response.text
        return response.json()

    def post(self, path: str, body: dict[str, Any], expect: int = 201) -> Any:
        return self.send("POST", path, body, expect)

    def patch(self, path: str, body: dict[str, Any], expect: int = 200) -> Any:
        return self.send("PATCH", path, body, expect)

    def error(self, method: str, path: str, body: dict[str, Any] | None, status: int) -> str:
        response = self.api.request(method, f"{EMP}{path}", json=body, headers=csrf(self.token))
        assert response.status_code == status, response.text
        return str(response.json()["error"]["code"])

    def error_body(self, method: str, path: str, body: dict[str, Any], status: int) -> Any:
        response = self.api.request(method, f"{EMP}{path}", json=body, headers=csrf(self.token))
        assert response.status_code == status, response.text
        return response.json()["error"]

    # -- set-up -----------------------------------------------------------------------

    def create(self, code: str, name: str = "Test Person", **extra: Any) -> dict[str, Any]:
        return dict(self.post("", {"employee_code": code, "full_name": name, **extra}))

    def assign(
        self, employee: dict[str, Any], unit: dict[str, Any], **extra: Any
    ) -> dict[str, Any]:
        body = {"org_unit_id": unit["public_id"], **extra}
        return dict(self.post(f"/{employee['public_id']}/assignments", body)["assignment"])


def employee_admin(api: TestClient, db: Session, login_id: str = "emp.hr.admin") -> EmployeeClient:
    make_user(db, login_id, roles=("hr_admin",))
    return EmployeeClient(api, login(api, login_id))


def employee_user(api: TestClient, db: Session, login_id: str, role: str) -> EmployeeClient:
    make_user(db, login_id, roles=(role,))
    return EmployeeClient(api, login(api, login_id))


def events_for(db: Session, target_id: str) -> list[AuditEvent]:
    return list(
        db.scalars(
            select(AuditEvent)
            .where(AuditEvent.target_type == "employee", AuditEvent.target_id == target_id)
            .order_by(AuditEvent.id)
        )
    )
