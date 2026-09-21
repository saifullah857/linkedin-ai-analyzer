"""
tools/report_tool.py

Deterministic assembly helpers for the final report. Chart libraries
(and reportlab, for the PDF) need plain (label, value) pairs rather
than the nested per-agent JSON -- this tool flattens the pipeline
output into that shape once, so both results.html and the PDF
exporter draw from the same source of truth.
"""

from __future__ import annotations

from agno.tools import Toolkit


class ReportTool(Toolkit):
    """Flattening / summarizing helpers for the final assembled report."""

    def __init__(self):
        super().__init__(name="report_tool")
        self.register(self.build_score_summary)
        self.register(self.compute_grand_overall)

    def build_score_summary(self, all_results: dict) -> list:
        """Flatten every agent's *_score fields into one chart-ready list.

        Args:
            all_results: dict of {agent_key: agent_output_dict}, e.g.
                {"profile_analysis": {...}, "resume_analysis": {...}, "ats": {...}}

        Returns:
            List of {"label": str, "score": int, "source": str} sorted
            by source then label, safe for direct use in a bar chart.
        """
        rows = []
        for source, data in (all_results or {}).items():
            if not isinstance(data, dict):
                continue
            for key, value in data.items():
                if key.endswith("_score") and isinstance(value, (int, float)):
                    label = key.replace("_score", "").replace("_", " ").title()
                    rows.append({"label": label, "score": int(round(value)), "source": source})
        return sorted(rows, key=lambda r: (r["source"], r["label"]))

    def compute_grand_overall(self, overall_scores: dict) -> float:
        """Average a dict of {agent_name: overall_score} into one number.

        Args:
            overall_scores: e.g. {"resume": 78, "profile": 82, "ats": 65}

        Returns:
            Rounded (1 decimal) overall score across all agents that
            reported one. Missing/None values are ignored rather than
            treated as zero, so one agent failing doesn't tank the score.
        """
        valid = [v for v in (overall_scores or {}).values() if isinstance(v, (int, float))]
        if not valid:
            return 0.0
        return round(sum(valid) / len(valid), 1)
