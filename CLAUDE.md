# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Single-user 1:1 meeting tracker for managers. Server-rendered Flask + Jinja, SQLite,
almost no JavaScript (progressive enhancement only). No auth — anyone reaching the app sees
everything.

## Commands

```bash
export FLASK_APP=app
flask db upgrade          # create/upgrade schema (Alembic)
flask run                 # dev server, http://localhost:5000
python seed.py --fresh    # demo data: 5 reports, ~4 months of history

pytest                    # all tests
pytest tests/test_recurrence.py::test_name   # single test
ruff check .              # lint
ruff format --check .

gunicorn -b 0.0.0.0:8000 'app:create_app()'  # production serve
```

Schema changes: edit `app/models.py`, then `flask db migrate -m "msg"` and `flask db upgrade`.

## Architecture

**App factory** (`app/__init__.py`): `create_app(config)` takes an optional config dict (tests
pass `TESTING` + in-memory SQLite URI). Extensions (`db`, `migrate`) are instantiated bare in
`app/extensions.py` and bound in the factory. Three blueprints: `dashboard`, `reports`, `meetings`.

**Domain model** (`app/models.py`) — vocab lives in class constants, honor them:
- `Report` → one *active* `Series` (`report.active_series`), many `Meeting`, `ActionItem`, `SalaryChange`.
- `Series.CADENCES = weekly|biweekly|monthly`, anchored by `day_of_week` (0=Mon) + `time_of_day`.
- `Meeting.STATUSES = scheduled|done|cancelled`; `mood` 1..5 set on completion.
- `AgendaItem.raised_by` / `ActionItem.owner` = `manager|report`.
- `ActionItem.STATUSES = open|done|dropped`; `SalaryChange.CHANGE_TYPES = hire|raise|promotion|adjustment`.

**Conventions (do not break):** datetimes are naive UTC — always use `utcnow()` from
`app/models.py`, never `datetime.now()`. Money is integer cents (`amount_cents`).

**Two services carry the non-obvious logic:**

- `services/recurrence.py` — **lazy materialization, no scheduler/cron.** Each active series
  keeps exactly one upcoming `scheduled` meeting. `ensure_next_meeting()` is called on
  dashboard load, meeting completion/cancellation, and series create/reactivate. Weekly/biweekly
  advance by `timedelta`; monthly is computed by month arithmetic (`advance()`).

- `services/carryover.py` — **two deliberately different carry-over semantics.** Action items
  are NEVER copied; `open_action_items(report_id)` re-queries open ones so they show on every
  meeting until resolved. Agenda items ARE copied: `copy_uncovered_agenda()` duplicates uncovered
  items into the next meeting on completion.

- `services/charts.py` — hand-rolled inline SVG mood sparkline, generated server-side.

## Tests

`tests/conftest.py` fixtures: `app` (in-memory SQLite, create_all/drop_all per test), `client`,
`db`, and pre-built `report` / `series`. Tests run inside the app context.
