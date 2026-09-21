"""
tests/conftest.py

Shared pytest fixtures. Uses an in-memory SQLite database and disables
CSRF so form-post tests don't need a token, matching how the app
factory is already environment-driven (config.py / config_map).
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

os.environ.setdefault("FLASK_ENV", "development")
os.environ.setdefault("SECRET_KEY", "test-only-secret")

from app import create_app
from models import db as _db


@pytest.fixture()
def app():
    application = create_app("development")
    application.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
        SQLALCHEMY_DATABASE_URI="sqlite:///:memory:",
        RATELIMIT_ENABLED=False,
    )
    with application.app_context():
        _db.drop_all()
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    return _db
