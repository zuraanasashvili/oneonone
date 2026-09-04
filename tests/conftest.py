import pytest

from app import create_app
from app.extensions import db as _db
from app.models import Report, Series


@pytest.fixture()
def app():
    app = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
        }
    )
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def db(app):
    return _db


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def report(db):
    r = Report(name="Test Person", role="Engineer")
    _db.session.add(r)
    _db.session.commit()
    return r


@pytest.fixture()
def series(db, report):
    s = Series(report_id=report.id, cadence="weekly", day_of_week=1, active=True)
    _db.session.add(s)
    _db.session.commit()
    return s
