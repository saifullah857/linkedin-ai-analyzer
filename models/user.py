"""
models/user.py

Optional user account model. Login is NOT required to run an
analysis -- an anonymous visitor can still use /analyze -- but a
logged-in user gets their past reports listed on a dashboard instead
of having to keep the analysis_id URL around.

Passwords are hashed with Werkzeug's PBKDF2 helpers. Nothing about
this model ever touches the user's Groq API key; that continues to
live only in flask.session, exactly as in Chapter 1.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

from models import db


def _uuid() -> str:
    return uuid.uuid4().hex


class User(UserMixin, db.Model):
    """A registered user. Optional -- analyses work without an account."""

    __tablename__ = "users"

    id = db.Column(db.String(32), primary_key=True, default=_uuid)
    name = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, raw_password: str) -> None:
        self.password_hash = generate_password_hash(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return check_password_hash(self.password_hash, raw_password)

    def to_dict(self) -> dict:
        return {"id": self.id, "name": self.name, "email": self.email}
