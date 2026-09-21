"""
tools/keyword_tool.py

Provides curated keyword banks (AI/ML, Python, Backend, Cloud, RAG,
LLM, GenAI) and a lightweight keyword-matching function used by the
Keyword Optimizer Agent and the ATS Agent.
"""

from __future__ import annotations

import re
from agno.tools import Toolkit

KEYWORD_BANKS = {
    "ai_ml": [
        "machine learning", "deep learning", "neural networks", "computer vision",
        "natural language processing", "nlp", "scikit-learn", "tensorflow", "pytorch",
        "keras", "model deployment", "mlops", "feature engineering", "hyperparameter tuning",
    ],
    "python": [
        "python", "flask", "django", "fastapi", "pandas", "numpy", "asyncio",
        "pytest", "poetry", "pydantic", "sqlalchemy",
    ],
    "backend": [
        "rest api", "graphql", "microservices", "docker", "kubernetes", "postgresql",
        "mysql", "redis", "celery", "message queue", "ci/cd", "system design",
    ],
    "cloud": [
        "aws", "azure", "gcp", "lambda", "ec2", "s3", "terraform", "cloudformation",
        "serverless", "cloud architecture",
    ],
    "rag": [
        "retrieval augmented generation", "rag", "vector database", "chromadb",
        "pinecone", "faiss", "embeddings", "semantic search", "chunking", "reranking",
    ],
    "llm": [
        "large language models", "llm", "prompt engineering", "fine-tuning",
        "quantization", "llamaindex", "langchain", "context window", "tokenization",
    ],
    "genai": [
        "generative ai", "agentic ai", "ai agents", "agno", "autogen", "crewai",
        "multi-agent systems", "function calling", "tool use", "groq", "openai api",
    ],
}


class KeywordTool(Toolkit):
    """Keyword bank lookup and matching for ATS / SEO style checks."""

    def __init__(self):
        super().__init__(name="keyword_tool")
        self.register(self.get_keyword_bank)
        self.register(self.find_keywords_in_text)

    def get_keyword_bank(self, category: str) -> list:
        """Return the curated keyword list for a category.

        Args:
            category: one of ai_ml, python, backend, cloud, rag, llm, genai.
                      Use "all" to get every category merged.
        """
        if category == "all":
            merged = []
            for kws in KEYWORD_BANKS.values():
                merged.extend(kws)
            return sorted(set(merged))
        return KEYWORD_BANKS.get(category, [])

    def find_keywords_in_text(self, text: str, category: str = "all") -> list:
        """Case-insensitive whole-word/phrase search for bank keywords in text.

        Args:
            text: resume or LinkedIn text to search.
            category: which keyword bank to search against.

        Returns:
            List of keywords found in the text.
        """
        if not text:
            return []
        bank = self.get_keyword_bank(category)
        text_lower = text.lower()
        found = []
        for kw in bank:
            pattern = r"\b" + re.escape(kw.lower()) + r"\b"
            if re.search(pattern, text_lower):
                found.append(kw)
        return found
