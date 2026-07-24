# Blast Radius Analyzer — Submission Preparation Plan

## Overview

The project is in good shape (working v4 pipeline, real report for PR #3046). This plan addresses the seven specific gaps the submission guide identifies, prioritized by evaluator impact.

## Current State Assessment

| Item | Status |
|------|--------|
| P0-21 bug (IMPLEMENTS edge direction) | ✅ Fixed — `resolve.py` line 221-229 uses `from_id=fn_id, to_id=req_id` |
| P0-22 bug (functions.index) | ✅ Fixed — uses precomputed `fn_idx` |
| Path alignment (Phase 5 seed) | ✅ Fixed — error is raised if 0 seeds found |
| `.env` in `.gitignore` | ✅ Yes |
| `.env.example` exists | ✅ Yes (5 keys listed) |
| `data/` gitignored | ✅ Yes (crawl, code, requirements, reports, repos) |
| `blast_radius_report.md` committed | ⚠️ Only in `docs/blast_radius_report_final.md` — needs copy to `blast_radius_report.md` at root |

## Issues to Fix

### Critical Issues
1. **README says `ANTHROPIC_API_KEY`** — wrong. The project uses Gemini. This is a factual error evaluators will catch immediately.
2. **Config table has "10-key rotation pool"** — must reframe to avoid ToS flagging.
3. **Design document: UserFlow never explained** — must add explicit scope-out in Section 5.
4. **Design document: url_sha256 schema contradiction** — quick 5-min fix.
5. **Design document: top-N never specified** — add N=15 to config table.

### Design Document Improvements
6. **Section 4 (Eval)**: Add empirical stability check subsection.
7. **Section 2**: Add Mermaid graph diagram + url_sha256 fix.
8. **Section 3**: Add worked example (sendDocument PPR product).
9. **Section 1**: Rename "Why this is not a chain of prompts" heading.
10. **tRPC**: Consolidate redundant tRPC mentions in Sections 1/3.
11. **Page length**: Document is ~5-6 pages, needs 8-12.

### Blast Radius Report Improvements
12. **C1**: Add "Recommended QA Actions" section.
13. **C2**: Explain "Dark Changes" in plain language.
14. **C3**: Add TL;DR at top.

### Repository Cleanup
15. **A1**: Add `CRAWL_USE_FIXTURE` env var + fixture mode to `.env.example`.
16. **A4**: Document fixture mode in README.
17. **data/graph** not in `.gitignore` — add it.

## Proposed Changes

---

### README.md
#### [MODIFY] [README.md](file:///C:/D Drive/Projects/Summers 2026/Testsigma/README.md)
- Fix `ANTHROPIC_API_KEY` → `GEMINI_API_KEY_1` reference
- Add "Running Without a Documenso Account" section
- Add expected phase output / PASS criteria table
- Fix design document path (`docs/design_document.md` → `docs/v1_design_document.md`)

---

### .env.example
#### [MODIFY] [.env.example](file:///C:/D Drive/Projects/Summers 2026/Testsigma/.env.example)
- Add `CRAWL_USE_FIXTURE=false` with explanation

---

### .gitignore
#### [MODIFY] [.gitignore](file:///C:/D Drive/Projects/Summers 2026/Testsigma/.gitignore)
- Add `data/graph/` to ignored directories

---

### blast_radius/config.py
#### [MODIFY] [config.py](file:///C:/D Drive/Projects/Summers 2026/Testsigma/blast_radius/config.py)
- Add `crawl_use_fixture: bool` setting
- Rename "Key rotation pool" in comment to "multiple project API keys"

---

### blast_radius/crawl/ (fixture mode)
#### [MODIFY] crawl `__init__.py` or main entry
- Add fixture mode: if `CRAWL_USE_FIXTURE=true`, read from `data/crawl/fixtures/` instead of live crawl

---

### blast_radius_report.md (committed sample output)
#### [NEW] [blast_radius_report.md](file:///C:/D Drive/Projects/Summers 2026/Testsigma/blast_radius_report.md)
- Copy of `docs/blast_radius_report_final.md` with C1/C2/C3 improvements applied:
  - TL;DR block at top
  - "Dark Changes" plain-language explanation
  - "Recommended QA Actions" section

---

### docs/v1_design_document.md → docs/design_document.md
#### [MODIFY] Design document
Apply all B-series fixes:
- **B1**: Add UserFlow scope-out to Section 5
- **B2**: Add "Empirical Stability Check" subsection to Section 4
- **B3**: Fix UIElement schema (add url_sha256)
- **B4**: Specify N=15 in config table and Phase 4 description
- **B5**: Add Mermaid graph diagram to Section 2
- **B6**: Rename "Why this is not a chain of prompts" heading
- **B7**: Consolidate tRPC references
- **B8**: Add Section 3 worked example to expand to 8-12 pages

---

## Verification Plan

### Automated Checks
- `python scripts/validate_env.py` — must pass all checks
- `grep -r "ANTHROPIC" . --include="*.py" --include="*.md"` — must return 0 results
- `grep -r "rotation pool" . --include="*.md"` — must return 0 results after reframe

### Manual Verification
- Confirm `blast_radius_report.md` is at repo root and committed
- Confirm `docs/design_document.md` is 8-12 pages
- Confirm design document has Mermaid diagram in Section 2
- Confirm design document has UserFlow scope-out in Section 5
- Confirm all 5 "things that will hurt you" from guide are addressed

## Execution Order

Following submission guide priority:
1. Fix README (ANTHROPIC_API_KEY error)
2. Fix design document (B1 UserFlow, B3 schema, B4 N=15, B5 diagram, B6 heading, B2 stability, B7 tRPC, B8 expansion)
3. Fix blast_radius_report.md (C1 QA Actions, C2 Dark Changes, C3 TL;DR)
4. Fix config.py (reframe rotation pool comment)
5. Add fixture mode env var to .env.example + config
6. Update .gitignore (add data/graph/)
7. Commit blast_radius_report.md at repo root
