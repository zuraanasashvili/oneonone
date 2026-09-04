"""Meeting page, action items, and completion flow."""

from datetime import date, datetime

from flask import Blueprint, abort, redirect, render_template, request, url_for

from app.extensions import db
from app.models import ActionItem, Meeting, utcnow
from app.services.carryover import open_action_items
from app.services.recurrence import ensure_next_meeting

bp = Blueprint("meetings", __name__)


def _get_meeting(meeting_id: int) -> Meeting:
    meeting = db.session.get(Meeting, meeting_id)
    if meeting is None:
        abort(404)
    return meeting


@bp.get("/meetings/<int:meeting_id>")
def detail(meeting_id: int):
    meeting = _get_meeting(meeting_id)
    return render_template(
        "meetings/detail.html",
        meeting=meeting,
        open_items=open_action_items(meeting.report_id),
        today=date.today(),
    )


@bp.post("/meetings/<int:meeting_id>/notes")
def save_notes(meeting_id: int):
    meeting = _get_meeting(meeting_id)
    meeting.notes = request.form.get("notes", "")
    db.session.commit()
    return redirect(url_for("meetings.detail", meeting_id=meeting.id))


@bp.post("/meetings/<int:meeting_id>/action-items")
def add_action_item(meeting_id: int):
    meeting = _get_meeting(meeting_id)
    text = request.form.get("text", "").strip()
    if text:
        due = request.form.get("due_date")
        item = ActionItem(
            report_id=meeting.report_id,
            meeting_id=meeting.id,
            text=text,
            owner=request.form.get("owner", "manager"),
            due_date=datetime.strptime(due, "%Y-%m-%d").date() if due else None,
        )
        db.session.add(item)
        db.session.commit()
    return redirect(url_for("meetings.detail", meeting_id=meeting.id))


@bp.post("/reports/<int:report_id>/action-items")
def add_action_item_for_report(report_id: int):
    text = request.form.get("text", "").strip()
    if text:
        due = request.form.get("due_date")
        item = ActionItem(
            report_id=report_id,
            meeting_id=None,
            text=text,
            owner=request.form.get("owner", "manager"),
            due_date=datetime.strptime(due, "%Y-%m-%d").date() if due else None,
        )
        db.session.add(item)
        db.session.commit()
    return redirect(url_for("reports.detail", report_id=report_id))


@bp.post("/action-items/<int:item_id>/<status>")
def set_action_item_status(item_id: int, status: str):
    if status not in ("open", "done", "dropped"):
        abort(400)
    item = db.session.get(ActionItem, item_id)
    if item is None:
        abort(404)
    item.status = status
    db.session.commit()
    return redirect(request.referrer or url_for("dashboard.index"))


@bp.post("/meetings/<int:meeting_id>/complete")
def complete(meeting_id: int):
    meeting = _get_meeting(meeting_id)
    if meeting.status != "scheduled":
        return redirect(url_for("meetings.detail", meeting_id=meeting.id))

    meeting.status = "done"
    meeting.completed_at = utcnow()
    meeting.notes = request.form.get("notes", meeting.notes)
    mood = request.form.get("mood")
    meeting.mood = int(mood) if mood else None
    db.session.flush()

    # Recurring series: materialize the next meeting. Open action items carry
    # forward automatically (queried per-report), so nothing is copied.
    ensure_next_meeting(meeting.series)

    db.session.commit()
    return redirect(url_for("reports.detail", report_id=meeting.report_id))


@bp.post("/meetings/<int:meeting_id>/cancel")
def cancel(meeting_id: int):
    meeting = _get_meeting(meeting_id)
    if meeting.status == "scheduled":
        meeting.status = "cancelled"
        db.session.flush()
        ensure_next_meeting(meeting.series)
        db.session.commit()
    return redirect(request.referrer or url_for("dashboard.index"))
