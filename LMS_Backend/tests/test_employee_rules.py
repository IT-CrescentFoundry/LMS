"""Pure employee rules (no database). All codes and names are synthetic."""

from datetime import date

import pytest

from app.core.errors import AppError
from app.models.employees import Employee
from app.models.identity import UserAccount
from app.services.employees.accounts import account_flags
from app.services.employees.common import (
    decode_employee_cursor,
    employment_end,
    encode_text_cursor,
    ensure_within_employment,
    normalise_employee_code,
)
from app.services.employees.quality import CHECKS
from app.services.employees.roles import AssignmentFact, MappingFact, derive_roles, mapping_applies
from app.services.organisation.periods import Period

# --- employee codes ----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("00123", "00123"),  # leading zeros kept: codes are text
        ("  cf-0042  ", "CF-0042"),  # trimmed and stored in capitals
        ("a/b.c_d-1", "A/B.C_D-1"),
        ("X" * 30, "X" * 30),
    ],
)
def test_employee_codes_are_trimmed_upper_cased_text(raw: str, expected: str) -> None:
    assert normalise_employee_code(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "-01", "AB CD", "X" * 31, "CODE#1", "ÄB12"])
def test_invalid_employee_codes_are_refused(raw: str) -> None:
    with pytest.raises(AppError) as caught:
        normalise_employee_code(raw)
    assert caught.value.code == "invalid_employee_code"


def test_employee_cursor_round_trips_and_rejects_garbage() -> None:
    assert decode_employee_cursor(encode_text_cursor("00042")) == "00042"
    assert decode_employee_cursor(None) is None
    for bad in ("!!!", encode_text_cursor("bad code")):
        with pytest.raises(AppError) as caught:
            decode_employee_cursor(bad)
        assert caught.value.code == "invalid_cursor"


# --- employment period -------------------------------------------------------------------


def _employee(**values: object) -> Employee:
    return Employee(employee_code="T001", full_name="Test Person", **values)


def test_separation_date_is_the_last_working_day() -> None:
    assert employment_end(_employee()) is None
    assert employment_end(_employee(date_of_separation=date(2026, 3, 31))) == date(2026, 4, 1)


def test_records_must_fall_within_known_employment_dates() -> None:
    employee = _employee(date_of_joining=date(2026, 1, 1), date_of_separation=date(2026, 6, 30))
    ensure_within_employment(employee, Period(date(2026, 1, 1), date(2026, 7, 1)))
    for period, code in (
        (Period(None, date(2026, 2, 1)), "assignment_start_required"),
        (Period(date(2025, 12, 31), date(2026, 2, 1)), "outside_employment_period"),
        (Period(date(2026, 2, 1), date(2026, 7, 2)), "outside_employment_period"),
        (Period(date(2026, 2, 1), None), "outside_employment_period"),
    ):
        with pytest.raises(AppError) as caught:
            ensure_within_employment(employee, period)
        assert caught.value.code == code, period
    # Unknown dates do not restrict anything.
    ensure_within_employment(_employee(), Period(None, None))


# --- derived functional roles -------------------------------------------------------------

# Hierarchy: 1 (function) > 2 (sub-function) > 3 (department); 9 is elsewhere.
PARENTS = {2: 1, 3: 2}


def _mapping(
    mapping_id: int, role: int, scope: int | None, descendants: bool = True
) -> MappingFact:
    return MappingFact(
        mapping_id,
        designation_id=100,
        functional_role_id=role,
        scope_unit_id=scope,
        include_descendants=descendants,
    )


def test_mapping_scope_and_descendants() -> None:
    assert mapping_applies(_mapping(1, 7, None), 9, PARENTS)
    assert mapping_applies(_mapping(1, 7, 3), 3, PARENTS)
    assert mapping_applies(_mapping(1, 7, 1), 3, PARENTS)
    assert not mapping_applies(_mapping(1, 7, 1, descendants=False), 3, PARENTS)
    assert not mapping_applies(_mapping(1, 7, 3), 1, PARENTS)  # never upwards
    assert not mapping_applies(_mapping(1, 7, 1), 9, PARENTS)


def test_every_assignment_contributes_roles() -> None:
    assignments = [
        AssignmentFact(assignment_id=10, org_unit_id=3, designation_id=100),  # primary
        AssignmentFact(assignment_id=11, org_unit_id=9, designation_id=100),  # additional
        AssignmentFact(assignment_id=12, org_unit_id=9, designation_id=None),  # no designation
    ]
    mappings = [_mapping(1, 7, None), _mapping(2, 8, 1), _mapping(3, 6, 9, descendants=False)]
    derived = {
        (d.functional_role_id, d.assignment_id)
        for d in derive_roles(assignments, mappings, PARENTS)
    }
    assert derived == {(7, 10), (7, 11), (8, 10), (6, 11)}


# --- account flags and data-quality catalogue ------------------------------------------------


def _account(status: str, email: str | None = None) -> UserAccount:
    return UserAccount(login_id="test.login", display_name="Test", status=status, email=email)


def test_account_flags_never_change_anything_and_flag_mismatches() -> None:
    separated = _employee(employment_status="separated", work_email="t@example.test")
    assert account_flags(separated, [_account("disabled")]) == []
    assert account_flags(separated, [_account("active", "T@EXAMPLE.TEST")]) == [
        "separated_with_active_account"
    ]
    active = _employee(employment_status="active", work_email="t@example.test")
    assert account_flags(active, [_account("active", "other@example.test")]) == ["email_mismatch"]
    assert account_flags(_employee(), [_account("suspended")]) == []


def test_data_quality_checks_are_the_planned_set() -> None:
    assert set(CHECKS) == {
        "unknown_status",
        "no_primary_assignment",
        "missing_location",
        "missing_designation",
        "separated_with_active_account",
        "manager_inactive",
        "no_line_manager",
        "incomplete_record",
    }
