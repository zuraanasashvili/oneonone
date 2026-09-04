"""Database models.

Conventions:
- All datetimes are stored in UTC (naive, via ``datetime.now(timezone.utc).replace(tzinfo=None)``).
- Money is stored as integer cents to avoid floating point errors.
"""

from datetime import UTC, date, datetime, time

from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


def utcnow() -> datetime:
    """Current UTC time as a naive datetime (SQLite-friendly)."""
    return datetime.now(UTC).replace(tzinfo=None)


class Report(db.Model):
    """A direct report of the manager using the app."""

    __tablename__ = "report"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
    role: Mapped[str] = mapped_column(default="")
    start_date: Mapped[date | None]
    archived: Mapped[bool] = mapped_column(default=False)

    series: Mapped[list["Series"]] = relationship(back_populates="report")
    meetings: Mapped[list["Meeting"]] = relationship(back_populates="report")
    action_items: Mapped[list["ActionItem"]] = relationship(back_populates="report")
    salary_changes: Mapped[list["SalaryChange"]] = relationship(
        back_populates="report", order_by="SalaryChange.effective_date"
    )

    @property
    def current_salary(self) -> "SalaryChange | None":
        """Most recent salary change on or before today."""
        today = date.today()
        effective = [c for c in self.salary_changes if c.effective_date <= today]
        return effective[-1] if effective else None

    @property
    def active_series(self) -> "Series | None":
        return next((s for s in self.series if s.active), None)


class Series(db.Model):
    """A recurring 1:1 series with a report (one active series per report)."""

    __tablename__ = "series"

    CADENCES = ("weekly", "biweekly", "monthly")

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("report.id"))
    cadence: Mapped[str] = mapped_column(default="weekly")
    day_of_week: Mapped[int] = mapped_column(default=0)  # 0 = Monday
    time_of_day: Mapped[time] = mapped_column(default=time(10, 0))
    duration_minutes: Mapped[int] = mapped_column(default=30)
    active: Mapped[bool] = mapped_column(default=True)

    report: Mapped[Report] = relationship(back_populates="series")
    meetings: Mapped[list["Meeting"]] = relationship(back_populates="series")


class Meeting(db.Model):
    """A single 1:1 meeting instance."""

    __tablename__ = "meeting"

    STATUSES = ("scheduled", "done", "cancelled")

    id: Mapped[int] = mapped_column(primary_key=True)
    series_id: Mapped[int] = mapped_column(ForeignKey("series.id"))
    report_id: Mapped[int] = mapped_column(ForeignKey("report.id"))
    scheduled_at: Mapped[datetime]
    status: Mapped[str] = mapped_column(default="scheduled")
    notes: Mapped[str] = mapped_column(default="")
    mood: Mapped[int | None]  # 1 (rough) .. 5 (great), set on completion
    completed_at: Mapped[datetime | None]

    series: Mapped[Series] = relationship(back_populates="meetings")
    report: Mapped[Report] = relationship(back_populates="meetings")
    agenda_items: Mapped[list["AgendaItem"]] = relationship(
        back_populates="meeting", order_by="AgendaItem.sort_order", cascade="all, delete-orphan"
    )


class AgendaItem(db.Model):
    """A talking point on a specific meeting's agenda."""

    __tablename__ = "agenda_item"

    id: Mapped[int] = mapped_column(primary_key=True)
    meeting_id: Mapped[int] = mapped_column(ForeignKey("meeting.id"))
    text: Mapped[str]
    raised_by: Mapped[str] = mapped_column(default="manager")  # manager | report
    covered: Mapped[bool] = mapped_column(default=False)
    sort_order: Mapped[int] = mapped_column(default=0)

    meeting: Mapped[Meeting] = relationship(back_populates="agenda_items")


class ActionItem(db.Model):
    """A commitment owned by either side, tied to a report.

    Open action items are never copied between meetings; they are simply
    queried per-report, which is how they "carry over" until resolved.
    """

    __tablename__ = "action_item"

    STATUSES = ("open", "done", "dropped")

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("report.id"))
    meeting_id: Mapped[int | None] = mapped_column(ForeignKey("meeting.id"))
    text: Mapped[str]
    owner: Mapped[str] = mapped_column(default="manager")  # manager | report
    due_date: Mapped[date | None]
    status: Mapped[str] = mapped_column(default="open")
    created_at: Mapped[datetime] = mapped_column(default=utcnow)

    report: Mapped[Report] = relationship(back_populates="action_items")


class SalaryChange(db.Model):
    """A compensation change in a report's salary history."""

    __tablename__ = "salary_change"

    CHANGE_TYPES = ("hire", "raise", "promotion", "adjustment")

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(ForeignKey("report.id"))
    effective_date: Mapped[date]
    amount_cents: Mapped[int]
    currency: Mapped[str] = mapped_column(default="USD")
    change_type: Mapped[str] = mapped_column(default="raise")
    note: Mapped[str] = mapped_column(default="")

    report: Mapped[Report] = relationship(back_populates="salary_changes")
