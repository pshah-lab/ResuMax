"""
Unit and integration tests for Stage 1a: Project Ingestion & Review Gate (PRD FR-1a).
"""

import pytest
import httpx
from pathlib import Path

from github_scraper import build_project, scrape_github
from portfolio_scraper import scrape_portfolio, scrape_portfolio_page
from local_scraper import scrape_local, detect_tech_stack
from project_extractor import extract_project_details, ingest_and_extract_projects
from profile_manager import ProfileManager
from models import MasterProfile, ProjectItem
from app import app


def test_github_project_builder():
    """Test building project item from GitHub repo payload."""
    mock_repo = {
        "name": "resumax",
        "owner": {"login": "prathamshah"},
        "html_url": "https://github.com/prathamshah/resumax",
        "description": "AI Resume Tailoring Engine",
        "created_at": "2026-08-20T00:00:00Z",
        "pushed_at": "2026-08-22T00:00:00Z",
        "private": False,
        "language": "Python"
    }
    project = build_project(mock_repo)
    assert project["name"] == "resumax"
    assert project["source"] == "github"
    assert project["reviewed_by_user"] is False
    assert "Python" in project["tech_stack"]


def test_local_tech_stack_detection(tmp_path):
    """Test manifest-based tech stack detection on local folder."""
    project_dir = tmp_path / "sample_app"
    project_dir.mkdir()
    (project_dir / "package.json").write_text("{}", encoding="utf-8")
    (project_dir / "requirements.txt").write_text("fastapi", encoding="utf-8")

    detected = detect_tech_stack(project_dir)
    assert "Node.js/JavaScript" in detected
    assert "Python" in detected


def test_project_extractor_safety_gate():
    """Test that Project Extractor drafts candidate bullets and enforces reviewed_by_user = False."""
    raw_project = {
        "id": "proj_demo",
        "name": "Cloud Cost Engine",
        "source": "github",
        "source_ref": "https://github.com/prathamshah/cost-engine",
        "description_raw": "A tool that analyzes AWS and GCP usage patterns to optimize cloud compute resources.",
        "tech_stack": ["Python", "AWS", "Docker"],
        "start_date": "2026-01-01",
        "last_active_date": "2026-04-01",
        "visibility": "public"
    }

    item = extract_project_details(raw_project)
    assert isinstance(item, ProjectItem)
    assert item.name == "Cloud Cost Engine"
    assert len(item.draft_bullets) >= 1
    assert item.reviewed_by_user is False  # Mandatory Gate


@pytest.mark.anyio
async def test_project_ingest_and_review_api(tmp_path):
    """Test API endpoint for ingesting and reviewing projects."""
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://testserver") as client:
        # 1. Fetch current projects
        res = await client.get("/api/projects")
        assert res.status_code == 200
        data = res.json()
        assert "projects" in data

        # 2. Ingest
        ingest_res = await client.post("/api/projects/ingest", json={"source": "portfolio", "portfolio_url": "https://pshah.fun"})
        assert ingest_res.status_code == 200
        ingest_data = ingest_res.json()
        assert ingest_data["status"] in ["success", "warning", "info"]

        # 3. Review a project dynamically
        projects_after = (await client.get("/api/projects")).json()["projects"]
        if not projects_after:
            profile_res = await client.get("/api/profile")
            prof = profile_res.json()["profile"]
            prof["projects"] = [{
                "id": "proj_test_item",
                "name": "Test App",
                "source": "manual",
                "source_ref": "",
                "description_raw": "Test project",
                "draft_bullets": ["Built test project"],
                "tech_stack": ["Python"],
                "visibility": "public",
                "reviewed_by_user": False
            }]
            await client.post("/api/profile", json=prof)
            target_id = "proj_test_item"
        else:
            target_id = projects_after[0]["id"]

        review_res = await client.post("/api/projects/review", json={
            "project_id": target_id,
            "approve": True
        })
        assert review_res.status_code == 200
        review_data = review_res.json()
        assert review_data["status"] == "success"


def test_is_project_already_ingested_deduplication(tmp_path):
    """Test deterministic deduplication checker in ProfileManager."""
    mgr = ProfileManager(tmp_path / "test_profile.json")
    mgr.profile.projects = [
        ProjectItem(
            id="proj_stream_vault",
            name="StreamVault: Secure HLS Streaming",
            source="github",
            source_ref="https://github.com/pshah-lab/StreamVault",
            reviewed_by_user=True
        )
    ]

    # Test exact ID match
    assert mgr.is_project_already_ingested(project_id="proj_stream_vault") is True
    assert mgr.is_project_already_ingested(project_id="proj_other") is False

    # Test repository URL match (case-insensitive, trailing slash resilient)
    assert mgr.is_project_already_ingested(source_ref="https://github.com/pshah-lab/StreamVault/") is True
    assert mgr.is_project_already_ingested(source_ref="https://github.com/pshah-lab/OtherRepo") is False

    # Test name match
    assert mgr.is_project_already_ingested(name="StreamVault: Secure HLS Streaming") is True
    assert mgr.is_project_already_ingested(name="Completely Brand New App") is False

    # Test merge_projects skip_existing=True
    duplicate_item = ProjectItem(
        id="proj_stream_vault",
        name="StreamVault",
        source_ref="https://github.com/pshah-lab/StreamVault",
        draft_bullets=["New draft bullet that should be skipped"],
        reviewed_by_user=False
    )
    added = mgr.merge_projects([duplicate_item], skip_existing=True)
    assert added == 0
    assert mgr.profile.projects[0].reviewed_by_user is True  # Preserved!

