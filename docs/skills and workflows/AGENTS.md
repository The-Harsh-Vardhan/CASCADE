# AGENTS.md — Blast Radius Analyzer
# Testsigma AI Engineer Assignment

---

## What This Project Is

A 6-phase pipeline that crawls Documenso (a live SaaS app), ingests its PRD,
builds a Neo4j knowledge graph across three layers (Requirements / UI / Code),
then given a real PR produces a "blast radius" report: which UI elements are at
risk, which user flows are affected, which requirements lose coverage.

Target app:    https://app.documenso.com
Target repo:   https://github.com/documenso/documenso
Language:      TypeScript / Next.js / Prisma / tRPC (target app)
Pipeline lang: Python 3.11+

---

## Assignment Deliverables (non-negotiable)

Every component you build must map to one of these four:

1. GitHub repo — runnable README, end-to-end
2. Design document — 8–12 pages covering: agent decomposition, graph schema
   with justification, confidence handling, eval approach, scope decisions,
   and what you'd build next with another week
3. Blast radius report — for a real merged PR, readable by a non-engineer QA lead
4. 5–10 min Loom walkthrough of the prototype running + the design doc

The design document and code are weighted EQUALLY. Do not neglect the design doc.

---

## Tech Stack (exact — from v4 plan)

| Component         | Library / Tool                        | Notes |
|-------------------|---------------------------------------|-------|
| Crawler           | Playwright (direct, not crawl4ai)     | crawl4ai==0.4.3 is yanked — use Playwright |
| Doc parsing       | Docling >=2.0.0,<3.0                  | For README + docs.documenso.com |
| Static analysis   | ast-grep (system binary, not pip)     | Install: brew install ast-grep / prebuilt binary |
| PR ingestion      | GitHub API via httpx (NOT PyDriller)  | PyDriller replaced in v4 |
| Graph DB          | Neo4j 5.14-community via Docker       | bolt://localhost:7687 |
| Graph library     | networkx >=3.2,<4.0                   | PPR + DFS traversal |
| LLM calls         | anthropic >=0.25.0,<1.0              | claude-sonnet-4-6 |
| Embeddings        | sentence-transformers >=2.7.0,<4.0   | Cosine similarity for entity resolution |
| Report rendering  | Jinja2 >=3.1.0,<4.0                  | HTML + Markdown outputs |
| Settings          | pydantic-settings >=2.1.0,<3.0       | Loaded from .env |
| HTTP              | httpx >=0.26.0,<1.0                  | GitHub API + doc fetching |
| Models            | pydantic >=2.5.0,<3.0               | All inter-phase data contracts |

Package layout: FLAT — `blast_radius/` at repo root, NO `src/` wrapper.

---

## Six-Phase Pipeline

```
Phase 0: Project skeleton + pre-flight validation
Phase 1: Playwright crawler (unauth + auth Documenso flows)
Phase 2: Docling ingest (README + docs.documenso.com → Requirement models)
Phase 3: ast-grep + GitHub API (TypeScript AST → CodeFunction + PRDelta)
Phase 4: Entity resolution + Neo4j graph build (cosine+LLM + GapNodes)
Phase 5: PR blast radius (PPR + DFS → BlastRadiusReport JSON)
Phase 6: Jinja2 report render (HTML + Markdown)
```

Runner: `python scripts/run_pipeline.py --phase N`
Each phase writes typed Pydantic models to `data/` — schema mismatches raise
ValidationError immediately.

---

## Known Bugs in the v4 Plan (apply these fixes silently)

These are confirmed P0/P1 bugs from the v4 audit. Fix them as you implement
each phase — do not reproduce the broken code from the plan:

| Bug ID        | Phase | Fix |
|---------------|-------|-----|
| P0-PHASE0-01  | 0     | pyproject.toml backend must be "setuptools.build_meta" NOT "setuptools.backends.legacy:build" |
| P0-PHASE1-01  | 1     | crawl4ai==0.4.3 is yanked — use Playwright directly |
| P0-PHASE1-02  | 1     | static.py is defined but never called by run_crawl() — wire it in |
| P0-PHASE3-01  | 3     | fn.file path format ≠ cf.path format → 100% dark changes. Add verify_path_alignment() |
| P0-PHASE4-01  | 4     | RENDERS assert fails with unauthenticated crawl — auth is mandatory |
| P0-PHASE5-01  | 5     | Functions with descendants but no UI path silently disappear — add fallback |
| P0-CROSS-01   | All   | No graph reset between runs → GapNodes accumulate. Add cleanup at start of build_graph() |
| P1-PHASE0-02  | 0     | playwright install --dry-run does not exist — use try/except launch() check |
| P1-PHASE5-02  | 5     | PPR sink nodes score near 0 → add 2.5x sink boost or BFS fallback |
| P0-DOC-01     | Doc   | Design document section is MISSING from the plan — must be created |

Full audit is in: docs/audits/v4_audit_report_implementation_plan.md

---

## Data Contracts (key Pydantic models)

All phases exchange typed JSON. Never guess field names — reference models.py:

- `PageSnapshot` — output of Phase 1 crawler
- `Requirement` — output of Phase 2 ingest
- `CodeFunction` — output of Phase 3 ast-grep
- `PRDelta` — output of Phase 3 GitHub API
- `BlastRadiusReport` — output of Phase 5

Inter-phase directory layout:
```
data/crawl/{url_sha256}.json        # PageSnapshot
data/crawl/manifest.json            # CrawlManifest
data/requirements/requirements.json # list[Requirement]
data/code/call_graph.json           # list[CodeFunction]
data/code/pr_{number}.json          # PRDelta
data/reports/blast_radius_report.json   # BlastRadiusReport
data/reports/blast_radius_report.md
data/reports/blast_radius_report.html
```

---

## Graph Schema (Neo4j)

Three node types, three edge types:

Nodes:
- `Requirement(id, label, source, text, coverage_status)`
- `UIElement(id, label, url, selector, page_title)`
- `CodeFunction(id, label, file, name, signature)`
- `GapNode(id, requirement_id)` — for absent requirements

Edges:
- `IMPLEMENTS`: CodeFunction → Requirement  (entity resolution output)
- `RENDERS`:    CodeFunction → UIElement    (code→UI traceability)
- `COVERS`:     UIElement → Requirement     (UI→PRD traceability)
- `CALLS`:      CodeFunction → CodeFunction (call graph)

---

## Blast Radius Report Format (non-negotiable)

The final report must contain ALL of these sections:

1. Plain-English executive summary (2–3 sentences, no jargon)
2. Changed files table (path, status, +/− lines)
3. Affected UI elements — HIGH / MEDIUM / LOW with evidence path
4. Affected requirements — HIGH / MEDIUM / LOW with evidence path
5. Absent requirements — requirements in the PRD with no code/UI link
6. Dark changes — changed functions with no traceable path to UI/requirements
7. Manual review items
8. Coverage statistics table

Evidence paths must use HUMAN-READABLE labels, not SHA hashes.
Written for a QA lead who understands the product but not the code.

---

## Checkpointing Rules

- Read ALL reference docs before writing any code
- After reading, produce a scope summary (which 2 phases to go deep on,
  what gets cut, why) — wait for approval before coding
- Commit to git after each phase is working and its smoke test passes
- If you hit a bug in the v4 plan not in the bug table above, flag it
  explicitly before patching it — do not silently guess
- If the audit conflicts with the plan, the audit wins
- State every architectural interpretation explicitly before acting on it

---

## Scope Philosophy

"A working narrow slice with honest scope decisions is the strong submission.
Three half-done layers is the weak one." — from the assignment brief.

Quality over coverage. Name every cut. Defend every cut.
The evaluator scores scope honesty higher than scope breadth.

---

## Reference Docs (read in this order)

1. docs/assignment/d0_AI Engineer Updated - Assignment.md          ← source of truth for evaluation
2. docs/implementation_plans/v4_implementation_guide_unified.md    ← architecture to follow
3. docs/audits/v4_audit_report_implementation_plan.md              ← bugs to fix; overrides plan
4. docs/distilled research/d1_documentation.md
5. docs/distilled research/d2_CODING_CONTEXT_v1.md
6. docs/distilled research/d4_blast_radius_analyzer_reference.md
