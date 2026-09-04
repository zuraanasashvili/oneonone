from datetime import datetime, time, timedelta

from app.models import Meeting, Series, utcnow
from app.services.recurrence import advance, ensure_next_meeting, next_occurrence


def _series(cadence="weekly", dow=1, active=True, report_id=1):
    s = Series(cadence=cadence, day_of_week=dow, active=active)
    s.report_id = report_id
    s.time_of_day = time(10, 0)
    return s


class TestNextOccurrence:
    def test_same_day_later_time(self):
        # Monday 09:00, series on Mondays at 10:00 -> today at 10:00.
        s = _series(dow=0)
        after = datetime(2026, 9, 7, 9, 0)  # a Monday
        assert next_occurrence(s, after) == datetime(2026, 9, 7, 10, 0)

    def test_same_day_earlier_time_rolls_to_next_week(self):
        s = _series(dow=0)
        after = datetime(2026, 9, 7, 11, 0)  # Monday, already past 10:00
        assert next_occurrence(s, after) == datetime(2026, 9, 14, 10, 0)

    def test_different_day(self):
        s = _series(dow=4)  # Friday
        after = datetime(2026, 9, 7, 9, 0)  # Monday
        assert next_occurrence(s, after) == datetime(2026, 9, 11, 10, 0)


class TestAdvance:
    def test_weekly(self):
        s = _series("weekly")
        prev = datetime(2026, 9, 8, 10, 0)
        assert advance(s, prev) == prev + timedelta(weeks=1)

    def test_biweekly(self):
        s = _series("biweekly")
        prev = datetime(2026, 9, 8, 10, 0)
        assert advance(s, prev) == prev + timedelta(weeks=2)

    def test_monthly_keeps_day(self):
        s = _series("monthly")
        prev = datetime(2026, 1, 15, 10, 0)
        assert advance(s, prev) == datetime(2026, 2, 15, 10, 0)

    def test_monthly_clamps_short_month(self):
        s = _series("monthly")
        prev = datetime(2026, 1, 31, 10, 0)
        assert advance(s, prev) == datetime(2026, 2, 28, 10, 0)

    def test_monthly_year_rollover(self):
        s = _series("monthly")
        prev = datetime(2026, 12, 10, 10, 0)
        assert advance(s, prev) == datetime(2027, 1, 10, 10, 0)


class TestEnsureNextMeeting:
    def test_creates_first_meeting(self, db, series):
        m = ensure_next_meeting(series)
        assert m is not None
        assert m.status == "scheduled"
        assert m.scheduled_at > utcnow()
        assert m.report_id == series.report_id

    def test_idempotent(self, db, series):
        first = ensure_next_meeting(series)
        second = ensure_next_meeting(series)
        assert first.id == second.id
        assert Meeting.query.filter_by(series_id=series.id).count() == 1

    def test_inactive_series_returns_none(self, db, series):
        series.active = False
        assert ensure_next_meeting(series) is None
        assert Meeting.query.count() == 0

    def test_advances_from_last_meeting(self, db, series):
        past = utcnow() - timedelta(weeks=2)
        db.session.add(
            Meeting(
                series_id=series.id,
                report_id=series.report_id,
                scheduled_at=past,
                status="done",
            )
        )
        db.session.commit()
        m = ensure_next_meeting(series)
        # Weekly cadence anchored to the past meeting's weekday/time.
        assert m.scheduled_at > utcnow()
        assert m.scheduled_at.weekday() == past.weekday()
        assert (m.scheduled_at - past).days % 7 == 0

    def test_existing_upcoming_meeting_is_kept(self, db, series):
        future = utcnow() + timedelta(days=3)
        existing = Meeting(
            series_id=series.id,
            report_id=series.report_id,
            scheduled_at=future,
            status="scheduled",
        )
        db.session.add(existing)
        db.session.commit()
        assert ensure_next_meeting(series).id == existing.id
        assert Meeting.query.count() == 1
