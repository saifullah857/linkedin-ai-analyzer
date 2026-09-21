"""
services/groq_client.py

Builds an Agno-compatible Groq model instance from a user-supplied
API key that lives ONLY in the Flask session for that browser
session. This module never reads a key from environment variables
and never writes a key to disk or database.

Usage:
    from services.groq_client import get_groq_model
    model = get_groq_model(session["groq_api_key"])
"""

from __future__ import annotations

from agno.models.groq import Groq
from flask import current_app


class MissingGroqKeyError(Exception):
    """Raised when no Groq API key is present in the current session."""


def get_groq_model(api_key: str | None, model_id: str | None = None):
    """Construct an Agno Groq model bound to the user's own API key.

    Args:
        api_key: the user's Groq API key, read from flask.session.
        model_id: optional override; defaults to config.GROQ_MODEL.

    Returns:
        An agno.models.groq.Groq instance ready to hand to an Agent.

    Raises:
        MissingGroqKeyError: if api_key is falsy.
    """
    if not api_key:
        raise MissingGroqKeyError(
            "No Groq API key found in this session. Please enter your "
            "Groq API key on the analysis form before running the analysis."
        )

    resolved_model_id = model_id or current_app.config.get(
        "GROQ_MODEL", "llama-3.3-70b-versatile"
    )

    return Groq(id=resolved_model_id, api_key=api_key)
