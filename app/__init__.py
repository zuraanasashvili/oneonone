"""Application factory for the oneonone app."""

import os
from pathlib import Path

from flask import Flask

from app.extensions import db, migrate


def create_app(config: dict | None = None) -> Flask:
    app = Flask(__name__)

    instance_path = Path(app.instance_path)
    instance_path.mkdir(parents=True, exist_ok=True)

    app.config.from_mapping(
        SQLALCHEMY_DATABASE_URI=os.environ.get(
            "DATABASE_URL", f"sqlite:///{instance_path / 'oneonone.db'}"
        ),
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if config:
        app.config.from_mapping(config)

    db.init_app(app)
    migrate.init_app(app, db)

    from app import models  # noqa: F401  (register models with SQLAlchemy)
    from app.routes import dashboard, meetings, reports

    app.register_blueprint(dashboard.bp)
    app.register_blueprint(reports.bp)
    app.register_blueprint(meetings.bp)

    return app
