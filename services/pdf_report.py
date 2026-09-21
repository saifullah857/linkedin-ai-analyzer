"""
services/pdf_report.py

Renders a completed AnalysisReport dict (the same shape returned by
AnalysisReport.to_dict()) into a polished, downloadable PDF using
reportlab's Platypus layer. This is the "Download as PDF" feature
from the Report Generator step of the spec.

Kept deterministic and dependency-free of the LLM -- it only formats
data that was already produced by the agent pipeline, so PDF
generation never fails due to a Groq call and never costs an
additional API call.
"""

from __future__ import annotations

import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable,
)

NAVY = colors.HexColor("#0a1a2f")
BLUE = colors.HexColor("#2f7cf6")
LIGHT_GRAY = colors.HexColor("#f2f4f7")
MUTED = colors.HexColor("#5b6472")


def _styles():
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(
        name="ReportTitle", fontSize=22, leading=26, textColor=NAVY,
        spaceAfter=6, fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="SectionHeading", fontSize=14, leading=18, textColor=NAVY,
        spaceBefore=18, spaceAfter=8, fontName="Helvetica-Bold",
    ))
    styles.add(ParagraphStyle(
        name="MutedSmall", fontSize=9, leading=12, textColor=MUTED,
    ))
    styles.add(ParagraphStyle(
        name="BodyTextTight", fontSize=10, leading=14,
    ))
    return styles


def _score_table(rows: list[tuple[str, int]], styles) -> Table:
    """Build a 2-column label/score table with an inline bar-style cell."""
    data = [["Category", "Score"]]
    for label, score in rows:
        data.append([label, f"{int(score)}/100"])
    table = Table(data, colWidths=[3.6 * inch, 1.4 * inch])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), NAVY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9.5),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT_GRAY]),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dfe3e8")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _bullet_list(items: list[str], styles):
    flow = []
    for item in items:
        flow.append(Paragraph(f"&bull;&nbsp;&nbsp;{item}", styles["BodyTextTight"]))
        flow.append(Spacer(1, 3))
    return flow


def build_pdf_report(report: dict) -> bytes:
    """Render a full AnalysisReport dict into PDF bytes.

    Args:
        report: dict shaped like AnalysisReport.to_dict().

    Returns:
        Raw PDF bytes, ready to send as a file download.
    """
    styles = _styles()
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=letter,
        topMargin=0.7 * inch, bottomMargin=0.7 * inch,
        leftMargin=0.7 * inch, rightMargin=0.7 * inch,
        title="LinkedIn AI Profile Analyzer Report",
    )
    story = []

    # --- Cover / header ---
    story.append(Paragraph("LinkedIn AI Profile Analyzer", styles["ReportTitle"]))
    story.append(Paragraph("Multi-Agent Analysis Report", styles["MutedSmall"]))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#dfe3e8")))
    story.append(Spacer(1, 14))

    overall = report.get("overall_score", 0)
    story.append(Paragraph(f"Overall Score: <b>{overall}/100</b>", styles["SectionHeading"]))
    if report.get("linkedin_url"):
        story.append(Paragraph(f"LinkedIn: {report['linkedin_url']}", styles["MutedSmall"]))
    story.append(Paragraph(f"Analysis ID: {report.get('analysis_id', '')}", styles["MutedSmall"]))
    story.append(Spacer(1, 12))

    final_report = report.get("final_report") or {}
    if final_report.get("one_line_verdict"):
        story.append(Paragraph(f"<i>{final_report['one_line_verdict']}</i>", styles["BodyTextTight"]))
        story.append(Spacer(1, 8))
    if final_report.get("executive_summary"):
        story.append(Paragraph("Executive Summary", styles["SectionHeading"]))
        story.append(Paragraph(final_report["executive_summary"], styles["BodyTextTight"]))

    if final_report.get("key_strengths"):
        story.append(Paragraph("Key Strengths", styles["SectionHeading"]))
        story.extend(_bullet_list(final_report["key_strengths"], styles))

    if final_report.get("key_gaps"):
        story.append(Paragraph("Key Gaps", styles["SectionHeading"]))
        story.extend(_bullet_list(final_report["key_gaps"], styles))

    if final_report.get("top_priority_actions"):
        story.append(Paragraph("Top Priority Actions", styles["SectionHeading"]))
        story.extend(_bullet_list(final_report["top_priority_actions"], styles))

    story.append(PageBreak())

    # --- Profile scores ---
    profile = report.get("profile_analysis") or {}
    if profile and not profile.get("error"):
        story.append(Paragraph("LinkedIn Profile Scores", styles["SectionHeading"]))
        rows = [
            ("Headline", profile.get("headline_score", 0)),
            ("About", profile.get("about_score", 0)),
            ("Experience", profile.get("experience_score", 0)),
            ("Projects", profile.get("projects_score", 0)),
            ("Education", profile.get("education_score", 0)),
            ("Skills", profile.get("skills_score", 0)),
            ("Certifications", profile.get("certifications_score", 0)),
            ("Activity", profile.get("activity_score", 0)),
            ("Recruiter Friendliness", profile.get("recruiter_friendliness_score", 0)),
            ("SEO", profile.get("seo_score", 0)),
        ]
        story.append(_score_table(rows, styles))
        story.append(Spacer(1, 10))

    # --- Resume scores ---
    resume = report.get("resume_analysis") or {}
    if resume and not resume.get("error"):
        story.append(Paragraph("Resume Scores", styles["SectionHeading"]))
        rows = [
            ("ATS Compatibility", resume.get("ats_compatibility_score", 0)),
            ("Formatting", resume.get("formatting_score", 0)),
            ("Grammar", resume.get("grammar_score", 0)),
            ("Keywords", resume.get("keyword_score", 0)),
            ("Professionalism", resume.get("professionalism_score", 0)),
        ]
        story.append(_score_table(rows, styles))
        story.append(Spacer(1, 10))
        if resume.get("weak_bullet_points"):
            story.append(Paragraph("Weak Bullet Points to Fix", styles["SectionHeading"]))
            story.extend(_bullet_list(resume["weak_bullet_points"], styles))

    # --- ATS ---
    ats = report.get("ats") or {}
    if ats and not ats.get("error"):
        story.append(Paragraph(f"ATS Score: {ats.get('ats_score', 0)}/100", styles["SectionHeading"]))
        if ats.get("recommended_keywords"):
            story.append(Paragraph(
                "Recommended keywords: " + ", ".join(ats["recommended_keywords"]),
                styles["BodyTextTight"],
            ))
        if ats.get("action_plan"):
            story.append(Spacer(1, 6))
            story.extend(_bullet_list(ats["action_plan"], styles))

    story.append(PageBreak())

    # --- Recruiter verdict ---
    recruiter = report.get("recruiter") or {}
    if recruiter and not recruiter.get("error"):
        verdict = recruiter.get("final_recommendation", "N/A")
        story.append(Paragraph(f"Recruiter Verdict: {verdict}", styles["SectionHeading"]))
        story.append(Paragraph(recruiter.get("final_recommendation_reason", ""), styles["BodyTextTight"]))
        story.append(Spacer(1, 8))
        rows = [
            ("Technical Rating", recruiter.get("technical_rating", 0)),
            ("Communication Rating", recruiter.get("communication_rating", 0)),
            ("Portfolio Rating", recruiter.get("portfolio_rating", 0)),
        ]
        story.append(_score_table(rows, styles))
        if recruiter.get("pros"):
            story.append(Paragraph("Pros", styles["SectionHeading"]))
            story.extend(_bullet_list(recruiter["pros"], styles))
        if recruiter.get("cons"):
            story.append(Paragraph("Cons", styles["SectionHeading"]))
            story.extend(_bullet_list(recruiter["cons"], styles))

    # --- Career advice ---
    career = report.get("career_advice") or {}
    if career and not career.get("error"):
        story.append(Paragraph("Career Roadmap", styles["SectionHeading"]))
        if career.get("best_career_path"):
            story.append(Paragraph(career["best_career_path"], styles["BodyTextTight"]))
        if career.get("target_job_roles"):
            story.append(Spacer(1, 6))
            story.append(Paragraph("Target Roles: " + ", ".join(career["target_job_roles"]), styles["BodyTextTight"]))
        if career.get("missing_skills"):
            story.append(Paragraph("Skills to Learn Next", styles["SectionHeading"]))
            story.extend(_bullet_list(career["missing_skills"], styles))
        if career.get("projects_to_build"):
            story.append(Paragraph("Projects to Build", styles["SectionHeading"]))
            story.extend(_bullet_list(career["projects_to_build"], styles))

    story.append(Spacer(1, 20))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#dfe3e8")))
    story.append(Spacer(1, 6))
    story.append(Paragraph(
        "Generated by LinkedIn AI Profile Analyzer (Flask + Agno + Groq). "
        "This report is AI-generated guidance, not professional career advice.",
        styles["MutedSmall"],
    ))

    doc.build(story)
    return buf.getvalue()
