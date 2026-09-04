"""
Shared project record shape used by all three scrapers (github_scraper.py,
local_scraper.py, portfolio_scraper.py) and consumed by main.py.

This mirrors the `projects` array in the Master Profile schema defined in
Technical_Architecture.md §3 — keep them in sync if you change one.
"""

from typing import TypedDict, List, Optional, Dict


class Project(TypedDict):
    id: str
    name: str
    source: str  # "github" | "portfolio" | "local"
    source_ref: str  # repo URL, portfolio page URL, or local filesystem path
    description_raw: str  # untouched README / commit / page text — ground truth
    tech_stack: List[str]
    start_date: Optional[str]  # YYYY-MM-DD if known
    end_date: Optional[str]
    last_active_date: Optional[str]
    visibility: str  # "public" | "private" | "unknown"
    links: Dict[str, str]
    reviewed_by_user: bool  # gate: Stage 5 (tailoring) must never read a
    # project where this is False — see PRD.md §8 (zero-fabrication policy).
    # Scraped/LLM-drafted content is not "ground truth" until a human confirms it.
