"""Competency gap calculation (pure, unit-tested).

Required level (from the matrix) and assessed level (latest assessment) are compared
only within the same proficiency scale:

* no required level        -> ``requirement_pending`` (never guessed);
* no assessment            -> ``not_assessed`` (a blank is never level 0 or 1);
* level from another scale -> ``scale_mismatch`` (not comparable);
* otherwise ``met`` / ``exceeds`` / ``below``, with ``gap_steps`` = number of ranks
  below the requirement. ``gap_value`` (numeric difference) is given only when the
  scale's ``gap_method`` is ``numeric`` and both levels carry a numeric value; for
  ordinal scales arithmetic on labels is not meaningful, so it stays ``None``.
"""

from dataclasses import dataclass
from enum import StrEnum


class GapStatus(StrEnum):
    REQUIREMENT_PENDING = "requirement_pending"
    NOT_ASSESSED = "not_assessed"
    SCALE_MISMATCH = "scale_mismatch"
    BELOW = "below"
    MET = "met"
    EXCEEDS = "exceeds"


@dataclass(frozen=True)
class LevelRef:
    scale_id: int
    rank: int
    numeric_value: float | None


@dataclass(frozen=True)
class Gap:
    status: GapStatus
    gap_steps: int | None = None
    gap_value: float | None = None

    @property
    def is_gap(self) -> bool:
        return self.status is GapStatus.BELOW


def compute_gap(required: LevelRef | None, assessed: LevelRef | None, *, gap_method: str) -> Gap:
    if required is None:
        return Gap(GapStatus.REQUIREMENT_PENDING)
    if assessed is None:
        return Gap(GapStatus.NOT_ASSESSED)
    if required.scale_id != assessed.scale_id:
        return Gap(GapStatus.SCALE_MISMATCH)
    steps = required.rank - assessed.rank
    value = None
    if (
        gap_method == "numeric"
        and required.numeric_value is not None
        and assessed.numeric_value is not None
    ):
        value = round(required.numeric_value - assessed.numeric_value, 2)
    if steps > 0:
        return Gap(GapStatus.BELOW, steps, value)
    if steps == 0:
        return Gap(GapStatus.MET, 0, value if value is None else max(value, 0.0))
    return Gap(GapStatus.EXCEEDS, 0, value if value is None else 0.0)


def summarise(gaps: list[Gap]) -> dict[str, int]:
    """Counts per status, plus ``assessed`` and ``required`` totals."""
    counts = {status.value: 0 for status in GapStatus}
    for gap in gaps:
        counts[gap.status.value] += 1
    counts["required"] = sum(1 for g in gaps if g.status is not GapStatus.REQUIREMENT_PENDING)
    counts["assessed_against_requirement"] = counts["below"] + counts["met"] + counts["exceeds"]
    return counts


def needs_development_plan(gap: Gap, plan_gap_steps: int | None) -> bool:
    """Library rule: a gap of ``plan_gap_steps`` ranks or more needs an individual plan."""
    return (
        plan_gap_steps is not None
        and gap.status is GapStatus.BELOW
        and gap.gap_steps is not None
        and gap.gap_steps >= plan_gap_steps
    )


class StaffingRisk(StrEnum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


def staffing_risk(available: int, required: int | None, medium_margin: int) -> StaffingRisk | None:
    """Company skill-matrix formula, preserved exactly:

    ``=IF(available<=required,"High",IF(available<=(required+1),"Medium","Low"))``

    with the ``+1`` configurable as ``medium_margin``. Note the source rates "High"
    even when the skilled headcount exactly meets the requirement (recorded as an
    open question; kept as-is). No requirement -> no risk rating.
    """
    if required is None:
        return None
    if available <= required:
        return StaffingRisk.HIGH
    if available <= required + medium_margin:
        return StaffingRisk.MEDIUM
    return StaffingRisk.LOW
