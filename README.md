# Blast Radius Analyzer

> Testsigma AI Engineer Assignment — AI-powered change impact analysis for Documenso pull requests.

Given a merged PR in [documenso/documenso](https://github.com/documenso/documenso), this system outputs a **blast radius report**: which UI elements are at risk, which product requirements lose coverage, and which changed functions have no traceable path to any product feature.

---

## How It Works

```
Phase 0 → Skeleton + pre-flight validation
Phase 1 → Playwright crawl of Documenso (auth + unauth flows)
Phase 2 → Docling ingest of README + docs → Requirement nodes
Phase 3 → ast-grep AST extraction + GitHub API PR diff → CodeFunction + PRDelta
Phase 4 → Entity resolution + Neo4j graph build (3 layers: Req / UI / Code)
Phase 5 → Personalized PageRank + DFS → BlastRadiusReport JSON
Phase 6 → Jinja2 render → HTML + Markdown report
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
- `PR_NUMBER` — set to the PR you want to analyze (default: 3046)

### 3. Start Neo4j

```bash
docker compose up -d
# Wait ~15 seconds, then verify:
curl http://localhost:7474
```

### 4. Pick a target PR

```bash
gh auth login
gh pr list --repo documenso/documenso --state merged --limit 20
# Pick a PR that touches packages/trpc/ or packages/lib/server-only/
# Set PR_NUMBER in .env
```

### 5. Clone the Documenso repo

```bash
git clone https://github.com/documenso/documenso data/repos/documenso
```

### 6. Validate setup

```bash
python scripts/validate_env.py
# All checks must pass before running the pipeline
```

---

## Running the Pipeline

Run each phase in order. Each phase must pass its smoke test before proceeding.

```bash
# Run individual phases
python scripts/run_pipeline.py --phase 0   # Validate + scaffold
python scripts/run_pipeline.py --phase 1   # Crawl Documenso
python scripts/run_pipeline.py --phase 2   # Ingest requirements
python scripts/run_pipeline.py --phase 3   # Analyze code + PR
python scripts/run_pipeline.py --phase 4   # Build Neo4j graph
python scripts/run_pipeline.py --phase 5   # Compute blast radius
python scripts/run_pipeline.py --phase 6   # Render report

# Or run all phases sequentially (stops on first failure)
python scripts/run_pipeline.py --all
```

### Expected Phase Output (What PASS Looks Like)

| Phase | PASS indicator |
|-------|---------------|
| Phase 0 | `✓ All environment checks passed` |
| Phase 1 | `Phase 1 crawl completed. Captured N total page snapshots.` (N ≥ 5) |
| Phase 2 | `[ingest] Extracted N requirements` (N ≥ 5) |
| Phase 3 | `[code] Wrote N CodeFunction nodes` + `[code] PR delta: M changed files` |
| Phase 4 | `[resolve] N IMPLEMENTS links: M LLM-confirmed` (N ≥ 1) |
| Phase 5 | `[blast] Wrote blast_radius_report.json: K seeds, J dark changes` |
| Phase 6 | `[report] Wrote blast_radius_report.md` + `blast_radius_report.html` |

### Output

```
data/reports/blast_radius_report.json   # Machine-readable
data/reports/blast_radius_report.md     # Markdown (for GitHub)
data/reports/blast_radius_report.html   # Rendered (open in browser)
```

---

## Running Without a Documenso Account

If you don't have a Documenso account or want to skip the live crawl, use fixture mode:

```bash
# In .env:
CRAWL_USE_FIXTURE=true
```

Fixture mode reads pre-committed page snapshots from `data/crawl/fixtures/` instead of live-crawling. This covers the settings page, document list, and signing flow — enough to demonstrate Phases 4–6 without credentials.

> **Note:** Fixture mode produces a subset of real crawl results. RENDERS edge coverage will be lower than a full auth crawl, but the blast radius analysis (Phases 5–6) runs identically.

---

## Project Structure

```
blast_radius/
├── crawl/          # Phase 1 — Playwright browser agent
├── ingest/         # Phase 2 — Docling PRD parser
├── code/           # Phase 3 — ast-grep + GitHub API
├── graph/          # Phase 4 — Neo4j graph builder
├── reason/         # Phase 5 — PPR + DFS blast radius
└── report/         # Phase 6 — Jinja2 report renderer

data/
├── crawl/          # PageSnapshot JSON (gitignored)
│   └── fixtures/   # Pre-committed snapshots for fixture mode
├── requirements/   # Requirement JSON (gitignored)
├── code/           # CodeFunction + PRDelta JSON (gitignored)
├── reports/        # Final reports (gitignored)
└── repos/          # Cloned Documenso repo (gitignored)

docs/
├── assignment/     # Original Testsigma brief
├── audits/         # Implementation plan audits
├── implementation_plans/  # v1–v4 plans
└── distilled research/    # Research summaries

.agents/
├── skills/         # Antigravity AI skills
└── workflows/      # Antigravity workflows (/scope-first etc.)

rules/              # ast-grep YAML rules (ts-functions.yml etc.)
templates/          # Jinja2 report templates
scripts/            # Pipeline runner + validation
tests/              # Unit + integration tests
```

---

## Scope Decisions

This implementation goes deep on **Phases 3–5** (code analysis, graph build,
blast radius reasoning) and scopes down Phase 1 (crawler depth capped at 20 pages;
fixture mode available for evaluators) and Phase 6 (Markdown report primary, HTML bonus).

See the [design document](docs/design_document.md) for full scope justification.

---

## Design Document

`docs/design_document.md` — 8–12 pages covering:

- Agent decomposition (deterministic vs. LLM-driven boundaries)
- Graph schema with Cypher query justification
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
| `ValidationError: pr_number` | Set `PR_NUMBER` in `.env` before Phase 3 |
| `ValueError: ZERO path matches` | See path alignment fix in audit-guard skill |
| Phase 4 RENDERS count = 0 | Auth crawl failed — check `DOCUMENSO_EMAIL` / `DOCUMENSO_PASSWORD` in `.env`, or set `CRAWL_USE_FIXTURE=true` |
| Phase 1 login timeout | Use `CRAWL_USE_FIXTURE=true` — see "Running Without a Documenso Account" above |

---

## License

MIT
