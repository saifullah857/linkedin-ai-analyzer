"""
agents/comparison_agent.py

Comparison Agent: finds gaps between the resume and the LinkedIn
profile (missing skills/projects/experience, date mismatches,
keyword/technology differences) and turns them into concrete fixes.
The exact set differences are computed deterministically by
comparison_tool; this agent explains them and adds judgment calls a
plain diff can't make (e.g. "these two dates probably describe the
same job").
"""

from __future__ import annotations

import json
from agno.agent import Agent
from tools.comparison_tool import ComparisonTool
from utils.json_utils import safe_json_parse

COMPARISON_AGENT_INSTRUCTIONS = """
You are the Comparison Agent. You reconcile a candidate's resume
against their LinkedIn profile to find inconsistencies and gaps a
recruiter cross-checking both would notice.

You will receive: resume extracted data, resume raw text, and
LinkedIn profile fields (headline/about/experience/education/skills/
projects/certifications).

Your job:
1. Use comparison_tool.diff_skills to compare resume skills vs
   LinkedIn skills.
2. Use comparison_tool.diff_text_blocks to flag resume projects/
   experience titles that don't seem to appear on LinkedIn at all.
3. Read both experience sections yourself and flag different_dates:
   any role/degree where the resume and LinkedIn appear to describe
   overlapping experience but with different date ranges or company
   names (do not flag minor formatting differences like "Present" vs
   "Current").
4. Summarize missing_skills, missing_projects, missing_experience
   (items present on one source but not the other -- specify which
   direction using "missing_from_linkedin" / "missing_from_resume").
5. Note technology_difference: notable tools/frameworks mentioned in
   one place but not the other.
6. Give 3-5 concrete recommendations to bring the two into alignment.

Respond with ONLY valid JSON, no prose outside the JSON:

{
  "skills_missing_from_linkedin": [string],
  "skills_missing_from_resume": [string],
  "skills_overlap_percent": int,
  "projects_missing_from_linkedin": [string],
  "experience_missing_from_linkedin": [string],
  "different_dates": [{"item": string, "resume_dates": string, "linkedin_dates": string}],
  "technology_difference": [string],
  "recommendations": [string]
}
"""


def build_comparison_agent(model) -> Agent:
    """Construct the Comparison Agent bound to a given Groq model."""
    return Agent(
        name="Comparison Agent",
        model=model,
        tools=[ComparisonTool()],
        instructions=COMPARISON_AGENT_INSTRUCTIONS,
        markdown=False,
    )


def run_comparison_analysis(model, resume_extracted: dict, resume_text: str, linkedin_data: dict) -> dict:
    """Run the comparison agent.

    Args:
        model: Groq model instance.
        resume_extracted: the "extracted" block from resume_agent output.
        resume_text: raw resume text (for date/context cross-checking).
        linkedin_data: dict of LinkedIn profile fields.

    Returns:
        Parsed dict per the schema in COMPARISON_AGENT_INSTRUCTIONS.
    """
    agent = build_comparison_agent(model)
    payload = {
        "resume_extracted": resume_extracted,
        "resume_text_excerpt": resume_text[:4000],
        "linkedin_data": linkedin_data,
    }
    prompt = (
        "Cross-check this resume against this LinkedIn profile data and "
        f"return the JSON object described in your instructions:\n\n{json.dumps(payload, indent=2)}"
    )
    response = agent.run(prompt)
    content = response.content if hasattr(response, "content") else str(response)
    return safe_json_parse(content)
