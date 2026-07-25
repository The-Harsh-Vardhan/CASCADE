# Blast Radius Analyzer

> Testsigma AI Engineer Assignment — AI-powered change impact analysis for Documenso pull requests.

Given a merged PR in [documenso/documenso](https://github.com/documenso/documenso), this system outputs a **blast radius report**: which UI elements are at risk, which product requirements lose coverage, and which changed functions have no traceable path to any product feature.

---

## Quick Start

> **Prerequisite:** the offline pipeline must have been run once to populate the Neo4j graph.
> See [Running the Offline Pipeline](#running-the-offline-pipeline) below.

```bash
# Analyze any Documenso PR:
python run.py https://github.com/documenso/documenso/pull/3046

# Output:
#   outputs/reports/pr_3046_blast_radius.md  ← saved here
#   (full report also printed to terminal)
```

See a real example report: [`blast_radius_report.md`](blast_radius_report.md)

---

## How It Works

```
Offline (one-time setup):
  Phase 1 → Playwright crawl of Documenso (auth + unauth flows)
  Phase 2 → Docling ingest of README + docs → Requirement nodes
  Phase 3 → ast-grep AST extraction → CodeFunction nodes
  Phase 4 → Entity resolution + Neo4j graph build (3 layers: Req / UI / Code)

Online (per PR, run.py):
  parse PR URL → fetch PR diff (GitHub API) → retrieve subgraph →
  Phase 5 (PPR reasoning) → Phase 6 (Jinja2 report render)
```

Each phase reads typed Pydantic models from `data/` and writes typed outputs.
A phase failing its smoke test stops the pipeline — no silent corruption.

---

## Prerequisites

| Requirement | Version | Install |
|-------------|---------|---------|
| Python | 3.11+ | [python.org](https://python.org) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker | latest | [docker.com](https://docker.com) |
| ast-grep | latest | `brew install ast-grep` or [releases](https://github.com/ast-grep/ast-grep/releases) |
| Playwright | via pip | `playwright install chromium` |
| GitHub CLI | latest | `brew install gh` |

---

## Setup

### 1. Clone and install

```bash
git clone https://github.com/The-Harsh-Vardhan/blast-radius-analyzer
cd blast-radius-analyzer
uv pip install -e ".[dev]"
playwright install chromium
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env — fill in ALL values before running any phase
```

Required values in `.env`:

- `GEMINI_API_KEY_1` — get from [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
- `GITHUB_TOKEN` — needs `repo` scope, get from GitHub → Settings → Developer settings
- `DOCUMENSO_EMAIL` + `DOCUMENSO_PASSWORD` — create free account at [app.documenso.com/signup](https://app.documenso.com/signup)
- `NEO4J_PASSWORD` — set to match your `docker-compose.yml` (default: `password`)

### 3. Start Neo4j

```bash
docker compose up -d
# Wait ~15 seconds, then verify:
curl http://localhost:7474
```

### 4. Clone the Documenso repo (for Phase 3 static analysis)

```bash
git clone https://github.com/documenso/documenso data/repos/documenso
```

### 5. Validate setup

```bash
python scripts/validate_env.py
# All checks must pass before running the pipeline
```

---

## Running the Offline Pipeline

The offline pipeline crawls Documenso, extracts requirements, and builds the Neo4j knowledge graph.
Run it **once** before using `run.py`.

```bash
python pipeline/offline.py
```

Or run individual phases:

```bash
python scripts/run_pipeline.py --phase 1   # Crawl Documenso
python scripts/run_pipeline.py --phase 2   # Ingest requirements
python scripts/run_pipeline.py --phase 3   # Analyze code
python scripts/run_pipeline.py --phase 4   # Build Neo4j graph
```

### Expected Phase Output (What PASS Looks Like)

| Phase | PASS indicator |
|-------|---------------|
| Phase 1 | `Phase 1 crawl completed. Captured N total page snapshots.` (N ≥ 5) |
| Phase 2 | `[ingest] Extracted N requirements` (N ≥ 5) |
| Phase 3 | `[code] Wrote N CodeFunction nodes` + `[code] PR delta: M changed files` |
| Phase 4 | `[resolve] N IMPLEMENTS links: M LLM-confirmed` (N ≥ 1) |
| Graph ready | `Graph ready — N nodes loaded.` (N ≥ 100) |

---

## Running Without a Documenso Account

If you don't have a Documenso account or want to skip the live crawl, use fixture mode:

```bash
# In .env:
CRAWL_USE_FIXTURE=true
```

Fixture mode reads pre-committed page snapshots from `data/crawl/fixtures/` instead of live-crawling.
This covers the settings page, document list, and signing flow — enough to demonstrate Phases 4–6 without credentials.

> **Note:** Fixture mode produces a subset of real crawl results. RENDERS edge coverage will be lower than a full auth crawl, but the blast radius analysis (Phases 5–6) runs identically.

---

## Sample Output

A real blast radius report for [PR #3046](https://github.com/documenso/documenso/pull/3046)
(*fix: tighten permission and validation checks*) is committed at:

**[`blast_radius_report.md`](blast_radius_report.md)**

Key findings for PR #3046:
- 1 UI page affected (`/settings/profile`) at medium confidence
- 13 dark changes — security utility functions with no traceable graph path
- 0 requirements directly traced (expected: PR is a permission-hardening change)

---

## Project Structure

```
run.py                   # Entry point — python run.py <github_pr_url>
pipeline/
├── offline.py           # One-time: crawl + ingest + graph build
└── online.py            # Per-PR: fetch diff + PPR reason + render report

blast_radius/
├── crawl/               # Phase 1 — Playwright browser agent
├── ingest/              # Phase 2 — Docling PRD parser
├── code/                # Phase 3 — ast-grep + GitHub API
├── graph/               # Phase 4 — Neo4j graph builder
├── reason/              # Phase 5 — PPR + DFS blast radius
└── report/              # Phase 6 — Jinja2 report renderer

data/
├── crawl/               # PageSnapshot JSON (gitignored)
│   └── fixtures/        # Pre-committed snapshots for fixture mode
├── requirements/        # Requirement JSON (gitignored)
├── code/                # CodeFunction + PRDelta JSON (gitignored)
├── reports/             # Phase 5/6 reports (gitignored)
└── repos/               # Cloned Documenso repo (gitignored)

outputs/
└── reports/             # run.py output — pr_{number}_blast_radius.md

docs/
├── design_document.md   # 8–12 page design document (deliverable)
├── assignment/          # Original Testsigma brief
├── audits/              # Implementation plan audits
└── implementation_plans/

scripts/                 # Pipeline runner, validation, debug utilities
templates/               # Jinja2 report templates
tests/                   # Unit + integration tests
rules/                   # ast-grep YAML rules
```

---

## Scope Decisions

This implementation goes deep on **Phases 3–5** (code analysis, graph build,
blast radius reasoning) and scopes down Phase 1 (crawler depth capped at 20 pages;
fixture mode available for evaluators) and Phase 6 (Markdown report primary, HTML bonus).

See the [design document](docs/design_document.md) for full scope justification.

---

## Design Document

[`docs/design_document.md`](docs/design_document.md) — 8–12 pages covering:

- Agent decomposition (deterministic vs. LLM-driven boundaries)
- Graph schema with Cypher query justification
- UserFlow node modeling and COVERS edge design
- Confidence handling and GapNode modeling
- Eval approach and correctness criteria
- Scope decisions and what comes next

---

## Tests

```bash
pytest tests/unit/          # Fast, no external dependencies
pytest tests/integration/   # Requires Neo4j + .env configured
```

---

## Troubleshooting

| Error | Fix |
|-------|-----|
| `ModuleNotFoundError: blast_radius` | Run `uv pip install -e .` from repo root |
| `playwright._impl._errors.Error: Executable doesn't exist` | Run `playwright install chromium` |
| `neo4j.exceptions.ServiceUnavailable` | Run `docker compose up -d` and wait 15s |
| `Error: Knowledge graph is empty` | Run `python pipeline/offline.py` first |
| `Error: PR #N not found` | Check the URL and that `GITHUB_TOKEN` has `repo` scope |
| `ValueError: ZERO path matches` | See path alignment fix in audit-guard skill |
| Phase 4 RENDERS count = 0 | Auth crawl failed — set `CRAWL_USE_FIXTURE=true` |
| Phase 1 login timeout | Use `CRAWL_USE_FIXTURE=true` — see above |

---

## License

MIT
