"""Unit tests for first-release business rules (no database).

Covers the competency gap calculation, the skill-matrix staffing-risk formula preserved
from the company workbooks, the development-plan threshold from the competency library,
the derived past/ongoing/upcoming timeframe and the manhours formula.
"""

from datetime import date

import pytest

from app.models.training import EventStatus
from app.services.competency.gap import (
    Gap,
    GapStatus,
    LevelRef,
    StaffingRisk,
    compute_gap,
    needs_development_plan,
    staffing_risk,
    summarise,
)
from app.services.training.records import manhours
from app.services.training.timeframe import Timeframe, Window, classify, event_window, month_end

SCALE = 1
OTHER_SCALE = 2


def level(rank: int, scale: int = SCALE, value: float | None = None) -> LevelRef:
    return LevelRef(scale, rank, float(rank) if value is None else value)


# ----------------------------------------------------------------------------- gaps


def test_pending_requirement_is_never_guessed() -> None:
    assert compute_gap(None, level(3), gap_method="ordinal").status is GapStatus.REQUIREMENT_PENDING


def test_blank_assessment_is_not_assessed_not_level_zero() -> None:
    gap = compute_gap(level(3), None, gap_method="ordinal")
    assert gap.status is GapStatus.NOT_ASSESSED
    assert gap.gap_steps is None


def test_levels_of_different_scales_are_not_compared() -> None:
    gap = compute_gap(level(2), level(4, OTHER_SCALE), gap_method="numeric")
    assert gap.status is GapStatus.SCALE_MISMATCH


@pytest.mark.parametrize(
    ("required", "assessed", "status", "steps"),
    [(4, 2, GapStatus.BELOW, 2), (3, 3, GapStatus.MET, 0), (2, 5, GapStatus.EXCEEDS, 0)],
)
def test_ordinal_gap_uses_rank_order_only(
    required: int, assessed: int, status: GapStatus, steps: int
) -> None:
    gap = compute_gap(level(required), level(assessed), gap_method="ordinal")
    assert gap.status is status
    assert gap.gap_steps == steps
    assert gap.gap_value is None  # no arithmetic on ordinal labels


def test_numeric_gap_is_required_minus_current() -> None:
    gap = compute_gap(level(3, value=3.0), level(1, value=1.0), gap_method="numeric")
    assert gap.status is GapStatus.BELOW
    assert gap.gap_value == 2.0


def test_development_plan_threshold_from_library_read_me() -> None:
    two_below = compute_gap(level(3), level(1), gap_method="numeric")
    one_below = compute_gap(level(3), level(2), gap_method="numeric")
    assert needs_development_plan(two_below, 2) is True
    assert needs_development_plan(one_below, 2) is False
    assert needs_development_plan(two_below, None) is False  # not configured


def test_summary_counts_each_status() -> None:
    gaps = [
        compute_gap(level(3), level(1), gap_method="ordinal"),
        compute_gap(level(3), level(3), gap_method="ordinal"),
        compute_gap(None, level(3), gap_method="ordinal"),
        Gap(GapStatus.NOT_ASSESSED),
    ]
    summary = summarise(gaps)
    assert summary["below"] == 1
    assert summary["met"] == 1
    assert summary["requirement_pending"] == 1
    assert summary["not_assessed"] == 1
    assert summary["required"] == 3
    assert summary["assessed_against_requirement"] == 2


# ------------------------------------------------------------------- staffing risk


@pytest.mark.parametrize(
    ("available", "required", "expected"),
    [
        (2, 3, StaffingRisk.HIGH),
        (3, 3, StaffingRisk.HIGH),  # source formula: available <= required is High
        (4, 3, StaffingRisk.MEDIUM),  # <= required + 1
        (5, 3, StaffingRisk.LOW),
        (0, 0, StaffingRisk.HIGH),
    ],
)
def test_staffing_risk_matches_workbook_formula(
    available: int, required: int, expected: StaffingRisk
) -> None:
    assert staffing_risk(available, required, 1) is expected


def test_staffing_risk_margin_is_configurable_and_needs_a_requirement() -> None:
    assert staffing_risk(5, 3, 2) is StaffingRisk.MEDIUM
    assert staffing_risk(5, None, 1) is None


# ----------------------------------------------------------------------- timeframe


TODAY = date(2026, 11, 23)


def test_actual_dates_take_precedence_over_planned() -> None:
    window = event_window(
        actual_start=date(2026, 11, 1),
        actual_end=None,
        planned_start=date(2026, 12, 1),
        planned_end=None,
        session_days=[],
        planned_month=None,
    )
    assert window == Window(date(2026, 11, 1), date(2026, 11, 1))


def test_month_only_plan_spans_the_month() -> None:
    window = event_window(
        actual_start=None,
        actual_end=None,
        planned_start=None,
        planned_end=None,
        session_days=[],
        planned_month=date(2027, 2, 1),
    )
    assert window == Window(date(2027, 2, 1), date(2027, 2, 28))
    assert month_end(date(2028, 2, 1)) == date(2028, 2, 29)


@pytest.mark.parametrize(
    ("window", "status", "expected"),
    [
        (Window(date(2026, 11, 1), date(2026, 11, 2)), "planned", Timeframe.PAST),
        (Window(date(2026, 11, 20), date(2026, 11, 25)), "scheduled", Timeframe.ONGOING),
        (Window(date(2026, 12, 1), date(2026, 12, 1)), "scheduled", Timeframe.UPCOMING),
        (Window(None, None), "planned", Timeframe.UNSCHEDULED),
        (Window(date(2026, 12, 1), date(2026, 12, 1)), "cancelled", Timeframe.CANCELLED),
    ],
)
def test_classification(window: Window, status: str, expected: Timeframe) -> None:
    assert classify(status, window, TODAY) is expected


def test_past_planned_event_is_not_reported_as_completed() -> None:
    # The timeframe says "past" but the status stays "planned": nothing is inferred.
    window = Window(date(2026, 4, 1), date(2026, 4, 1))
    assert classify(EventStatus.PLANNED.value, window, TODAY) is Timeframe.PAST


# ------------------------------------------------------------------------ manhours


def test_manhours_formula_and_missing_inputs() -> None:
    assert manhours(90, 10) == 15.0
    assert manhours(None, 10) is None
    assert manhours(60, None) is None


# ------------------------------------------------------ review 2026-11-23 boundaries


@pytest.mark.parametrize(
    ("skilled", "expected"),
    [
        (0, StaffingRisk.HIGH),
        (4, StaffingRisk.HIGH),
        (5, StaffingRisk.HIGH),  # equal to the requirement is still High (source formula)
        (6, StaffingRisk.MEDIUM),  # required + 1
        (7, StaffingRisk.LOW),
        (20, StaffingRisk.LOW),
    ],
)
def test_staffing_risk_boundaries_for_required_headcount_five(
    skilled: int, expected: StaffingRisk
) -> None:
    # Workbook: =IF(L18<=L17,"High",IF(L18<=(L17+1),"Medium","Low"))
    assert staffing_risk(skilled, 5, 1) is expected


@pytest.mark.parametrize(
    ("required_rank", "assessed_rank", "steps", "plan"),
    [(4, 3, 1, False), (4, 2, 2, True), (4, 1, 3, True), (3, 3, 0, False), (2, 4, 0, False)],
)
def test_development_plan_trigger_below_at_and_above_two(
    required_rank: int, assessed_rank: int, steps: int, plan: bool
) -> None:
    gap = compute_gap(
        LevelRef(1, required_rank, float(required_rank)),
        LevelRef(1, assessed_rank, float(assessed_rank)),
        gap_method="numeric",
    )
    assert gap.gap_steps == steps
    assert needs_development_plan(gap, 2) is plan


def test_reminder_times_are_shown_in_business_time() -> None:
    from datetime import UTC, datetime

    from app.services.notifications import local_time_text

    moment = datetime(2026, 11, 25, 4, 30, tzinfo=UTC)
    assert local_time_text(moment, 330) == "2026-11-25 10:00 IST"
    assert local_time_text(moment, 0) == "2026-11-25 04:30 UTC+00:00"
    assert local_time_text(moment, -300) == "2026-11-24 23:30 UTC-05:00"
