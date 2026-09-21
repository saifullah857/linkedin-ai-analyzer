"""
agents/report_agent.py

Report Generator Agent: the final step in the pipeline. Reads every
other agent's output and writes one cohesive executive summary plus a
single prioritized action list, so the person doesn't have to read
eight separate JSON blobs to know what to do first. The numeric
scores/charts themselves are handled deterministically by report_tool
and rendered directly in results.html / the PDF -- this agent's job is
purely the narrative synthesis.
"""

from __future__ import annotations

import json
from agno.agent import Agent
from tools.recommendation_tool import RecommendationTool
from tools.report_tool import ReportTool
from utils.json_utils import safe_json_parse

REPORT_AGENT_INSTRUCTIONS = """
You are the Report Generator Agent, responsible for the executive
summary of a full multi-agent LinkedIn + resume analysis.

You will receive the combined JSON output of every specialist agent
that already ran: profile_analysis, resume_analysis, comparison,
ats, career_advice, keywords, recruiter, content_analysis.

Your job:
1. Use recommendation_tool.merge_recommendations to combine the
   recommendation lists from resume_analysis, comparison, ats, and
   career_advice into one de-duplicated list, then select the 5 most
   impactful as top_priority_actions (rewrite them as short, concrete
   action items, not vague advice).
2. Write an executive_summary: 3-5 sentences giving a candid, high-
   level read of this candidate's current standing (combine the
   recruiter agent's verdict with the strongest/weakest score areas).
3. Write key_strengths: 3-4 bullet points.
4. Write key_gaps: 3-4 bullet points (the biggest weaknesses across
   all agents, not just one).
5. Write a one_line_verdict: a single sentence a candidate could put
   at the top of their to-do list (e.g. "Your resume outshines your
   LinkedIn profile -- the biggest wins are on LinkedIn.").

Respond with ONLY valid JSON, no prose outside the JSON:

{
  "executive_summary": string,
  "key_strengths": [string],
  "key_gaps": [string],
  "top_priority_actions": [string],
  "one_line_verdict": string
}
"""


def build_report_agent(model) -> Agent:
    """Construct the Report Generator Agent bound to a given Groq model."""
    return Agent(
        name="Report Generator Agent",
        model=model,
        tools=[RecommendationTool(), ReportTool()],
        instructions=REPORT_AGENT_INSTRUCTIONS,
        markdown=False,
    )


def run_report_generation(model, all_results: dict) -> dict:
    """Run the report generator agent over every prior agent's output.

    Args:
        model: Groq model instance.
        all_results: dict of every specialist agent's parsed output,
            keyed by name (profile_analysis, resume_analysis,
            comparison, ats, career_advice, keywords, recruiter,
            content_analysis).

    Returns:
        Parsed dict per the schema in REPORT_AGENT_INSTRUCTIONS.
    """
    agent = build_report_agent(model)
    prompt = (
        "Synthesize this full multi-agent analysis into the executive "
        f"summary JSON object described in your instructions:\n\n{json.dumps(all_results, indent=2)}"
    )
    response = agent.run(prompt)
    content = response.content if hasattr(response, "content") else str(response)
    return safe_json_parse(content)
