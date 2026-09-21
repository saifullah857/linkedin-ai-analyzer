"""
tools/resume_tool.py

Heuristic pre-processing of raw resume text before it is handed to
the Resume Analysis Agent. Regex-based extraction handles the "easy"
fields (email, phone) deterministically; the LLM agent still does the
semantic heavy-lifting (skills, projects, experience parsing).
"""

from __future__ import annotations

import re
from agno.tools import Toolkit

EMAIL_RE = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
PHONE_RE = re.compile(r"(\+?\d{1,3}[\s-]?)?(\(?\d{2,4}\)?[\s-]?)?\d{3,4}[\s-]?\d{3,4}")

SECTION_HEADERS = [
    "experience", "work experience", "education", "skills", "projects",
    "certifications", "achievements", "languages", "summary", "objective",
]


class ResumeTool(Toolkit):
    """Deterministic pre-parsing helpers for resume text."""

    def __init__(self):
        super().__init__(name="resume_tool")
        self.register(self.extract_contact_info)
        self.register(self.split_into_sections)

    def extract_contact_info(self, text: str) -> dict:
        """Extract email and phone number via regex.

        Args:
            text: raw resume text.

        Returns:
            {"email": str|None, "phone": str|None}
        """
        email_match = EMAIL_RE.search(text or "")
        phone_match = PHONE_RE.search(text or "")
        return {
            "email": email_match.group(0) if email_match else None,
            "phone": phone_match.group(0).strip() if phone_match else None,
        }

    def split_into_sections(self, text: str) -> dict:
        """Split resume text into rough sections based on common headers.

        This is a best-effort heuristic (resume formats vary wildly).
        The Resume Analysis Agent should still read the full raw_text
        for anything this heuristic misses.

        Args:
            text: raw resume text.

        Returns:
            Dict mapping section name -> text block.
        """
        if not text:
            return {}

        lines = text.split("\n")
        sections: dict[str, list[str]] = {}
        current = "header"
        sections[current] = []

        for line in lines:
            stripped = line.strip().lower().rstrip(":")
            matched_header = None
            for header in SECTION_HEADERS:
                if stripped == header or (len(stripped) < 30 and stripped.startswith(header)):
                    matched_header = header
                    break
            if matched_header:
                current = matched_header
                sections.setdefault(current, [])
                continue
            sections.setdefault(current, []).append(line)

        return {k: "\n".join(v).strip() for k, v in sections.items() if "\n".join(v).strip()}
