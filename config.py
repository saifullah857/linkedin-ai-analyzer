"""
config.py
Central configuration for the LinkedIn AI Profile Analyzer.

Loads values from environment variables (.env) and exposes a Config
object that Flask's app.config.from_object() consumes.

IMPORTANT: There is intentionally NO GROQ_API_KEY setting here.
Every user supplies their own Groq API key through the UI, and it is
kept only in the Flask session (server-side, signed, in-memory /
filesystem session store) for the duration of that session. It is
never written to the database or to any file on disk.
"""

import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INSTANCE_DIR = os.path.join(BASE_DIR, "instance")
DATABASE_DIR = os.path.join(INSTANCE_DIR, "database")
SESSION_DIR = os.path.join(INSTANCE_DIR, "flask_session")


def _resolve_sqlite_url(url: str) -> str:
    """Rewrite a relative sqlite:/// URL into an absolute one.

    Flask-SQLAlchemy resolves relative sqlite paths against
    ``app.instance_path``, not the process's working directory -- so a
    seemingly reasonable "sqlite:///instance/database/app.db" actually
    resolves to ".../instance/instance/database/app.db" and fails with
    "unable to open database file". Non-sqlite URLs (Postgres, MySQL,
    etc.) and already-absolute sqlite URLs pass through unchanged.
    """
    prefix = "sqlite:///"
    if not url.startswith(prefix) or url.startswith("sqlite:////"):
        return url
    relative_path = url[len(prefix):]
    if os.path.isabs(relative_path):
        return url
    return f"{prefix}{os.path.join(BASE_DIR, relative_path)}"


class Config:
    # --- Core Flask ---
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-only-insecure-key-change-me")
    SESSION_TYPE = os.getenv("SESSION_TYPE", "filesystem")
    SESSION_FILE_DIR = SESSION_DIR
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(hours=2)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # --- Database ---
    # NOTE: built from DATABASE_DIR (an absolute path). If DATABASE_URL is
    # supplied via .env with a *relative* sqlite:/// path, Flask-SQLAlchemy
    # resolves it against app.instance_path (NOT the working directory or
    # BASE_DIR) -- e.g. "sqlite:///instance/database/app.db" silently
    # resolves to ".../instance/instance/database/app.db" and fails with
    # "unable to open database file". _resolve_sqlite_url() below guards
    # against that by rewriting any relative sqlite:/// URL to an absolute
    # one before Flask ever sees it.
    SQLALCHEMY_DATABASE_URI = _resolve_sqlite_url(
        os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(DATABASE_DIR, 'app.db')}")
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Uploads ---
    UPLOAD_FOLDER = os.path.join(BASE_DIR, os.getenv("UPLOAD_FOLDER", "uploads"))
    REPORTS_FOLDER = os.path.join(BASE_DIR, os.getenv("REPORTS_FOLDER", "reports"))
    ALLOWED_EXTENSIONS = {"pdf"}
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH_MB", 10)) * 1024 * 1024

    # --- Vector DB (optional ChromaDB store for embeddings) ---
    VECTOR_DB_DIR = os.path.join(BASE_DIR, "vector_db")

    # --- Rate limiting ---
    RATE_LIMIT_DEFAULT = os.getenv("RATE_LIMIT_DEFAULT", "100 per hour")

    # --- Groq model defaults (the KEY is user-supplied, the model name is not secret) ---
    GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    GROQ_API_BASE = "https://api.groq.com/openai/v1"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True


config_map = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "default": DevelopmentConfig,
}
