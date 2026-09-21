"""
tools/scoring_tool.py

Deterministic (non-LLM) scoring helpers. The LLM agents produce
qualitative judgments, but for numbers that should be *stable and
reproducible* (e.g. profile completeness, keyword coverage %) we
compute them in plain Python rather than trusting the model to do
arithmetic consistently.
"""

from __future__ import annotations

from agno.tools import Toolkit


class ScoringTool(Toolkit):
    """Deterministic scoring utilities shared across agents."""

    def __init__(self):
        super().__init__(name="scoring_tool")
        self.register(self.profile_completeness)
        self.register(self.keyword_coverage)
        self.register(self.weighted_overall_score)

    def profile_completeness(self, sections_present: dict) -> dict:
        """Compute a 0-100 completeness score from a dict of booleans.

        Args:
            sections_present: e.g. {"headline": True, "about": False, ...}

        Returns:
            {"score": int, "missing": [list of missing section names]}
        """
        if not sections_present:
            return {"score": 0, "missing": []}

        total = len(sections_present)
        filled = sum(1 for v in sections_present.values() if v)
        missing = [k for k, v in sections_present.items() if not v]
        score = round((filled / total) * 100)
        return {"score": score, "missing": missing}

    def keyword_coverage(self, required_keywords: list, found_keywords: list) -> dict:
        """Compute what % of required keywords are present.

        Args:
            required_keywords: canonical keyword list for the target role.
            found_keywords: keywords actually detected in resume/profile.

        Returns:
            {"coverage_percent": int, "missing_keywords": [...], "matched_keywords": [...]}
        """
        if not required_keywords:
            return {"coverage_percent": 0, "missing_keywords": [], "matched_keywords": []}

        required_norm = {k.strip().lower() for k in required_keywords}
        found_norm = {k.strip().lower() for k in found_keywords}

        matched = required_norm & found_norm
        missing = required_norm - found_norm

        coverage = round((len(matched) / len(required_norm)) * 100)
        return {
            "coverage_percent": coverage,
            "matched_keywords": sorted(matched),
            "missing_keywords": sorted(missing),
        }

    def weighted_overall_score(self, scores: dict, weights: dict) -> float:
        """Combine multiple sub-scores into one weighted overall score.

        Args:
            scores: e.g. {"headline": 80, "about": 60, "experience": 90}
            weights: e.g. {"headline": 0.1, "about": 0.2, "experience": 0.3}
                     (weights need not sum to 1; they are normalized)

        Returns:
            Weighted average rounded to 1 decimal place.
        """
        if not scores or not weights:
            return 0.0

        total_weight = sum(weights.get(k, 0) for k in scores) or 1
        weighted_sum = sum(scores[k] * weights.get(k, 0) for k in scores)
        return round(weighted_sum / total_weight, 1)
