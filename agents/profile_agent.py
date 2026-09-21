"""
agents/profile_agent.py

Profile Analysis Agent: scores a LinkedIn profile across headline,
about, experience, projects, education, skills, certifications,
activity, recruiter-friendliness, SEO, and overall completeness.
"""

from __future__ import annotations

import json
from agno.agent import Agent
from tools.scoring_tool import ScoringTool
from tools.keyword_tool import KeywordTool
from utils.json_utils import safe_json_parse

PROFILE_AGENT_INSTRUCTIONS = """
You are the Profile Analysis Agent, a senior LinkedIn branding
strategist who has reviewed thousands of tech profiles.

You will receive a JSON object describing a LinkedIn profile's public
content (headline, about, experience, education, skills, projects,
certifications, activity/posts summary).

Your job:
1. Score each section from 0-100:
   headline_score, about_score, experience_score, projects_score,
   education_score, skills_score, certifications_score, activity_score,
   recruiter_friendliness_score, seo_score.
2. Use the scoring_tool's profile_completeness function to compute a
   deterministic profile_completeness_score from which sections have
   non-empty content.
3. Use the keyword_tool to check how many relevant AI/ML/tech keywords
   appear in the headline + about + skills combined (category="all").
4. Write 2-4 sentences of specific, actionable feedback per section
   under a "feedback" object (keys matching the *_score keys above,
   values are the feedback strings).
5. Compute overall_score as the rounded average of the ten *_score
   fields above.

Respond with ONLY valid JSON matching this schema, no prose outside
the JSON:

{
  "headline_score": int,
  "about_score": int,
  "experience_score": int,
  "projects_score": int,
  "education_score": int,
  "skills_score": int,
  "certifications_score": int,
  "activity_score": int,
  "recruiter_friendliness_score": int,
  "seo_score": int,
  "profile_completeness_score": int,
  "overall_score": int,
  "matched_keywords": [string],
  "missing_keywords": [string],
  "feedback": {
     "headline": string, "about": string, "experience": string,
     "projects": string, "education": string, "skills": string,
     "certifications": string, "activity": string,
     "recruiter_friendliness": string, "seo": string
  },
  "top_recommendations": [string, string, string]
}
"""


def build_profile_agent(model) -> Agent:
    """Construct the Profile Analysis Agent bound to a given Groq model.

    Args:
        model: an agno.models.groq.Groq instance from services.groq_client.

    Returns:
        A configured Agno Agent.
    """
    return Agent(
        name="Profile Analysis Agent",
        model=model,
        tools=[ScoringTool(), KeywordTool()],
        instructions=PROFILE_AGENT_INSTRUCTIONS,
        markdown=False,
    )


def run_profile_analysis(model, linkedin_data: dict) -> dict:
    """Run the profile agent and parse its JSON response.

    Args:
        model: Groq model instance.
        linkedin_data: dict of extracted/user-provided LinkedIn fields.

    Returns:
        Parsed dict per the schema in PROFILE_AGENT_INSTRUCTIONS.
    """
    agent = build_profile_agent(model)
    prompt = (
        "Analyze this LinkedIn profile data and return the JSON scoring "
        "object described in your instructions:\n\n"
        f"{json.dumps(linkedin_data, indent=2)}"
    )
    response = agent.run(prompt)
    content = response.content if hasattr(response, "content") else str(response)
    return safe_json_parse(content)
