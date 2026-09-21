"""
agents/resume_agent.py

Resume Analysis Agent: extracts structured resume data AND scores the
resume on ATS compatibility, formatting, grammar, keywords,
professionalism, plus flags weak/strong bullet points.
"""

from __future__ import annotations

import json
from agno.agent import Agent
from tools.resume_tool import ResumeTool
from tools.keyword_tool import KeywordTool
from utils.json_utils import safe_json_parse

RESUME_AGENT_INSTRUCTIONS = """
You are the Resume Analysis Agent, a senior technical resume writer
and ATS specialist for AI/ML and software engineering roles.

You will receive raw resume text (already extracted from a PDF, may
contain minor extraction artifacts/line-break issues -- account for
that).

Your job:
1. Extract structured fields: name, email, phone, skills (list),
   projects (list of {name, description}), experience (list of
   {title, company, duration, description}), education (list of
   {degree, institution, year}), certifications (list),
   languages (list), achievements (list).
2. Score 0-100 each of: ats_compatibility_score, formatting_score,
   grammar_score, keyword_score, professionalism_score.
3. List 3-6 weak_bullet_points (verbatim or near-verbatim from the
   resume) that are vague, passive, or lack measurable impact.
4. List 3-6 strong_bullet_points that already use action verbs and
   quantifiable results.
5. Compute overall_resume_score as the rounded average of the five
   *_score fields above.
6. Give 3-5 specific, prioritized recommendations to improve the resume.

Respond with ONLY valid JSON, no prose outside the JSON:

{
  "extracted": {
    "name": string, "email": string, "phone": string,
    "skills": [string], "projects": [{"name": string, "description": string}],
    "experience": [{"title": string, "company": string, "duration": string, "description": string}],
    "education": [{"degree": string, "institution": string, "year": string}],
    "certifications": [string], "languages": [string], "achievements": [string]
  },
  "ats_compatibility_score": int,
  "formatting_score": int,
  "grammar_score": int,
  "keyword_score": int,
  "professionalism_score": int,
  "overall_resume_score": int,
  "weak_bullet_points": [string],
  "strong_bullet_points": [string],
  "recommendations": [string]
}
"""


def build_resume_agent(model) -> Agent:
    """Construct the Resume Analysis Agent bound to a given Groq model."""
    return Agent(
        name="Resume Analysis Agent",
        model=model,
        tools=[ResumeTool(), KeywordTool()],
        instructions=RESUME_AGENT_INSTRUCTIONS,
        markdown=False,
    )


def run_resume_analysis(model, resume_text: str) -> dict:
    """Run the resume agent on raw extracted resume text.

    Args:
        model: Groq model instance.
        resume_text: raw text extracted via tools.pdf_tool.

    Returns:
        Parsed dict per the schema in RESUME_AGENT_INSTRUCTIONS.
    """
    agent = build_resume_agent(model)
    prompt = (
        "Analyze this resume text and return the JSON object described "
        f"in your instructions:\n\n---\n{resume_text}\n---"
    )
    response = agent.run(prompt)
    content = response.content if hasattr(response, "content") else str(response)
    return safe_json_parse(content)
