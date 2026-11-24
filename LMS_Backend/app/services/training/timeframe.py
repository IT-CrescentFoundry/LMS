"""Past / ongoing / upcoming classification of training events (pure functions).

The timeframe is derived from dates, never stored, so it cannot go stale:

* the event window is the **actual** period when recorded, otherwise the **planned**
  period, otherwise the scheduled sessions, otherwise the planned month;
* ``cancelled`` events are reported as cancelled whatever their dates;
* an event with no date at all is ``unscheduled``.

A past *planned* event is still only planned: the timeframe says nothing about
whether it took place (that is ``status == completed`` with actual dates).
"""

import calendar
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

from sqlalchemy import ColumnElement, and_, func, or_

from app.models.training import EventStatus, TrainingEvent


class Timeframe(StrEnum):
    PAST = "past"
    ONGOING = "ongoing"
    UPCOMING = "upcoming"
    UNSCHEDULED = "unscheduled"
    CANCELLED = "cancelled"


@dataclass(frozen=True)
class Window:
    start: date | None
    end: date | None


def month_end(first: date) -> date:
    return first.replace(day=calendar.monthrange(first.year, first.month)[1])


def event_window(
    *,
    actual_start: date | None,
    actual_end: date | None,
    planned_start: date | None,
    planned_end: date | None,
    session_days: list[date],
    planned_month: date | None,
) -> Window:
    if actual_start is not None:
        return Window(actual_start, actual_end or actual_start)
    if planned_start is not None:
        return Window(planned_start, planned_end or planned_start)
    if session_days:
        return Window(min(session_days), max(session_days))
    if planned_month is not None:
        return Window(planned_month, month_end(planned_month))
    return Window(None, None)


def classify(status: str, window: Window, today: date) -> Timeframe:
    if status == EventStatus.CANCELLED.value:
        return Timeframe.CANCELLED
    if window.start is None or window.end is None:
        return Timeframe.UNSCHEDULED
    if window.end < today:
        return Timeframe.PAST
    if window.start > today:
        return Timeframe.UPCOMING
    return Timeframe.ONGOING


# SQL equivalents (sessions are not consulted: scheduling an event with sessions
# fills its planned dates, see records.sync_planned_dates).
def _start_expr() -> ColumnElement[date]:
    return func.coalesce(
        TrainingEvent.actual_start_date,
        TrainingEvent.planned_start_date,
        TrainingEvent.planned_month,
    )


def _end_expr() -> ColumnElement[date]:
    return func.coalesce(
        TrainingEvent.actual_end_date,
        TrainingEvent.actual_start_date,
        TrainingEvent.planned_end_date,
        TrainingEvent.planned_start_date,
        func.last_day(TrainingEvent.planned_month),
    )


def timeframe_condition(timeframe: Timeframe, today: date) -> ColumnElement[bool]:
    not_cancelled = TrainingEvent.status != EventStatus.CANCELLED.value
    start, end = _start_expr(), _end_expr()
    if timeframe is Timeframe.CANCELLED:
        return TrainingEvent.status == EventStatus.CANCELLED.value
    if timeframe is Timeframe.UNSCHEDULED:
        return and_(not_cancelled, start.is_(None))
    if timeframe is Timeframe.PAST:
        return and_(not_cancelled, end < today)
    if timeframe is Timeframe.UPCOMING:
        return and_(not_cancelled, start > today)
    return and_(not_cancelled, start <= today, end >= today)


def overlaps_condition(start: date, end: date) -> ColumnElement[bool]:
    """Events whose window overlaps [start, end] (inclusive)."""
    return or_(and_(_start_expr() <= end, _end_expr() >= start))
