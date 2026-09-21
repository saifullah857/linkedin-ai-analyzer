"""
agents/master_agent.py

Master Coordinator Agent. Rather than using free-form agent-to-agent
delegation (which is harder to debug and to show in a portfolio demo),
this coordinator explicitly orchestrates each specialist agent in a
deterministic pipeline and assembles their outputs into one report.

Chapter 2: all nine specialist agents are now wired in --

  1. Resume Analysis Agent   (extraction + resume scoring)
  2. Profile Analysis Agent  (LinkedIn scoring)
  3. Comparison Agent        (resume vs LinkedIn gap analysis)
  4. ATS Agent                (ATS-specific keyword/formatting check)
  5. Career Advisor Agent    (roadmap, skills, roles, salary)
  6. Keyword Optimizer Agent (SEO keyword coverage)
  7. Recruiter Agent         (would-you-interview verdict)
  8. Content Analyzer Agent  (public post analysis, optional)
  9. Report Generator Agent  (executive summary synthesis)

Each specialist call is individually fault-isolated: if one agent's
LLM call fails or returns malformed JSON, the pipeline degrades
gracefully (that section becomes {"error": "..."} in the final
report) instead of failing the entire analysis.
"""

from __future__ import annotations

import logging

from agents.profile_agent import run_profile_analysis
from agents.resume_agent import run_resume_analysis
from agents.comparison_agent import run_comparison_analysis
from agents.ats_agent import run_ats_analysis
from agents.career_agent import run_career_analysis
from agents.keyword_agent import run_keyword_analysis
from agents.recruiter_agent import run_recruiter_analysis
from agents.content_agent import run_content_analysis
from agents.report_agent import run_report_generation
from tools.report_tool import ReportTool

logger = logging.getLogger(__name__)


def _safe_run(step_name: str, fn, *args, **kwargs) -> dict:
    """Run one specialist agent and isolate failures to that section.

    A single flaky Groq call (rate limit, malformed JSON, transient
    network error) should not take down the whole nine-agent pipeline
    -- the user still gets every other section plus a clear note about
    what failed.
    """
    try:
        result = fn(*args, **kwargs)
        if not isinstance(result, dict):
            return {"error": f"{step_name} returned an unexpected response type."}
        return result
    except Exception as exc:  # noqa: BLE001
        logger.exception("Agent step failed: %s", step_name)
        return {"error": f"{step_name} failed: {exc}"}


def _extract_scores(data: dict) -> dict:
    """Pull every `*_score` field out of an agent's output dict."""
    if not isinstance(data, dict):
        return {}
    return {k: v for k, v in data.items() if k.endswith("_score") and isinstance(v, (int, float))}


def run_full_analysis(
    model,
    resume_text: str,
    linkedin_data: dict,
    posts: list | None = None,
    target_role: str = "",
) -> dict:
    """Coordinate all nine specialist agents and assemble the final report.

    Args:
        model: Groq model instance built from the user's session API key.
        resume_text: raw resume text extracted from the uploaded PDF.
        linkedin_data: dict of LinkedIn profile fields provided by the user.
        posts: optional list of public LinkedIn post text (for the
            Content Analyzer Agent). Defaults to an empty list.
        target_role: optional target job title, used to bias the ATS
            and Career Advisor agents' keyword/role suggestions.

    Returns:
        A dict with every specialist agent's output plus a combined
        overall_score and a per-agent scores breakdown.
    """
    posts = posts or []

    # 1 & 2: run the two foundational agents first -- everything else
    # (comparison, ats, career, recruiter) depends on their output.
    resume_analysis = _safe_run("Resume Analysis Agent", run_resume_analysis, model, resume_text)
    profile_analysis = _safe_run("Profile Analysis Agent", run_profile_analysis, model, linkedin_data)

    resume_extracted = resume_analysis.get("extracted", {}) if not resume_analysis.get("error") else {}
    resume_scores = _extract_scores(resume_analysis)
    profile_scores = _extract_scores(profile_analysis)

    # 3-8: run the remaining specialists. Each only needs the outputs
    # already computed above, not each other, so ordering here is for
    # readability rather than a hard dependency chain.
    comparison = _safe_run(
        "Comparison Agent", run_comparison_analysis,
        model, resume_extracted, resume_text, linkedin_data,
    )
    ats = _safe_run("ATS Agent", run_ats_analysis, model, resume_text, target_role)
    career_advice = _safe_run(
        "Career Advisor Agent", run_career_analysis,
        model, resume_extracted, resume_scores,
    )
    keywords = _safe_run(
        "Keyword Optimizer Agent", run_keyword_analysis,
        model, resume_text, linkedin_data,
    )
    recruiter = _safe_run(
        "Recruiter Agent", run_recruiter_analysis,
        model, resume_extracted, resume_scores, profile_scores,
    )
    content_analysis = _safe_run(
        "Content Analyzer Agent", run_content_analysis,
        model, posts,
    )

    all_results = {
        "resume_analysis": resume_analysis,
        "profile_analysis": profile_analysis,
        "comparison": comparison,
        "ats": ats,
        "career_advice": career_advice,
        "keywords": keywords,
        "recruiter": recruiter,
        "content_analysis": content_analysis,
    }

    # 9: the Report Generator Agent reads everything above and writes
    # the executive summary / prioritized action list.
    final_report = _safe_run("Report Generator Agent", run_report_generation, model, all_results)
    all_results["final_report"] = final_report

    # Deterministic scoring (no LLM call) via ReportTool, so the
    # headline number never depends on an agent successfully
    # self-reporting an "overall_*" field.
    report_tool = ReportTool()
    overall_inputs = {
        "resume": resume_analysis.get("overall_resume_score"),
        "profile": profile_analysis.get("overall_score"),
        "ats": ats.get("ats_score"),
        "recruiter_technical": recruiter.get("technical_rating"),
        "recruiter_portfolio": recruiter.get("portfolio_rating"),
        "content": content_analysis.get("overall_content_score"),
    }
    overall_score = report_tool.compute_grand_overall(overall_inputs)
    score_breakdown = report_tool.build_score_summary(all_results)

    all_results["overall_score"] = overall_score
    all_results["score_breakdown"] = score_breakdown
    return all_results
