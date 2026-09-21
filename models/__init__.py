"""
models package

Exposes a single shared SQLAlchemy `db` instance used across the app,
plus the ORM models. Import models AFTER db is created to avoid
circular imports (see models/report.py).
"""

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import models so they register with SQLAlchemy metadata when the
# package is imported (e.g. from app.py during db.create_all()).
from models.report import AnalysisReport, ResumeRecord  # noqa: E402,F401
from models.user import User  # noqa: E402,F401
