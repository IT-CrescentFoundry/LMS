"""Half-open business-date periods ``[start, end)`` (pure; no database).

``start`` None means "since an unrecorded / unbounded start"; ``end`` None means
open-ended. A period with both bounds must satisfy ``end > start``.
"""

from dataclasses import dataclass
from datetime import date


class InvalidPeriodError(ValueError):
    """The end of a period is not after its start."""


@dataclass(frozen=True)
class Period:
    start: date | None = None
    end: date | None = None

    def __post_init__(self) -> None:
        if self.start is not None and self.end is not None and self.end <= self.start:
            raise InvalidPeriodError("The end date must be after the start date.")

    def contains(self, day: date) -> bool:
        return (self.start is None or self.start <= day) and (self.end is None or day < self.end)

    def overlaps(self, other: "Period") -> bool:
        starts_before_other_ends = self.start is None or other.end is None or self.start < other.end
        other_starts_before_end = other.start is None or self.end is None or other.start < self.end
        return starts_before_other_ends and other_starts_before_end

    def covers(self, other: "Period") -> bool:
        """True when ``other`` lies entirely within this period."""
        start_ok = self.start is None or (other.start is not None and self.start <= other.start)
        end_ok = self.end is None or (other.end is not None and other.end <= self.end)
        return start_ok and end_ok

    def starts_after(self, day: date) -> bool:
        return self.start is not None and self.start > day

    def intersection(self, other: "Period") -> "Period | None":
        if not self.overlaps(other):
            return None
        starts = [value for value in (self.start, other.start) if value is not None]
        ends = [value for value in (self.end, other.end) if value is not None]
        return Period(max(starts) if starts else None, min(ends) if ends else None)


def period_of(effective_from: date | None, effective_to: date | None) -> Period:
    return Period(effective_from, effective_to)


def fully_covered(target: Period, parts: list[Period]) -> bool:
    """True when the union of ``parts`` covers every day of ``target``."""
    low = target.start or date.min
    high = target.end or date.max
    spans = sorted(
        (part.start or date.min, part.end or date.max) for part in parts if part.overlaps(target)
    )
    reached = low
    for start, end in spans:
        if start > reached:
            return False
        reached = max(reached, end)
        if reached >= high:
            return True
    return reached >= high
