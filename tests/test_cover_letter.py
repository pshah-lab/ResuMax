"""
Tests for Grounded Cover Letter Generator (FR-10).
"""

import pytest
import httpx
from pathlib import Path

from models import MasterProfile, JDExtraction, CoverLetter
from cover_letter_generator import generate_cover_letter
from document_exporter import export_cover_letter_to_docx, export_cover_letter_to_pdf
from ats_validator import validate_pdf_file
from app import app


@pytest.fixture
def sample_profile():
    return MasterProfile(
        personal_info={
            "full_name": "Pratham Shah",
            "email": "pshah88669@gmail.com",
            "phone": "+91-6356356971",
            "location": "India",
            "portfolio_url": "https://pshah.fun"
        },
        summary="Cloud Security & Full-Stack Engineer.",
        work_experience=[
            {
                "id": "we_1",
                "company": "Searce Inc.",
                "title": "Cloud Security Reliability Engineer Intern",
                "bullets": [
                    {
                        "id": "b_1",
                        "text": "Analyzed Google Cloud infrastructure utilization and billing data.",
                        "skills_tags": ["Google Cloud", "FinOps"],
                        "metrics": []
                    },
                    {
                        "id": "b_2",
                        "text": "Developed FinOps optimization strategies that saved $2,000+ in verified client savings.",
                        "skills_tags": ["Google Cloud", "FinOps"],
                        "metrics": ["$2,000+ savings"]
                    }
                ]
            }
        ],
        education=[],
        skills={
            "technical": ["Google Cloud", "AWS", "Python", "Docker"],
            "tools": ["Git", "CI/CD"],
            "soft": ["Problem Solving"],
            "languages": ["English"]
        },
        certifications=["Google Cloud Associate Cloud Engineer"],
        projects=[]
    )


@pytest.fixture
def sample_jd():
    return JDExtraction(
        job_title="Senior Backend Distributed Systems Engineer",
        company="CloudScale Inc.",
        must_have_requirements=[
            {"requirement": "Experience with Python, distributed systems, and cloud infrastructure", "category": "hard_skill", "keywords": ["Python", "Cloud"]}
        ],
        keywords_for_ats=["Python", "Cloud", "AWS", "GCP", "Distributed Systems"]
    )


def test_cover_letter_generation(sample_profile, sample_jd):
    """Test generating a structured, grounded cover letter."""
    cl = generate_cover_letter(sample_profile, sample_jd)
    assert isinstance(cl, CoverLetter)
    assert cl.target_company == "CloudScale Inc."
    assert cl.target_job_title == "Senior Backend Distributed Systems Engineer"
    assert len(cl.opening) > 20
    assert len(cl.body_paragraphs) >= 1
    assert len(cl.closing) > 10
    assert len(cl.full_text) > 50


def test_cover_letter_docx_export(sample_profile, sample_jd, tmp_path):
    """Test exporting cover letter to Word document."""
    cl = generate_cover_letter(sample_profile, sample_jd)
    docx_path = tmp_path / "test_cover_letter.docx"
    exported_path = export_cover_letter_to_docx(sample_profile, cl, docx_path)

    assert exported_path.exists()
    assert exported_path.stat().st_size > 1000


def test_cover_letter_pdf_export(sample_profile, sample_jd, tmp_path):
    """Test exporting cover letter to text-layer PDF."""
    cl = generate_cover_letter(sample_profile, sample_jd)
    pdf_path = tmp_path / "test_cover_letter.pdf"
    exported_path = export_cover_letter_to_pdf(sample_profile, cl, pdf_path)

    assert exported_path.exists()
    assert exported_path.stat().st_size > 1000

    # Verify text layer
    pdf_val = validate_pdf_file(exported_path)
    assert pdf_val.passed is True


@pytest.mark.anyio
async def test_cover_letter_api_generate_and_export():
    """Test cover letter API generation and export endpoints."""
    req_body = {
        "jd_text": "Senior Cloud Engineer at CloudScale Inc. Must know Python, AWS, and GCP."
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        # 1. Generate
        gen_res = await client.post("/api/cover-letter/generate", json=req_body)
        assert gen_res.status_code == 200
        gen_data = gen_res.json()
        assert "cover_letter" in gen_data
        cl = gen_data["cover_letter"]

        # 2. Export
        export_res = await client.post("/api/cover-letter/export", json={"cover_letter": cl})
        assert export_res.status_code == 200
        export_data = export_res.json()
        assert export_data["status"] == "success"
        assert "docx_url" in export_data
        assert "pdf_url" in export_data
