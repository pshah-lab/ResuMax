"""
Grounded Cover Letter Generator for PRD FR-10.
Generates role-tailored, zero-fabrication cover letters from Master Profile ground truth
and structured JD requirements.
"""

from datetime import datetime
from typing import Optional, Dict, Any, List

from models import MasterProfile, JDExtraction, GapAnalysisResult, CoverLetter
from llm_client import LLMClient


COVER_LETTER_SYSTEM_PROMPT = """
You are an expert executive career writer and technical cover letter generator.
You will be given:
(1) a Master Profile — the candidate's complete, factual work history, education, skills, and approved projects,
(2) a structured JD Requirements object for a specific role, and
(3) a Gap Analysis report showing matched requirements.

Your task:
Draft a compelling, highly tailored, and 100% grounded cover letter.

Rules:
1. ZERO FABRICATION: Never invent a past project, metric, employer, degree, or skill.
   Every achievement cited MUST trace directly back to a verified bullet or project in the Master Profile.
2. AVOID GENERIC AI CLICHÉS:
   Do NOT use hollow filler phrases like "I am writing to express my enthusiastic interest," "I am uniquely qualified,"
   or "I leveraged synergies to drive impactful results."
   Use crisp, direct, engineering-focused language that highlights concrete problem solving.
3. STRUCTURE:
   - Salutation: "Dear [Company] Hiring Team," or specific title if available.
   - Opening: Hook interest in the specific company mission and target role, stating immediate core alignment.
   - Body Paragraph 1 (Technical & Business Impact): Directly connect 1-2 major verified accomplishments
     from the Master Profile (with real metrics) to the job's primary responsibilities.
   - Body Paragraph 2 (Architectural / Problem-Solving Depth): Connect another verified project or technical
     mastery area to the company's tech stack and scale.
   - Closing: Professional, confident closing with clear call to action.
4. Output valid JSON matching this schema:
{
  "job_id_ref": "...",
  "target_company": "...",
  "target_job_title": "...",
  "generated_at": "YYYY-MM-DD",
  "recipient_title": "Hiring Team",
  "salutation": "...",
  "opening": "...",
  "body_paragraphs": ["...", "..."],
  "closing": "...",
  "full_text": "...",
  "grounded_bullet_refs": ["b_1", "b_2"]
}
"""


def generate_cover_letter(
    profile: MasterProfile,
    jd: JDExtraction,
    gap_result: Optional[GapAnalysisResult] = None,
    llm_client: Optional[LLMClient] = None
) -> CoverLetter:
    """Generates a grounded, role-aligned cover letter."""
    client = llm_client or LLMClient()

    sanitized_profile = profile.model_copy(deep=True)
    sanitized_profile.projects = sanitized_profile.get_approved_projects()

    user_prompt = (
        f"MASTER PROFILE (GROUND TRUTH):\n"
        f"{sanitized_profile.model_dump_json(indent=2)}\n\n"
        f"TARGET JOB DESCRIPTION:\n"
        f"{jd.model_dump_json(indent=2)}\n\n"
        f"GAP ANALYSIS:\n"
        f"{gap_result.model_dump_json(indent=2) if gap_result else 'None provided'}"
    )

    extracted_dict = client.generate_json(
        system_prompt=COVER_LETTER_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.3
    )

    if not extracted_dict.get("generated_at"):
        extracted_dict["generated_at"] = datetime.now().strftime("%Y-%m-%d")

    # Ensure full_text is assembled if empty
    if not extracted_dict.get("full_text"):
        parts = [
            extracted_dict.get("salutation", "Dear Hiring Team,"),
            "",
            extracted_dict.get("opening", ""),
            "",
        ]
        for p in extracted_dict.get("body_paragraphs", []):
            parts.extend([p, ""])
        parts.append(extracted_dict.get("closing", ""))
        extracted_dict["full_text"] = "\n".join(parts)

    return CoverLetter(**extracted_dict)
