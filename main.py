"""
Runs all three scrapers and merges the results into one deduped projects.json,
ready for the Project Extraction prompt (ATS_Guidelines_and_Prompt_Design.md).

Config via environment variables:
  GITHUB_USERNAME, GITHUB_TOKEN   — skips GitHub if either is missing
  LOCAL_PROJECTS_ROOT             — defaults to ~/projects

Portfolio scraping is intentionally left commented out below until
portfolio_scraper.py's selectors are configured to your actual site.

Run:
  python main.py
  -> writes projects.json
"""

import os
import json

from github_scraper import scrape_github
from local_scraper import scrape_local
# from portfolio_scraper import scrape_portfolio  # uncomment once selectors are set


def dedupe_local_against_github(github_projects: list, local_projects: list) -> list:
    """The same project often exists both as a local folder and a GitHub repo.
    Prefer the GitHub version (it has richer metadata) and drop the local
    duplicate rather than double-counting it."""
    github_urls = {p["source_ref"].rstrip("/").rstrip(".git") for p in github_projects}
    deduped = []
    for p in local_projects:
        remote = p.pop("_remote_url", None)
        if remote and remote.rstrip("/").rstrip(".git") in github_urls:
            continue
        deduped.append(p)
    return deduped


def main():
    username = os.environ.get("GITHUB_USERNAME")
    token = os.environ.get("GITHUB_TOKEN")
    local_root = os.environ.get("LOCAL_PROJECTS_ROOT", "~/projects")

    github_projects = scrape_github(username, token) if username and token else []
    if not github_projects:
        print("Skipping GitHub (set GITHUB_USERNAME + GITHUB_TOKEN to include it).")

    raw_local = scrape_local(local_root)
    local_projects = dedupe_local_against_github(github_projects, raw_local)

    # portfolio_projects = scrape_portfolio()
    portfolio_projects = []

    all_projects = github_projects + local_projects + portfolio_projects

    with open("projects.json", "w") as f:
        json.dump(all_projects, f, indent=2)

    print(f"GitHub: {len(github_projects)} | Local (deduped): {len(local_projects)} | Portfolio: {len(portfolio_projects)}")
    print(f"Wrote {len(all_projects)} total projects -> projects.json")
    print("\nNext step: run each through the Project Extraction prompt "
          "(ATS_Guidelines_and_Prompt_Design.md) to draft resume-ready bullets, "
          "then review and flip reviewed_by_user=true before they can feed the "
          "tailoring engine. See PRD.md §8 for why that gate exists.")


if __name__ == "__main__":
    main()
