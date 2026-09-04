from datetime import datetime

from app.models import Meeting
from app.services.charts import mood_sparkline


def _done(mood):
    return Meeting(
        mood=mood, status="done", scheduled_at=datetime(2026, 1, 1), report_id=1, series_id=1
    )


def test_empty_when_no_data():
    assert mood_sparkline([]) == ""


def test_empty_with_single_point():
    assert mood_sparkline([_done(3)]) == ""


def test_svg_rendered_for_two_points():
    svg = mood_sparkline([_done(2), _done(4)])
    assert svg.startswith("<svg")
    assert "<polyline" in svg
    assert svg.count("<circle") == 2


def test_meetings_without_mood_skipped():
    no_mood = Meeting(
        mood=None, status="done", scheduled_at=datetime(2026, 1, 1), report_id=1, series_id=1
    )
    svg = mood_sparkline([_done(3), no_mood, _done(5)])
    assert svg.count("<circle") == 2


def test_scheduled_meetings_ignored():
    scheduled = Meeting(
        mood=None, status="scheduled", scheduled_at=datetime(2026, 1, 1), report_id=1, series_id=1
    )
    assert mood_sparkline([scheduled, _done(3)]) == ""


def test_scaling_extremes():
    # mood 5 should map to the top, mood 1 to the bottom of the inner area.
    svg = mood_sparkline([_done(5), _done(1)])
    assert 'cy="6.0"' in svg  # pad
    assert 'cy="42.0"' in svg  # height - pad
