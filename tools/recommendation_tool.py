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

    def merge_recommendations(self, recommendation_lists: list) -> list:
        """Merge several recommendation lists into one de-duplicated list.

        Near-identical entries (case-insensitive exact match) are dropped
        while first-seen order is preserved (earlier lists win).

        NOTE: the parameter is a single list-of-lists, NOT *varargs.
        Varargs produce a JSON schema that LLM function-calling (Groq)
        rejects with ``tool_use_failed``, which is exactly what broke
        the Report Generator Agent.

        Args:
            recommendation_lists: e.g. [["a", "b"], ["b", "c"]]. A flat
                list of strings is also accepted.

        Returns:
            A single de-duplicated list[str].
        """
        seen = set()
        merged = []
        for lst in recommendation_lists or []:
            items = [lst] if isinstance(lst, str) else (lst or [])
            for item in items:
                key = str(item).strip().lower()
                if key and key not in seen:
                    seen.add(key)
                    merged.append(item)
        return merged
