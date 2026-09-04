# Project Scraper

Pulls your project details from GitHub, local project folders, and (once configured) your
portfolio site, and merges them into one deduped `projects.json` — the raw material that
feeds the Master Profile's `projects` array (see `Technical_Architecture.md §3`).

**Important:** everything this produces has `"reviewed_by_user": false`. Nothing here is
trusted content yet — it's raw material. Run it through the Project Extraction prompt in
`ATS_Guidelines_and_Prompt_Design.md`, review the drafted bullets yourself, correct anything
off, *then* flip that flag. The resume tailoring engine (Stage 5) must never read a project
that hasn't cleared this gate — that's what keeps the zero-fabrication guarantee (`PRD.md §8`)
intact even though this data was auto-collected rather than hand-entered.

## Setup

```bash
pip install requests beautifulsoup4
```

**GitHub:**
1. Create a token at https://github.com/settings/tokens — a fine-grained token scoped to
   your own repos with read-only Contents + Metadata access is enough.
2. `export GITHUB_USERNAME=your-username`
3. `export GITHUB_TOKEN=ghp_...`

**Local files:**
- `export LOCAL_PROJECTS_ROOT=~/projects` (or wherever your project folders live)
- No further setup — this walks the directory and reads what's already there.

**Portfolio:**
- Open `portfolio_scraper.py` and fill in `BASE_URL` and the three CSS selectors at the top
  of the file (instructions are in the docstring). This one can't run generically since every
  site's HTML is different — if you'd rather not do the selector-hunting yourself, share your
  portfolio URL and I'll configure it for you.
- Once configured, uncomment the portfolio lines in `main.py`.

## Run

```bash
python main.py
```

Writes `projects.json` — one deduped list, tagged by source, with local/GitHub duplicates
of the same repo collapsed into a single entry (GitHub's version wins, since it has richer
metadata).

Run scrapers individually if you just want one source:
```bash
python github_scraper.py         # -> github_projects.json
python local_scraper.py ~/projects  # -> local_projects.json
python portfolio_scraper.py      # -> portfolio_projects.json (after configuring)
```

## What happens to a low-signal repo?

Repos/folders with barely any README content and no detectable tech stack are skipped
automatically (not everything in your GitHub is resume material) — tune the `min_content_len`
argument in each scraper if it's being too aggressive or too lenient.

## Notes on confidentiality

If any of your local/GitHub projects are work repos under an employer confidentiality
agreement, "scraping your own project" doesn't automatically make everything in it safe to
put on a public resume. General framing ("built an internal analytics pipeline that cut
report time by 40%") is normally fine; pulling in proprietary code specifics, client names, or
internal system names usually isn't. The Project Extraction prompt in
`ATS_Guidelines_and_Prompt_Design.md` is instructed to flag anything that looks like it might
be confidential so you can make that call yourself during review — it doesn't decide for you.
