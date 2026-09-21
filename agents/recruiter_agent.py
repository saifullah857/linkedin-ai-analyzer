"""
agents/recruiter_agent.py

Recruiter Agent: role-plays a senior technical recruiter giving an
honest, first-pass screening verdict on the candidate's resume +
profile, the way they'd actually be judged in the first 30 seconds.
"""

from __future__ import annotations

import json
from agno.agent import Agent
from utils.json_utils import safe_json_parse

RECRUITER_AGENT_INSTRUCTIONS = """
You are the Recruiter Agent, role-playing as a Senior Technical
Recruiter at a mid-size tech company with 8+ years screening AI/ML
and software engineering candidates. Be honest and direct, the way a
real recruiter would be in an internal notes doc -- constructive, not
cruel, but not falsely flattering either.

You will receive: extracted resume data, resume analysis scores, and
LinkedIn profile analysis scores.

Your job:
1. Decide would_interview: bool -- would you move this candidate to a
   phone screen based on what's in front of you right now?
2. List pros (3-5 concrete strengths visible in the materials).
3. List cons (3-5 concrete gaps or weaknesses).
4. List red_flags: [] if none found -- do NOT invent red flags just
   to fill the list. Only include real concerns (unexplained gaps,
   inconsistent claims, vague impact statements, etc.).
5. List strengths_summary (2-3 sentences a recruiter might actually
   write in their notes).
6. Rate technical_rating, communication_rating, portfolio_rating
   (each 0-100, communication_rating inferred from writing clarity in
   the resume/about section, portfolio_rating from project quality/count).
7. Give a final_recommendation: one of "Strong Yes", "Yes",
   "Maybe", "No" plus a 1-2 sentence justification.

Respond with ONLY valid JSON, no prose outside the JSON:

{
  "would_interview": bool,
  "pros": [string],
  "cons": [string],
  "red_flags": [string],
  "strengths_summary": string,
  "technical_rating": int,
  "communication_rating": int,
  "portfolio_rating": int,
  "final_recommendation": string,
  "final_recommendation_reason": string
}
"""


def build_recruiter_agent(model) -> Agent:
    """Construct the Recruiter Agent bound to a given Groq model."""
    return Agent(
        name="Recruiter Agent",
        model=model,
        tools=[],
        instructions=RECRUITER_AGENT_INSTRUCTIONS,
        markdown=False,
    )


def run_recruiter_analysis(model, resume_extracted: dict, resume_scores: dict, profile_scores: dict) -> dict:
    """Run the recruiter agent.

    Args:
        model: Groq model instance.
        resume_extracted: the "extracted" block from resume_agent output.
        resume_scores: the *_score fields from resume_agent output.
        profile_scores: the *_score fields from profile_agent output.

    Returns:
        Parsed dict per the schema in RECRUITER_AGENT_INSTRUCTIONS.
    """
    agent = build_recruiter_agent(model)
    payload = {
        "resume_extracted": resume_extracted,
        "resume_scores": resume_scores,
        "profile_scores": profile_scores,
    }
    prompt = (
        "Screen this candidate like you would in a real ATS review and "
        f"return the JSON object described in your instructions:\n\n{json.dumps(payload, indent=2)}"
    )
    response = agent.run(prompt)
    content = response.content if hasattr(response, "content") else str(response)
    return safe_json_parse(content)
