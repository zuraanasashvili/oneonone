"""Reports CRUD, salary history, and series settings."""

from datetime import date, datetime

from flask import Blueprint, abort, redirect, render_template, request, url_for

from app.extensions import db
from app.models import Meeting, Report, SalaryChange, Series, utcnow
from app.services.carryover import open_action_items
from app.services.charts import mood_sparkline
from app.services.recurrence import ensure_next_meeting

bp = Blueprint("reports", __name__, url_prefix="/reports")


def _get_report(report_id: int) -> Report:
    report = db.session.get(Report, report_id)
    if report is None:
        abort(404)
    return report


@bp.get("/")
def index():
    now = utcnow()
    rows = []
    for report in Report.query.filter_by(archived=False).order_by(Report.name):
        series = report.active_series
        if series:
            ensure_next_meeting(series, now)
        next_meeting = (
            Meeting.query.filter_by(report_id=report.id, status="scheduled")
            .filter(Meeting.scheduled_at > now)
            .order_by(Meeting.scheduled_at)
            .first()
        )
        rows.append(
            {
                "report": report,
                "series": series,
                "next": next_meeting,
                "days_since": report.days_since_last_1on1,
                "open_count": len(open_action_items(report.id)),
            }
        )
    return render_template("reports/list.html", rows=rows)


@bp.get("/new")
def new():
    return render_template("reports/form.html", report=None)


@bp.post("/")
def create():
    report = Report(
        name=request.form["name"].strip(),
        role=request.form.get("role", "").strip(),
        start_date=_parse_date(request.form.get("start_date")),
    )
    db.session.add(report)
    db.session.commit()
    return redirect(url_for("reports.detail", report_id=report.id))


@bp.get("/<int:report_id>")
def detail(report_id: int):
    report = _get_report(report_id)
    series = report.active_series
    if series:
        ensure_next_meeting(series)
        db.session.commit()

    past_meetings = (
        Meeting.query.filter_by(report_id=report.id, status="done")
        .order_by(Meeting.scheduled_at.desc())
        .all()
    )
    upcoming = (
        Meeting.query.filter_by(report_id=report.id, status="scheduled")
        .order_by(Meeting.scheduled_at)
        .all()
    )
    sparkline = mood_sparkline(list(reversed(past_meetings)), width=520, height=56)
    return render_template(
        "reports/detail.html",
        report=report,
        series=series,
        past_meetings=past_meetings,
        upcoming=upcoming,
        open_items=open_action_items(report.id),
        sparkline=sparkline,
    )


@bp.get("/<int:report_id>/edit")
def edit(report_id: int):
    return render_template("reports/form.html", report=_get_report(report_id))


@bp.post("/<int:report_id>/edit")
def update(report_id: int):
    report = _get_report(report_id)
    report.name = request.form["name"].strip()
    report.role = request.form.get("role", "").strip()
    report.start_date = _parse_date(request.form.get("start_date"))
    db.session.commit()
    return redirect(url_for("reports.detail", report_id=report.id))


@bp.post("/<int:report_id>/archive")
def archive(report_id: int):
    report = _get_report(report_id)
    report.archived = True
    for series in report.series:
        series.active = False
    db.session.commit()
    return redirect(url_for("dashboard.index"))


@bp.post("/<int:report_id>/schedule")
def schedule(report_id: int):
    """Schedule the next 1:1: a one-off meeting, optionally set to repeat."""
    report = _get_report(report_id)
    when = datetime.strptime(
        f"{request.form['date']} {request.form.get('time') or '10:00'}", "%Y-%m-%d %H:%M"
    )
    repeat = request.form.get("repeat", "none")

    series = None
    if repeat in Series.CADENCES:
        series = report.active_series or Series(report_id=report.id)
        series.cadence = repeat
        series.day_of_week = when.weekday()
        series.time_of_day = when.time()
        series.duration_minutes = int(request.form.get("duration_minutes") or 30)
        series.active = True
        db.session.add(series)
        db.session.flush()

    meeting = Meeting(
        report_id=report.id,
        series_id=series.id if series else None,
        scheduled_at=when,
        status="scheduled",
    )
    db.session.add(meeting)
    db.session.commit()
    return redirect(url_for("meetings.detail", meeting_id=meeting.id))


@bp.post("/<int:report_id>/series/toggle")
def toggle_series(report_id: int):
    report = _get_report(report_id)
    series = report.active_series or (report.series[-1] if report.series else None)
    if series:
        series.active = not series.active
        db.session.flush()
        ensure_next_meeting(series)
        db.session.commit()
    return redirect(url_for("reports.detail", report_id=report.id))


@bp.post("/<int:report_id>/salary")
def add_salary(report_id: int):
    report = _get_report(report_id)
    change = SalaryChange(
        report_id=report.id,
        effective_date=_parse_date(request.form["effective_date"]) or date.today(),
        amount_cents=int(round(float(request.form["amount"]) * 100)),
        currency=request.form.get("currency", "USD").strip() or "USD",
        change_type=request.form.get("change_type", "raise"),
        note=request.form.get("note", "").strip(),
    )
    db.session.add(change)
    db.session.commit()
    return redirect(url_for("reports.detail", report_id=report.id))


@bp.post("/<int:report_id>/salary/<int:change_id>/delete")
def delete_salary(report_id: int, change_id: int):
    change = db.session.get(SalaryChange, change_id)
    if change is None or change.report_id != report_id:
        abort(404)
    db.session.delete(change)
    db.session.commit()
    return redirect(url_for("reports.detail", report_id=report_id))


def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()
