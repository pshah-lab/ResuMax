"""
Project Relevance Ranker for ResuMax (Stage 4.5).
Ranks candidate projects against a parsed Job Description based on tech stack overlap,
semantic keyword alignment, and must-have requirement matching.
Allows candidate to review and approve which projects get included in the tailored resume.
"""

import re
from typing import List, Dict, Any, Set, Tuple
from pydantic import BaseModel, Field

from models import MasterProfile, JDExtraction, ProjectItem


class RankedProject(BaseModel):
    project_id: str
    name: str
    tech_stack: List[str] = Field(default_factory=list)
    draft_bullets: List[str] = Field(default_factory=list)
    source_ref: str = ""
    score: float = 0.0  # 0 to 100%
    matched_keywords: List[str] = Field(default_factory=list)
    matched_requirements: List[str] = Field(default_factory=list)
    is_approved: bool = False


def _normalize(text: str) -> str:
    """Normalizes string for robust substring matching."""
    return re.sub(r"[^a-z0-9+#]+", " ", text.lower()).strip()


def rank_projects_for_jd(profile: MasterProfile, jd: JDExtraction) -> List[RankedProject]:
    """
    Ranks all projects in the Master Profile against the target JD.
    Returns a sorted list of RankedProject objects from most relevant to least relevant.
    """
    if not profile.projects:
        return []

    # 1. Gather JD keywords & requirements
    jd_keywords: Set[str] = set()
    for kw in jd.keywords_for_ats:
        if kw.strip():
            jd_keywords.add(kw.strip())

    must_have_texts: List[str] = []
    for req in jd.must_have_requirements:
        must_have_texts.append(req.requirement)
        for kw in getattr(req, "keywords", []):
            jd_keywords.add(kw.strip())

    ranked_results: List[RankedProject] = []

    for proj in profile.projects:
        proj_text_blocks = [proj.name, proj.description_raw] + proj.draft_bullets + proj.tech_stack
        combined_proj_text = " ".join(proj_text_blocks).lower()
        proj_tech_set = {_normalize(t) for t in proj.tech_stack}

        matched_kws: List[str] = []
        matched_reqs: List[str] = []
        raw_score = 0.0

        # Score Tech Stack matches
        for kw in jd_keywords:
            norm_kw = _normalize(kw)
            if not norm_kw:
                continue
            
            # Direct tech stack match (high value)
            if norm_kw in proj_tech_set or any(norm_kw == _normalize(t) for t in proj.tech_stack):
                matched_kws.append(kw)
                raw_score += 25.0
            # Text occurrence in bullets/description
            elif norm_kw in combined_proj_text or re.search(r"\b" + re.escape(norm_kw) + r"\b", combined_proj_text):
                matched_kws.append(kw)
                raw_score += 10.0

        # Score Must-Have requirement alignment
        for mh in must_have_texts:
            norm_mh = _normalize(mh)
            words = [w for w in norm_mh.split() if len(w) > 3]
            matched_words = [w for w in words if w in combined_proj_text]
            if words and (len(matched_words) / len(words)) >= 0.4:
                matched_reqs.append(mh)
                raw_score += 20.0

        # Deduplicate matched keywords
        matched_kws = list(dict.fromkeys(matched_kws))

        # Calculate percentage score normalized to 100% max
        # Cap raw score against total potential score
        max_possible = max(len(jd_keywords) * 20.0 + len(must_have_texts) * 20.0, 50.0)
        percentage_score = min(round((raw_score / max_possible) * 100.0, 1), 100.0)

        # Baseline minimum boost if project has clear verified tech
        if matched_kws and percentage_score < 30.0:
            percentage_score = min(30.0 + len(matched_kws) * 10.0, 100.0)

        ranked_results.append(RankedProject(
            project_id=proj.id,
            name=proj.name,
            tech_stack=proj.tech_stack,
            draft_bullets=proj.draft_bullets,
            source_ref=proj.source_ref,
            score=percentage_score,
            matched_keywords=matched_kws,
            matched_requirements=matched_reqs,
            is_approved=proj.reviewed_by_user
        ))

    # Sort descending by score, then by approval status
    ranked_results.sort(key=lambda p: (p.score, 1 if p.is_approved else 0), reverse=True)
    return ranked_results
