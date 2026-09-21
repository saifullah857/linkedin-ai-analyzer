"""
agents/career_agent.py

Career Advisor Agent: turns the resume + profile analysis into a
forward-looking roadmap (skills to learn, certifications, projects to
build, target roles, rough salary band, and a staged timeline).
"""

from __future__ import annotations

import json
from agno.agent import Agent
from tools.keyword_tool import KeywordTool
from tools.recommendation_tool import RecommendationTool
from utils.json_utils import safe_json_parse

CAREER_AGENT_INSTRUCTIONS = """
You are the Career Advisor Agent, a senior tech career coach who
specializes in AI/ML, data science, and software engineering careers,
with strong knowledge of the current job market.

You will receive: extracted resume data (skills/projects/experience/
education) and the resume analysis scores.

Your job:
1. Use recommendation_tool.rank_weak_areas on the provided scores to
   see which areas need the most improvement.
2. Use keyword_tool.get_keyword_bank("all") as a reference list of
   in-demand skills to check what's missing from this candidate's
   current skill set.
3. Recommend a best_career_path (1-2 sentences) matching their
   current trajectory.
4. List missing_skills (5-8 specific skills worth learning next).
5. List recommended_certifications (3-5, real and specific, e.g.
   "AWS Certified Machine Learning – Specialty").
6. List recommended_courses (3-5, can name real platforms like
   Coursera/DeepLearning.AI/Udemy generically without inventing fake
   course titles -- describe the topic instead if unsure of an exact name).
7. List projects_to_build (3-5 specific, portfolio-worthy project
   ideas that fill their skill gaps).
8. List target_job_roles (3-5 specific titles they're a good fit for
   now, plus 1-2 stretch roles).
9. Give a salary_estimation_note: a *rough*, clearly-labeled-as-
   approximate USD range for their apparent experience level and
   role, with a caveat that it varies heavily by region and company.
10. Produce a roadmap: a list of 3-4 stages, each with a "timeframe"
    (e.g. "0-3 months") and "focus" (what to prioritize in that stage).

Respond with ONLY valid JSON, no prose outside the JSON:

{
  "best_career_path": string,
  "missing_skills": [string],
  "recommended_certifications": [string],
  "recommended_courses": [string],
  "projects_to_build": [string],
  "target_job_roles": [string],
  "salary_estimation_note": string,
  "roadmap": [{"timeframe": string, "focus": string}]
}
"""


def build_career_agent(model) -> Agent:
    """Construct the Career Advisor Agent bound to a given Groq model."""
    return Agent(
        name="Career Advisor Agent",
        model=model,
        tools=[KeywordTool(), RecommendationTool()],
        instructions=CAREER_AGENT_INSTRUCTIONS,
        markdown=False,
    )


def run_career_analysis(model, resume_extracted: dict, resume_scores: dict) -> dict:
    """Run the career advisor agent.

    Args:
        model: Groq model instance.
        resume_extracted: the "extracted" block from resume_agent output.
        resume_scores: the *_score fields from resume_agent output.

    Returns:
        Parsed dict per the schema in CAREER_AGENT_INSTRUCTIONS.
    """
    agent = build_career_agent(model)
    payload = {"resume_extracted": resume_extracted, "resume_scores": resume_scores}
    prompt = (
        "Build a career roadmap from this candidate data and return the "
        f"JSON object described in your instructions:\n\n{json.dumps(payload, indent=2)}"
    )
    response = agent.run(prompt)
    content = response.content if hasattr(response, "content") else str(response)
    return safe_json_parse(content)
