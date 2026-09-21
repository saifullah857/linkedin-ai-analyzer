"""
tests/test_agents.py

Tests the master agent's orchestration logic in isolation from Groq --
every specialist agent function is mocked, so these tests run offline
and verify the *pipeline*, not the LLM's judgment:

  - all nine agents are called and their outputs assembled
  - a single agent failure is isolated (doesn't take down the run)
  - overall_score / score_breakdown are computed deterministically
"""

from __future__ import annotations

from unittest.mock import patch

from agents.master_agent import run_full_analysis, _extract_scores


def _patched_pipeline(**overrides):
    """Return a dict of patch targets -> mock return values, with
    sane defaults that individual tests can override."""
    defaults = dict(
        run_resume_analysis={
            "extracted": {"name": "Jane Doe", "skills": ["Python"]},
            "overall_resume_score": 80,
            "ats_compatibility_score": 78,
        },
        run_profile_analysis={"overall_score": 65, "headline_score": 60},
        run_comparison_analysis={"skills_overlap_percent": 70},
        run_ats_analysis={"ats_score": 72},
        run_career_analysis={"best_career_path": "GenAI Engineer"},
        run_keyword_analysis={"top_keywords_to_add": ["RAG", "LLM"]},
        run_recruiter_analysis={"technical_rating": 80, "portfolio_rating": 75},
        run_content_analysis={"posts": [], "overall_content_score": 0},
        run_report_generation={"executive_summary": "Solid candidate."},
    )
    defaults.update(overrides)
    return defaults


def _run_with(overrides=None, side_effects=None):
    patches = _patched_pipeline(**(overrides or {}))
    side_effects = side_effects or {}
    patchers = []
    try:
        for name, value in patches.items():
            target = f"agents.master_agent.{name}"
            if name in side_effects:
                p = patch(target, side_effect=side_effects[name])
            else:
                p = patch(target, return_value=value)
            p.start()
            patchers.append(p)
        return run_full_analysis(
            model="fake-model", resume_text="some resume text",
            linkedin_data={"headline": "AI Engineer"}, posts=[], target_role="",
        )
    finally:
        for p in patchers:
            p.stop()


def test_full_pipeline_assembles_all_sections():
    result = _run_with()
    for key in [
        "resume_analysis", "profile_analysis", "comparison", "ats",
        "career_advice", "keywords", "recruiter", "content_analysis",
        "final_report", "overall_score", "score_breakdown",
    ]:
        assert key in result, f"missing key: {key}"
    assert result["overall_score"] > 0


def test_one_agent_failure_is_isolated():
    def boom(*a, **k):
        raise RuntimeError("simulated Groq outage")

    result = _run_with(side_effects={"run_comparison_analysis": boom})

    assert "error" in result["comparison"]
    # Everything else should still be present and unaffected.
    assert result["ats"]["ats_score"] == 72
    assert result["overall_score"] > 0


def test_multiple_agent_failures_still_return_partial_report():
    def boom(*a, **k):
        raise RuntimeError("down")

    result = _run_with(side_effects={
        "run_comparison_analysis": boom,
        "run_career_analysis": boom,
        "run_content_analysis": boom,
    })

    assert "error" in result["comparison"]
    assert "error" in result["career_advice"]
    assert "error" in result["content_analysis"]
    # Resume + profile + ats + recruiter still succeeded.
    assert result["resume_analysis"]["overall_resume_score"] == 80
    assert result["ats"]["ats_score"] == 72


def test_extract_scores_only_pulls_score_suffixed_numeric_fields():
    data = {
        "ats_score": 80, "formatting_score": 70, "name": "not a score",
        "notes": None, "weird_score": "not numeric",
    }
    scores = _extract_scores(data)
    assert scores == {"ats_score": 80, "formatting_score": 70}


def test_extract_scores_handles_non_dict_input():
    assert _extract_scores(None) == {}
    assert _extract_scores([]) == {}
