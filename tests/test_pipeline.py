"""
Comprehensive tests for all stages of the ResuMax pipeline:
Stages 2 through 10.
"""

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
    JDExtraction,
    RequirementItem,
    TailoredResume,
    TailoredExperience,
    TailoredBullet
)
from llm_client import LLMClient
from jd_parser import parse_job_description
from gap_analyzer import analyze_gap
from tailoring_engine import tailor_resume
from grounding_checker import verify_grounding
from ats_validator import validate_tailored_resume_structure, validate_docx_file, validate_pdf_file
from review_diff import generate_review_diff, format_terminal_diff
from document_exporter import export_to_docx, export_to_pdf_text_layer
from version_store import VersionStore


@pytest.fixture
def sample_master_profile():
    profile = MasterProfile(
        personal_info=PersonalInfo(
            full_name="Alex Mercer",
            email="alex@example.com",
            phone="+1-555-0199",
            location="San Francisco, CA"
        ),
        summary="Senior Backend Engineer with 5+ years experience building distributed systems.",
        work_experience=[
            WorkExperience(
                id="we_1",
                company="Acme Cloud Corp",
                title="Senior Software Engineer",
                start_date="2022-03",
                end_date=None,
                is_current=True,
                bullets=[
                    BulletPoint(id="b_1", text="Architected event streaming pipeline with Kafka and FastAPI.", skills_tags=["Kafka", "FastAPI", "Python"]),
                    BulletPoint(id="b_2", text="Optimized database queries and Redis caching to reduce latency by 45%.", skills_tags=["Redis", "PostgreSQL"])
                ]
            ),
            WorkExperience(
                id="we_2",
                company="Nexus Systems",
                title="Software Engineer",
                start_date="2019-06",
                end_date="2022-02",
                bullets=[
                    BulletPoint(id="b_3", text="Developed analytics dashboard with TypeScript and GraphQL.", skills_tags=["TypeScript", "GraphQL"])
                ]
            )
        ],
        education=[Education(id="ed_1", institution="UW", degree="B.S.", field="CS", graduation_date="2019-05")],
        skills=SkillCategories(
            technical=["Python", "FastAPI", "Kafka", "Redis", "PostgreSQL", "GraphQL", "TypeScript", "Distributed Systems"],
            tools=["Docker", "Kubernetes", "AWS", "Git", "GitHub Actions"],
            soft=["System Design", "Leadership"],
            languages=["English"]
        ),
        certifications=["AWS Certified Solutions Architect"],
        projects=[
            ProjectItem(id="proj_1", name="AudioEngine", description_raw="DSP library", draft_bullets=["Built DSP"], reviewed_by_user=True)
        ]
    )
    profile.ensure_unique_ids()
    return profile


def test_stage2_and_3_jd_parsing():
    """Test Stage 2 & 3: JD Ingestion and structured extraction."""
    raw_jd = """
    Senior Backend Engineer at CloudScale Inc.
    Requirements:
    - 5+ years experience with Python and distributed systems (Required)
    - Experience with Kafka and Redis caching
    - Familiarity with Kubernetes and AWS
    """
    mock_client = LLMClient(provider="mock")
    jd = parse_job_description(raw_jd, llm_client=mock_client)

    assert jd.job_title == "Senior Backend Distributed Systems Engineer"
    assert jd.company == "CloudScale Inc."
    assert len(jd.must_have_requirements) > 0
    assert "Python" in jd.keywords_for_ats


def test_stage4_gap_analysis(sample_master_profile):
    """Test Stage 4: Deterministic Gap and Match calculation."""
    jd = JDExtraction(
        job_title="Senior Backend Engineer",
        company="CloudScale Inc.",
        must_have_requirements=[
            RequirementItem(requirement="Experience with Kafka", category="tool", keywords=["Kafka"]),
            RequirementItem(requirement="Experience with Rust", category="hard_skill", keywords=["Rust"]),
        ],
        keywords_for_ats=["Python", "Kafka", "Redis", "Rust", "Golang"]
    )

    gap = analyze_gap(sample_master_profile, jd)

    assert "Python" in gap.matched_keywords
    assert "Kafka" in gap.matched_keywords
    assert "Rust" in gap.missing_keywords
    assert "Golang" in gap.missing_keywords
    assert gap.keyword_coverage_pct == 60.0  # 3 out of 5
    assert len(gap.matched_must_haves) == 1
    assert len(gap.unmatched_must_haves) == 1
    assert gap.unmatched_must_haves[0].keywords == ["Rust"]


def test_stage5_tailoring_engine(sample_master_profile):
    """Test Stage 5: Tailoring engine produces valid TailoredResume referencing bullet IDs."""
    jd = JDExtraction(
        job_title="Senior Backend Engineer",
        company="CloudScale Inc.",
        must_have_requirements=[],
        keywords_for_ats=["Python", "Kafka"]
    )
    mock_client = LLMClient(provider="mock")
    tailored = tailor_resume(sample_master_profile, jd, llm_client=mock_client)

    assert tailored.target_company == "CloudScale Inc."
    assert len(tailored.selected_experience) > 0
    for exp in tailored.selected_experience:
        for b in exp.bullets:
            assert b.source_bullet_id.startswith("b_")


def test_stage6_grounding_check(sample_master_profile):
    """Test Stage 6: Grounding checker catches fabricated bullet IDs or claims."""
    # Valid tailored resume
    valid_tailored = TailoredResume(
        target_company="CloudScale Inc.",
        target_job_title="Senior Backend Engineer",
        selected_experience=[
            TailoredExperience(
                id="we_1",
                company="Acme Cloud Corp",
                title="Senior Software Engineer",
                location="San Francisco, CA",
                bullets=[TailoredBullet(source_bullet_id="b_1", tailored_text="Valid rephrased bullet")]
            )
        ]
    )
    mock_client = LLMClient(provider="mock")
    result_valid = verify_grounding(sample_master_profile, valid_tailored, llm_client=mock_client)
    assert result_valid.passed is True

    # Invalid tailored resume with fabricated source_bullet_id
    invalid_tailored = TailoredResume(
        target_company="CloudScale Inc.",
        target_job_title="Senior Backend Engineer",
        selected_experience=[
            TailoredExperience(
                id="we_1",
                company="Acme Cloud Corp",
                title="Senior Software Engineer",
                location="San Francisco, CA",
                bullets=[TailoredBullet(source_bullet_id="b_hallucinated_999", tailored_text="Invented bullet")]
            )
        ]
    )
    result_invalid = verify_grounding(sample_master_profile, invalid_tailored, llm_client=mock_client)
    assert result_invalid.passed is False
    assert any("b_hallucinated_999" in c.reason for c in result_invalid.unsupported_claims)


def test_stage7_and_9_ats_validator_and_exporter(tmp_path, sample_master_profile):
    """Test Stage 7 & 9: Exporting DOCX and PDF and passing ATS validation."""
    mock_client = LLMClient(provider="mock")
    jd = parse_job_description("Sample JD", llm_client=mock_client)
    tailored = tailor_resume(sample_master_profile, jd, llm_client=mock_client)

    # 1. Structural check
    data_check = validate_tailored_resume_structure(tailored)
    assert data_check.passed is True
    assert data_check.score >= 80

    # 2. DOCX Export and validation
    docx_path = tmp_path / "test_resume.docx"
    export_to_docx(sample_master_profile, tailored, docx_path)
    assert docx_path.exists()

    docx_check = validate_docx_file(docx_path)
    assert docx_check.passed is True
    assert docx_check.score == 100

    # 3. PDF Export and text-layer validation
    pdf_path = tmp_path / "test_resume.pdf"
    export_to_pdf_text_layer(sample_master_profile, tailored, pdf_path)
    assert pdf_path.exists()

    pdf_check = validate_pdf_file(pdf_path)
    assert pdf_check.passed is True


def test_stage8_review_diff(sample_master_profile):
    """Test Stage 8: Human Review Diff engine."""
    mock_client = LLMClient(provider="mock")
    jd = parse_job_description("Sample JD", llm_client=mock_client)
    tailored = tailor_resume(sample_master_profile, jd, llm_client=mock_client)

    diff = generate_review_diff(sample_master_profile, tailored)
    assert len(diff) > 0
    assert diff[0]["source_id"] == "b_1"
    assert "original_text" in diff[0]
    assert "tailored_text" in diff[0]

    terminal_diff = format_terminal_diff(sample_master_profile, tailored)
    assert "HUMAN REVIEW DIFF" in terminal_diff
    assert "ORIGINAL:" in terminal_diff
    assert "TAILORED:" in terminal_diff


def test_stage10_version_store(tmp_path, sample_master_profile):
    """Test Stage 10: Version Store persistence and indexing."""
    store = VersionStore(tmp_path / "exports")
    mock_client = LLMClient(provider="mock")
    jd = parse_job_description("Sample JD", llm_client=mock_client)
    tailored = tailor_resume(sample_master_profile, jd, llm_client=mock_client)

    record = store.save_application_version(
        tailored=tailored,
        jd=jd,
        raw_jd_text="Sample JD Text",
        docx_path=tmp_path / "resume.docx"
    )

    assert record.company == "CloudScale Inc."
    assert (tmp_path / "exports" / "versions_index.json").exists()

    versions = store.list_versions()
    assert len(versions) == 1
    assert versions[0].version_id == record.version_id
