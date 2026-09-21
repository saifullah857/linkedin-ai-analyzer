"""
tests/test_auth.py

Covers the optional-login flow: register, login, wrong password,
duplicate email, logout, and the dashboard report-history page.
"""

from __future__ import annotations

from models.user import User


def _register(client, email="jane@example.com", password="password123", name="Jane Doe"):
    return client.post(
        "/register",
        data={"name": name, "email": email, "password": password},
        follow_redirects=True,
    )


def test_register_creates_user_and_logs_in(client, db):
    resp = _register(client)
    assert resp.status_code == 200
    assert b"My Reports" in resp.data
    assert User.query.filter_by(email="jane@example.com").first() is not None


def test_password_is_hashed_not_stored_plain(client, db):
    _register(client)
    user = User.query.filter_by(email="jane@example.com").first()
    assert user.password_hash != "password123"
    assert user.check_password("password123") is True
    assert user.check_password("wrong-password") is False


def test_duplicate_email_rejected(client, db):
    _register(client)
    client.get("/logout")
    resp = _register(client)
    assert b"already exists" in resp.data


def test_login_with_wrong_password_fails(client, db):
    _register(client)
    client.get("/logout")
    resp = client.post(
        "/login",
        data={"email": "jane@example.com", "password": "wrong"},
        follow_redirects=True,
    )
    assert b"Invalid email or password" in resp.data


def test_login_success_reaches_dashboard(client, db):
    _register(client)
    client.get("/logout")
    resp = client.post(
        "/login",
        data={"email": "jane@example.com", "password": "password123"},
        follow_redirects=True,
    )
    assert b"My Reports" in resp.data


def test_logout_then_dashboard_redirects(client, db):
    _register(client)
    client.get("/logout")
    resp = client.get("/dashboard")
    assert resp.status_code == 302


def test_dashboard_empty_state_for_new_user(client, db):
    _register(client)
    resp = client.get("/dashboard")
    assert b"haven't run an analysis" in resp.data
