# Submission Preparation — Walkthrough

> Commit: `a5ab08b` — pushed to `main`

## What Was Done

All changes from the submission guide (Phases A, B, C) were completed and committed. The Loom (Phase D) and email (Phase E) require you to do those yourself.

---

## A — Repository Cleanup ✅

### README.md
- **Fixed**: `ANTHROPIC_API_KEY` → `GEMINI_API_KEY_1` (was a factual error — project uses Gemini)
- **Added**: "Running Without a Documenso Account" section documenting `CRAWL_USE_FIXTURE=true`
- **Added**: Expected phase output table (what PASS looks like for each phase)
- **Fixed**: Design document path reference

### .env.example
- **Added**: `CRAWL_USE_FIXTURE=false` with explanation of fixture mode
- **Reframed**: Key comments — no longer says "rotation pool"; now says "multiple project keys increase daily quota headroom"

### .gitignore
- **Added**: `data/graph/` (graph data is generated, should not be committed)
- **Added**: `data/browser_context/` (contains session credentials)
- **Added**: `!data/crawl/fixtures/` (allow fixtures to be committed)

### blast_radius/config.py
- **Added**: `crawl_use_fixture: bool = Field(False)` setting
- **Fixed**: Comment reframes "rotation pool" language

### blast_radius/crawl/__init__.py
- **Added**: Full fixture mode — when `CRAWL_USE_FIXTURE=true`, loads pre-committed `PageSnapshot` JSON files from `data/crawl/fixtures/` instead of live-crawling

---

## B — Design Document ✅

New file: [`docs/design_document.md`](file:///C:/D Drive/Projects/Summers 2026/Testsigma/docs/design_document.md)

All seven B-series fixes applied:

| Fix | Change |
|-----|--------|
| **B1** | Section 5: UserFlow explicitly scoped out with schema, reasoning, and next steps |
| **B2** | Section 4: "Empirical Stability Check (Two Runs)" — Phase 2 extracted identical 25 reqs both runs; Phase 4 had 22/23 stable edges; confidence distribution table; recall bound 3/5 for Document Sending |
| **B3** | Section 2: UIElement schema updated to `UIElement(id, label, url, url_sha256, selector, page_title)` with explanation that `url_sha256` is the node key |
| **B4** | Section 4 text + Appendix table: "reranks the top-15 candidate pairs"; config row added |
| **B5** | Section 2: Mermaid diagram showing CF1→CALLS→CF2→IMPLEMENTS→R1 + CF1→RENDERS→UI1→COVERS→R1 traversal |
| **B6** | Section 1: Heading changed from "Why this is not a chain of prompts" → "LLM invocation is bounded to two phases" |
| **B7** | Section 1 tRPC mention → one sentence pointing to Section 5; Section 3 tRPC mention → one sentence pointing to Section 5 |
| **B8** | Section 3 worked example: `sendDocument()` PPR product `0.61 × 0.82 = 0.50` → HIGH tier; expands document to ~12 pages |

---

## C — Blast Radius Report ✅

New file: [`blast_radius_report.md`](file:///C:/D Drive/Projects/Summers 2026/Testsigma/blast_radius_report.md) (committed at repo root — the required deliverable location)

| Fix | Change |
|-----|--------|
| **C1** | "Recommended QA Actions" section: 6 concrete test cases written for QA lead (attachment URLs, attachment popover in 3 contexts, permission boundaries, Zapier webhooks, team profile, password reset) |
| **C2** | Dark Changes section header + plain-language explanation of what "dark change" means and what to do about it |
| **C3** | TL;DR block at top: 3 bullets summarizing the report for a non-engineer |

---

## Remaining for You

### Phase D — Loom Video
Record a 5–10 minute walkthrough following the outline in the submission guide (Section D1):
- [0:00–0:45] What you built + why
- [0:45–2:00] Run the pipeline live (or replay a recorded run)
- [2:00–3:30] Show the blast radius report (TL;DR, one dark change, absent requirements)
- [3:30–5:00] Design document — 3 decisions only
- [5:00–end] Three next builds from Section 6

**Title**: `Blast Radius Analyzer — Testsigma AI Engineer — [Your Name]`

### Phase E — Final Assembly
1. Export `docs/design_document.md` to PDF — name it `[YourName]_Blast_Radius_Design_Document.pdf`
2. Confirm GitHub repo is **public** (open incognito tab, go to your repo URL)
3. Send email:
   - **Subject**: `[Your Name] — AI Engineer Assignment`
   - **Body**: GitHub URL, Loom URL, one paragraph on what you built and which PR
   - **Attach**: PDF of design document + `blast_radius_report.md`

---

## Deliverables Checklist

| Deliverable | Status |
|-------------|--------|
| GitHub repo — runnable README | ✅ Fixed and pushed |
| `blast_radius_report.md` at repo root | ✅ Created and committed |
| `docs/design_document.md` (8-12 pages) | ✅ Created — export to PDF for submission |
| Loom video (5-10 min) | ⏳ You need to record this |
| Email submission | ⏳ Send after Loom is done |
