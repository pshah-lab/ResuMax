# ATS Guidelines & LLM Prompt Design
## ResumeForge — JD-to-Resume Tailoring Pipeline

**Companion to `PRD.md` and `Technical_Architecture.md`.** This is the domain-knowledge reference that the prompts and the format validator should encode. Treat §1–§4 as a living document — ATS/AI-screening behavior shifts over time; revisit periodically rather than trusting this as permanently accurate.

---

## 1. How ATS + AI Screening Actually Work in 2026

An ATS's core job is unglamorous: parse resumes into structured fields (contact, experience, education, skills) so recruiters can search, filter, and sort a database instead of reading every submission by hand. Most ATS failures aren't a mysterious black-box rejection — they're a parsing failure (your info gets misread or lost) or a relevance failure (your resume doesn't contain what a recruiter is searching/filtering by). Functionally those look the same to you — silence — but they need different fixes.

Three things are true simultaneously heading into 2026, based on current industry reporting:

**1. The talent market is a volume-and-quality paradox.** Companies report both more applicants per role and a shortage of qualified candidates at the same time — nearly half of talent-acquisition professionals cite a lack of quality candidates as a top problem despite rising volume. That's the environment your resume is competing in.

**2. AI is now layered on top of classic keyword ATS at most companies.** Most organizations now use AI at some stage of resume screening — sourcing, pre-screening, or ranking — on top of (not instead of) traditional keyword filtering. This means both exact-keyword matching *and* semantic/contextual relevance now matter; older "just stuff the keywords in" advice is incomplete on its own.

**3. The most important recent shift: a "signal-quality" backlash.** Because generative AI has made polished-sounding resumes (and confident-sounding interview answers) cheap and scalable to produce, multiple 2026 studies report hiring managers increasingly distrust applications that read as generic AI output — some report it actively slows hiring down because skills become harder to verify, and a hardening minority of recruiters say they now reject resumes they can identify as AI-generated. The practical takeaway: **specificity and verifiable evidence are becoming the actual differentiator**, on both the algorithmic and human side. This is the strongest argument for this project's grounding-first design (`PRD.md §8`) — it's not just an ethics requirement, it's increasingly a competitiveness requirement.

Worth knowing, not because it changes what you should do, but for context: the AI screening tools themselves are imperfect and contested — there are ongoing legal challenges alleging bias in at least two major AI-screening products (age-discrimination and fair-credit-reporting claims, respectively, both unresolved as of this writing). You're not being evaluated by an infallible, neutral system.

## 2. Formatting Rules Reference

Consistent across essentially every credible source on this, despite a lot of noisy disagreement on the finer points:

- **Single-column layout.** Multi-column and complex-grid templates are the single most common cause of scrambled parsing — text can get read out of order or dropped entirely.
- **No tables, text boxes, or graphics carrying essential content.** Decorative graphics are fine if the actual information also exists as plain text elsewhere.
- **Standard section headings**: `Summary`, `Experience`, `Education`, `Skills`, `Certifications` — not creative alternatives like "My Journey."
- **Contact info in the document body**, not in a header or footer — some parsers don't read headers/footers at all.
- **Standard fonts**: Arial, Calibri, Georgia, Garamond, Times New Roman, Helvetica, Tahoma, Verdana. 10–12pt body text.
- **A dedicated Skills section.** Beyond helping parsing, multiple sources independently note skills listed here are treated as self-declared competencies and can carry more weight than the same term appearing once inside a bullet — don't rely on bullets alone to carry your keywords.
- **1–2 pages.** Length itself isn't usually a hard parsing issue, but it correlates with the "duty-listing vs. achievement-oriented" problem below.
- **Quantify achievements.** Resumes framed around measurable outcomes (numbers, %, scope, timeframes) are consistently reported to score better than task-only descriptions — *provided the numbers are real*, per the zero-fabrication policy.

## 3. File Format: .docx vs .pdf

This is the most contradictory topic in resume-advice content — searching it turns up confidently-stated, mutually exclusive "test results" from different sites, often from companies selling their own ATS-checker tool. Treat any precise pass-rate percentage you see quoted online (including specific ones you might find elsewhere) with real skepticism; they don't agree with each other and several read as marketing copy dressed as data.

What's actually consistent across sources despite the contradictions:
- **Image-based / scanned PDFs are universally bad** — an ATS literally cannot read text from an image. Quick test: open the PDF and try to click-drag select individual words. If you can only draw a rectangular selection box (not select real text), it's an image, not text.
- **Modern major ATS (Workday, Greenhouse, Lever, iCIMS) handle clean, text-based PDFs reasonably well as of 2026.**
- **`.docx` remains the safer universal default**, particularly for older or stricter systems (Taleo is mentioned repeatedly as a laggard here).
- **Always follow explicit instructions in the job posting** if it specifies a format — this overrides every general rule.

**This pipeline's default:** generate both. Submit `.docx` unless the posting says otherwise or you're emailing a resume directly to a person (where PDF preserves exact visual layout).

## 4. Anti-Patterns — Don't Design Around These

- **Hidden/white-on-white text keyword stuffing.** A real technique some "ATS hack" content still recommends. As of 2026, major platforms (Workday, Greenhouse, Lever) are reported to actively detect this and can flag the application as fraudulent — this is now actively harmful, not just ineffective. The pipeline must never generate this.
- **Keyword stuffing the Skills section with terms not actually true of you.** Increasingly penalized by contextual/semantic scoring, and it's exactly the kind of claim the grounding check exists to catch.
- **Generic "AI voice."** Phrases like "leveraged synergies to drive impactful results" read as hollow to both human reviewers and increasingly to AI screeners trained to spot them. The tailoring prompt below explicitly preserves your specific, concrete phrasing rather than generic corporate-impact language.
- **The "75% of resumes are auto-rejected by ATS" claim.** Widely repeated, weakly sourced, and old — treat it as folklore, not a design input. Most companies don't run a system that silently nukes 3 in 4 applicants without any human ever seeing them; the real failure modes are the parsing/relevance issues above, which are fixable.

## 5. Prompt Design: JD Parsing (Stage 3 / LLM call #1)

```
SYSTEM:
You are a job-description analysis engine. You will be given the raw text of a job posting.
Extract a structured summary. Do not add information that is not present in the text —
if something is ambiguous or missing, leave the field empty rather than guessing.

Classify each requirement as "must_have" or "nice_to_have":
- Language like "required," "must have," or listing under a "Requirements" heading → must_have
- Language like "preferred," "a plus," "nice to have," or listing under "Preferred
  Qualifications" → nice_to_have
- Ambiguous phrasing defaults to nice_to_have.

For every skill, tool, or credential, extract BOTH the acronym and full term if the JD uses
either (e.g. "Search Engine Optimization (SEO)" → capture both forms) — this matters for
downstream keyword matching.

Output valid JSON matching this schema exactly: [JD Extraction schema —
see Technical_Architecture.md §3]

JOB DESCRIPTION:
{jd_text}
```
Use JSON output mode / strict tool use so you get schema-valid JSON directly rather than parsing free text. Low temperature (0–0.2).

## 6. Prompt Design: Resume Tailoring (Stage 5 / LLM call #2)

```
SYSTEM:
You are a resume tailoring assistant. You will be given (1) a Master Profile — the candidate's
complete, factual work history, education, and skills — and (2) a structured JD Requirements
object for a specific role.

Your task:
1. Select the subset of experience most relevant to this JD. Don't omit genuinely relevant
   experience, and don't pad with irrelevant roles if space is constrained.
2. Reorder bullets within each role to lead with the most JD-relevant achievements.
3. Rephrase bullet wording to mirror JD terminology ONLY where that terminology accurately
   describes what the candidate actually did. Example: if the Master Profile says "led a team
   of 5 engineers to launch a product" and the JD asks for "cross-functional leadership," you
   MAY write "led a cross-functional team of 5 engineers..." only if the team was in fact
   cross-functional — otherwise leave it as-is.
4. Work JD keywords into the summary and skills sections naturally, but ONLY skills/tools that
   already appear in the Master Profile.
5. Preserve the candidate's specific, concrete phrasing where possible rather than replacing it
   with generic corporate-impact language ("leveraged synergies," "drove results") — specific
   beats polished.
6. NEVER invent a company, title, date, degree, certification, skill, or metric not present in
   the Master Profile. NEVER change employment dates or job titles.
7. List, separately from the resume content itself (not inside it), any JD must-have
   requirements the Master Profile does not clearly support. This is for the candidate's
   awareness — do not paper over gaps by fabricating coverage.

Output valid JSON matching this schema exactly: [Tailored Resume Output schema —
see Technical_Architecture.md §3]. Every tailored bullet must include the source_bullet_id
it was derived from.

MASTER PROFILE:
{master_profile_json}

JD REQUIREMENTS:
{jd_requirements_json}
```
Moderate temperature (0.3–0.5) — enough room for natural rephrasing without drifting from source material.

## 7. Prompt Design: Grounding / Fabrication Check (Stage 6 / LLM call #3)

Run this as a **separate call**, ideally against a different, cheaper model — the point is independence from the call that wrote the content, not just asking the same model to "double check itself" in the same breath.

```
SYSTEM:
You are a fact-checking validator. You will be given a Master Profile (ground truth) and a
Tailored Resume generated from it. Your only job is to identify any claim, skill, metric, or
fact in the Tailored Resume that cannot be directly traced to a specific entry in the Master
Profile.

For each tailored bullet, verify the source_bullet_id points to a real Master Profile bullet,
and that the tailored text is a genuine rephrasing of that bullet's content — not an addition.

Return a list of unsupported_claims (exact text + why it doesn't match). If none are found,
return an empty list and passed=true. Be strict: when in doubt, flag it — a human will make
the final call.

MASTER PROFILE:
{master_profile_json}

TAILORED RESUME:
{tailored_resume_json}
```

## 8. Prompt Design: Project Extraction (turns scraped project data into draft bullets)

Runs on each record coming out of `/project_scraper` (Stage 1a) — a README, a handful of commit messages, or a portfolio page's prose isn't resume-ready on its own. This step drafts candidate bullets; it does **not** get to skip human review (`reviewed_by_user` stays `false` until you say otherwise — see `PRD.md §8`).

```
SYSTEM:
You are drafting resume bullet candidates from raw project material (a README, commit
messages, and/or a portfolio page description). You are NOT tailoring to any specific job
yet — just turning what's actually documented into 2-4 clear, specific, achievement-oriented
draft bullets the person can review and correct.

Rules:
1. Only state what the source material actually supports. If scope, scale, or impact isn't
   stated (e.g. no user count, no performance number), do not estimate or invent one — write
   the bullet without a fabricated metric rather than guessing at a plausible-sounding number.
2. Prefer concrete, specific phrasing over generic "impact language" — describe what was
   actually built/done, not "drove significant improvements."
3. Note the tech stack only from what's evidenced (dependency files, explicit README mentions,
   language stats) — don't infer tools that aren't referenced anywhere in the source.
4. If anything in the source material looks like it could be confidential (client names,
   internal-only system names, proprietary business logic, anything that reads like it belongs
   to an employer rather than a personal project), flag it separately in a "review_flags" field
   instead of silently including or silently omitting it — that's a judgment call for the human
   reviewer, not you.
5. Do not guess at dates beyond what's provided in the input metadata.

Output valid JSON:
{ "draft_bullets": ["", ""], "tech_stack": [], "review_flags": [""] }

PROJECT SOURCE MATERIAL:
{project_description_raw}
{project_metadata}  // tech_stack/dates already detected by the scraper, for cross-reference
```
Low-to-moderate temperature (0.2–0.4). Output feeds back into the Project record's `description_tailored_ready` / `highlights` fields for you to review — once approved, flip `reviewed_by_user` to `true` and it becomes eligible input for Stage 5.

## 9. Evaluation Plan

Before trusting this pipeline on a real application, spot-check it:
- Run 3–5 real JDs through it and manually verify every line in the output against the Master Profile yourself, at least until you trust the grounding check's judgment.
- Feed it one deliberately-mismatched JD (something you're clearly underqualified for) and confirm it surfaces gaps honestly rather than stretching to cover them.
- Export a sample resume and run the "select individual words" test on the PDF, and open the `.docx` in both Word and Google Docs to confirm formatting holds.
- If you have access to any ATS-checker tool (several exist commercially), use one as an external sanity check on the format validator's output — not as a replacement for it.

## 10. Quick Start — Use This Today, Before Any Code Exists

You don't have to wait for the pipeline to be built. Paste this into a Claude conversation right now, along with your resume and a job description:

```
You are an expert resume writer and ATS optimization specialist. I'll give you my complete
work history and a job description.

1. Extract the must-have and nice-to-have requirements from the job description, including
   exact keyword phrasing (both acronym and full-term forms).
2. Compare them against my work history and identify genuine matches — do not invent anything
   I haven't done.
3. Produce a tailored resume that: leads with my most relevant experience, rewrites bullets to
   mirror the JD's language ONLY where it accurately reflects what I did, naturally works in
   keywords from the JD that are genuinely true of my background, keeps specific/concrete
   phrasing rather than generic corporate language, and uses standard ATS-safe formatting
   (single column, no tables/graphics/headers-footers, standard section headings).
4. List any must-have requirements from the JD my background doesn't clearly cover, for my
   awareness only — do not fabricate coverage.

My work history: [PASTE]
Job description: [PASTE]
```

## 11. Further Reading

- [Résumé parsing — Wikipedia](https://en.wikipedia.org/wiki/R%C3%A9sum%C3%A9_parsing)
- [Applicant tracking system — Wikipedia](https://en.wikipedia.org/wiki/Applicant_tracking_system)
- [HR Brew — recruiters turning to AI pre-screening amid application volume, April 2026](https://www.hr-brew.com/stories/2026/04/07/overwhelmed-by-applications-recruiters-turn-to-ai-pre-screening-tools-to-winnow-down-applications)
- Anthropic API docs on structured outputs, for implementing the schema-guaranteed JSON calls: [docs.claude.com](https://docs.claude.com)
