from datetime import timedelta

from app.models import ActionItem, Meeting, utcnow
from app.services.carryover import open_action_items
from app.services.recurrence import ensure_next_meeting


def _meeting(db, series, status="done", when=None):
    m = Meeting(
        series_id=series.id,
        report_id=series.report_id,
        scheduled_at=when or utcnow() - timedelta(days=7),
        status=status,
    )
    db.session.add(m)
    db.session.commit()
    return m


class TestActionItemCarryover:
    def test_open_items_queried_per_report(self, db, report):
        a = ActionItem(report_id=report.id, text="open one", status="open")
        b = ActionItem(report_id=report.id, text="done one", status="done")
        c = ActionItem(report_id=report.id, text="dropped one", status="dropped")
        db.session.add_all([a, b, c])
        db.session.commit()
        items = open_action_items(report.id)
        assert [i.text for i in items] == ["open one"]

    def test_action_items_never_copied_between_meetings(self, db, series):
        old = _meeting(db, series)
        db.session.add(ActionItem(report_id=series.report_id, meeting_id=old.id, text="follow up"))
        db.session.commit()
        ensure_next_meeting(series)
        db.session.commit()
        # Still exactly one action item; carry-over is by query, not copying.
        assert ActionItem.query.filter_by(report_id=series.report_id).count() == 1
