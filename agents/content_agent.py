"""
agents/content_agent.py

Content Analyzer Agent ("Post Analyzer"): reviews the candidate's
public LinkedIn posts (pasted in by the user, since we do not scrape
LinkedIn) and scores each one on engagement potential, professionalism,
writing quality, and gives an improved rewrite.
"""

from __future__ import annotations

import json
from agno.agent import Agent
from utils.json_utils import safe_json_parse

CONTENT_AGENT_INSTRUCTIONS = """
You are the Content Analyzer Agent, a LinkedIn content strategist who
has studied what makes technical posts perform well (hooks, structure,
hashtags, CTAs) without resorting to engagement-bait tactics.

You will receive a list of the candidate's public LinkedIn posts
(plain text, one string per post). The list may be empty.

For EACH post, produce:
  - engagement_prediction: "low" | "medium" | "high"
  - professional_score (0-100)
  - writing_style: 1-sentence description (e.g. "storytelling", "listicle", "technical deep-dive")
  - hashtag_quality: "none" | "weak" | "good" | "excessive"
  - has_call_to_action: bool
  - readability_score (0-100)
  - grammar_issues: [string] (specific issues found, empty list if none)
  - improved_version: a rewritten version of the post (2-4 short
    paragraphs, keep the original meaning/facts, improve hook/structure/CTA)
  - better_hooks: [string] (2-3 alternative opening lines)
  - better_cta: string (one strong call-to-action suggestion)

Also produce an overall summary across all posts:
  - overall_content_score (0-100, 0 if no posts were provided)
  - posting_pattern_note: 1-2 sentences on consistency/topics if
    inferable, otherwise a note that more posts are needed for a
    pattern read.

If the input list is empty, return overall_content_score: 0,
posts: [], and a posting_pattern_note explaining no posts were
provided to analyze.

Respond with ONLY valid JSON, no prose outside the JSON:

{
  "posts": [
    {
      "post_excerpt": string,
      "engagement_prediction": string,
      "professional_score": int,
      "writing_style": string,
      "hashtag_quality": string,
      "has_call_to_action": bool,
      "readability_score": int,
      "grammar_issues": [string],
      "improved_version": string,
      "better_hooks": [string],
      "better_cta": string
    }
  ],
  "overall_content_score": int,
  "posting_pattern_note": string
}
"""


def build_content_agent(model) -> Agent:
    """Construct the Content Analyzer Agent bound to a given Groq model."""
    return Agent(
        name="Content Analyzer Agent",
        model=model,
        tools=[],
        instructions=CONTENT_AGENT_INSTRUCTIONS,
        markdown=False,
    )


def run_content_analysis(model, posts: list) -> dict:
    """Run the content analyzer agent over a list of public LinkedIn posts.

    Args:
        model: Groq model instance.
        posts: list[str] of the candidate's public post text. May be empty.

    Returns:
        Parsed dict per the schema in CONTENT_AGENT_INSTRUCTIONS.
    """
    if not posts:
        return {
            "posts": [],
            "overall_content_score": 0,
            "posting_pattern_note": "No public posts were provided, so activity content could not be analyzed.",
        }

    agent = build_content_agent(model)
    prompt = (
        "Analyze these LinkedIn posts and return the JSON object "
        f"described in your instructions:\n\n{json.dumps(posts, indent=2)}"
    )
    response = agent.run(prompt)
    content = response.content if hasattr(response, "content") else str(response)
    return safe_json_parse(content)
