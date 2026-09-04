"""Lazy recurrence: materialize meeting instances on demand, with no scheduler.

A series always keeps exactly one upcoming ``scheduled`` meeting. The next
instance is created when:
- the dashboard is loaded,
- a meeting is completed or cancelled,
- a series is created or reactivated.
"""

from datetime import datetime, time, timedelta

from app.extensions import db
from app.models import Meeting, Series, utcnow

CADENCE_DELTAS = {
    "weekly": timedelta(weeks=1),
    "biweekly": timedelta(weeks=2),
}


def next_occurrence(series: Series, after: datetime) -> datetime:
    """First occurrence of the series strictly after ``after``."""
    candidate = datetime.combine(after.date(), series.time_of_day)
    days_ahead = (series.day_of_week - after.weekday()) % 7
    candidate += timedelta(days=days_ahead)
    if candidate <= after:
        candidate += timedelta(weeks=1)

    # Monthly and biweekly cadences are anchored to this first weekly hit;
    # advancing from here happens in steps of the cadence delta.
    return candidate


def advance(series: Series, previous: datetime) -> datetime:
    """The occurrence following ``previous`` for the series' cadence."""
    if series.cadence == "monthly":
        month = previous.month + 1
        year = previous.year
        if month > 12:
            month, year = 1, year + 1
        day = min(previous.day, _days_in_month(year, month))
        return datetime.combine(
            datetime(year, month, day).date(),
            previous.time() if isinstance(previous, datetime) else time(10, 0),
        )
    return previous + CADENCE_DELTAS.get(series.cadence, timedelta(weeks=1))


def ensure_next_meeting(series: Series, now: datetime | None = None) -> Meeting | None:
    """Create the series' next scheduled meeting if none is upcoming.

    Returns the upcoming meeting (existing or newly created), or None if the
    series is inactive.
    """
    if not series.active:
        return None
    now = now or utcnow()

    upcoming = (
        Meeting.query.filter_by(series_id=series.id, status="scheduled")
        .filter(Meeting.scheduled_at > now)
        .order_by(Meeting.scheduled_at)
        .first()
    )
    if upcoming:
        return upcoming

    last = (
        Meeting.query.filter(Meeting.series_id == series.id)
        .order_by(Meeting.scheduled_at.desc())
        .first()
    )
    if last is None:
        scheduled_at = next_occurrence(series, now)
    else:
        scheduled_at = advance(series, last.scheduled_at)
        while scheduled_at <= now:
            scheduled_at = advance(series, scheduled_at)

    meeting = Meeting(
        series_id=series.id,
        report_id=series.report_id,
        scheduled_at=scheduled_at,
        status="scheduled",
    )
    db.session.add(meeting)
    db.session.flush()
    return meeting


def _days_in_month(year: int, month: int) -> int:
    if month == 12:
        return 31
    return (datetime(year, month + 1, 1) - datetime(year, month, 1)).days
