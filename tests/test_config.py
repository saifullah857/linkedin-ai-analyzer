"""
tests/test_config.py

Regression coverage for a real bug: Flask-SQLAlchemy resolves a
relative sqlite:/// URL against app.instance_path, NOT the process's
working directory. "sqlite:///instance/database/app.db" silently
resolved to ".../instance/instance/database/app.db" and failed with
"unable to open database file" -- on every OS, not just Windows.

_resolve_sqlite_url() in config.py guards against this by rewriting
any relative sqlite:/// URL to an absolute one before Flask ever sees
it. These tests pin that behavior down directly.
"""

from __future__ import annotations

from config import _resolve_sqlite_url, BASE_DIR
import os


def test_relative_sqlite_url_is_rewritten_absolute():
    resolved = _resolve_sqlite_url("sqlite:///instance/database/app.db")
    assert resolved == f"sqlite:///{os.path.join(BASE_DIR, 'instance/database/app.db')}"
    assert os.path.isabs(resolved.replace("sqlite:///", "", 1))


def test_already_absolute_sqlite_url_is_left_unchanged():
    abs_url = f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'database', 'app.db')}"
    assert _resolve_sqlite_url(abs_url) == abs_url


def test_four_slash_absolute_form_is_left_unchanged():
    url = "sqlite:////var/data/app.db"
    assert _resolve_sqlite_url(url) == url


def test_non_sqlite_urls_pass_through_untouched():
    pg_url = "postgresql://user:pass@localhost:5432/mydb"
    assert _resolve_sqlite_url(pg_url) == pg_url


def test_flask_sqlalchemy_actually_opens_the_resolved_relative_url(tmp_path, monkeypatch):
    """End-to-end: the exact scenario that broke -- a relative sqlite URL
    from .env-style config must still result in a working database."""
    monkeypatch.chdir(tmp_path)
    from flask import Flask
    from flask_sqlalchemy import SQLAlchemy

    app = Flask(__name__)
    app.config["SQLALCHEMY_DATABASE_URI"] = _resolve_sqlite_url(
        "sqlite:///instance/database/app.db"
    )
    db_dir = os.path.dirname(app.config["SQLALCHEMY_DATABASE_URI"].replace("sqlite:///", "", 1))
    os.makedirs(db_dir, exist_ok=True)

    db = SQLAlchemy()
    db.init_app(app)
    with app.app_context():
        db.create_all()  # would raise "unable to open database file" pre-fix
