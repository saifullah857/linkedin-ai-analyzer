"""
tools/recommendation_tool.py

Deterministic helpers for turning raw score dicts into a prioritized,
de-duplicated action list. Used by the Career Advisor Agent and the
Report Generator Agent so the "top 5 things to fix first" logic is
consistent and testable rather than re-derived by the LLM every time.
"""

from __future__ import annotations

from agno.tools import Toolkit


class RecommendationTool(Toolkit):
    """Prioritization and de-duplication helpers for recommendations."""

    def __init__(self):
        super().__init__(name="recommendation_tool")
        self.register(self.rank_weak_areas)
        self.register(self.merge_recommendations)

    def rank_weak_areas(self, scores: dict, threshold: int = 70) -> list:
        """Return score fields below `threshold`, sorted worst-first.

        Args:
            scores: e.g. {"headline_score": 40, "about_score": 85, ...}
            threshold: scores at or above this are considered fine.

        Returns:
            List of {"area": str, "score": int} sorted ascending by score.
        """
        weak = [
            {"area": key.replace("_score", "").replace("_", " ").title(), "score": value}
            for key, value in (scores or {}).items()
            if isinstance(value, (int, float)) and value < threshold
        ]
        return sorted(weak, key=lambda x: x["score"])

    def merge_recommendations(self, *recommendation_lists) -> list:
        """Merge multiple agents' recommendation lists, de-duplicating
        near-identical entries (case-insensitive exact match) while
        preserving the first-seen order (earlier lists take priority).

        Args:
            *recommendation_lists: any number of list[str] arguments.

        Returns:
            A single de-duplicated list[str].
        """
        seen = set()
        merged = []
        for lst in recommendation_lists:
            for item in lst or []:
                key = str(item).strip().lower()
                if key and key not in seen:
                    seen.add(key)
                    merged.append(item)
        return merged
