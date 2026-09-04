"""Dashboard: upcoming meetings, open action items, staleness per report."""

from datetime import date, timedelta

from flask import Blueprint, render_template

from app.models import ActionItem, Meeting, Report, utcnow
from app.services.recurrence import ensure_next_meeting

bp = Blueprint("dashboard", __name__)


@bp.get("/")
def index():
    now = utcnow()

    # Lazy recurrence: make sure every active series has an upcoming meeting.
    for report in Report.query.filter_by(archived=False):
        for series in report.series:
            ensure_next_meeting(series, now)

    upcoming = (
        Meeting.query.filter(Meeting.status == "scheduled", Meeting.scheduled_at > now)
        .filter(Meeting.scheduled_at <= now + timedelta(days=7))
        .order_by(Meeting.scheduled_at)
        .all()
    )
    past_due = (
        Meeting.query.filter(Meeting.status == "scheduled", Meeting.scheduled_at <= now)
        .order_by(Meeting.scheduled_at)
        .all()
    )
    open_items = (
        ActionItem.query.filter_by(status="open")
        .join(Report)
        .filter(Report.archived.is_(False))
        .order_by(ActionItem.due_date.is_(None), ActionItem.due_date)
        .all()
    )

    reports = []
    for report in Report.query.filter_by(archived=False).order_by(Report.name):
        last_done = (
            Meeting.query.filter_by(report_id=report.id, status="done")
            .order_by(Meeting.scheduled_at.desc())
            .first()
        )
        days_since = (date.today() - last_done.scheduled_at.date()).days if last_done else None
        reports.append((report, days_since))

    return render_template(
        "dashboard.html",
        upcoming=upcoming,
        past_due=past_due,
        open_items=open_items,
        reports=reports,
        today=date.today(),
    )
