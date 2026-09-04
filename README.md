# oneonone

A single-user 1:1 meeting tracker for managers. Server-rendered, minimal JavaScript, SQLite.

Track recurring 1:1s with your direct reports: agendas, notes, action items that carry forward,
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

- **Recurring 1:1 series** — weekly / biweekly / monthly, pause & resume
- **Shared agenda** — items attributed to manager or report; uncovered items roll forward
- **Action items** — owned by either side, carry over until done or dropped
- **History & trends** — past meetings with mood ratings, rendered as an inline SVG sparkline
- **Salary history** — dated comp changes with type (hire / raise / promotion / adjustment)
- **Dashboard** — upcoming meetings, all open action items, "days since last 1:1" per report

## Design decisions

**Server-rendered, almost no JavaScript.** Flask + Jinja templates; the only JS is progressive
enhancement (confirm dialogs, textarea auto-resize) — the app is fully usable with JS disabled.
The mood sparkline is hand-rolled inline SVG generated server-side.

**SQLite.** A single-user manager tool is read-mostly, low-concurrency — SQLite is the right
sized tool. Money is stored as integer cents; datetimes are naive UTC.

**Lazy recurrence, no scheduler.** There is no cron. Each active series always keeps one
upcoming `scheduled` meeting; the next instance is materialized when the dashboard loads or
when a meeting is completed/cancelled. See `app/services/recurrence.py`.

**Two different carry-over semantics, deliberately.**
Action items are *never copied* — open items are simply queried per-report, so they appear on
every meeting until resolved. Agenda items *are copied*: anything uncovered when a meeting is
completed is carried into the next instance. See `app/services/carryover.py`.

## Layout

```
app/
  models.py              # Report, Series, Meeting, AgendaItem, ActionItem, SalaryChange
  services/recurrence.py # lazy meeting materialization
  services/carryover.py  # agenda copy-forward, open action-item queries
  services/charts.py     # server-side SVG sparklines
  routes/                # dashboard, reports (+ salary, series), meetings (+ agenda, action items)
  templates/             # Jinja2: base, dashboard, report detail/form, meeting detail
  static/                # one hand-written stylesheet, ~15 lines of vanilla JS
seed.py                  # demo dataset
tests/                   # pytest: recurrence, carry-over, charts, routes
migrations/              # Alembic
```

## Not in scope (yet)

No login or multi-user — anyone who can reach the app sees everything, so don't expose it to a
network without adding auth. No calendar sync, notifications, or deployment config.
