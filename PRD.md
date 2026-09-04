# Product Requirements Document
## ResumeForge — AI-Powered JD-to-Resume Tailoring Pipeline
*(working title — rename freely)*

| | |
|---|---|
| **Version** | 1.0 (Draft) |
| **Date** | August 18, 2026 |
| **Owner** | You |
| **Status** | Ready for review |
| **Related docs** | `Technical_Architecture.md`, `ATS_Guidelines_and_Prompt_Design.md` |

---

## 1. Problem Statement

Job seekers today are told to "tailor every resume," but doing that by hand for every application is slow and inconsistent — most people either send one generic resume everywhere, or burn hours re-writing bullets for each posting.

The market context makes this worse, not better. Recruiters are drowning in applications while simultaneously complaining they can't find qualified people — nearly half of talent-acquisition professionals report a lack of quality candidates despite rising application volume. In response, most companies now use AI at some stage of screening, layered on top of traditional keyword-matching ATS software.

That creates a second, less obvious problem: **generative AI has made both resumes and interview answers cheap to produce, and hiring teams have noticed.** Multiple 2026 industry studies report hiring managers increasingly flag AI-generated applications as harder to trust and slower to verify, and a growing minority of recruiters now actively reject resumes that read as obviously AI-written. A tool that makes tailoring *easier* is only useful if it doesn't make the output *generic* — the two failure modes (untailored, and unmistakably-AI-generic) can both cost you the interview.

**This project builds a pipeline that threads that needle**: given a job description and a complete, factual record of your real experience, it produces a resume that is (a) formatted so ATS software parses it correctly, (b) aligned to the specific language and requirements of that JD, and (c) still built entirely out of things you actually did — specific enough that it doesn't read as generic AI output, and defensible enough that you can back up every line in an interview.

## 2. Goals

- Turn a job description + your master profile into a tailored, ATS-parseable resume in minutes, not hours.
- Maximize genuine keyword/requirement alignment between resume and JD — without fabricating anything.
- Make every tailored resume traceable back to real entries in your master profile (full grounding).
- Keep a human review step before anything is used — this is an assistant, not an autopilot.
- Support dozens of tailored versions across a job search without losing track of what was sent where.
- Give you an ATS-compatibility check *before* you submit, not after you get silence.

## 3. Non-Goals

- **Not an auto-apply bot.** The pipeline stops at "here is your tailored resume, reviewed and exported." It does not submit applications on LinkedIn/Indeed/company portals. Most job platforms' terms of service restrict automated submission, and removing the human checkpoint removes the main safeguard against bad output going out the door.
- **Not a resume fabrication tool.** It will not invent employers, titles, dates, degrees, certifications, or metrics. See §8 — this is a hard constraint, not a style preference.
- **Not a guarantee of interviews or offers.** Resume quality is one input into a job search among many (network, role fit, market conditions, interview performance). The docs avoid promising outcomes they can't control.
- **Not a mass job-board scraper.** JD ingestion is paste-first; scraping job boards at scale raises ToS and legal questions that are out of scope for v1.
- **Not multi-tenant SaaS in v1.** This is scoped as a personal tool for your own search first. A shareable product is a possible *future* direction, not a v1 requirement (see §12).

## 4. Users & Core Use Case

**Primary user:** you, actively applying to multiple roles, wanting each application to be genuinely competitive without spending an hour per resume.

**Core use case:** You find a role. You paste the JD in. Within a couple of minutes you have a tailored, ATS-safe resume that emphasizes your most relevant real experience, plus a short list of any requirements you don't clearly meet — so you can decide whether to address them (in the resume, in a cover letter, or not at all) with full information.

## 5. Core User Journey

1. **One-time setup:** Build your Master Profile — the complete, structured record of your work history, education, skills, and projects. (Can be bootstrapped from an existing resume — see FR-1.)
2. **Per application:** Paste a job description.
3. System extracts structured requirements from the JD (must-haves vs. nice-to-haves, exact keyword phrasing).
4. System compares your Master Profile against those requirements and shows you the overlap and the gaps.
5. System generates a tailored resume: reordered, re-emphasized, rephrased where accurate — grounded entirely in your Master Profile.
6. System validates the output twice: a **grounding check** (did it invent anything?) and an **ATS format check** (will this parse cleanly?).
7. You review a diff against your master content, edit anything you want, approve.
8. System exports a clean `.docx` (and optionally `.pdf`) and saves it under that job/company for later reference.

## 6. Functional Requirements

| ID | Requirement | Notes |
|---|---|---|
| FR-1 | **Master Profile intake.** Structured store of contact info, work history (company, title, dates, bullets), education, skills, certifications, projects. Support bootstrapping by uploading an existing resume and having the LLM extract it into the schema, with the user confirming/correcting the result. | See `Technical_Architecture.md §3` for schema. |
| FR-1a | **Project auto-ingestion.** Pull project details automatically from GitHub (API), a personal portfolio site, and local project folders, instead of hand-entering every project. Merge into one deduped list (the same project often exists in more than one source). | Implemented in `/project_scraper`. Output is *raw material only* — see the guardrail below. |
| FR-2 | **JD ingestion.** Primary: paste raw text. Secondary (v2): fetch from a pasted URL, with a manual-paste fallback since many job boards block scraping or render JDs via JavaScript. | Do not build scraping that violates a job board's ToS. |
| FR-3 | **JD parsing.** Extract a structured requirements object: must-have vs. nice-to-have, hard skills, soft skills, tools, years of experience, education requirements, core responsibilities, exact keyword phrases (including acronym + full-term pairs), seniority level, and basic company context. | LLM call #1. Deterministic-leaning (low temperature). |
| FR-4 | **Gap/match analysis.** Compare Master Profile against JD requirements. Compute keyword/requirement coverage. Surface genuinely missing must-haves to the user — never silently paper over them. | Mostly deterministic logic over the two structured objects. |
| FR-5 | **Tailored resume generation.** Select and reorder the most relevant experience, rewrite bullets to mirror JD phrasing *only where it's accurate*, work in real keywords from the Master Profile naturally. Must never introduce a fact not present in the Master Profile. | LLM call #2. See §8 and the prompt-design doc. |
| FR-6 | **Grounding / anti-fabrication check.** Independently verify every claim in the generated resume traces back to a Master Profile entry. Flag anything that doesn't for human review before export. | LLM call #3 (or embedding-similarity check) — a second, independent pass, not the same call that wrote the content. |
| FR-7 | **ATS format validation.** Deterministic checks: single-column, no tables/text-boxes/images carrying essential text, standard section headings, contact info not in header/footer, approved font list, reasonable length (1–2 pages), text-layer integrity in exported PDF. | See `ATS_Guidelines_and_Prompt_Design.md §2`. |
| FR-8 | **Human review UI.** Show a diff between original Master Profile bullets and tailored output. Accept/reject/edit at the bullet level before export. | This is the safety net — never auto-export without this step in v1. |
| FR-9 | **Export & versioning.** Generate final `.docx` (default) and optional `.pdf`. Store each tailored version tagged by company/role/date so you can track what you sent where. | |
| FR-10 *(v2)* | Cover letter generation from the same grounded inputs. | |
| FR-11 *(v3)* | Outcome tracking (applied / interview / rejected) to learn which tailoring patterns actually correlate with responses. | Feedback loop — genuinely useful, but needs real usage data to mean anything, so it's explicitly post-MVP. |

## 7. Non-Functional Requirements

- **Accuracy/integrity:** Zero tolerance for fabricated content — see §8. This is treated as a correctness bug, not a quality nice-to-have.
- **Latency:** End-to-end (paste JD → reviewable draft) under ~2 minutes on a normal LLM call budget.
- **Privacy:** Resumes contain PII (name, contact details, sometimes more). Master Profile data should be encrypted at rest if stored beyond your own machine, and you should control retention. If you use the Claude API for the LLM calls, check Anthropic's current API data-retention terms at [docs.claude.com](https://docs.claude.com) for specifics, since policies can change.
- **Portability:** Output must open cleanly in Word, Google Docs, and common ATS parsers — no proprietary lock-in on the final file.
- **Cost:** LLM spend per tailored resume should be small and predictable (a few cents, not dollars) — see model guidance in the architecture doc.
- **Auditability:** You should always be able to see *why* a line is in the resume — which Master Profile entry it came from.

## 8. Guardrail: Zero-Fabrication Policy (non-negotiable)

This is the single most important requirement in this document, and it's both an ethical line and a practical one — a fabricated line is a liability the moment someone asks you to elaborate on it in an interview.

- **Closed-world generation:** the tailoring step is only ever allowed to *select, reorder, and rephrase* content that already exists in the Master Profile. It is never allowed to add a new employer, title, date, degree, certification, skill, or metric.
- **Independent grounding check (FR-6):** a second LLM pass (or embedding-similarity check), separate from the one that generated the resume, verifies every claim traces back to source data. This mirrors a "generate then verify" pattern that meaningfully reduces the chance an invented detail slips through unnoticed.
- **No hidden manipulation:** the pipeline must never use invisible/white-on-white text keyword stuffing to game parsers. This used to be a semi-common gray-hat trick; as of 2026, Workday, Greenhouse, and Lever are reported to actively detect it and can flag the application as fraudulent rather than simply ignoring it. Every optimization this tool makes must be content a human is meant to read.
- **Gaps are surfaced, not hidden:** if the JD asks for something your Master Profile doesn't support, the system tells you that explicitly (FR-4) instead of quietly stretching the truth to cover it.
- **Scraped data isn't trusted data until you say so:** project details pulled in via FR-1a carry a `reviewed_by_user: false` flag by default. The tailoring engine (Stage 5) must never read a project that hasn't been reviewed and flipped to `true` — auto-collected README/commit text can be incomplete, out of date, or (for work projects) touch on things that shouldn't appear on a public resume at all. Automation gets you a draft, not ground truth.

## 9. Setting Realistic Expectations (ATS & AI-Screening Reality Check)

Worth stating plainly, because a lot of resume-optimization content oversells this: there is no single universal "ATS score," most ATS platforms don't invisibly auto-reject every imperfect resume the way the oft-repeated "75% rejected by robots" claim suggests, and no tool — this one included — can guarantee an interview. What the research does support, consistently, going into 2026:

- Formatting failures are real and fixable: a parseable file gets you *into* the pool; a badly-formatted one can get silently misread even from a strong candidate.
- Keyword and skills alignment increasingly matters *before* a human ever opens the file — many hiring teams now filter by explicit skills first.
- AI is now layered on top of classic keyword ATS at most companies, doing more contextual/semantic matching — which rewards genuine relevance, not just keyword density.
- The newest, most consequential shift: hiring teams are actively trying to detect and discount resumes (and interview answers) that read as generic AI output, because AI has made it cheap to produce polished-sounding-but-hollow applications at scale. Specificity and verifiable evidence are becoming the actual differentiator.

Full detail and sourcing in `ATS_Guidelines_and_Prompt_Design.md §1`.

## 10. Success Metrics

| Metric | Target | Type |
|---|---|---|
| Must-have keyword/requirement coverage | ≥ 80% of JD must-haves reflected (truthfully) in output | Leading |
| ATS format validation pass rate | ~100% clean parse on the internal validator | Leading |
| Fabricated-content incidents | 0 | Guardrail (hard requirement) |
| Time per tailored resume | Under 5 minutes including your review | Leading |
| Application → response/interview rate | Improves vs. your own pre-tool baseline | Lagging (track over time; noisy, don't over-index on any single data point) |

## 11. Risks & Mitigations

| Risk | Mitigation |
|---|---|
| LLM invents or embellishes a qualification | Closed-world prompting + independent grounding check (§8) |
| Over-optimized resume reads as generic/robotic to a human or an AI screener | Prompt explicitly preserves specific, concrete phrasing from your real bullets rather than generic "impact language"; grounding check catches drift |
| Formatting choice breaks parsing on a specific ATS | Deterministic format validator (FR-7) + default to `.docx` unless the posting says otherwise |
| Resume data is sensitive PII | Encrypt at rest, minimize retention, keep processing local where practical |
| Scope creep into auto-applying | Explicitly out of scope (§3); human approval is a hard checkpoint before export |
| Chasing a moving target (ATS/AI-screening behavior shifts over time) | Treat `ATS_Guidelines_and_Prompt_Design.md` as a living document; revisit periodically rather than trusting it as permanently accurate |

## 12. Scope & Phased Roadmap

**Phase 0 — Setup (do this first, doesn't require any code):** Build your Master Profile. Can literally be a structured JSON/Markdown file you maintain by hand, or bootstrapped by having Claude extract it from your current resume.

**Phase 1 — MVP:** Paste-JD → parse → gap analysis → tailor → grounding check → ATS format check → human review → `.docx`/`.pdf` export. Can be built as a script or even run manually through a well-structured Claude conversation before any code exists (see the quick-start prompt in the ATS/prompts doc) — don't wait for the full build to start benefiting from this.

**Phase 2:** Lightweight web UI or dashboard, version history across applications, ATS-checker integration, browser extension to capture JDs with one click, cover letter generation (FR-10).

**Phase 3:** Outcome tracking and feedback loop (FR-11) — which tailoring patterns actually correlate with responses; possible integrations (e.g., auto-detecting JDs from application-confirmation emails, career-intelligence enrichment) once there's a stable core to build on.

## 13. Assumptions & Open Questions

**Assumptions made in this draft** (flag anything you want changed):
- This is a personal-use tool for your own search, not a multi-user product — architecture in the companion doc is scoped accordingly, but not in a way that would block scaling later.
- You'll maintain one Master Profile as the single source of truth, updated as your experience grows.
- `.docx` is the default export; `.pdf` is generated alongside it as an option, not a replacement.
- You have (or are willing to build) a complete, honest record of your work history to seed the Master Profile — the tool only works as well as that source data.

**Open questions for you to resolve:**
- Local script vs. simple web app vs. just doing this through Claude/Claude Code directly — how much "product" do you actually want to build vs. use?
- One resume template/design, or several for different resume styles (technical/creative/executive)?
- Do you want cover letter generation in scope sooner than Phase 2?

## 14. Related Documents

- `Technical_Architecture.md` — system design, data schemas, tech stack, storage, and security.
- `ATS_Guidelines_and_Prompt_Design.md` — the ATS/AI-screening domain knowledge and the actual LLM prompt templates for each pipeline stage, plus a ready-to-use manual prompt you can run today.
