"""Carry-over semantics.

Two different behaviors, deliberately:
- Action items are NEVER copied. Open items are queried per-report, so they
  naturally appear on every subsequent meeting until marked done/dropped.
- Agenda items: uncovered items ARE copied into the next meeting when a
  meeting is completed, so raised topics don't get lost.
"""

from app.extensions import db
from app.models import ActionItem, AgendaItem, Meeting


def open_action_items(report_id: int) -> list[ActionItem]:
    return (
        ActionItem.query.filter_by(report_id=report_id, status="open")
        .order_by(ActionItem.created_at)
        .all()
    )


def copy_uncovered_agenda(from_meeting: Meeting, to_meeting: Meeting) -> list[AgendaItem]:
    """Copy uncovered agenda items from a completed meeting to the next one."""
    copied = []
    start_order = len(to_meeting.agenda_items)
    for i, item in enumerate(from_meeting.agenda_items):
        if item.covered:
            continue
        new_item = AgendaItem(
            meeting_id=to_meeting.id,
            text=item.text,
            raised_by=item.raised_by,
            covered=False,
            sort_order=start_order + i,
        )
        db.session.add(new_item)
        copied.append(new_item)
    return copied
