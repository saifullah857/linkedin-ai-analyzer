"""
tools/comparison_tool.py

Deterministic diffing between the parsed resume and the LinkedIn
profile data. As with scoring_tool, set differences should be exact
and reproducible rather than left to the LLM to eyeball -- the
Comparison Agent uses these results as ground truth and then writes
the human-readable recommendations on top of them.
"""

from __future__ import annotations

import re
from agno.tools import Toolkit


def _normalize_terms(value) -> set:
    """Turn a string, comma-separated string, or list into a
    normalized (lowercase, stripped) set of terms."""
    if not value:
        return set()
    if isinstance(value, str):
        parts = re.split(r"[,\n;]+", value)
    else:
        parts = list(value)
    return {p.strip().lower() for p in parts if p and p.strip()}


class ComparisonTool(Toolkit):
    """Set-based comparison helpers for resume vs LinkedIn data."""

    def __init__(self):
        super().__init__(name="comparison_tool")
        self.register(self.diff_skills)
        self.register(self.diff_keywords)
        self.register(self.diff_text_blocks)

    def diff_skills(self, resume_skills: list, linkedin_skills) -> dict:
        """Compare the resume's skill list against LinkedIn's skill list.

        Args:
            resume_skills: list of skills extracted from the resume.
            linkedin_skills: LinkedIn skills as a list or comma-separated string.

        Returns:
            {
              "only_on_resume": [...],
              "only_on_linkedin": [...],
              "on_both": [...],
              "overlap_percent": int
            }
        """
        resume_set = _normalize_terms(resume_skills)
        linkedin_set = _normalize_terms(linkedin_skills)

        only_resume = sorted(resume_set - linkedin_set)
        only_linkedin = sorted(linkedin_set - resume_set)
        both = sorted(resume_set & linkedin_set)

        union_size = len(resume_set | linkedin_set) or 1
        overlap_percent = round((len(both) / union_size) * 100)

        return {
            "only_on_resume": only_resume,
            "only_on_linkedin": only_linkedin,
            "on_both": both,
            "overlap_percent": overlap_percent,
        }

    def diff_keywords(self, resume_text: str, linkedin_text: str, category: str = "all") -> dict:
        """Compare which bank keywords appear in resume text vs LinkedIn text.

        Args:
            resume_text: raw resume text.
            linkedin_text: concatenated LinkedIn about/headline/experience text.
            category: keyword bank category (see tools.keyword_tool).

        Returns:
            {"resume_only": [...], "linkedin_only": [...], "both": [...]}
        """
        from tools.keyword_tool import KeywordTool

        kw_tool = KeywordTool()
        resume_found = set(kw_tool.find_keywords_in_text(resume_text, category))
        linkedin_found = set(kw_tool.find_keywords_in_text(linkedin_text, category))

        return {
            "resume_only": sorted(resume_found - linkedin_found),
            "linkedin_only": sorted(linkedin_found - resume_found),
            "both": sorted(resume_found & linkedin_found),
        }

    def diff_text_blocks(self, resume_items: list, linkedin_text: str) -> dict:
        """Flag resume items (projects/experience titles) that don't
        appear to be mentioned anywhere in the LinkedIn text at all,
        which usually means they're missing from the profile.

        Args:
            resume_items: list of strings (e.g. project or job titles).
            linkedin_text: concatenated LinkedIn text to search within.

        Returns:
            {"likely_missing_from_linkedin": [...]}
        """
        linkedin_lower = (linkedin_text or "").lower()
        missing = []
        for item in resume_items or []:
            if not item:
                continue
            # Use the first few significant words as a fuzzy presence check
            probe = " ".join(str(item).lower().split()[:3])
            if probe and probe not in linkedin_lower:
                missing.append(item)
        return {"likely_missing_from_linkedin": missing}
