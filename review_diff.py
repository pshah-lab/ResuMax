"""
Human Review Diff Engine for Stage 8.
Generates side-by-side diffs between Master Profile ground truth and Tailored Resume bullets.
Allows bullet-by-bullet inspection, edits, and final approval (PRD.md §8).
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from models import MasterProfile, TailoredResume, BulletPoint


class BulletDiff(BaseModel):
    source_id: str
    company: str
    original_text: str
    tailored_text: str
    is_modified: bool


def generate_review_diff(profile: MasterProfile, tailored: TailoredResume) -> List[Dict[str, Any]]:
    """Compares tailored bullets against original Master Profile bullets."""
    bullets_map = profile.get_all_bullets()
    diff_records: List[Dict[str, Any]] = []

    for exp in tailored.selected_experience:
        for b in exp.bullets:
            orig = bullets_map.get(b.source_bullet_id)
            orig_text = orig.text if orig else "[Source Bullet Not Found]"
            is_mod = (orig_text.strip() != b.tailored_text.strip())

            diff_records.append({
                "source_id": b.source_bullet_id,
                "company": exp.company,
                "title": exp.title,
                "original_text": orig_text,
                "tailored_text": b.tailored_text,
                "is_modified": is_mod
            })

    return diff_records


def format_terminal_diff(profile: MasterProfile, tailored: TailoredResume) -> str:
    """Formats an easy-to-read terminal side-by-side diff representation."""
    diff_records = generate_review_diff(profile, tailored)
    lines: List[str] = []

    lines.append("\n=======================================================")
    lines.append(f"  HUMAN REVIEW DIFF: {tailored.target_company} - {tailored.target_job_title}")
    lines.append("=======================================================\n")

    lines.append(f"[SUMMARY]")
    lines.append(f"Original : {profile.summary}")
    lines.append(f"Tailored : {tailored.summary}\n")

    lines.append("[EXPERIENCE BULLET COMPARISONS]")
    for r in diff_records:
        mod_tag = "[REPHRASED]" if r["is_modified"] else "[UNCHANGED]"
        lines.append(f"\n- Bullet ID: {r['source_id']} ({r['company']} - {r['title']}) {mod_tag}")
        lines.append(f"  ORIGINAL: {r['original_text']}")
        lines.append(f"  TAILORED: {r['tailored_text']}")

    if tailored.unmatched_must_haves_notes:
        lines.append("\n[UNMATCHED MUST-HAVES (CANDIDATE AWARENESS)]")
        for note in tailored.unmatched_must_haves_notes:
            lines.append(f"  ! {note}")

    lines.append("\n=======================================================\n")
    return "\n".join(lines)
