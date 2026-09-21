"""
models/report.py

ORM models for persisting analysis runs.

We deliberately never persist the user's Groq API key here -- only
the *results* of an analysis (scores, extracted text, recommendations)
are stored, keyed by a random session-scoped analysis_id.
"""

import uuid
import json
from datetime import datetime

from models import db


def _uuid() -> str:
    return uuid.uuid4().hex


class ResumeRecord(db.Model):
    """Stores parsed resume data for one analysis run."""

    __tablename__ = "resume_records"

    id = db.Column(db.String(32), primary_key=True, default=_uuid)
    analysis_id = db.Column(db.String(32), index=True, nullable=False)

    name = db.Column(db.String(255))
    email = db.Column(db.String(255))
    phone = db.Column(db.String(64))

    # JSON-encoded lists/dicts for flexible structured data
    skills_json = db.Column(db.Text, default="[]")
    projects_json = db.Column(db.Text, default="[]")
    experience_json = db.Column(db.Text, default="[]")
    education_json = db.Column(db.Text, default="[]")
    certifications_json = db.Column(db.Text, default="[]")
    languages_json = db.Column(db.Text, default="[]")
    achievements_json = db.Column(db.Text, default="[]")

    raw_text = db.Column(db.Text)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_list(self, field: str, value: list):
        setattr(self, f"{field}_json", json.dumps(value or []))

    def get_list(self, field: str) -> list:
        raw = getattr(self, f"{field}_json") or "[]"
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return []

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "skills": self.get_list("skills"),
            "projects": self.get_list("projects"),
            "experience": self.get_list("experience"),
            "education": self.get_list("education"),
            "certifications": self.get_list("certifications"),
            "languages": self.get_list("languages"),
            "achievements": self.get_list("achievements"),
        }


class AnalysisReport(db.Model):
    """Stores the final multi-agent analysis output for one run."""

    __tablename__ = "analysis_reports"

    id = db.Column(db.String(32), primary_key=True, default=_uuid)
    analysis_id = db.Column(db.String(32), index=True, nullable=False, unique=True)

    # Nullable: login is optional, so anonymous analyses have no owner.
    user_id = db.Column(db.String(32), db.ForeignKey("users.id"), nullable=True, index=True)

    linkedin_url = db.Column(db.String(512))

    # Each field below stores a JSON blob produced by one agent.
    profile_analysis_json = db.Column(db.Text)
    resume_analysis_json = db.Column(db.Text)
    comparison_json = db.Column(db.Text)
    ats_json = db.Column(db.Text)
    career_advice_json = db.Column(db.Text)
    keyword_json = db.Column(db.Text)
    recruiter_json = db.Column(db.Text)
    content_analysis_json = db.Column(db.Text)
    final_report_json = db.Column(db.Text)

    overall_score = db.Column(db.Float, default=0.0)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_json(self, field: str, value: dict):
        setattr(self, f"{field}_json", json.dumps(value or {}))

    def get_json(self, field: str) -> dict:
        raw = getattr(self, f"{field}_json")
        if not raw:
            return {}
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def to_dict(self) -> dict:
        return {
            "analysis_id": self.analysis_id,
            "linkedin_url": self.linkedin_url,
            "overall_score": self.overall_score,
            "profile_analysis": self.get_json("profile_analysis"),
            "resume_analysis": self.get_json("resume_analysis"),
            "comparison": self.get_json("comparison"),
            "ats": self.get_json("ats"),
            "career_advice": self.get_json("career_advice"),
            "keywords": self.get_json("keyword"),
            "recruiter": self.get_json("recruiter"),
            "content_analysis": self.get_json("content_analysis"),
            "final_report": self.get_json("final_report"),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
