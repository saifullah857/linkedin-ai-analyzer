"""
app.py

Flask application entrypoint for the LinkedIn AI Profile Analyzer.

Chapter 1 scope (done):
  - Home / landing page
  - Analysis intake form (LinkedIn URL, Groq API key, resume PDF)
  - Resume text extraction
  - Master agent run (Resume Analysis Agent + Profile Analysis Agent)
  - Results dashboard page

Chapter 2 scope (this file):
  - Full 9-agent pipeline (comparison, ATS, career, keyword,
    recruiter, content, report generator) wired through master_agent
  - PDF report export
  - Optional authentication (Flask-Login) with a report-history dashboard
  - Rate limiting (Flask-Limiter) on the analysis and auth endpoints
"""

from __future__ import annotations

import os
import uuid

from flask import (
    Flask, render_template, request, redirect, url_for,
    session, flash, current_app, send_file,
)
from werkzeug.utils import secure_filename
from flask_login import (
    LoginManager, login_user, logout_user, login_required, current_user,
)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_session import Session

from config import config_map, DATABASE_DIR, SESSION_DIR
from models import db
from models.report import AnalysisReport, ResumeRecord
from models.user import User
from tools.pdf_tool import PDFTool
from services.groq_client import get_groq_model, MissingGroqKeyError
from services.pdf_report import build_pdf_report
from agents.master_agent import run_full_analysis

login_manager = LoginManager()
login_manager.login_view = "login"
login_manager.login_message = "Please log in to view that page."
login_manager.login_message_category = "info"

limiter = Limiter(key_func=get_remote_address)
server_session = Session()


def create_app(env: str | None = None) -> Flask:
    """Application factory.

    Args:
        env: "development" or "production". Defaults to FLASK_ENV env var.

    Returns:
        A configured Flask app instance.
    """
    app = Flask(__name__)
    env = env or os.getenv("FLASK_ENV", "development")
    app.config.from_object(config_map.get(env, config_map["default"]))

    # Create every directory the app writes to up front, using the plain
    # paths from config.py directly -- NOT by parsing them back out of the
    # sqlite:/// URI string, which breaks on Windows paths (C:\..., drive
    # letters, backslashes don't survive a naive string replace).
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    os.makedirs(app.config["REPORTS_FOLDER"], exist_ok=True)
    os.makedirs(DATABASE_DIR, exist_ok=True)
    os.makedirs(SESSION_DIR, exist_ok=True)

    db.init_app(app)
    login_manager.init_app(app)
    limiter.init_app(app)
    app.config.setdefault("RATELIMIT_DEFAULT", app.config.get("RATE_LIMIT_DEFAULT", "100 per hour"))

    # Server-side (filesystem) sessions -- the Groq API key lives here for
    # the duration of the browser session, never in the database or on disk
    # beyond this session store. Must init AFTER SECRET_KEY/SESSION_* config
    # is loaded and the session dir exists, and before any session access.
    server_session.init_app(app)

    with app.app_context():
        db.create_all()

    register_routes(app)
    return app


@login_manager.user_loader
def load_user(user_id: str):
    return User.query.get(user_id)


def _parse_posts(raw: str) -> list[str]:
    """Split the free-text "posts" textarea into individual post strings.

    Posts are separated by one or more blank lines.
    """
    if not raw or not raw.strip():
        return []
    chunks = [p.strip() for p in raw.replace("\r\n", "\n").split("\n\n")]
    return [c for c in chunks if c]


def register_routes(app: Flask) -> None:

    @app.route("/")
    def home():
        """Landing page: hero, features, footer."""
        return render_template("index.html")

    # ------------------------------------------------------------------
    # Authentication (optional -- /analyze works without an account)
    # ------------------------------------------------------------------

    @app.route("/register", methods=["GET", "POST"])
    @limiter.limit("10 per hour")
    def register():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        if request.method == "GET":
            return render_template("auth/register.html")

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 8:
            flash("Please provide a name, a valid email, and a password of at least 8 characters.", "danger")
            return redirect(url_for("register"))

        if User.query.filter_by(email=email).first():
            flash("An account with that email already exists. Try logging in instead.", "danger")
            return redirect(url_for("login"))

        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        login_user(user)
        flash("Account created. Welcome!", "success")
        return redirect(url_for("dashboard"))

    @app.route("/login", methods=["GET", "POST"])
    @limiter.limit("10 per minute")
    def login():
        if current_user.is_authenticated:
            return redirect(url_for("dashboard"))

        if request.method == "GET":
            return render_template("auth/login.html")

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        user = User.query.filter_by(email=email).first()

        if not user or not user.check_password(password):
            flash("Invalid email or password.", "danger")
            return redirect(url_for("login"))

        login_user(user)
        flash(f"Welcome back, {user.name}.", "success")
        next_url = request.args.get("next")
        return redirect(next_url or url_for("dashboard"))

    @app.route("/logout")
    @login_required
    def logout():
        logout_user()
        flash("You've been logged out.", "info")
        return redirect(url_for("home"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        reports = (
            AnalysisReport.query
            .filter_by(user_id=current_user.id)
            .order_by(AnalysisReport.created_at.desc())
            .all()
        )
        return render_template("dashboard.html", reports=reports)

    # ------------------------------------------------------------------
    # Analysis pipeline
    # ------------------------------------------------------------------

    @app.route("/analyze", methods=["GET", "POST"])
    @limiter.limit("5 per hour", methods=["POST"])
    def analyze():
        """Intake form: LinkedIn URL + Groq API key + resume PDF upload."""
        if request.method == "GET":
            return render_template("analyze.html")

        linkedin_url = request.form.get("linkedin_url", "").strip()
        groq_api_key = request.form.get("groq_api_key", "").strip()
        resume_file = request.files.get("resume")
        target_role = request.form.get("target_role", "").strip()

        if not linkedin_url or not groq_api_key or not resume_file:
            flash("LinkedIn URL, Groq API key, and resume PDF are all required.", "danger")
            return redirect(url_for("analyze"))

        if not resume_file.filename.lower().endswith(".pdf"):
            flash("Resume must be a PDF file.", "danger")
            return redirect(url_for("analyze"))

        # Store the key ONLY in the server-side session for this browser
        # session. Never written to disk or the database.
        session["groq_api_key"] = groq_api_key
        session["linkedin_url"] = linkedin_url

        filename = secure_filename(resume_file.filename)
        unique_name = f"{uuid.uuid4().hex}_{filename}"
        file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], unique_name)
        resume_file.save(file_path)

        try:
            pdf_tool = PDFTool()
            resume_text = pdf_tool.extract_text(file_path)
        finally:
            # Resume PDFs may contain PII; delete immediately after
            # extracting text rather than retaining the raw file.
            if os.path.exists(file_path):
                os.remove(file_path)

        if not resume_text or len(resume_text) < 20:
            flash("Could not extract readable text from that PDF. Try a different export.", "danger")
            return redirect(url_for("analyze"))

        # LinkedIn public-data fields provided directly by the user, since
        # we do not scrape LinkedIn (against their ToS).
        linkedin_data = {
            "url": linkedin_url,
            "headline": request.form.get("li_headline", ""),
            "about": request.form.get("li_about", ""),
            "experience": request.form.get("li_experience", ""),
            "education": request.form.get("li_education", ""),
            "skills": request.form.get("li_skills", ""),
            "projects": request.form.get("li_projects", ""),
            "certifications": request.form.get("li_certifications", ""),
        }
        posts = _parse_posts(request.form.get("posts", ""))

        try:
            model = get_groq_model(session.get("groq_api_key"))
        except MissingGroqKeyError as exc:
            flash(str(exc), "danger")
            return redirect(url_for("analyze"))

        try:
            results = run_full_analysis(model, resume_text, linkedin_data, posts=posts, target_role=target_role)
        except Exception as exc:  # noqa: BLE001
            current_app.logger.exception("Agent run failed")
            flash(f"Analysis failed: {exc}", "danger")
            return redirect(url_for("analyze"))

        analysis_id = uuid.uuid4().hex

        resume_record = ResumeRecord(analysis_id=analysis_id, raw_text=resume_text)
        extracted = results.get("resume_analysis", {}).get("extracted", {})
        resume_record.name = extracted.get("name")
        resume_record.email = extracted.get("email")
        resume_record.phone = extracted.get("phone")
        for field in ["skills", "projects", "experience", "education",
                       "certifications", "languages", "achievements"]:
            resume_record.set_list(field, extracted.get(field, []))
        db.session.add(resume_record)

        report = AnalysisReport(analysis_id=analysis_id, linkedin_url=linkedin_url)
        if current_user.is_authenticated:
            report.user_id = current_user.id
        report.set_json("resume_analysis", results.get("resume_analysis", {}))
        report.set_json("profile_analysis", results.get("profile_analysis", {}))
        report.set_json("comparison", results.get("comparison", {}))
        report.set_json("ats", results.get("ats", {}))
        report.set_json("career_advice", results.get("career_advice", {}))
        report.set_json("keyword", results.get("keywords", {}))
        report.set_json("recruiter", results.get("recruiter", {}))
        report.set_json("content_analysis", results.get("content_analysis", {}))
        report.set_json("final_report", results.get("final_report", {}))
        report.overall_score = results.get("overall_score", 0.0)
        db.session.add(report)
        db.session.commit()

        return redirect(url_for("results", analysis_id=analysis_id))

    @app.route("/results/<analysis_id>")
    def results(analysis_id: str):
        """Results dashboard for a completed analysis."""
        report = AnalysisReport.query.filter_by(analysis_id=analysis_id).first()
        if not report:
            flash("Analysis not found.", "warning")
            return redirect(url_for("home"))
        return render_template("results.html", report=report.to_dict())

    @app.route("/results/<analysis_id>/pdf")
    @limiter.limit("20 per hour")
    def download_report_pdf(analysis_id: str):
        """Generate and stream the PDF version of a completed report."""
        report = AnalysisReport.query.filter_by(analysis_id=analysis_id).first()
        if not report:
            flash("Analysis not found.", "warning")
            return redirect(url_for("home"))

        pdf_bytes = build_pdf_report(report.to_dict())
        buf_path = os.path.join(
            current_app.config["REPORTS_FOLDER"], f"{analysis_id}.pdf"
        )
        with open(buf_path, "wb") as f:
            f.write(pdf_bytes)

        return send_file(
            buf_path,
            as_attachment=True,
            download_name=f"linkedin-ai-analysis-{analysis_id[:8]}.pdf",
            mimetype="application/pdf",
        )

    @app.errorhandler(404)
    def not_found(_e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(429)
    def rate_limited(_e):
        return render_template("errors/429.html"), 429

    @app.errorhandler(500)
    def server_error(_e):
        return render_template("errors/500.html"), 500


app = create_app()

if __name__ == "__main__":
    app.run(debug=app.config.get("DEBUG", True), host="0.0.0.0", port=5000)
