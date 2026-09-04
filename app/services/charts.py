"""Server-side inline SVG charts — zero JavaScript."""

from app.models import Meeting


def mood_sparkline(meetings: list[Meeting], width: int = 240, height: int = 48) -> str:
    """An inline SVG sparkline of mood (1-5) across completed meetings.

    Returns an empty string when there is nothing to plot.
    """
    points = [m.mood for m in meetings if m.status == "done" and m.mood is not None]
    if len(points) < 2:
        return ""

    pad = 6
    inner_w = width - 2 * pad
    inner_h = height - 2 * pad
    step_x = inner_w / (len(points) - 1)
    # mood 5 -> y at top, mood 1 -> y at bottom
    coords = [(pad + i * step_x, pad + inner_h * (5 - mood) / 4) for i, mood in enumerate(points)]
    path = " ".join(f"{x:.1f},{y:.1f}" for x, y in coords)
    dots = "".join(
        f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" class="spark-dot" />' for x, y in coords
    )
    return (
        f'<svg viewBox="0 0 {width} {height}" width="{width}" height="{height}" '
        f'class="sparkline" role="img" aria-label="Mood trend over time">'
        f'<polyline points="{path}" class="spark-line" />{dots}</svg>'
    )
