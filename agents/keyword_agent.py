"""
agents/keyword_agent.py

Keyword Optimizer Agent: surfaces the highest-value AI/ML, Python,
backend, cloud, RAG, LLM, and GenAI keywords the candidate should be
using across resume + LinkedIn, based on what's already present.
"""

from __future__ import annotations

import json
from agno.agent import Agent
from tools.keyword_tool import KeywordTool
from utils.json_utils import safe_json_parse

KEYWORD_AGENT_INSTRUCTIONS = """
You are the Keyword Optimizer Agent, specializing in SEO for tech
resumes and LinkedIn profiles targeting AI/ML and software roles.

You will receive combined resume + LinkedIn text.

Your job:
1. Use keyword_tool.find_keywords_in_text once per category (ai_ml,
   python, backend, cloud, rag, llm, genai) against the combined text
   to see what's already present in each category.
2. Use keyword_tool.get_keyword_bank per category to know the full
   universe of keywords to draw missing/recommended terms from.
3. For each category, return the found keywords and up to 5
   recommended (currently missing) keywords most relevant to this
   candidate's apparent profile.
4. Produce a top_keywords_to_add: the single highest-impact 8-10
   keywords across all categories combined, ranked by likely impact.

Respond with ONLY valid JSON, no prose outside the JSON:

{
  "ai_ml_keywords": {"found": [string], "recommended": [string]},
  "python_keywords": {"found": [string], "recommended": [string]},
  "backend_keywords": {"found": [string], "recommended": [string]},
  "cloud_keywords": {"found": [string], "recommended": [string]},
  "rag_keywords": {"found": [string], "recommended": [string]},
  "llm_keywords": {"found": [string], "recommended": [string]},
  "genai_keywords": {"found": [string], "recommended": [string]},
  "top_keywords_to_add": [string]
}
"""


def build_keyword_agent(model) -> Agent:
    """Construct the Keyword Optimizer Agent bound to a given Groq model."""
    return Agent(
        name="Keyword Optimizer Agent",
        model=model,
        tools=[KeywordTool()],
        instructions=KEYWORD_AGENT_INSTRUCTIONS,
        markdown=False,
    )


def run_keyword_analysis(model, resume_text: str, linkedin_data: dict) -> dict:
    """Run the keyword optimizer agent over combined resume + LinkedIn text.

    Args:
        model: Groq model instance.
        resume_text: raw resume text.
        linkedin_data: dict of LinkedIn profile fields.

    Returns:
        Parsed dict per the schema in KEYWORD_AGENT_INSTRUCTIONS.
    """
    agent = build_keyword_agent(model)
    combined_text = resume_text + "\n\n" + "\n".join(
        str(v) for v in linkedin_data.values() if isinstance(v, str)
    )
    prompt = (
        "Analyze this combined resume + LinkedIn text for keyword "
        "coverage and return the JSON object described in your "
        f"instructions:\n\n---\n{combined_text}\n---"
    )
    response = agent.run(prompt)
    content = response.content if hasattr(response, "content") else str(response)
    return safe_json_parse(content)
