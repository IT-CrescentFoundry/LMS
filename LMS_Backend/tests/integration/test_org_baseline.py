"""The reviewed organisation baseline (migrations 0005 and 0007) as seeded in the database."""

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.identity import AccessPermission, AccessRole
from app.models.organisation import (
    ORG_HIERARCHY_LOCK,
    GraphLock,
    OrgUnit,
    OrgUnitHierarchy,
    OrgUnitType,
    OrgUnitTypeRule,
)
from app.services.identity.access_control import role_permission_codes
from app.services.identity.permissions import Permission

pytestmark = pytest.mark.db

# Approved codes (Q-46) and names exactly as supplied by the business.
BASELINE_FUNCTIONS = {
    "ACC_COM": "Accounts & Commercial",
    "HR_ADMIN_IT": "HR, Admin & IT",
    "OPERATION": "Operation",
    "PURCHASE": "Purchase",
    "SALES_BD": "Sales & BD",
}
ORGANISATION_PERMISSIONS = {
    Permission.ORGANISATION_VIEW,
    Permission.ORGANISATION_MANAGE,
    Permission.DESIGNATIONS_MANAGE,
    Permission.FUNCTIONAL_ROLES_MANAGE,
    Permission.RESPONSIBILITIES_MANAGE,
}


def test_five_baseline_functions_are_seeded_exactly(db: Session) -> None:
    units = list(db.scalars(select(OrgUnit)))
    assert {unit.code: unit.name for unit in units} == BASELINE_FUNCTIONS
    for unit in units:
        assert unit.unit_type.code == "FUNCTION"
        assert unit.effective_from is None  # start date not recorded, not invented
        assert unit.effective_to is None
        assert unit.location_id is None
        assert unit.version == 1
        assert unit.public_id.version == 7
    # Byte-exact names (ampersands and commas preserved).
    assert sorted(unit.name.encode() for unit in units) == sorted(
        name.encode() for name in BASELINE_FUNCTIONS.values()
    )
    # All five are roots; nothing is placed under them yet.
    assert list(db.scalars(select(OrgUnitHierarchy))) == []


def test_no_sub_function_or_department_is_seeded(db: Session) -> None:
    types = {unit_type.code: unit_type for unit_type in db.scalars(select(OrgUnitType))}
    assert set(types) == {"FUNCTION", "SUB_FUNCTION", "DEPARTMENT"}
    assert {t.name for t in types.values()} == {"Function", "Sub-function", "Department"}
    assert all(t.parent_rule_mode == "advisory" and t.is_active for t in types.values())
    seeded_type_codes = {unit.unit_type.code for unit in db.scalars(select(OrgUnit))}
    assert seeded_type_codes == {"FUNCTION"}


def test_seeded_type_rules_are_advisory_and_as_reviewed(db: Session) -> None:
    by_id = {t.id: t.code for t in db.scalars(select(OrgUnitType))}
    pairs = {
        (by_id[rule.child_type_id], by_id.get(rule.parent_type_id) if rule.parent_type_id else None)
        for rule in db.scalars(select(OrgUnitTypeRule))
    }
    assert pairs == {
        ("FUNCTION", None),
        ("SUB_FUNCTION", "FUNCTION"),
        ("DEPARTMENT", "SUB_FUNCTION"),
        ("DEPARTMENT", "FUNCTION"),
    }


def test_hierarchy_graph_lock_row_exists(db: Session) -> None:
    assert db.get(GraphLock, ORG_HIERARCHY_LOCK) is not None


def test_organisation_permissions_are_granted_as_designed(db: Session) -> None:
    codes = set(db.scalars(select(AccessPermission.code)))
    assert codes >= ORGANISATION_PERMISSIONS
    privileged = set(
        db.scalars(select(AccessPermission.code).where(AccessPermission.is_privileged))
    )
    assert not privileged & ORGANISATION_PERMISSIONS

    roles = {role.code: role_permission_codes(role) for role in db.scalars(select(AccessRole))}
    assert not roles["employee"] & ORGANISATION_PERMISSIONS
    for code in ("supervisor", "hod", "sme"):
        assert roles[code] & ORGANISATION_PERMISSIONS == {Permission.ORGANISATION_VIEW}, code
    for code in ("hr_admin", "super_admin"):
        assert roles[code] >= ORGANISATION_PERMISSIONS, code
