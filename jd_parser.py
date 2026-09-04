"""
JD Ingestion & Parser for Stage 2 & Stage 3.
Extracts structured requirements, acronym pairs, categorized skills, and ATS keywords
from raw job descriptions (ATS_Guidelines_and_Prompt_Design.md §5).
"""

import json
from pathlib import Path
from typing import Union, Optional, Dict, Any

from models import JDExtraction
from llm_client import LLMClient


JD_EXTRACTION_SYSTEM_PROMPT = """
You are a job-description analysis engine. You will be given the raw text of a job posting.
Extract a structured summary. Do not add information that is not present in the text —
if something is ambiguous or missing, leave the field empty rather than guessing.

Classify each requirement as "must_have" or "nice_to_have":
- Language like "required," "must have," or listing under a "Requirements" heading -> must_have
- Language like "preferred," "a plus," "nice to have," or listing under "Preferred Qualifications" -> nice_to_have
- Ambiguous phrasing defaults to nice_to_have.

For every skill, tool, or credential, extract BOTH the acronym and full term if the JD uses
either (e.g. "Search Engine Optimization (SEO)" -> capture both forms) — this matters for
downstream keyword matching.

Categorize each must_have requirement into one of:
- hard_skill | soft_skill | tool | certification | experience_years | education

Output valid JSON matching this schema exactly:
{
  "job_title": "...",
  "company": "...",
  "seniority_level": "...",
  "employment_type": "...",
  "must_have_requirements": [
    {
      "requirement": "...",
      "category": "hard_skill | soft_skill | tool | certification | experience_years | education",
      "keywords": ["...", "..."]
    }
  ],
  "nice_to_have_requirements": ["...", "..."],
  "core_responsibilities": ["...", "..."],
  "keywords_for_ats": ["...", "..."],
  "company_context": {
    "industry": "...",
    "size": "...",
    "notes": "..."
  }
}
"""


def parse_job_description(jd_text: str, llm_client: Optional[LLMClient] = None) -> JDExtraction:
    """Parses raw JD text into a structured JDExtraction object."""
    if not jd_text.strip():
        raise ValueError("Job description text cannot be empty.")

    client = llm_client or LLMClient()
    user_prompt = f"JOB DESCRIPTION:\n\n{jd_text}"

    extracted_dict = client.generate_json(
        system_prompt=JD_EXTRACTION_SYSTEM_PROMPT,
        user_prompt=user_prompt,
        temperature=0.0  # Low temperature for deterministic extraction
    )

    return JDExtraction(**extracted_dict)


def parse_job_description_file(file_path: Union[str, Path], llm_client: Optional[LLMClient] = None) -> JDExtraction:
    """Reads a JD from a text file and extracts structured requirements."""
    path = Path(file_path).expanduser()
    if not path.exists():
        raise FileNotFoundError(f"JD file not found: {path}")

    text = path.read_text(encoding="utf-8", errors="ignore")
    return parse_job_description(text, llm_client=llm_client)
