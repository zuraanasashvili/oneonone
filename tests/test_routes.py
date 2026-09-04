from app.models import ActionItem, Meeting, Report, utcnow


def test_dashboard_empty(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"No reports yet" in resp.data


def test_create_report(client, db):
    resp = client.post(
        "/reports/", data={"name": "Ada", "role": "Engineer"}, follow_redirects=False
    )
    assert resp.status_code == 302
    assert Report.query.filter_by(name="Ada").count() == 1


def test_report_detail(client, report):
    resp = client.get(f"/reports/{report.id}")
    assert resp.status_code == 200
    assert b"Test Person" in resp.data


def test_schedule_recurring_creates_meeting_and_series(client, report):
    resp = client.post(
        f"/reports/{report.id}/schedule",
        data={"date": "2026-09-16", "time": "14:00", "repeat": "weekly", "duration_minutes": "30"},
    )
    assert resp.status_code == 302
    meeting = Meeting.query.filter_by(report_id=report.id).one()
    assert meeting.status == "scheduled"
    assert meeting.series_id is not None
    assert meeting.series.cadence == "weekly"


def test_schedule_one_off_has_no_series(client, report):
    resp = client.post(
        f"/reports/{report.id}/schedule",
        data={"date": "2026-09-16", "time": "14:00", "repeat": "none"},
    )
    assert resp.status_code == 302
    meeting = Meeting.query.filter_by(report_id=report.id).one()
    assert meeting.series_id is None


def test_meeting_completion_flow(client, db, series):
    meeting = Meeting(
        series_id=series.id,
        report_id=series.report_id,
        scheduled_at=utcnow(),
        status="scheduled",
    )
    db.session.add(meeting)
    db.session.commit()

    resp = client.post(
        f"/meetings/{meeting.id}/complete",
        data={"notes": "went well", "mood": "4"},
    )
    assert resp.status_code == 302

    assert meeting.status == "done"
    assert meeting.mood == 4
    assert meeting.notes == "went well"

    # Completing a recurring meeting materializes the next scheduled one.
    next_meeting = (
        Meeting.query.filter_by(series_id=series.id, status="scheduled")
        .filter(Meeting.id != meeting.id)
        .one()
    )
    assert next_meeting.scheduled_at > meeting.scheduled_at


def test_action_item_status_change(client, db, report):
    item = ActionItem(report_id=report.id, text="do the thing")
    db.session.add(item)
    db.session.commit()
    resp = client.post(f"/action-items/{item.id}/done")
    assert resp.status_code == 302
    assert item.status == "done"


def test_add_salary(client, report):
    resp = client.post(
        f"/reports/{report.id}/salary",
        data={
            "effective_date": "2026-01-01",
            "amount": "120000",
            "currency": "USD",
            "change_type": "raise",
        },
    )
    assert resp.status_code == 302
    change = report.salary_changes[0]
    assert change.amount_cents == 12_000_000
    assert report.current_salary == change


def test_404_for_missing_report(client):
    assert client.get("/reports/999").status_code == 404
