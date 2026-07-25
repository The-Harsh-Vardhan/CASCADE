# Pre-Submission Audit
**Project:** Blast Radius Analyzer · **Date:** 2026-07-25

---

## Current State (What's Actually Done)

| Deliverable | Status |
|---|---|
| Working 6-phase pipeline | ✅ Runs end-to-end |
| `run.py` entry point | ✅ Created today |
| `pipeline/online.py` | ✅ Created today |
| Blast radius report for PR #3046 | ✅ `blast_radius_report.md` at root |
| Design document (8–12 pages) | ✅ `docs/design_document.md` (476 lines, ~44KB) |
| Unit tests (8 passing) | ✅ `tests/unit/test_placeholder.py` |
| AbsentRequirement fix | ✅ 181 → 20 nodes (done today) |
| README with end-to-end instructions | ✅ Present |
| Loom walkthrough | ❌ **Not recorded** |
| GitHub repo clean (no secrets) | ⚠️ Not verified |
| `pipeline/online.py` committed | ❌ Uncommitted |
| `run.py` committed | ❌ Uncommitted |

---

## P0 — Blockers (will cost significant points if not fixed)

### P0-1: Loom video not recorded
The assignment requires a 5–10 min Loom walkthrough — equal weight to every other deliverable. Without it you are submitting 3/4 deliverables.

**What to cover:**
1. Show `docker compose up -d` → Neo4j running
2. Run `python run.py https://github.com/documenso/documenso/pull/3046`
3. Show the report printing in terminal
4. Open `outputs/reports/pr_3046_blast_radius.md` and walk through the findings
5. Open Neo4j browser → show the graph (the graph_explorer.html is perfect)
6. Open `docs/design_document.md` → briefly narrate the key design decisions

**Effort:** 30–60 min

---

### P0-2: Three new files not committed
`run.py`, `pipeline/online.py`, and `scripts/fix_absent_requirements.py` are untracked.

```bash
git add run.py pipeline/online.py scripts/fix_absent_requirements.py
git commit -m "feat: add run.py entry point, online pipeline, and absent req fix script"
```

---

### P0-3: The blast radius report at root is the OLD version
`blast_radius_report.md` at the repo root was generated *before* the AbsentRequirement fix. It shows 3 absent reqs (Docker/PostgreSQL/Kubernetes infrastructure ones). That's actually a *good* report — those are the real findings for PR #3046, not the 181 false positives. But the report at root is manually written (enhanced), not auto-generated. Confirm it matches what `run.py` would produce, or replace it with `outputs/reports/pr_3046_blast_radius.md` after running `run.py`.

---

## P1 — High Impact (noticeable by evaluators)

### P1-1: Only 8 unit tests, all testing one function
The test suite covers only `Settings.gemini_api_keys`. There are no tests for:
- `parse_pr_url()` in `run.py` (the user-facing entry point)
- `classify()` in `fix_absent_requirements.py` (the core rule-based classifier)  
- `check_graph_ready()` in `pipeline/online.py`
- URL parsing edge cases

These take ~30 minutes to write and demonstrate the codebase is tested end-to-end.

### P1-2: README still references `scripts/run_pipeline.py --phase N` as the primary interface
The README says to run `python scripts/run_pipeline.py --phase 0` through `--phase 6`. But the whole point of today's `run.py` work is that the evaluator should run `python run.py <PR_URL>`. The README's primary command needs updating to reflect the new entry point.

**Fix:** Add this at the very top of the README, before everything else:
```bash
# Quick start (graph must be pre-built):
python run.py https://github.com/documenso/documenso/pull/3046
```

### P1-3: No `outputs/reports/` sample committed
The `.gitignore` ignores all of `outputs/`. But the evaluator needs to see what the output looks like without running the pipeline. The root-level `blast_radius_report.md` serves this purpose — but it's not linked from the README's Output section. Update the README to point to it explicitly.

### P1-4: `data/graph_explorer.html` is modified but not committed
You have modified `data/graph.html` and `data/graph_explorer.html` (per `git status`). If these are important demo assets for the Loom, commit them.

---

## P2 — Medium Impact (noticeable by a careful reader)

### P2-1: Integration test directory is empty
`tests/integration/__init__.py` only. A minimal Neo4j integration test (check graph has ≥ 100 nodes, run `analyze_pr()` on a cached delta) would strengthen the submission.

### P2-2: `outputs/` directory has no `.gitkeep` files
`outputs/crawl/` and `outputs/requirements/` exist but `outputs/reports/` doesn't appear to be tracked. After running `run.py`, the canonical report goes to `outputs/reports/pr_3046_blast_radius.md`. Add an `outputs/reports/.gitkeep` and commit the sample report there.

### P2-3: `blast_radius_report.md` at root vs. `docs/blast_radius_report_final.md`
There are two report files: `blast_radius_report.md` (root, 9.4KB) and `docs/blast_radius_report_final.md` (7.8KB). Pick one canonical location and update the README to point to it. Having two is confusing.

### P2-4: Design doc references `run_id: 26e8fc39` but report is not linked
The design doc's Section 8 mentions run ID `26e8fc39`. The README doesn't link directly to `blast_radius_report.md`. Add a direct link in the README under a "Sample Output" heading.

### P2-5: `scripts/` directory has ~28 files, mostly debug scripts
`diagnose_graph.py`, `diagnose_graph_2.py`, `audit_implements.py`, `run_api_handles_query.py`, etc. are internal debug tools. They're not harmful but they make the repo look messy. Either move them to `scripts/debug/` or add a comment at the top of `scripts/README.md` explaining their purpose.

---

## P3 — Low Impact / Polish

### P3-1: `scratch_test.js` at project root (23KB)
An unignored scratch file. `git rm scratch_test.js` or add `*.js` to `.gitignore`.

### P3-2: `crawler.py` and `ingestor.py` at root
Root-level scripts that duplicate `pipeline/offline.py`. If they're unused, delete them. If they're useful entry points, document them in the README.

### P3-3: `tmp_pr3046.json` at root
A 4KB temp file. `git rm tmp_pr3046.json`.

### P3-4: `graph.html` at root
Duplicate of `data/graph.html`? Clarify or delete.

---

## Priority Order for Remaining Time

| # | Task | Time | Impact |
|---|---|---|---|
| 1 | **Record Loom video** | 45 min | P0 — 25% of grade |
| 2 | **Commit run.py, pipeline/online.py, fix script** | 5 min | P0 — blocker |
| 3 | **Update README top section** to feature `run.py` as primary interface | 10 min | P1 |
| 4 | **Add 3 unit tests** for `parse_pr_url` + `classify` | 20 min | P1 |
| 5 | **Run `run.py` → commit the output** to `outputs/reports/pr_3046_blast_radius.md` | 10 min | P1 |
| 6 | **Delete root clutter** (`scratch_test.js`, `tmp_pr3046.json`) | 5 min | P3 |
| 7 | **Commit graph_explorer.html** if it's the demo asset | 3 min | P1 |

---

## What's Already Strong (Don't Touch)

- ✅ Design document is thorough — UserFlow graph schema, PPR rationale, confidence handling, scope decisions are all there
- ✅ The `blast_radius_report.md` is well-written with QA action items — non-engineer readable
- ✅ Graph schema is complete: Requirement / UIElement / UserFlow / CodeFunction / GapNode + 6 edge types
- ✅ `run.py` correctly separates online (read-only) from offline (build) pipeline
- ✅ `check_graph_ready()` guard prevents running on empty graph
- ✅ `AbsentRequirement` nodes are now 20, meaningfully classified
- ✅ 8 unit tests all pass
- ✅ `.gitignore` correctly excludes credentials and generated data
- ✅ `pyproject.toml` matches the assignment's exact tech stack requirements
