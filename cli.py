"""
ResuMax CLI - Complete 10-Stage Pipeline
Commands:
  python cli.py bootstrap --file <resume_file>
  python cli.py scrape-projects
  python cli.py extract-projects
  python cli.py list-projects
  python cli.py review-project <project_id> [--reject]
  python cli.py parse-jd --file <jd_file>
  python cli.py analyze-gap --jd <jd_file>
  python cli.py tailor --jd <jd_file> [--no-pdf] [--force]
  python cli.py list-versions
  python cli.py show-profile
"""

import sys
import os
import argparse
import json
from pathlib import Path

from models import MasterProfile, JDExtraction, TailoredResume
from profile_manager import ProfileManager
from resume_bootstrapper import bootstrap_master_profile_from_file
from project_extractor import extract_projects_from_file, ingest_and_extract_projects
from github_scraper import scrape_github
from local_scraper import scrape_local
from portfolio_scraper import scrape_portfolio
from main import dedupe_local_against_github

from jd_parser import parse_job_description_file, parse_job_description
from gap_analyzer import analyze_gap
from project_ranker import rank_projects_for_jd
from tailoring_engine import tailor_resume
from grounding_checker import verify_grounding
from ats_validator import validate_tailored_resume_structure, validate_docx_file, validate_pdf_file
from review_diff import format_terminal_diff
from document_exporter import (
    export_to_docx,
    export_to_pdf_text_layer,
    export_cover_letter_to_docx,
    export_cover_letter_to_pdf,
    export_to_latex
)
from cover_letter_generator import generate_cover_letter
from version_store import VersionStore, sanitize_filename


def cmd_bootstrap(args):
    """Stage 1: Bootstrap master profile from an existing resume file."""
    file_path = Path(args.file)
    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    print(f"[*] Parsing and extracting Master Profile from: {file_path}...")
    profile = bootstrap_master_profile_from_file(file_path)
    
    manager = ProfileManager(Path(args.profile))
    manager.set_profile(profile)
    
    print(f"[+] Successfully bootstrapped Master Profile -> {args.profile}")
    print("\nProfile Summary:")
    for k, v in manager.get_stats().items():
        print(f"  - {k.replace('_', ' ').title()}: {v}")


def cmd_scrape_projects(args):
    """Stage 1a: Scrape GitHub & local projects and write projects.json."""
    username = os.environ.get("GITHUB_USERNAME")
    token = os.environ.get("GITHUB_TOKEN")
    local_root = os.environ.get("LOCAL_PROJECTS_ROOT", args.local_root or "~/projects")

    github_projects = scrape_github(username, token) if username and token else []
    if not github_projects:
        print("[!] Note: GitHub credentials not set (export GITHUB_USERNAME & GITHUB_TOKEN to include GitHub repos).")

    raw_local = scrape_local(local_root) if Path(local_root).expanduser().exists() else []
    local_projects = dedupe_local_against_github(github_projects, raw_local)

    all_projects = github_projects + local_projects
    output_file = Path(args.output)
    output_file.write_text(json.dumps(all_projects, indent=2), encoding="utf-8")

    print(f"[+] Scraped {len(github_projects)} GitHub + {len(local_projects)} Local projects -> {output_file}")


def cmd_extract_projects(args):
    """Stage 1a -> 1: Run Project Extraction LLM on scraped projects."""
    projects_file = Path(args.file)
    if not projects_file.exists():
        print(f"Error: Scraped projects file '{projects_file}' does not exist. Run 'scrape-projects' first.")
        sys.exit(1)

    print(f"[*] Extracting candidate bullets and metadata from {projects_file}...")
    extracted_items = extract_projects_from_file(projects_file)

    manager = ProfileManager(Path(args.profile))
    merged_count = manager.merge_projects(extracted_items)

    print(f"[+] Extracted and merged {merged_count} projects into {args.profile}")
    print(f"[!] Safety Gate: All {merged_count} projects have 'reviewed_by_user: false'.")
    print("    Run 'python cli.py list-projects' or 'python cli.py review-project <id>' to approve them.")


def cmd_list_projects(args):
    """List projects in Master Profile and their review status."""
    manager = ProfileManager(Path(args.profile))
    if not manager.profile.projects:
        print("[!] No projects currently in Master Profile.")
        return

    print("\n=== Master Profile Projects ===")
    for p in manager.profile.projects:
        status = "APPROVED (Ready for Tailoring)" if p.reviewed_by_user else "PENDING REVIEW"
        flags = f" [FLAGS: {', '.join(p.review_flags)}]" if p.review_flags else ""
        print(f"\n- ID: {p.id}")
        print(f"  Name: {p.name} ({p.source}) | Status: {status}{flags}")
        print(f"  Tech: {', '.join(p.tech_stack) or 'None'}")
        if p.draft_bullets:
            print("  Draft Bullets:")
            for b in p.draft_bullets:
                print(f"    * {b}")


def cmd_review_project(args):
    """Approve or reject a project in the Master Profile."""
    manager = ProfileManager(Path(args.profile))
    proj_id = args.project_id
    approve = not args.reject

    found = manager.review_project(proj_id, approve=approve)
    if not found:
        print(f"Error: Project ID '{proj_id}' not found in Master Profile.")
        sys.exit(1)

    status_str = "APPROVED (reviewed_by_user = True)" if approve else "REJECTED (reviewed_by_user = False)"
    print(f"[+] Project '{proj_id}' updated -> {status_str}")


def cmd_parse_jd(args):
    """Stage 2 & 3: Ingest and parse a Job Description."""
    jd_file = Path(args.file)
    if not jd_file.exists():
        print(f"Error: JD file '{jd_file}' not found.")
        sys.exit(1)

    print(f"[*] Parsing Job Description from: {jd_file}...")
    jd = parse_job_description_file(jd_file)

    print("\n==========================================")
    print("        PARSED JOB DESCRIPTION            ")
    print("==========================================")
    print(f"Role:       {jd.job_title} ({jd.seniority_level})")
    print(f"Company:    {jd.company}")
    print(f"Type:       {jd.employment_type}")
    print(f"\nMust-Have Requirements ({len(jd.must_have_requirements)}):")
    for r in jd.must_have_requirements:
        print(f"  - [{r.category}] {r.requirement}")
        if r.keywords:
            print(f"    Keywords: {', '.join(r.keywords)}")
    print(f"\nNice-to-Have Requirements ({len(jd.nice_to_have_requirements)}):")
    for n in jd.nice_to_have_requirements:
        print(f"  - {n}")
    print(f"\nKeywords for ATS ({len(jd.keywords_for_ats)}):")
    print(f"  {', '.join(jd.keywords_for_ats)}")
    print("==========================================\n")


def cmd_analyze_gap(args):
    """Stage 4: Run deterministic Gap & Match Analysis between profile and JD."""
    manager = ProfileManager(Path(args.profile))
    jd_file = Path(args.jd)
    if not jd_file.exists():
        print(f"Error: JD file '{jd_file}' not found.")
        sys.exit(1)

    jd = parse_job_description_file(jd_file)
    gap = analyze_gap(manager.profile, jd)

    print("\n==========================================")
    print(f"  GAP ANALYSIS: {jd.company} - {jd.job_title}")
    print("==========================================")
    print(f"Keyword Coverage:   {gap.keyword_coverage_pct}% ({len(gap.matched_keywords)}/{len(jd.keywords_for_ats)} keywords)")
    print(f"Must-Have Coverage: {gap.must_have_coverage_pct}% ({len(gap.matched_must_haves)}/{len(jd.must_have_requirements)} requirements)")
    
    if gap.missing_keywords:
        print(f"\n[Missing Keywords]: {', '.join(gap.missing_keywords)}")
    if gap.unmatched_must_haves:
        print("\n[Unmatched Must-Have Requirements]:")
        for u in gap.unmatched_must_haves:
            print(f"  ! [{u.category}] {u.requirement}")
    print("==========================================\n")


def cmd_tailor(args):
    """Complete End-to-End Pipeline: Stages 2 through 10."""
    manager = ProfileManager(Path(args.profile))
    jd_file = Path(args.jd)
    if not jd_file.exists():
        print(f"Error: JD file '{jd_file}' not found.")
        sys.exit(1)

    raw_jd_text = jd_file.read_text(encoding="utf-8")

    # 1. Stage 3: Parse JD
    print(f"\n[Stage 3] Ingesting and parsing Job Description from: {jd_file}...")
    jd = parse_job_description(raw_jd_text)
    print(f"  -> Target: {jd.job_title} at {jd.company}")

    # 2. Stage 4: Gap Analysis
    print(f"[Stage 4] Running Gap & Match Analysis...")
    gap_result = analyze_gap(manager.profile, jd)
    print(f"  -> Keyword Match: {gap_result.keyword_coverage_pct}% | Must-Have Match: {gap_result.must_have_coverage_pct}%")

    # 2.5 Stage 4.5: JD Project Relevance Ranking & Human Approval Gate
    print(f"\n[Stage 4.5] Ranking candidate projects for relevance against: {jd.job_title} at {jd.company}...")
    ranked_projects = rank_projects_for_jd(manager.profile, jd)

    selected_project_ids = []
    if ranked_projects:
        print("\n=======================================================")
        print("  JD RELEVANCE PROJECT RANKINGS & APPROVAL GATE")
        print("=======================================================")
        for idx, rp in enumerate(ranked_projects[:5], 1):
            status_tag = "[Approved in Profile]" if rp.is_approved else "[Pending Review]"
            print(f"  [{idx}] {rp.name} (Match Score: {rp.score}%) {status_tag}")
            if rp.matched_keywords:
                print(f"      Matched Tech: {', '.join(rp.matched_keywords)}")
            if rp.draft_bullets:
                print(f"      Key Bullet: {rp.draft_bullets[0]}")
            print()
        print("=======================================================")

        # Check for explicit flags or interactive selection
        if getattr(args, "projects", None):
            indices = [int(x.strip()) - 1 for x in args.projects.split(",") if x.strip().isdigit()]
            selected_project_ids = [ranked_projects[i].project_id for i in indices if 0 <= i < len(ranked_projects)]
        elif getattr(args, "auto_approve_top", False) or not sys.stdin.isatty():
            # In automated / non-interactive mode, select top 2-3 projects
            top_approved = [p for p in ranked_projects if p.is_approved]
            selected_project_ids = [p.project_id for p in (top_approved[:3] if top_approved else ranked_projects[:2])]
        else:
            try:
                user_input = input("Select projects to include in tailored Resume (e.g. 1, 2) [Press Enter for Top 2]: ").strip()
                if user_input:
                    indices = [int(x.strip()) - 1 for x in user_input.split(",") if x.strip().isdigit()]
                    selected_project_ids = [ranked_projects[i].project_id for i in indices if 0 <= i < len(ranked_projects)]
                else:
                    selected_project_ids = [p.project_id for p in ranked_projects[:2]]
            except (EOFError, KeyboardInterrupt):
                selected_project_ids = [p.project_id for p in ranked_projects[:2]]

        print(f"  -> Approved {len(selected_project_ids)} project(s) for Resume inclusion: {selected_project_ids}\n")

    # 3. Stage 5: Resume Tailoring Engine with User-Approved Projects
    print(f"[Stage 5] Generating tailored resume with zero-fabrication constraints...")
    tailored = tailor_resume(
        manager.profile,
        jd,
        gap_result=gap_result,
        approved_project_ids=selected_project_ids if selected_project_ids else None
    )

    # 4. Stage 6: Grounding Check
    print(f"[Stage 6] Running independent fact-checking / grounding verification...")
    grounding = verify_grounding(manager.profile, tailored)
    if not grounding.passed:
        print(f"  [!] WARNING: Grounding verification flagged {len(grounding.unsupported_claims)} claims:")
        for claim in grounding.unsupported_claims:
            print(f"      - {claim.source_id}: {claim.reason} ('{claim.tailored_text[:60]}...')")
        if not args.force:
            print("  [!] Halting before export due to grounding check failures. (Use --force to override).")
            sys.exit(1)
    else:
        print("  -> Grounding check PASSED: 100% of claims verified against Master Profile.")

    # 5. Stage 7: ATS Format Validation (Structural)
    print(f"[Stage 7] Validating ATS formatting rules...")
    ats_data_check = validate_tailored_resume_structure(tailored)
    print(f"  -> ATS Structure Score: {ats_data_check.score}/100")
    for issue in ats_data_check.issues:
        print(f"     [{issue.severity.upper()}] {issue.rule}: {issue.message}")

    # 6. Stage 8: Human Review Diff
    print(f"[Stage 8] Generating Human Review Diff...")
    diff_text = format_terminal_diff(manager.profile, tailored)
    print(diff_text)

    # 7. Stage 9: Export (.docx + .pdf + .tex)
    company_slug = sanitize_filename(jd.company or "Company")
    role_slug = sanitize_filename(jd.job_title or "Role")
    exports_dir = Path("exports")
    exports_dir.mkdir(parents=True, exist_ok=True)

    docx_path = exports_dir / f"{company_slug}_{role_slug}.docx"
    pdf_path = exports_dir / f"{company_slug}_{role_slug}.pdf" if not args.no_pdf else None
    tex_path = exports_dir / f"{company_slug}_{role_slug}.tex"

    print(f"[Stage 9] Exporting ATS-compliant documents...")
    export_to_docx(manager.profile, tailored, docx_path)
    print(f"  -> Exported Word document: {docx_path}")

    export_to_latex(manager.profile, tailored, tex_path)
    print(f"  -> Exported LaTeX document: {tex_path}")

    # Validate exported docx
    docx_check = validate_docx_file(docx_path)
    print(f"  -> DOCX ATS Compliance Score: {docx_check.score}/100")

    if pdf_path:
        export_to_pdf_text_layer(manager.profile, tailored, pdf_path)
        print(f"  -> Exported Text-Layer PDF: {pdf_path}")
        pdf_check = validate_pdf_file(pdf_path)
        print(f"  -> PDF Text Layer Verification: {'PASSED' if pdf_check.passed else 'FAILED'}")

    # 8. Stage 10: Version Store
    print(f"[Stage 10] Storing application version in Version Store...")
    store = VersionStore(exports_dir)
    record = store.save_application_version(
        tailored=tailored,
        jd=jd,
        raw_jd_text=raw_jd_text,
        gap_result=gap_result,
        ats_result=docx_check,
        grounding_result=grounding,
        docx_path=docx_path,
        pdf_path=pdf_path
    )
    print(f"  -> Stored version ID: {record.version_id}")
    print("\n[+] Resume Tailoring Pipeline Completed Successfully!")


def cmd_list_versions(args):
    """Stage 10: List all past tailored application versions."""
    store = VersionStore()
    versions = store.list_versions()
    if not versions:
        print("[!] No saved application versions found in exports/.")
        return

    print("\n==========================================")
    print("       SAVED RESUME APPLICATIONS          ")
    print("==========================================")
    for v in versions:
        print(f"\n- Version ID: {v.version_id}")
        print(f"  Target:     {v.job_title} at {v.company} ({v.date})")
        print(f"  Match:      {v.keyword_coverage_pct}% keywords | ATS Score: {v.ats_score}/100")
        print(f"  Files:      DOCX: {v.docx_path} | PDF: {v.pdf_path or 'N/A'}")
    print("==========================================\n")


def cmd_cover_letter(args):
    """Draft a grounded, role-aligned cover letter from Master Profile and JD."""
    manager = ProfileManager(Path(args.profile))
    jd_file = Path(args.jd)
    if not jd_file.exists():
        print(f"Error: JD file '{jd_file}' not found.")
        sys.exit(1)

    raw_jd_text = jd_file.read_text(encoding="utf-8")
    print(f"\n[1/3] Ingesting and parsing Job Description from: {jd_file}...")
    jd = parse_job_description(raw_jd_text)
    print(f"  -> Target: {jd.job_title} at {jd.company}")

    print("[2/3] Analyzing gaps & requirements...")
    gap_result = analyze_gap(manager.profile, jd)

    print("[3/3] Generating grounded cover letter with zero-fabrication constraints...")
    cover_letter = generate_cover_letter(manager.profile, jd, gap_result=gap_result)

    print("\n=======================================================")
    print(f"  COVER LETTER: {jd.company} - {jd.job_title}")
    print("=======================================================\n")
    print(cover_letter.full_text)
    print("\n=======================================================\n")

    # Export documents
    company_slug = sanitize_filename(jd.company or "Company")
    role_slug = sanitize_filename(jd.job_title or "Role")
    exports_dir = Path("exports")
    exports_dir.mkdir(parents=True, exist_ok=True)

    docx_path = exports_dir / f"{company_slug}_{role_slug}_Cover_Letter.docx"
    pdf_path = exports_dir / f"{company_slug}_{role_slug}_Cover_Letter.pdf"

    export_cover_letter_to_docx(manager.profile, cover_letter, docx_path)
    print(f"[+] Exported Word document: {docx_path}")

    if not args.no_pdf:
        export_cover_letter_to_pdf(manager.profile, cover_letter, pdf_path)
        print(f"[+] Exported PDF document: {pdf_path}")


def cmd_ingest_projects(args):
    """Stage 1a: Automated scraping (GitHub, Portfolio, Local) + LLM extraction into Master Profile."""
    manager = ProfileManager(Path(args.profile))
    raw_projects = []

    print(f"\n[*] Running Automated Project Ingestion (Source: {args.source})...")

    # 1. GitHub
    if args.source in ["github", "all"]:
        gh_user = args.github_user or "prathamshah"
        print(f"  -> Scraping GitHub repositories for @{gh_user}...")
        gh_projects = scrape_github(username=gh_user, token=args.github_token)
        print(f"     Found {len(gh_projects)} repository project records.")
        raw_projects.extend(gh_projects)

    # 2. Portfolio
    if args.source in ["portfolio", "all"]:
        port_url = args.portfolio_url or manager.profile.personal_info.portfolio_url or "https://pshah.fun"
        print(f"  -> Scraping Portfolio site: {port_url}...")
        port_projects = scrape_portfolio(portfolio_url=port_url)
        print(f"     Found {len(port_projects)} portfolio project records.")
        raw_projects.extend(port_projects)

    # 3. Local
    if args.source in ["local", "all"]:
        loc_dir = Path(args.local_dir or "~/projects").expanduser()
        if loc_dir.exists():
            print(f"  -> Scanning local project directories in {loc_dir}...")
            loc_projects = scrape_local(str(loc_dir))
            print(f"     Found {len(loc_projects)} local project records.")
            raw_projects.extend(loc_projects)

    # Deduplication check
    new_raw_projects = []
    skipped_count = 0
    for raw_p in raw_projects:
        p_name = raw_p.get("name", "")
        p_ref = raw_p.get("source_ref", "") or raw_p.get("links", {}).get("repo", "")
        p_id = raw_p.get("id", "")
        if manager.is_project_already_ingested(name=p_name, source_ref=p_ref, project_id=p_id):
            skipped_count += 1
        else:
            new_raw_projects.append(raw_p)

    if not new_raw_projects:
        print(f"[+] All {len(raw_projects)} discovered projects are already ingested in {args.profile}. Skipped {skipped_count} duplicates.")
        return

    print(f"\n[*] Running LLM bullet candidate drafting for {len(new_raw_projects)} new projects (Skipped {skipped_count} existing)...")
    extracted_items = ingest_and_extract_projects(new_raw_projects)
    merged_count = manager.merge_projects(extracted_items, skip_existing=True)

    print(f"[+] Ingested and merged {merged_count} new projects into {args.profile} ({skipped_count} skipped).")
    print(f"[!] Safety Gate Active: All newly ingested projects have 'reviewed_by_user: false'.")
    print("    Review and approve them in the Web UI (http://localhost:8008) or via 'python cli.py review-project <id>'")


def cmd_show_profile(args):
    """Display Master Profile statistics and details."""
    manager = ProfileManager(Path(args.profile))
    stats = manager.get_stats()
    
    print("\n==========================================")
    print("        RESUMAX - MASTER PROFILE          ")
    print("==========================================")
    print(f"Full Name:     {stats['name']}")
    print(f"Work History:  {stats['work_experiences']} experiences ({stats['total_bullets']} bullets)")
    print(f"Education:     {stats['education_entries']} entries")
    print(f"Skills:        {stats['total_skills']} total skills")
    print(f"Certifications:{stats['certifications']}")
    print(f"Projects:      {stats['total_projects']} ({stats['approved_projects']} approved, {stats['pending_project_reviews']} pending review)")
    print("==========================================\n")


def main():
    parser = argparse.ArgumentParser(description="ResuMax CLI - Resume Tailoring Pipeline")
    parser.add_argument("--profile", default="master_profile.json", help="Path to master_profile.json")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Bootstrap
    p_bootstrap = subparsers.add_parser("bootstrap", help="Bootstrap profile from existing resume file")
    p_bootstrap.add_argument("--file", "-f", required=True, help="Path to resume (.pdf, .docx, .txt)")

    # Ingest Projects (Automated)
    p_ingest = subparsers.add_parser("ingest-projects", help="Automated project scraping & bullet extraction")
    p_ingest.add_argument("--source", choices=["all", "github", "portfolio", "local"], default="all", help="Source to scrape")
    p_ingest.add_argument("--github-user", default="prathamshah", help="GitHub username")
    p_ingest.add_argument("--github-token", help="Optional GitHub PAT token")
    p_ingest.add_argument("--portfolio-url", help="Portfolio website URL")
    p_ingest.add_argument("--local-dir", default="~/projects", help="Local projects directory path")

    # Scrape
    p_scrape = subparsers.add_parser("scrape-projects", help="Scrape GitHub & local projects")
    p_scrape.add_argument("--local-root", default="~/projects", help="Local projects directory")
    p_scrape.add_argument("--output", "-o", default="projects.json", help="Output projects JSON")

    # Extract Projects
    p_extract = subparsers.add_parser("extract-projects", help="Run Project Extraction on scraped projects")
    p_extract.add_argument("--file", "-f", default="projects.json", help="Scraped projects JSON")

    # List Projects
    subparsers.add_parser("list-projects", help="List all projects in profile and review status")

    # Review Project
    p_rev = subparsers.add_parser("review-project", help="Review and approve/reject a project")
    p_rev.add_argument("project_id", help="Project ID to review")
    p_rev.add_argument("--reject", action="store_true", help="Mark project as unapproved")

    # Parse JD
    p_parse_jd = subparsers.add_parser("parse-jd", help="Ingest and parse a Job Description")
    p_parse_jd.add_argument("--file", "-f", required=True, help="Path to JD text file")

    # Analyze Gap
    p_gap = subparsers.add_parser("analyze-gap", help="Run Gap & Match Analysis against Master Profile")
    p_gap.add_argument("--jd", "-j", required=True, help="Path to JD text file")

    # Tailor
    p_tailor = subparsers.add_parser("tailor", help="Run end-to-end resume tailoring pipeline")
    p_tailor.add_argument("--jd", "-j", required=True, help="Path to JD text file")
    p_tailor.add_argument("--projects", "-p", help="Comma-separated project IDs or rank indices (e.g. 1,2) to approve for resume")
    p_tailor.add_argument("--auto-approve-top", action="store_true", help="Auto-approve top-ranked projects without prompting")
    p_tailor.add_argument("--no-pdf", action="store_true", help="Skip PDF generation")
    p_tailor.add_argument("--force", action="store_true", help="Proceed even if grounding check warns")

    # Cover Letter
    p_cl = subparsers.add_parser("cover-letter", help="Draft grounded, tailored cover letter")
    p_cl.add_argument("--jd", "-j", required=True, help="Path to JD text file")
    p_cl.add_argument("--no-pdf", action="store_true", help="Skip PDF generation")

    # List Versions
    subparsers.add_parser("list-versions", help="List saved application versions in Version Store")

    # Show Profile
    subparsers.add_parser("show-profile", help="Show summary of Master Profile")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    cmd_map = {
        "bootstrap": cmd_bootstrap,
        "ingest-projects": cmd_ingest_projects,
        "scrape-projects": cmd_scrape_projects,
        "extract-projects": cmd_extract_projects,
        "list-projects": cmd_list_projects,
        "review-project": cmd_review_project,
        "parse-jd": cmd_parse_jd,
        "analyze-gap": cmd_analyze_gap,
        "tailor": cmd_tailor,
        "cover-letter": cmd_cover_letter,
        "list-versions": cmd_list_versions,
        "show-profile": cmd_show_profile,
    }
    cmd_map[args.command](args)


if __name__ == "__main__":
    main()
