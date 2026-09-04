"""Dashboard: upcoming meetings, open action items, staleness per report."""

from datetime import date, timedelta
from itertools import groupby

from flask import Blueprint, render_template

from app.models import ActionItem, Meeting, Report, utcnow
from app.services.recurrence import ensure_next_meeting

bp = Blueprint("dashboard", __name__)


def _materialize_upcoming(now):
    """Ensure every active series has its next scheduled meeting."""
    for report in Report.query.filter_by(archived=False):
        for series in report.series:
            ensure_next_meeting(series, now)


@bp.get("/")
def index():
    now = utcnow()
    _materialize_upcoming(now)  # lazy recurrence

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

    reports = [
        (report, report.days_since_last_1on1)
        for report in Report.query.filter_by(archived=False).order_by(Report.name)
    ]

    return render_template(
        "dashboard.html",
        upcoming=upcoming,
        past_due=past_due,
        open_items=open_items,
        reports=reports,
        today=date.today(),
    )


@bp.get("/timeline")
def timeline():
    now = utcnow()
    _materialize_upcoming(now)

    meetings = (
        Meeting.query.filter_by(status="scheduled")
        .join(Report)
        .filter(Report.archived.is_(False))
        .order_by(Meeting.scheduled_at)
        .all()
    )
    months = [
        (label, list(group))
        for label, group in groupby(meetings, key=lambda m: m.scheduled_at.strftime("%B %Y"))
    ]
    return render_template("timeline.html", months=months, now=now)
