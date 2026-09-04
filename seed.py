"""Seed the database with a believable demo dataset.

Usage:
    python seed.py          # fill the configured database
    python seed.py --fresh  # drop existing data first
"""

import random
import sys
from datetime import date, timedelta

from app import create_app
from app.extensions import db
from app.models import ActionItem, Meeting, Report, SalaryChange, Series, utcnow
from app.services.recurrence import ensure_next_meeting

PEOPLE = [
    (
        "Employee 1",
        "Senior Engineer",
        date(2023, 3, 13),
        2,
        145_000,
        [
            (date(2023, 3, 13), 132_000, "hire", ""),
            (date(2024, 4, 1), 140_000, "raise", "Annual review"),
            (date(2025, 4, 1), 145_000, "raise", "Annual review"),
        ],
    ),
    (
        "Employee 2",
        "Engineer",
        date(2024, 6, 3),
        1,
        98_000,
        [
            (date(2024, 6, 3), 95_000, "hire", ""),
            (date(2025, 4, 1), 98_000, "raise", "Annual review"),
        ],
    ),
    (
        "Employee 3",
        "Staff Engineer",
        date(2022, 1, 10),
        3,
        172_000,
        [
            (date(2022, 1, 10), 150_000, "hire", ""),
            (date(2023, 4, 1), 160_000, "raise", ""),
            (date(2024, 4, 1), 172_000, "promotion", "Promoted to Staff"),
        ],
    ),
    (
        "Employee 4",
        "Junior Engineer",
        date(2025, 2, 17),
        4,
        78_000,
        [
            (date(2025, 2, 17), 78_000, "hire", ""),
        ],
    ),
    (
        "Employee 5",
        "Engineer",
        date(2023, 9, 4),
        0,
        118_000,
        [
            (date(2023, 9, 4), 110_000, "hire", ""),
            (date(2024, 4, 1), 115_000, "raise", ""),
            (date(2025, 4, 1), 118_000, "adjustment", "Market adjustment"),
        ],
    ),
]

TOPICS = [
    "Career goals for next quarter",
    "Feedback on code review turnaround",
    "On-call rotation concerns",
    "Pairing with the platform team",
    "Conference talk proposal",
    "Tech debt in the billing service",
    "Mentoring the new intern",
    "Sprint retrospective takeaways",
]

NOTES = [
    "Discussed progress on the migration. Wants more ownership of the design doc.",
    "Good conversation about team dynamics. Raised concern about meeting load.",
    "Reviewed quarterly goals. On track, needs support with cross-team comms.",
    "Talked about growth toward senior. Agreed on a stretch project.",
    "Short one this week — mostly status updates.",
]


def seed(fresh: bool = False) -> None:
    app = create_app()
    with app.app_context():
        if fresh:
            db.drop_all()
        db.create_all()

        if Report.query.first():
            print("Database already has data; use --fresh to reseed.")
            return

        rng = random.Random(42)
        now = utcnow()

        for name, role, start, dow, _salary, history in PEOPLE:
            report = Report(name=name, role=role, start_date=start)
            db.session.add(report)
            db.session.flush()

            series = Series(
                report_id=report.id,
                cadence=rng.choice(["weekly", "biweekly"]),
                day_of_week=dow,
                active=True,
            )
            db.session.add(series)
            db.session.flush()

            for eff, amount, ctype, note in history:
                db.session.add(
                    SalaryChange(
                        report_id=report.id,
                        effective_date=eff,
                        amount_cents=amount * 100,
                        change_type=ctype,
                        note=note,
                    )
                )

            # ~4 months of completed meetings in the past.
            weeks = 16
            step = 7 if series.cadence == "weekly" else 14
            first = now - timedelta(weeks=weeks)
            offset = (dow - first.weekday()) % 7
            scheduled = first + timedelta(days=offset, hours=10)
            while scheduled < now - timedelta(days=3):
                meeting = Meeting(
                    series_id=series.id,
                    report_id=report.id,
                    scheduled_at=scheduled,
                    status="done",
                    notes=rng.choice(NOTES),
                    mood=rng.choices([1, 2, 3, 4, 5], weights=[5, 10, 25, 40, 20])[0],
                    completed_at=scheduled + timedelta(minutes=30),
                )
                db.session.add(meeting)
                db.session.flush()
                for topic in rng.sample(TOPICS, k=rng.randint(1, 3)):
                    db.session.add(
                        ActionItem(
                            report_id=report.id,
                            meeting_id=meeting.id,
                            text=topic,
                            owner=rng.choice(["manager", "report"]),
                            status="done",
                        )
                    )
                if rng.random() < 0.5:
                    db.session.add(
                        ActionItem(
                            report_id=report.id,
                            meeting_id=meeting.id,
                            text=rng.choice(
                                [
                                    "Share the design doc template",
                                    "Book skip-level chat",
                                    "Review promotion packet draft",
                                    "Send reading list on system design",
                                ]
                            ),
                            owner=rng.choice(["manager", "report"]),
                            status=rng.choice(["done", "done", "dropped"]),
                        )
                    )
                scheduled += timedelta(days=step)

            # One upcoming meeting (lazy recurrence from the real "now").
            ensure_next_meeting(series, now)
            db.session.flush()

            # A couple of currently-open action items.
            for text, owner in rng.sample(
                [
                    ("Prepare mid-year review notes", "manager"),
                    ("Draft conference talk abstract", "report"),
                    ("Update onboarding doc", "report"),
                    ("Approve expense report", "manager"),
                ],
                k=2,
            ):
                db.session.add(
                    ActionItem(
                        report_id=report.id,
                        meeting_id=None,
                        text=text,
                        owner=owner,
                        due_date=date.today() + timedelta(days=rng.randint(2, 14)),
                    )
                )

        db.session.commit()
        print(f"Seeded {len(PEOPLE)} reports with history.")


if __name__ == "__main__":
    seed(fresh="--fresh" in sys.argv)
