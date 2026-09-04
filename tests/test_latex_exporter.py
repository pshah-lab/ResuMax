"""
Unit and integration tests for LaTeX Resume Exporter.
"""

import pytest
import httpx
from pathlib import Path

from latex_exporter import escape_latex, generate_latex_code, export_to_latex
from profile_manager import ProfileManager
from tailoring_engine import tailor_resume
from jd_parser import parse_job_description
from app import app


def test_escape_latex():
    """Verify LaTeX special character escaping."""
    raw = "Saved $2,000+ & reduced latency by 50% using C#_v2 {core}"
    escaped = escape_latex(raw)
    assert r"\$2,000+" in escaped
    assert r"\&" in escaped
    assert r"\%" in escaped
    assert r"\_" in escaped
    assert r"\{" in escaped
    assert r"\}" in escaped


def test_generate_latex_code():
    """Verify end-to-end LaTeX code assembly from Master Profile & Tailored Resume."""
    manager = ProfileManager()
    profile = manager.profile
    jd = parse_job_description("Senior Backend Engineer at Stripe. Expertise in Python, AWS, Docker.")
    tailored = tailor_resume(profile, jd)

    tex_code = generate_latex_code(profile, tailored)

    assert r"\documentclass[a4paper,10pt]{article}" in tex_code
    assert r"\begin{document}" in tex_code
    assert r"\end{document}" in tex_code
    assert r"\section*{Experience}" in tex_code
    if profile.education:
        assert r"\section*{Education}" in tex_code
    assert r"\section*{Technical Skills}" in tex_code
    if profile.personal_info.full_name:
        assert profile.personal_info.full_name in tex_code


def test_export_to_latex(tmp_path):
    """Verify writing .tex file to disk."""
    manager = ProfileManager()
    profile = manager.profile
    jd = parse_job_description("Cloud Reliability Engineer. Google Cloud, FinOps.")
    tailored = tailor_resume(profile, jd)

    out_file = tmp_path / "test_resume.tex"
    exported = export_to_latex(profile, tailored, out_file)

    assert exported.exists()
    content = exported.read_text(encoding="utf-8")
    assert r"\documentclass" in content
    assert r"\begin{document}" in content


@pytest.mark.anyio
async def test_latex_api_endpoints():
    """Verify that tailor generate and export API endpoints return valid latex_code and tex_url."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        # Generate
        gen_res = await client.post("/api/tailor/generate", json={
            "jd_text": "Cloud Security Reliability Engineer at Searce. Google Cloud, FinOps, Cost Optimization."
        })
        assert gen_res.status_code == 200
        gen_data = gen_res.json()
        assert "latex_code" in gen_data
        assert r"\documentclass" in gen_data["latex_code"]

        # Export
        export_res = await client.post("/api/tailor/export", json={
            "tailored_resume": gen_data["tailored_resume"],
            "export_format": "all"
        })
        assert export_res.status_code == 200
        export_data = export_res.json()
        assert "tex_url" in export_data
        assert export_data["tex_url"].endswith(".tex")
