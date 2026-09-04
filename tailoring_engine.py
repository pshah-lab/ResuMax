"""
Resume Tailoring Engine for Stage 5 (LLM Call #2).
Reorders experience, mirrors JD phrasing accurately, integrates genuine keywords,
and enforces closed-world generation (ATS_Guidelines_and_Prompt_Design.md §6).
"""

import json
from datetime import datetime
from typing import Optional, Dict, Any, List

from models import MasterProfile, JDExtraction, GapAnalysisResult, TailoredResume
from llm_client import LLMClient


TAILORING_SYSTEM_PROMPT = """
You are a resume tailoring assistant. You will be given:
(1) a Master Profile — the candidate's complete, factual work history, education, skills, and approved projects,
(2) a structured JD Requirements object for a specific role, and
(3) a Gap Analysis report showing matched and missing keywords.

Your task:
1. Select the subset of experience and projects most relevant to this JD. Don't omit genuinely relevant
   experience, and don't pad with irrelevant roles if space is constrained.
2. Reorder bullets within each role to lead with the most JD-relevant achievements.
3. Rephrase bullet wording to mirror JD terminology ONLY where that terminology accurately
   describes what the candidate actually did. Example: if the Master Profile says "led a team
   of 5 engineers to launch a product" and the JD asks for "cross-functional leadership," you
   MAY write "led a cross-functional team of 5 engineers..." only if the team was in fact
   cross-functional — otherwise leave it as-is.
4. Work JD keywords into the summary and skills sections naturally, but ONLY skills/tools that
   already appear in the Master Profile.
5. Preserve the candidate's specific, concrete phrasing where possible rather than replacing it
   with generic corporate-impact language ("leveraged synergies," "drove results") — specific
   beats polished.
6. NEVER invent a company, title, date, degree, certification, skill, or metric not present in
   the Master Profile. NEVER change employment dates or job titles.
7. Every tailored bullet MUST include the exact source_bullet_id it was derived from.
8. List, separately in unmatched_must_haves_notes (not inside the resume body), any JD must-have
   requirements the Master Profile does not clearly support. This is for candidate awareness —
   do not paper over gaps by fabricating coverage.

Output valid JSON matching this schema:
{
  "job_id_ref": "...",
  "target_job_title": "...",
  "target_company": "...",
  "generated_at": "YYYY-MM-DD",
  "summary": "...",
  "selected_experience": [
    {
      "id": "we_1",
      "company": "...",
      "title": "...",
      "location": "...",
      "start_date": "YYYY-MM",
      "end_date": "YYYY-MM or null",
      "is_current": true/false,
      "bullets": [
        {
          "source_bullet_id": "b_1",
          "tailored_text": "..."
        }
      ]
    }
  ],
  "selected_education": [
    {
      "id": "ed_1",
      "institution": "...",
      "degree": "...",
      "field": "...",
      "graduation_date": "..."
    }
  ],
  "selected_skills": {
    "technical": ["..."],
    "tools": ["..."],
    "soft": ["..."],
    "languages": ["..."]
  },
  "selected_certifications": ["..."],
  "selected_projects": [
    {
      "id": "proj_1",
      "name": "...",
      "source": "...",
      "source_ref": "...",
      "description_raw": "...",
      "draft_bullets": ["..."],
      "tech_stack": ["..."],
      "start_date": "...",
      "end_date": "...",
      "last_active_date": "...",
      "visibility": "public",
      "links": {},
      "review_flags": [],
      "reviewed_by_user": true
    }
  ],
  "unmatched_must_haves_notes": ["..."]
}
"""


def tailor_resume(
    profile: MasterProfile,
    jd: JDExtraction,
    gap_result: Optional[GapAnalysisResult] = None,
    approved_project_ids: Optional[List[str]] = None,
    llm_client: Optional[LLMClient] = None
) -> TailoredResume:
    """Generates a tailored, grounded resume targeting a specific job description."""
    client = llm_client or LLMClient()
    
    # Strictly filter projects to user-approved selection or existing approved ones (PRD.md §8 guardrail)
    sanitized_profile = profile.model_copy(deep=True)
    if approved_project_ids is not None:
        sanitized_profile.projects = [
            p for p in sanitized_profile.projects if p.id in approved_project_ids
        ]
        for p in sanitized_profile.projects:
            p.reviewed_by_user = True
    else:
        sanitized_profile.projects = sanitized_profile.get_approved_projects()

    user_prompt = (
        f"MASTER PROFILE (GROUND TRUTH):\n"
        f"{sanitized_profile.model_dump_json(indent=2)}\n\n"
        f"JD REQUIREMENTS:\n"
        f"{jd.model_dump_json(indent=2)}\n\n"
        f"GAP ANALYSIS REPORT:\n"
        f"{gap_result.model_dump_json(indent=2) if gap_result else 'None provided'}"
    )

    extracted_dict = client.generate_json(
        system_prompt=TAILORING_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.3  # Moderate temperature for natural rephrasing without hallucination
    )

    if not extracted_dict.get("generated_at"):
        extracted_dict["generated_at"] = datetime.now().strftime("%Y-%m-%d")

    return TailoredResume(**extracted_dict)
