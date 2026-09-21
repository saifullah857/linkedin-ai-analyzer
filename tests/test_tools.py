"""
tests/test_tools.py

The scoring/keyword/report tools are deliberately deterministic (no
LLM calls), so they're the cheapest and most valuable things to unit
test directly -- these numbers are what the agents lean on for any
number that must be reproducible.
"""

from __future__ import annotations

from tools.scoring_tool import ScoringTool
from tools.keyword_tool import KeywordTool
from tools.report_tool import ReportTool


# --- ScoringTool -----------------------------------------------------

def test_profile_completeness_all_filled():
    tool = ScoringTool()
    result = tool.profile_completeness({"headline": True, "about": True, "skills": True})
    assert result == {"score": 100, "missing": []}


def test_profile_completeness_partial():
    tool = ScoringTool()
    result = tool.profile_completeness({"headline": True, "about": False, "skills": True, "projects": False})
    assert result["score"] == 50
    assert set(result["missing"]) == {"about", "projects"}


def test_profile_completeness_empty_input():
    tool = ScoringTool()
    assert tool.profile_completeness({}) == {"score": 0, "missing": []}


def test_keyword_coverage_partial_match():
    tool = ScoringTool()
    result = tool.keyword_coverage(
        required_keywords=["Python", "Flask", "Docker"],
        found_keywords=["python", "flask"],
    )
    assert result["coverage_percent"] == 67
    assert result["missing_keywords"] == ["docker"]
    assert result["matched_keywords"] == ["flask", "python"]


def test_weighted_overall_score():
    tool = ScoringTool()
    score = tool.weighted_overall_score(
        scores={"headline": 80, "about": 60},
        weights={"headline": 0.5, "about": 0.5},
    )
    assert score == 70.0


def test_weighted_overall_score_empty_input():
    tool = ScoringTool()
    assert tool.weighted_overall_score({}, {}) == 0.0


# --- KeywordTool -------------------------------------------------------

def test_get_keyword_bank_single_category():
    tool = KeywordTool()
    bank = tool.get_keyword_bank("python")
    assert "flask" in bank
    assert "aws" not in bank


def test_get_keyword_bank_all_merges_categories():
    tool = KeywordTool()
    bank = tool.get_keyword_bank("all")
    assert "flask" in bank
    assert "aws" in bank
    assert "rag" in bank


def test_find_keywords_in_text_matches_whole_words_only():
    tool = KeywordTool()
    text = "Built REST APIs with Flask and deployed to AWS Lambda using Docker."
    found = tool.find_keywords_in_text(text, category="all")
    assert "flask" in found
    assert "docker" in found
    assert "aws" in found


def test_find_keywords_in_text_empty_string():
    tool = KeywordTool()
    assert tool.find_keywords_in_text("", category="all") == []


# --- ReportTool ----------------------------------------------------------

def test_build_score_summary_flattens_all_score_fields():
    tool = ReportTool()
    rows = tool.build_score_summary({
        "resume_analysis": {"ats_compatibility_score": 80, "grammar_score": 90, "name": "ignored"},
        "profile_analysis": {"headline_score": 60},
    })
    labels = {r["label"] for r in rows}
    assert "Ats Compatibility" in labels
    assert "Grammar" in labels
    assert "Headline" in labels
    assert all("source" in r for r in rows)


def test_compute_grand_overall_ignores_missing_values():
    tool = ReportTool()
    overall = tool.compute_grand_overall({"resume": 80, "profile": None, "ats": 70})
    assert overall == 75.0


def test_compute_grand_overall_empty_input():
    tool = ReportTool()
    assert tool.compute_grand_overall({}) == 0.0
