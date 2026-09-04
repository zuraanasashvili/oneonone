# oneonone

A single-user 1:1 meeting tracker for managers. Server-rendered, minimal JavaScript, SQLite.

Track one-off or recurring 1:1s with your direct reports: notes, action items that carry forward,
meeting history with mood trends, and salary change history.

## Quick start

**Local (Python 3.12+)**

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -e .                          # the app and its dependencies
pip install pytest ruff                   # dev tools (or: pip install --group dev, pip 25.1+)
export FLASK_APP=app
flask db upgrade                          # create the schema
python seed.py --fresh                    # optional demo data (5 reports, ~4 months of history)
flask run                                 # http://localhost:5000
```

**Production mode (gunicorn)**

```bash
gunicorn -b 0.0.0.0:8000 'app:create_app()'
```

**Docker**

```bash
docker build -t oneonone .
docker run -p 8000:8000 -v oneonone-data:/data oneonone   # http://localhost:8000
```

The container runs `flask db upgrade` on start (falling back to `db.create_all()`), then serves
via gunicorn. The SQLite file lives on the mounted `/data` volume.

**Tests & lint**

```bash
pytest              # recurrence, carry-over, charts, routes
ruff check .        # lint
ruff format --check .
```

## Features

- **Schedule 1:1s** — pick a date/time for a one-off, or set it to repeat weekly / biweekly / monthly (pause & resume)
- **Action items** — talking points and follow-ups in one list, owned by either side, carry over until done or dropped
- **Conduct a 1:1** — per-meeting notes and a mood rating on completion
- **History & trends** — past meetings with mood ratings, rendered as an inline SVG sparkline
- **Salary history** — dated comp changes with type (hire / raise / promotion / adjustment)
- **Dashboard** — upcoming & past-due meetings, all open action items (linked to their 1:1), "days since last 1:1" per report
- **Timeline** — every scheduled 1:1 across the team, grouped by month
- **Reports** — all teammates with role, cadence, next/last 1:1, salary, and open-item count

## Design decisions

**Server-rendered, almost no JavaScript.** Flask + Jinja templates; the only JS is progressive
enhancement (confirm dialogs, textarea auto-resize) — the app is fully usable with JS disabled.
The mood sparkline is hand-rolled inline SVG generated server-side.

**SQLite.** A single-user manager tool is read-mostly, low-concurrency — SQLite is the right
sized tool. Money is stored as integer cents; datetimes are naive UTC.

**One-off meetings or recurring series.** A meeting can stand alone (`series_id` is null) or belong
to a recurring series. Scheduling with a repeat cadence creates/updates the report's active series;
scheduling without one just books a single meeting.

**Lazy recurrence, no scheduler.** There is no cron. Each active series always keeps one
upcoming `scheduled` meeting; the next instance is materialized when the dashboard, timeline, or
reports page loads, or when a meeting is completed/cancelled. See `app/services/recurrence.py`.

**Action items carry over by query, never copied.** Open items are queried per-report, so they
appear on every meeting until resolved — no duplication across instances. See
`app/services/carryover.py`.

## Layout

```
app/
  models.py              # Report, Series, Meeting, ActionItem, SalaryChange
  services/recurrence.py # lazy meeting materialization (one-off + recurring)
  services/carryover.py  # open action-item queries
  services/charts.py     # server-side SVG sparklines
  routes/                # dashboard (+ timeline), reports (+ list, salary, scheduling), meetings (+ action items)
  templates/             # Jinja2: base, dashboard, timeline, report list/detail/form, meeting detail
  static/                # one hand-written stylesheet, ~15 lines of vanilla JS
seed.py                  # demo dataset
tests/                   # pytest: recurrence, carry-over, charts, routes
migrations/              # Alembic
```

## Not in scope (yet)

No login or multi-user — anyone who can reach the app sees everything, so don't expose it to a
network without adding auth. No calendar sync, notifications, or deployment config.
