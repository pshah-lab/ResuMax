"""
Unit tests for Project Relevance Ranker (Stage 4.5).
Verifies ranking logic, tech stack overlap calculation, and approval filtering.
"""

import pytest
from models import MasterProfile, JDExtraction, ProjectItem, RequirementItem, SkillCategories
from project_ranker import rank_projects_for_jd, RankedProject


def test_rank_projects_for_jd_relevance():
    profile = MasterProfile(
        skills=SkillCategories(technical=["Python", "FastAPI", "TypeScript", "Node.js", "Docker"]),
        projects=[
            ProjectItem(
                id="proj_video",
                name="StreamVault: Secure HLS Streaming",
                tech_stack=["AWS CloudFront", "AWS S3", "AWS Cognito", "TypeScript", "Node.js", "FastAPI"],
                draft_bullets=["Engineered token-gated HLS streaming with AWS CloudFront signed cookies and Cognito auth."],
                reviewed_by_user=True
            ),
            ProjectItem(
                id="proj_nlp",
                name="InsightVault: Semantic Search",
                tech_stack=["Python", "FastAPI", "Vector Search", "LLM"],
                draft_bullets=["Built semantic search pipeline with vector embeddings."],
                reviewed_by_user=True
            ),
            ProjectItem(
                id="proj_unrelated",
                name="Simple HTML Landing Page",
                tech_stack=["HTML", "CSS"],
                draft_bullets=["Static landing page."],
                reviewed_by_user=False
            )
        ]
    )

    jd = JDExtraction(
        job_title="Software Engineer - AI & Streaming",
        company="TechCorp",
        must_have_requirements=[
            RequirementItem(
                requirement="Experience with AWS CloudFront, S3 and video streaming architectures",
                category="tool",
                keywords=["AWS", "CloudFront", "S3"]
            ),
            RequirementItem(
                requirement="Strong proficiency with TypeScript and Node.js backend",
                category="hard_skill",
                keywords=["TypeScript", "Node.js"]
            )
        ],
        keywords_for_ats=["AWS", "CloudFront", "S3", "TypeScript", "Node.js", "FastAPI"]
    )

    ranked = rank_projects_for_jd(profile, jd)

    assert len(ranked) == 3
    # Top ranked should be StreamVault because of AWS, CloudFront, S3, TypeScript, Node.js match
    assert ranked[0].project_id == "proj_video"
    assert ranked[0].score > ranked[2].score
    assert "TypeScript" in ranked[0].matched_keywords or "AWS" in ranked[0].matched_keywords
    assert ranked[0].is_approved is True
