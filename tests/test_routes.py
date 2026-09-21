"""
tests/test_routes.py

Covers the routes anyone can hit without an account: landing page,
analysis form, results page for a missing analysis, and error pages.
"""

from __future__ import annotations


def test_home_page(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"LinkedIn AI Profile Analyzer" in resp.data or b"LinkedIn AI Analyzer" in resp.data


def test_analyze_get_renders_form(client):
    resp = client.get("/analyze")
    assert resp.status_code == 200
    assert b"groq_api_key" in resp.data
    assert b"linkedin_url" in resp.data
    assert b"resume" in resp.data


def test_analyze_post_missing_fields_redirects(client):
    resp = client.post("/analyze", data={}, follow_redirects=True)
    assert resp.status_code == 200
    assert b"required" in resp.data


def test_results_missing_analysis_redirects_home(client):
    resp = client.get("/results/does-not-exist", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Analysis not found" in resp.data


def test_pdf_missing_analysis_redirects_home(client):
    resp = client.get("/results/does-not-exist/pdf", follow_redirects=True)
    assert resp.status_code == 200
    assert b"Analysis not found" in resp.data


def test_404_page(client):
    resp = client.get("/this-route-does-not-exist")
    assert resp.status_code == 404
    assert b"404" in resp.data


def test_dashboard_requires_login(client):
    resp = client.get("/dashboard")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]
