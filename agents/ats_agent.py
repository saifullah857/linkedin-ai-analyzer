"""
agents/ats_agent.py

ATS Agent: checks how well the resume would survive an Applicant
Tracking System parse/rank for AI/ML and software engineering roles.
"""

from __future__ import annotations

import json
from agno.agent import Agent
from tools.keyword_tool import KeywordTool
from tools.resume_tool import ResumeTool
from utils.json_utils import safe_json_parse

ATS_AGENT_INSTRUCTIONS = """
You are the ATS Agent, an expert on how Applicant Tracking Systems
(Workday, Greenhouse, Lever, Taleo) parse and rank resumes for AI/ML
and software engineering roles.

You will receive raw resume text and, optionally, a target job title.

Your job:
1. Use resume_tool.split_into_sections to check whether standard ATS-
   friendly section headers exist (Experience, Education, Skills).
2. Use keyword_tool.find_keywords_in_text across categories
   (ai_ml, python, backend, cloud, rag, llm, genai) to see which
   in-demand keywords already appear.
3. Compute an ats_score (0-100) based on: presence of standard
   section headers, absence of tables/graphics/columns (infer from
   text irregularities), keyword density, and contact info clarity.
4. List missing_keywords (relevant keywords NOT found, pulled from
   the keyword_tool banks) and weak_keywords (keywords present only
   once or in a way that reads as keyword-stuffing).
5. List recommended_keywords: the 8-12 highest-value keywords this
   resume should add given its apparent target role.
6. Write a concrete, numbered action_plan (4-6 steps) to raise the
   ATS score.

Respond with ONLY valid JSON, no prose outside the JSON:

{
  "ats_score": int,
  "has_standard_sections": bool,
  "missing_section_headers": [string],
  "missing_keywords": [string],
  "weak_keywords": [string],
  "recommended_keywords": [string],
  "action_plan": [string],
  "summary": string
}
"""


def build_ats_agent(model) -> Agent:
    """Construct the ATS Agent bound to a given Groq model."""
    return Agent(
        name="ATS Agent",
        model=model,
        tools=[KeywordTool(), ResumeTool()],
        instructions=ATS_AGENT_INSTRUCTIONS,
        markdown=False,
    )


def run_ats_analysis(model, resume_text: str, target_role: str = "") -> dict:
    """Run the ATS agent on raw resume text.

    Args:
        model: Groq model instance.
        resume_text: raw text extracted via tools.pdf_tool.
        target_role: optional target job title to bias keyword picks.

    Returns:
        Parsed dict per the schema in ATS_AGENT_INSTRUCTIONS.
    """
    agent = build_ats_agent(model)
    prompt = (
        "Analyze this resume for ATS compatibility and return the JSON "
        f"object described in your instructions. Target role (if any): "
        f"'{target_role or 'not specified'}'.\n\n---\n{resume_text}\n---"
    )
    response = agent.run(prompt)
    content = response.content if hasattr(response, "content") else str(response)
    return safe_json_parse(content)
