# AGENTS.md — Blast Radius Analyzer

## Project
Testsigma AI Engineer assignment. Build a 6-phase pipeline that crawls
Documenso, ingests its PRD, builds a Neo4j knowledge graph (Requirements /
UI / Code), and produces a blast radius report for a real PR.

Target app:  https://app.documenso.com
Target repo: https://github.com/documenso/documenso
Pipeline:    Python 3.11+ | TypeScript target app

## Four Deliverables (all required, equal weight)
1. GitHub repo with runnable README end-to-end
2. Design document — 8–12 pages (see design-doc skill)
3. Blast radius report for a real PR — readable by a non-engineer QA lead
4. 5–10 min Loom walkthrough

## Tech Stack
| Component       | Tool                                            |
|-----------------|-------------------------------------------------|
| LLM             | google-generativeai>=0.7.0 / gemini-2.5-flash   |
| LLM wrapper     | blast_radius/llm.py (call_llm / call_llm_json)  |
| Crawler         | Playwright direct (NOT crawl4ai — yanked)       |
| Doc parsing     | Docling >=2.0.0,<3.0                            |
| Static analysis | ast-grep (system binary: brew install ast-grep) |
| PR ingestion    | GitHub API via httpx (NOT PyDriller)            |
| Graph DB        | Neo4j 5.14-community via Docker                 |
| Graph traversal | networkx >=3.2,<4.0                             |
| Embeddings      | sentence-transformers >=2.7.0,<4.0              |
| Reports         | Jinja2 >=3.1.0,<4.0                             |
| Settings        | pydantic-settings >=2.1.0,<3.0                  |

Package layout: FLAT — blast_radius/ at repo root, no src/ wrapper.

## LLM Usage Rule
NEVER call the Gemini API directly in phase code.
ALWAYS import from blast_radius.llm:

    from blast_radius.llm import call_llm, call_llm_json

call_llm(prompt)            → plain text response
call_llm_json(prompt)       → parsed JSON (strips fences, raises ValueError on fail)
call_llm_sync / _json_sync  → use only in smoke tests / non-async contexts

LLM calls happen in: Phase 2 (req extraction), Phase 4 (entity resolution
reranker), Phase 6 (executive summary generation). Do not add LLM calls
outside these phases without explicit approval.

## Non-Negotiables
- Quality over coverage: 2 phases deep beats 6 phases shallow
- Name and defend every scope cut — don't hide them
- No half-built pipelines — working narrow slice only
- Auth credentials are mandatory — unauthenticated crawl breaks Phase 4
- Fix all P0 bugs from the audit before shipping (see audit-guard skill)

## Checkpointing
- Run /scope-first at the start of every session — no code before approval
- Run /phase-checkpoint after each phase passes its smoke test
- Commit to git after each passing phase
- Flag ambiguities explicitly before acting on them — don't silently assume

## Reference Docs (read in this order)
1. docs/assignment/d0_AI Engineer Updated - Assignment.md
2. docs/implementation_plans/v4_implementation_guide_unified.md
3. docs/audits/v4_audit_report_implementation_plan.md
4. docs/distilled research/d1_documentation.md
5. docs/distilled research/d2_CODING_CONTEXT_v1.md
6. docs/distilled research/d4_blast_radius_analyzer_reference.md

## Skills to Load
- blast-radius-domain  — domain concepts, graph schema, PPR logic, report format
- audit-guard          — all P0/P1 bugs with exact fixes (load before any coding)
- design-doc           — section scaffolding for the 8–12 page design document
