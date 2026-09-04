"""
Unit tests for Stage 1: Master Profile Intake, Bootstrapping & Project Ingestion.
"""

import json
import pytest
from pathlib import Path

from models import (
    MasterProfile,
    PersonalInfo,
    WorkExperience,
    BulletPoint,
    Education,
    SkillCategories,
    ProjectItem,
)
from profile_manager import ProfileManager
from resume_bootstrapper import bootstrap_master_profile_from_text, extract_text_from_file
from project_extractor import extract_project_details
from llm_client import LLMClient


def test_master_profile_model_and_id_generation():
    """Verify MasterProfile assigns unique IDs if missing."""
    profile = MasterProfile(
        personal_info=PersonalInfo(full_name="Jane Doe", email="jane@example.com"),
        work_experience=[
            WorkExperience(
                id="",
                company="Tech Co",
                title="Lead Developer",
                bullets=[
                    BulletPoint(id="", text="Built distributed queue", skills_tags=["Python"], metrics=["10k rps"]),
                    BulletPoint(id="", text="Optimized database indices", skills_tags=["SQL"], metrics=["50% faster"]),
                ],
            )
        ],
        education=[Education(id="", institution="MIT", degree="B.S.", field="CS")],
        projects=[ProjectItem(id="", name="My Project", description_raw="Sample readme")],
    )

    profile.ensure_unique_ids()

    assert profile.work_experience[0].id == "we_1"
    assert profile.work_experience[0].bullets[0].id == "b_1"
    assert profile.work_experience[0].bullets[1].id == "b_2"
    assert profile.education[0].id == "ed_1"
    assert profile.projects[0].id == "proj_1"

    # Verify get_all_bullets mapping
    bullets_map = profile.get_all_bullets()
    assert "b_1" in bullets_map
    assert "b_2" in bullets_map
    assert bullets_map["b_1"].text == "Built distributed queue"


def test_project_safety_gate_reviewed_by_user():
    """Verify projects default to reviewed_by_user = False and get_approved_projects filters them."""
    proj1 = ProjectItem(id="p1", name="Proj 1", reviewed_by_user=False)
    proj2 = ProjectItem(id="p2", name="Proj 2", reviewed_by_user=True)

    profile = MasterProfile(projects=[proj1, proj2])
    approved = profile.get_approved_projects()

    assert len(approved) == 1
    assert approved[0].id == "p2"


def test_resume_bootstrapper_with_mock_llm(tmp_path):
    """Test bootstrapping a MasterProfile from resume text."""
    sample_text = """
    Alex Mercer
    Email: alex.mercer@example.com | Phone: +1-555-0199
    Senior Software Engineer at Acme Cloud Corp (2022 - Present)
    - Architected real-time event streaming pipeline processing 20M+ events/day using Kafka and FastAPI.
    """
    mock_client = LLMClient(provider="mock")
    profile = bootstrap_master_profile_from_text(sample_text, llm_client=mock_client)

    assert profile.personal_info.full_name == "Alex Mercer"
    assert len(profile.work_experience) >= 1
    assert profile.work_experience[0].bullets[0].id == "b_1"
    assert "Kafka" in profile.work_experience[0].bullets[0].skills_tags


def test_project_extractor_with_mock_llm():
    """Test extracting candidate bullets and tech stack from a scraped project."""
    raw_project = {
        "id": "github_resumax",
        "name": "resumax",
        "source": "github",
        "source_ref": "https://github.com/user/resumax",
        "description_raw": "A repository scraper that extracts repo metadata and README details.",
        "tech_stack": ["Python"],
        "start_date": "2026-01-01",
        "last_active_date": "2026-08-20",
        "visibility": "public",
        "links": {"repo": "https://github.com/user/resumax"},
        "reviewed_by_user": False
    }

    mock_client = LLMClient(provider="mock")
    extracted = extract_project_details(raw_project, llm_client=mock_client)

    assert extracted.id == "github_resumax"
    assert extracted.reviewed_by_user is False  # Must remain false until human review
    assert len(extracted.draft_bullets) >= 1
    assert "Python" in extracted.tech_stack


def test_profile_manager_lifecycle(tmp_path):
    """Test ProfileManager save, load, merge, and project review workflow."""
    profile_path = tmp_path / "test_master_profile.json"
    manager = ProfileManager(profile_path)

    # Initial state should be empty
    assert len(manager.profile.work_experience) == 0

    # Add experience and save
    manager.profile.personal_info.full_name = "Taylor Swift"
    manager.profile.work_experience.append(
        WorkExperience(
            id="we_1",
            company="Music Inc",
            title="Producer",
            bullets=[BulletPoint(id="b_1", text="Produced 10 hit albums")]
        )
    )
    manager.save()

    # Reload in a new manager instance
    manager2 = ProfileManager(profile_path)
    assert manager2.profile.personal_info.full_name == "Taylor Swift"
    assert len(manager2.profile.work_experience) == 1

    # Merge an unreviewed project
    new_proj = ProjectItem(
        id="proj_1",
        name="SoundEngine",
        description_raw="Audio processing lib",
        draft_bullets=["Engineered DSP filter"],
        reviewed_by_user=False
    )
    manager2.merge_projects([new_proj])
    assert len(manager2.profile.projects) == 1
    assert manager2.profile.projects[0].reviewed_by_user is False

    # Review and approve project
    success = manager2.review_project("proj_1", approve=True, edited_bullets=["Custom approved bullet"])
    assert success is True

    # Reload and verify approval persisted
    manager3 = ProfileManager(profile_path)
    assert manager3.profile.projects[0].reviewed_by_user is True
    assert manager3.profile.projects[0].draft_bullets == ["Custom approved bullet"]
    assert len(manager3.profile.get_approved_projects()) == 1


def test_extract_text_from_plain_text(tmp_path):
    """Test document reader on a plain text / markdown file."""
    txt_file = tmp_path / "sample_resume.txt"
    txt_file.write_text("John Doe\nSoftware Engineer\n5 years experience", encoding="utf-8")

    text = extract_text_from_file(txt_file)
    assert "John Doe" in text
    assert "Software Engineer" in text
