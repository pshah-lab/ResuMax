"""
Version Store for Stage 10.
Manages exported resumes, JD snapshots, match metadata, and multi-application history.
Saves records to exports/ and maintains versions_index.json (Technical_Architecture.md §2).
"""

import re
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

from models import VersionRecord, TailoredResume, JDExtraction, GapAnalysisResult, ATSValidationResult, GroundingCheckResult


DEFAULT_EXPORTS_DIR = Path("exports")


def sanitize_filename(name: str) -> str:
    """Removes special characters to produce safe file system basenames."""
    return re.sub(r"[^a-zA-Z0-9_\-]+", "_", name).strip("_")


class VersionStore:
    """Manages application history and exported resume artifacts."""

    def __init__(self, exports_dir: Path = DEFAULT_EXPORTS_DIR):
        self.exports_dir = Path(exports_dir)
        self.exports_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.exports_dir / "versions_index.json"
        self.records: List[VersionRecord] = self._load_index()

    def _load_index(self) -> List[VersionRecord]:
        if self.index_path.exists():
            try:
                data = json.loads(self.index_path.read_text(encoding="utf-8"))
                return [VersionRecord(**item) for item in data]
            except Exception:
                return []
        return []

    def _save_index(self):
        data = [r.model_dump() for r in self.records]
        self.index_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def save_application_version(
        self,
        tailored: TailoredResume,
        jd: Optional[JDExtraction] = None,
        raw_jd_text: Optional[str] = None,
        gap_result: Optional[GapAnalysisResult] = None,
        ats_result: Optional[ATSValidationResult] = None,
        grounding_result: Optional[GroundingCheckResult] = None,
        docx_path: Optional[Path] = None,
        pdf_path: Optional[Path] = None
    ) -> VersionRecord:
        """Stores a new tailored version and updates the central versions index."""
        company = sanitize_filename(tailored.target_company or "Company")
        role = sanitize_filename(tailored.target_job_title or "Role")
        date_str = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        version_id = f"{company}_{role}_{date_str}"

        # Save JD snapshot if provided
        jd_snapshot_path = None
        if jd or raw_jd_text:
            jd_file = self.exports_dir / f"{version_id}_jd.json"
            jd_data = {
                "raw_text": raw_jd_text or "",
                "structured": jd.model_dump() if jd else {}
            }
            jd_file.write_text(json.dumps(jd_data, indent=2), encoding="utf-8")
            jd_snapshot_path = str(jd_file)

        record = VersionRecord(
            version_id=version_id,
            company=tailored.target_company or "Company",
            job_title=tailored.target_job_title or "Role",
            date=datetime.now().strftime("%Y-%m-%d %H:%M"),
            docx_path=str(docx_path) if docx_path else "",
            pdf_path=str(pdf_path) if pdf_path else None,
            jd_snapshot_path=jd_snapshot_path,
            keyword_coverage_pct=gap_result.keyword_coverage_pct if gap_result else 0.0,
            ats_score=ats_result.score if ats_result else 100,
            grounding_passed=grounding_result.passed if grounding_result else True
        )

        self.records.append(record)
        self._save_index()
        return record

    def list_versions(self) -> List[VersionRecord]:
        """Returns all saved application versions in reverse chronological order."""
        return sorted(self.records, key=lambda r: r.date, reverse=True)
