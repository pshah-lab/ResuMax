"""
Gap & Match Analysis for Stage 4.
Performs deterministic keyword and requirement matching between MasterProfile and JDExtraction.
Surfaces genuinely missing must-haves explicitly (zero-fabrication policy).
"""

import re
from typing import Set, List, Dict, Tuple
from models import MasterProfile, JDExtraction, GapAnalysisResult, RequirementItem


def _normalize(text: str) -> str:
    """Normalizes string for robust substring / token matching."""
    return re.sub(r"[^a-z0-9+#]+", " ", text.lower()).strip()


def build_candidate_search_corpus(profile: MasterProfile) -> Tuple[Set[str], str]:
    """
    Builds both a set of discrete skill/tool tokens and a combined text corpus
    from all verified Master Profile entries.
    """
    discrete_skills: Set[str] = set()
    text_blocks: List[str] = []

    # Personal info summary
    if profile.summary:
        text_blocks.append(profile.summary)

    # Skills categories
    for skill in profile.skills.technical + profile.skills.tools + profile.skills.soft + profile.skills.languages:
        discrete_skills.add(_normalize(skill))
        text_blocks.append(skill)

    # Work experiences & bullets
    for exp in profile.work_experience:
        text_blocks.append(exp.title)
        text_blocks.append(exp.company)
        for b in exp.bullets:
            text_blocks.append(b.text)
            for tag in b.skills_tags:
                discrete_skills.add(_normalize(tag))
                text_blocks.append(tag)

    # Education
    for edu in profile.education:
        text_blocks.append(edu.degree)
        text_blocks.append(edu.field)
        text_blocks.append(edu.institution)

    # Certifications
    for cert in profile.certifications:
        discrete_skills.add(_normalize(cert))
        text_blocks.append(cert)

    # Approved projects ONLY (safety gate)
    for proj in profile.get_approved_projects():
        text_blocks.append(proj.name)
        for tech in proj.tech_stack:
            discrete_skills.add(_normalize(tech))
            text_blocks.append(tech)
        for b in proj.draft_bullets:
            text_blocks.append(b)

    corpus = " ".join(text_blocks).lower()
    return discrete_skills, corpus


def is_keyword_present(keyword: str, discrete_skills: Set[str], corpus: str) -> bool:
    """Checks whether a keyword exists in candidate profile via discrete token or regex match."""
    norm_kw = _normalize(keyword)
    if not norm_kw:
        return False

    if norm_kw in discrete_skills:
        return True

    # Use word boundary search in corpus
    pattern = r"\b" + re.escape(norm_kw) + r"\b"
    return bool(re.search(pattern, corpus, re.IGNORECASE))


def analyze_gap(profile: MasterProfile, jd: JDExtraction) -> GapAnalysisResult:
    """
    Compares MasterProfile against JDExtraction.
    Computes keyword coverage and surfaces matched vs. unmatched must-haves.
    """
    discrete_skills, corpus = build_candidate_search_corpus(profile)

    # 1. Keywords for ATS coverage
    matched_kws: List[str] = []
    missing_kws: List[str] = []

    for kw in jd.keywords_for_ats:
        if is_keyword_present(kw, discrete_skills, corpus):
            matched_kws.append(kw)
        else:
            missing_kws.append(kw)

    total_kws = len(jd.keywords_for_ats)
    kw_coverage = round((len(matched_kws) / total_kws * 100.0), 1) if total_kws > 0 else 100.0

    # 2. Must-Have requirements analysis
    matched_must_haves: List[RequirementItem] = []
    unmatched_must_haves: List[RequirementItem] = []

    for req in jd.must_have_requirements:
        # A requirement is considered matched if any of its explicit keywords match,
        # or if the requirement text itself matches significantly
        req_matched = False
        if req.keywords:
            for kw in req.keywords:
                if is_keyword_present(kw, discrete_skills, corpus):
                    req_matched = True
                    break
        else:
            # Fallback: check significant words in requirement string
            norm_req = _normalize(req.requirement)
            req_matched = norm_req in corpus or any(word in corpus for word in norm_req.split() if len(word) > 4)

        if req_matched:
            matched_must_haves.append(req)
        else:
            unmatched_must_haves.append(req)

    total_must_haves = len(jd.must_have_requirements)
    must_have_coverage = (
        round((len(matched_must_haves) / total_must_haves * 100.0), 1) if total_must_haves > 0 else 100.0
    )

    # 3. Nice-to-Have requirements check
    unmatched_nice_to_haves: List[str] = []
    for nth in jd.nice_to_have_requirements:
        norm_nth = _normalize(nth)
        if not any(word in corpus for word in norm_nth.split() if len(word) > 4):
            unmatched_nice_to_haves.append(nth)

    return GapAnalysisResult(
        matched_keywords=matched_kws,
        missing_keywords=missing_kws,
        keyword_coverage_pct=kw_coverage,
        matched_must_haves=matched_must_haves,
        unmatched_must_haves=unmatched_must_haves,
        must_have_coverage_pct=must_have_coverage,
        unmatched_nice_to_haves=unmatched_nice_to_haves,
    )
