"""Pure organisation rules: periods, graph checks, codes, cursors and PATCH bodies."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.core.errors import AppError
from app.schemas.occupation import DesignationUpdate
from app.schemas.organisation import OrgUnitCorrect, OrgUnitCreate
from app.services.organisation.graph import ancestor_path, creates_cycle, descendants
from app.services.organisation.periods import InvalidPeriodError, Period, fully_covered
from app.services.organisation.support import (
    decode_code_cursor,
    encode_code_cursor,
    like_pattern,
    normalise_code,
)

JAN = date(2026, 1, 1)
MAR = date(2026, 3, 1)
JUN = date(2026, 6, 1)
SEP = date(2026, 9, 1)

# --- periods -------------------------------------------------------------------------


def test_period_rejects_end_on_or_before_start() -> None:
    with pytest.raises(InvalidPeriodError):
        Period(JUN, JUN)
    with pytest.raises(InvalidPeriodError):
        Period(JUN, MAR)
    Period(None, JUN)
    Period(JUN, None)


def test_period_is_half_open() -> None:
    period = Period(MAR, JUN)
    assert period.contains(MAR)
    assert not period.contains(JUN)
    assert Period(None, None).contains(date(1900, 1, 1))


def test_adjacent_periods_do_not_overlap() -> None:
    assert not Period(JAN, MAR).overlaps(Period(MAR, JUN))
    assert Period(JAN, JUN).overlaps(Period(MAR, SEP))
    assert Period(None, MAR).overlaps(Period(JAN, None))
    assert not Period(None, JAN).overlaps(Period(JAN, None))


def test_covers_treats_unknown_start_as_earliest() -> None:
    assert Period(None, None).covers(Period(MAR, JUN))
    assert Period(JAN, None).covers(Period(MAR, None))
    assert not Period(MAR, None).covers(Period(None, JUN))  # unknown start may be earlier
    assert not Period(JAN, JUN).covers(Period(MAR, None))


def test_intersection() -> None:
    assert Period(JAN, JUN).intersection(Period(MAR, SEP)) == Period(MAR, JUN)
    assert Period(None, JUN).intersection(Period(MAR, None)) == Period(MAR, JUN)
    assert Period(JAN, MAR).intersection(Period(MAR, JUN)) is None


def test_fully_covered_detects_gaps() -> None:
    target = Period(JAN, SEP)
    assert fully_covered(target, [Period(JAN, MAR), Period(MAR, SEP)])
    assert fully_covered(target, [Period(None, None)])
    assert not fully_covered(target, [Period(JAN, MAR), Period(JUN, SEP)])
    assert not fully_covered(target, [Period(MAR, None)])
    assert not fully_covered(target, [])
    assert fully_covered(Period(None, None), [Period(None, JUN), Period(JUN, None)])
    assert not fully_covered(Period(None, None), [Period(JAN, None)])


# --- graph -----------------------------------------------------------------------------


def test_creates_cycle() -> None:
    edges = [(2, 1), (3, 2)]  # 3 -> 2 -> 1 (child, parent)
    assert creates_cycle(edges, 1, 3)  # 1 under its grandchild
    assert creates_cycle(edges, 1, 2)
    assert creates_cycle(edges, 4, 4)  # self link
    assert not creates_cycle(edges, 4, 3)
    assert not creates_cycle(edges, 3, 1)  # re-parenting within the tree is fine


def test_creates_cycle_considers_every_overlapping_parent() -> None:
    # A unit with two parents over the period of interest (conservative check).
    edges = [(2, 1), (2, 5), (5, 6)]
    assert creates_cycle(edges, 6, 2)


def test_ancestor_path_and_descendants() -> None:
    parent_of = {2: 1, 3: 2, 4: 2, 5: 9}
    assert ancestor_path(3, parent_of) == [1, 2]
    assert ancestor_path(1, parent_of) == []
    assert descendants(1, parent_of) == {2, 3, 4}
    assert descendants(4, parent_of) == set()
    assert ancestor_path(1, {1: 2, 2: 1}) == [2]  # corrupt data cannot loop forever


# --- codes, search and cursors ---------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("acc_com", "ACC_COM"), ("  ops-maint ", "OPS-MAINT"), ("P1", "P1")],
)
def test_codes_are_normalised_to_upper_case(raw: str, expected: str) -> None:
    assert normalise_code(raw) == expected


@pytest.mark.parametrize("raw", ["", " ", "-LEAD", "HAS SPACE", "A.B", "Ä1", "X" * 51])
def test_invalid_codes_are_rejected(raw: str) -> None:
    with pytest.raises(AppError) as excinfo:
        normalise_code(raw)
    assert excinfo.value.status_code == 422
    assert excinfo.value.code == "invalid_code"


def test_like_pattern_escapes_wildcards() -> None:
    assert like_pattern(" 50%_x\\ ") == "%50\\%\\_x\\\\%"


def test_code_cursor_round_trip_and_rejects_garbage() -> None:
    assert decode_code_cursor(encode_code_cursor("HR_ADMIN_IT")) == "HR_ADMIN_IT"
    assert decode_code_cursor(None) is None
    with pytest.raises(AppError) as excinfo:
        decode_code_cursor("%%%")
    assert excinfo.value.code == "invalid_cursor"


# --- request bodies --------------------------------------------------------------------


def test_patch_rejects_null_for_required_fields() -> None:
    with pytest.raises(ValidationError):
        OrgUnitCorrect.model_validate({"version": 1, "name": None})
    with pytest.raises(ValidationError):
        DesignationUpdate.model_validate({"version": 1, "title": None})


def test_patch_reports_only_fields_sent() -> None:
    body = OrgUnitCorrect.model_validate(
        {"version": 3, "reason": "typo", "short_name": None, "translations": {"bn": "x"}}
    )
    assert body.changes() == {"short_name": None}


def test_translations_accept_only_supported_locales() -> None:
    unit_type = "00000000-0000-7000-8000-000000000000"
    OrgUnitCreate.model_validate(
        {"code": "X", "name": "X", "unit_type_id": unit_type, "translations": {"gu": "x"}}
    )
    with pytest.raises(ValidationError):
        OrgUnitCreate.model_validate(
            {"code": "X", "name": "X", "unit_type_id": unit_type, "translations": {"fr": "x"}}
        )
