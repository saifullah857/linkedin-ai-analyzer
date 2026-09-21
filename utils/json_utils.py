"""
utils/json_utils.py

Shared helpers for parsing LLM JSON responses. Every agent in Chapter 1
duplicated a `_safe_json_parse` function; Chapter 2 consolidates that
here so new agents (ats, career, keyword, content, recruiter,
comparison, report) share one implementation.
"""

from __future__ import annotations

import json
import re


def safe_json_parse(content: str) -> dict:
    """Best-effort JSON parsing that tolerates markdown code fences and
    stray prose the model sometimes adds before/after the JSON object.

    Args:
        content: raw text returned by an Agno agent run.

    Returns:
        Parsed dict. On failure, returns
        {"error": "...", "raw": content} so callers can still store
        and display something instead of crashing the pipeline.
    """
    if not content:
        return {"error": "Empty agent response", "raw": ""}

    cleaned = content.strip()

    if cleaned.startswith("```"):
        cleaned = cleaned.strip("`")
        if cleaned.lower().startswith("json"):
            cleaned = cleaned[4:]
        cleaned = cleaned.strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback: grab the first {...} block in case the model added
    # commentary before/after the JSON object.
    match = re.search(r"\{.*\}", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return {"error": "Could not parse agent response as JSON", "raw": content}


def clamp_score(value, default: int = 0, lo: int = 0, hi: int = 100) -> int:
    """Coerce a model-provided score into a safe int within [lo, hi].

    Agents occasionally return floats, strings, or None for score
    fields; downstream templates and PDF export assume plain ints.
    """
    try:
        num = int(round(float(value)))
    except (TypeError, ValueError):
        return default
    return max(lo, min(hi, num))
