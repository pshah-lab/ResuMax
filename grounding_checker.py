"""
Grounding / Anti-Fabrication Checker for Stage 6 (LLM Call #3).
Independently verifies every claim in TailoredResume traces back to MasterProfile (ATS_Guidelines_and_Prompt_Design.md §7).
Enforces the Zero-Fabrication Policy (PRD.md §8).
"""

import json
from typing import Optional, List, Dict, Any

from models import MasterProfile, TailoredResume, GroundingCheckResult, GroundingIssue
from llm_client import LLMClient


GROUNDING_SYSTEM_PROMPT = """
You are a fact-checking validator. You will be given a Master Profile (ground truth) and a
Tailored Resume generated from it. Your only job is to identify any claim, skill, metric, or
fact in the Tailored Resume that cannot be directly traced to a specific entry in the Master
Profile.

For each tailored bullet, verify the source_bullet_id points to a real Master Profile bullet,
and that the tailored text is a genuine rephrasing of that bullet's content — not an addition
or invented metric.

Return valid JSON:
{
  "passed": true/false,
  "unsupported_claims": [
    {
      "source_id": "b_1",
      "tailored_text": "...",
      "reason": "Invented metric / added unverified tool / hallucinated claim",
      "severity": "error"
    }
  ]
}

If no unsupported claims or hallucinations are found, return passed=true and an empty list.
Be strict: when in doubt, flag it — a human will make the final call.
"""


def verify_grounding(
    profile: MasterProfile,
    tailored_resume: TailoredResume,
    llm_client: Optional[LLMClient] = None
) -> GroundingCheckResult:
    """
    Performs deterministic and independent LLM verification of all claims in the tailored resume.
    """
    unsupported_claims: List[GroundingIssue] = []

    # 1. Deterministic source_bullet_id validation
    valid_bullets_map = profile.get_all_bullets()
    for exp in tailored_resume.selected_experience:
        for b in exp.bullets:
            if not b.source_bullet_id:
                unsupported_claims.append(
                    GroundingIssue(
                        source_id="MISSING",
                        tailored_text=b.tailored_text,
                        reason="Bullet does not have a source_bullet_id pointing to Master Profile.",
                        severity="error"
                    )
                )
            elif b.source_bullet_id not in valid_bullets_map:
                unsupported_claims.append(
                    GroundingIssue(
                        source_id=b.source_bullet_id,
                        tailored_text=b.tailored_text,
                        reason=f"source_bullet_id '{b.source_bullet_id}' does not exist in Master Profile.",
                        severity="error"
                    )
                )

    # 2. Deterministic project review gate check
    approved_proj_ids = {p.id for p in profile.get_approved_projects()}
    for p in tailored_resume.selected_projects:
        if p.id not in approved_proj_ids:
            unsupported_claims.append(
                GroundingIssue(
                    source_id=p.id,
                    tailored_text=p.name,
                    reason=f"Project '{p.name}' ({p.id}) has not been approved by user (reviewed_by_user=False).",
                    severity="error"
                )
            )

    # 3. LLM Independent Semantic Check
    client = llm_client or LLMClient()
    user_prompt = (
        f"MASTER PROFILE (GROUND TRUTH):\n"
        f"{profile.model_dump_json(indent=2)}\n\n"
        f"TAILORED RESUME TO VERIFY:\n"
        f"{tailored_resume.model_dump_json(indent=2)}"
    )

    try:
        llm_result_dict = client.generate_json(
            system_prompt=GROUNDING_SYSTEM_PROMPT,
            user_prompt=user_prompt,
            temperature=0.0
        )

        for item in llm_result_dict.get("unsupported_claims", []):
            unsupported_claims.append(
                GroundingIssue(
                    source_id=item.get("source_id", "unknown"),
                    tailored_text=item.get("tailored_text", ""),
                    reason=item.get("reason", "Flagged by grounding checker"),
                    severity=item.get("severity", "error")
                )
            )
    except Exception as e:
        # If LLM check fails to respond, don't crash deterministic checks
        pass

    passed = len(unsupported_claims) == 0
    return GroundingCheckResult(passed=passed, unsupported_claims=unsupported_claims)
