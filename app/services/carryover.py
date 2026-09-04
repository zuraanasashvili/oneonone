"""Carry-over of open action items.

Action items are NEVER copied between meetings. Open items are queried
per-report, so they naturally appear on every meeting until marked done or
dropped.
"""

from app.models import ActionItem


def open_action_items(report_id: int) -> list[ActionItem]:
    return (
        ActionItem.query.filter_by(report_id=report_id, status="open")
        .order_by(ActionItem.created_at)
        .all()
    )
