"""
Unit and integration tests for FastAPI Web Dashboard backend (app.py).
"""

import pytest
import httpx
from pathlib import Path

from app import app
from models import MasterProfile, PersonalInfo, WorkExperience, BulletPoint


@pytest.mark.anyio
async def test_get_profile_endpoint():
    """Test retrieving current Master Profile."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/profile")
        assert response.status_code == 200
        data = response.json()
        assert "profile" in data
        assert "stats" in data
        assert "work_experiences" in data["stats"]


@pytest.mark.anyio
async def test_update_profile_endpoint():
    """Test updating Master Profile via API."""
    profile_data = {
        "personal_info": {
            "full_name": "Pratham Shah",
            "email": "pshah88669@gmail.com",
            "phone": "+91-6356356971",
            "location": "India",
            "linkedin_url": "https://github.com/prathamshah",
            "portfolio_url": "https://pshah.fun"
        },
        "summary": "Cloud Security & Full-Stack Engineer.",
        "work_experience": [
            {
                "id": "we_1",
                "company": "Searce Inc.",
                "title": "Cloud Security Reliability Engineer Intern",
                "location": "",
                "start_date": "2026-04",
                "end_date": None,
                "is_current": True,
                "bullets": [
                    {
                        "id": "b_1",
                        "text": "Analyzed Google Cloud infrastructure utilization.",
                        "skills_tags": ["Google Cloud"],
                        "metrics": []
                    }
                ]
            }
        ],
        "education": [],
        "skills": {
            "technical": ["Google Cloud", "AWS", "Python"],
            "tools": ["Docker", "Git"],
            "soft": ["Problem Solving"],
            "languages": ["English"]
        },
        "certifications": ["Google Cloud Associate Cloud Engineer"],
        "projects": []
    }

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/api/profile", json=profile_data)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["stats"]["work_experiences"] == 1


@pytest.mark.anyio
async def test_tailor_analyze_endpoint():
    """Test analyzing a Job Description for keyword alignment."""
    req_body = {
        "jd_text": "Looking for a Cloud Engineer with Google Cloud, AWS, and Python experience."
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/api/tailor/analyze", json=req_body)
        assert response.status_code == 200
        data = response.json()
        assert "jd" in data
        assert "gap_analysis" in data
        assert data["gap_analysis"]["keyword_coverage_pct"] >= 0


@pytest.mark.anyio
async def test_tailor_generate_endpoint():
    """Test generating a tailored resume with grounding check."""
    req_body = {
        "jd_text": "Senior Cloud Engineer at CloudScale Inc. Must have Python, Kafka, Redis, and Docker."
    }
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/api/tailor/generate", json=req_body)
        assert response.status_code == 200
        data = response.json()
        assert "tailored_resume" in data
        assert "grounding_check" in data
        assert "bullet_diffs" in data


@pytest.mark.anyio
async def test_tailor_export_endpoint():
    """Test exporting a tailored resume to docx and pdf."""
    tailored_data = {
        "job_id_ref": "test_job_1",
        "target_job_title": "Senior Cloud Engineer",
        "target_company": "CloudScale Inc",
        "generated_at": "2026-08-22",
        "summary": "Experienced Cloud Engineer.",
        "selected_experience": [
            {
                "id": "we_1",
                "company": "Searce Inc.",
                "title": "Cloud Engineer",
                "location": "India",
                "start_date": "2026-04",
                "end_date": None,
                "is_current": True,
                "bullets": [
                    {
                        "source_bullet_id": "b_1",
                        "tailored_text": "Optimized cloud costs and infrastructure."
                    }
                ]
            }
        ],
        "selected_education": [],
        "selected_skills": {
            "technical": ["Google Cloud", "AWS", "Python"],
            "tools": ["Docker"],
            "soft": [],
            "languages": ["English"]
        },
        "selected_certifications": [],
        "selected_projects": []
    }

    req_body = {
        "tailored_resume": tailored_data,
        "export_format": "all"
    }

    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.post("/api/tailor/export", json=req_body)
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert "docx_url" in data
        assert "pdf_url" in data


@pytest.mark.anyio
async def test_get_version_history():
    """Test retrieving version history."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        response = await client.get("/api/versions")
        assert response.status_code == 200
        data = response.json()
        assert "versions" in data
        assert len(data["versions"]) >= 1
