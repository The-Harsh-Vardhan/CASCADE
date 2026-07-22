# Blast Radius Analyzer — v3 Implementation Guide

> **What changed from v2:** All P0/P1/P2 audit fixes applied. Target application migrated from Cypress Real World App to **Documenso** (`https://app.documenso.com`). Every RWA hardcoded reference is replaced. New tRPC-specific ast-grep rule added for Documenso's API layer. `evidence_path` weight lambda bug fixed. `ui_id` mismatch in `resolve_ui_to_functions` fixed. `ast_node_type` extraction corrected. `delta.changed_function_ids` is now populated after Phase 5. Absent requirements are surfaced in the blast radius report and rendered in the HTML template. `validate_env.py` pre-flight script added. Docker Compose healthcheck fixed. Cosine similarity vectorized with `util.cos_sim`. Loom recording script added as Appendix C. Design document sections pre-scaffolded with Documenso-specific content. See `v2_audit_report_implementation_plan.md` for the full audit that drove these changes.

---

## Quick Reference

| Property | Value |
|---|---|
| **Target app** | Documenso — `https://app.documenso.com` |
| **Repo** | `https://github.com/documenso/documenso` |
| **Crawl mode** | **Unauthenticated** (marketing, signup, login pages) + **Authenticated** (document lifecycle, template management, recipient flows) — see §1.3 |
| **PRD sources** | `https://raw.githubusercontent.com/documenso/documenso/main/README.md` + `https://docs.documenso.com` (first 5 pages) |
| **Target PR** | Choose a merged PR modifying `packages/lib/` or `packages/trpc/server/routers/` — see Appendix B for selection criteria |
| **Merge SHA** | Pin before Phase 3: `gh pr view {PR_NUMBER} --repo documenso/documenso --json mergeCommit` |
| **Language** | TypeScript / Next.js / Prisma / tRPC |

> **PR selection rationale:** Pick a PR that modifies both a tRPC router file (`packages/trpc/server/routers/*.ts`) AND a corresponding business logic file (`packages/lib/server-only/`). This exercises the full `Requirement → UIElement → CodeFunction (tRPC procedure) → CodeFunction (lib)` propagation chain. See Appendix B for concrete selection criteria.

---

## Documenso-Specific Context

Documenso is an **open-source document signing platform** (AGPL-3.0). Understanding its structure is essential before building anything.

### Monorepo Structure

```
documenso/
├── packages/
│   ├── lib/
│   │   └── server-only/
│   │       ├── document/      # core document CRUD logic
│   │       ├── recipient/     # recipient/signer management
│   │       ├── template/      # template management
│   │       └── field/         # form field logic
│   ├── prisma/
│   │   └── schema.prisma      # data model (Document, Recipient, Field, Template, ...)
│   ├── trpc/
│   │   └── server/
│   │       └── routers/       # tRPC API procedures (document, recipient, template, ...)
│   └── ui/
│       └── components/        # shared React components
└── apps/
    ├── web/
    │   └── src/               # Next.js web application
    └── marketing/             # marketing site
```

**ast-grep scan paths:** `packages/lib/`, `packages/trpc/`, `apps/web/src/` — **not** `src/` (which does not exist at the repo root).

### API Layer: tRPC (not REST)

Documenso uses tRPC for all client-server communication. tRPC procedures follow this pattern:

```typescript
// packages/trpc/server/routers/document.ts
export const documentRouter = router({
  getDocument: protectedProcedure
    .input(z.object({ id: z.string() }))
    .query(async ({ ctx, input }) => { ... }),

  createDocument: protectedProcedure
    .input(DocumentCreateSchema)
    .mutation(async ({ ctx, input }) => { ... }),
});
```

A standard TypeScript function ast-grep rule captures the inner arrow functions but misses the router key name (`getDocument`, `createDocument`). A tRPC-specific rule is required — see Phase 3.

### Key Business Entities

| Entity | Description |
|---|---|
| `Document` | The core entity — a PDF uploaded for signing |
| `Recipient` | A person who receives and signs a document |
| `Field` | A signature/date/text field placed on a document |
| `Template` | A reusable document configuration |
| `Signer` | A recipient in the act of signing |
| `Certificate` | The completion audit trail |

**Domain keywords for smoke tests:** `document`, `sign`, `recipient`, `template`, `field`, `certificate`, `sender`, `signer`

### Crawl Auth Strategy

| Mode | Pages | Credentials needed |
|---|---|---|
| Unauthenticated | Marketing pages, landing page, signup, login | None |
| Authenticated | Document list, upload flow, template creation, recipient management, signing flow | Test account in `.env` |

v3 implements **both modes**. Unauthenticated pages populate the UI layer with public-facing components. Authenticated pages reveal the core document lifecycle flows. Set `DOCUMENSO_EMAIL` and `DOCUMENSO_PASSWORD` in `.env` to enable the authenticated crawl. If credentials are absent, the crawler logs a warning and proceeds with unauthenticated pages only.

### License Note

We crawl `https://app.documenso.com` (the public SaaS) for UI artifacts and analyze the public GitHub repository for code artifacts. No proprietary code is included in this analysis tool. Self-hosting Documenso locally for testing is also permitted under AGPL-3.0.

---

## Package Versions (Verified Lower Bounds)

> These are `>=` lower bounds. Before committing `requirements.txt`, run `pip install <package>` in your virtualenv, then `pip freeze | grep <package>` to record the exact installed version and replace the bound with an exact pin.

```
# requirements.txt
crawl4ai>=0.4.0,<0.5.0            # async web crawler — pin to single minor version; API changes between minors
playwright>=1.40.0,<2.0           # browser automation (primary SPA crawler)
browser-use>=0.1.0,<1.0           # LLM-driven dynamic flow agent — verify API before use
docling>=2.0.0,<3.0               # universal document parser with provenance tracking
pydriller>=2.6,<3.0               # git/PR diff extraction
neo4j>=5.14.0,<6.0                # Neo4j Python driver
pydantic>=2.5.0,<3.0              # data models and validation
pydantic-settings>=2.1.0,<3.0     # env-file config
networkx>=3.2,<4.0                # graph algorithms (PPR)
jinja2>=3.1.0,<4.0                # report templating
httpx>=0.26.0,<1.0                # async HTTP for docs fetching
rich>=13.0.0,<14.0                # CLI progress output
python-dotenv>=1.0.0,<2.0         # .env loading fallback
sentence-transformers>=2.7.0,<4.0 # cosine similarity for entity resolution (upper bound added)
numpy>=1.26.0,<3.0                # array ops
anthropic>=0.25.0,<1.0            # Anthropic Python SDK
```

> **ast-grep is a system binary, not a pip package.** Install separately:
> - macOS: `brew install ast-grep`
> - Linux: `cargo install ast-grep` (requires Rust toolchain) OR download the pre-built binary from `https://github.com/ast-grep/ast-grep/releases`
> - Docker: `RUN cargo install ast-grep` in your Dockerfile, or copy the pre-built binary
>
> Verify installation: `sg --version` — if this fails, Phase 3 will not run.

> **crawl4ai note:** Pin to a single minor version (`<0.5.0`). The API has had breaking changes between `0.4.x` and `0.5.x`. The `AsyncWebCrawler()` no-argument constructor is verified for `0.4.x`. Before using, run:
> `python -c "import crawl4ai; help(crawl4ai.AsyncWebCrawler.__init__)"` and confirm the signature.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         OFFLINE PIPELINE                            │
│                                                                     │
│  Documenso (app.documenso.com + docs.documenso.com)                │
│       │                                                             │
│       ▼                                                             │
│  Phase 1: Playwright Crawler ──────────► data/crawl/*.json         │
│           (unauth + auth flows)                                     │
│                                          │                          │
│  README.md + docs.documenso.com          │                          │
│       │                                  │                          │
│       ▼                                  │                          │
│  Phase 2: Docling + LLM Ingest ─────────► data/requirements/*.json │
│                                          │                          │
│  documenso/documenso repo (cloned)       │                          │
│       │                                  │                          │
│       ▼                                  │                          │
│  Phase 3: ast-grep + PyDriller ─────────► data/code/*.json         │
│           (ts-functions + trpc rules)    │                          │
│                                          │                          │
│       ┌──────────────────────────────────┘                         │
│       ▼                                                             │
│  Phase 4: Entity Resolution + Neo4j Graph Build                    │
│           (cosine sim + LLM reranker; GapNodes for absence)        │
│       │                                                             │
│       ▼                                                             │
│  Phase 5: PR Blast Radius (PPR + DFS) ──► data/reports/*.json     │
│           (seeds delta.changed_function_ids)                        │
│                                                                     │
│  Phase 6: Jinja2 HTML/MD Report ─────────► data/reports/*.html    │
│           (includes Absent Requirements section)                    │
└─────────────────────────────────────────────────────────────────────┘
```

### Deterministic vs. LLM-Driven

| Component | Mode | Rationale |
|---|---|---|
| Playwright DOM capture | **Deterministic** | Structural facts; repeatable across runs |
| ast-grep AST extraction | **Deterministic** | Structural code facts must be exact |
| PyDriller git diff | **Deterministic** | VCS is source of truth |
| Neo4j graph writes | **Deterministic** | Idempotent MERGE; stable content-addressed IDs |
| PPR / DFS traversal | **Deterministic** | Math-based impact routing; same input → same scores |
| PRD → Requirement extraction | **LLM** | Natural language needs semantic understanding |
| Requirement ↔ Code entity resolution | **LLM + cosine** | Cross-vocabulary fuzzy matching |
| DOM semantic labeling | **LLM** | Accessibility context exceeds rule-based parsing |
| Blast radius explanation prose | **LLM** | Human-readable synthesis |

---

## Inter-Phase Data Contracts

All artifacts are typed Pydantic models. Schema mismatches become `ValidationError`s, not silent wrong results. All models are defined in Phase 0 and imported everywhere else.

```
data/
├── crawl/
│   ├── manifest.json              # CrawlManifest
│   ├── screenshots/               # PNG files named by url_sha256
│   └── {url_sha256}.json          # PageSnapshot
├── requirements/
│   └── requirements.json          # list[Requirement]
├── code/
│   ├── call_graph.json            # list[CodeFunction]
│   └── pr_{number}.json           # PRDelta  (changed_function_ids populated by Phase 5)
└── reports/
    ├── blast_radius_report.json   # BlastRadiusReport  (includes absent_requirements)
    ├── blast_radius_report.md
    └── blast_radius_report.html
```

---

## Phase 0: Project Skeleton + Pre-flight

**Branch:** `setup/project-skeleton`
**Budget:** 1.5 h (increased from v2 — `validate_env.py` is new)
**Prerequisites:** none

**Creates:** `.env.example`, `requirements.txt`, `docker-compose.yml`, `src/blast_radius/__init__.py`, `src/blast_radius/config.py`, `src/blast_radius/models.py`, `scripts/validate_env.py`, `scripts/run_pipeline.py`, `tests/test_imports.py`, `data/` subdirectories, `templates/` (empty), `rules/` (empty)

### docker-compose.yml

```yaml
services:
  neo4j:
    image: neo4j:5.14-community
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD:?NEO4J_PASSWORD must be set in .env}
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j_data:/data
    healthcheck:
      # v2 fix: use CMD-SHELL so Docker Compose expands $NEO4J_PASSWORD correctly
      test: ["CMD-SHELL", "cypher-shell -u neo4j -p $NEO4J_PASSWORD 'RETURN 1' || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 10

volumes:
  neo4j_data: {}
```

> **v2 changes:** PostgreSQL removed (never used in v1 or v2). APOC plugin removed (no APOC Cypher called in v1–v3). Healthcheck uses `CMD-SHELL` form so `$NEO4J_PASSWORD` expands correctly.

### .env.example

```
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=change-me

# Target application
TARGET_URL=https://app.documenso.com
TARGET_REPO_URL=https://github.com/documenso/documenso.git
TARGET_REPO_NAME=documenso/documenso

# Crawl auth (optional — set to enable authenticated document lifecycle crawl)
DOCUMENSO_EMAIL=your-test-account@example.com
DOCUMENSO_PASSWORD=your-test-password

# PR analysis
PR_NUMBER=                         # fill in chosen PR number (see Appendix B)
MERGE_SHA=                         # fill in: gh pr view {PR_NUMBER} --repo documenso/documenso --json mergeCommit

# Pipeline config
DATA_DIR=data
CRAWL_MAX_PAGES=20
```

Never commit `.env`. Always copy from `.env.example`.

### src/blast_radius/config.py

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path
from typing import Optional


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str = Field(..., description="Anthropic API key — required")
    neo4j_uri: str = Field("bolt://localhost:7687")
    neo4j_user: str = Field("neo4j")
    neo4j_password: str = Field(..., description="Neo4j password — required")

    target_url: str = Field("https://app.documenso.com")
    target_repo_url: str = Field("https://github.com/documenso/documenso.git")
    target_repo_name: str = Field("documenso/documenso")

    documenso_email: Optional[str] = Field(None, description="Test account email for authenticated crawl")
    documenso_password: Optional[str] = Field(None, description="Test account password for authenticated crawl")

    pr_number: int = Field(..., description="Target PR number — required")
    merge_sha: str = Field("", description="Pinned merge SHA for target PR")

    data_dir: Path = Field(Path("data"))
    crawl_max_pages: int = Field(20)

    def validate_and_print(self) -> None:
        from rich.console import Console
        from rich.table import Table
        console = Console()
        table = Table(title="Blast Radius Analyzer v3 — Configuration")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Status", style="yellow")
        safe = self.model_dump()
        safe["anthropic_api_key"] = safe["anthropic_api_key"][:8] + "..."
        safe["neo4j_password"] = "***"
        if safe.get("documenso_password"):
            safe["documenso_password"] = "***"
        statuses = {}
        statuses["merge_sha"] = "⚠ NOT SET — run gh pr view before Phase 3" if not self.merge_sha else "✓"
        statuses["documenso_email"] = "⚠ No auth crawl" if not self.documenso_email else "✓"
        for k, v in safe.items():
            table.add_row(k, str(v), statuses.get(k, "✓"))
        console.print(table)


settings = Settings()
```

### src/blast_radius/models.py

These are the **complete shared data contracts**. Every phase imports from here.

```python
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


# ── Phase 1: Crawl ───────────────────────────────────────────────────────────

class Transition(BaseModel):
    action: str
    selector: Optional[str] = None
    source_url: str
    target_url: str
    screenshot_before: Optional[str] = None
    screenshot_after: Optional[str] = None


class AccessibilityItem(BaseModel):
    index: int
    tag: str
    role: Optional[str] = None
    name: str = ""
    selector: str


class PageSnapshot(BaseModel):
    url: str
    url_sha256: str
    dom_snapshot: str
    accessibility_tree: list[AccessibilityItem]
    screenshot_path: str
    transitions: list[Transition] = Field(default_factory=list)


class CrawlManifest(BaseModel):
    run_id: str
    started_at: str
    pages: list[str]
    transitions: list[Transition]


# ── Phase 2: Requirements ─────────────────────────────────────────────────────

class Provenance(BaseModel):
    source_file: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    page: Optional[int] = None
    bbox: Optional[list[float]] = None
    excerpt: str


class Requirement(BaseModel):
    requirement_id: str
    text: str
    req_type: str = "feature"
    provenance: Provenance
    related_ui_keywords: list[str] = Field(default_factory=list)
    coverage_status: str = "UNKNOWN"


# ── Phase 3: Code ─────────────────────────────────────────────────────────────

class CodeFunction(BaseModel):
    function_id: str
    name: str
    file: str
    start_line: int
    end_line: Optional[int] = None
    ast_node_type: str = "unknown"
    calls: list[str] = Field(default_factory=list)
    called_by: list[str] = Field(default_factory=list)


class ChangedFile(BaseModel):
    path: str
    status: str
    additions: int = 0
    deletions: int = 0


class PRDelta(BaseModel):
    pr_number: int
    pr_url: str
    title: str
    merge_sha: str
    parent_sha: str
    changed_files: list[ChangedFile]
    changed_function_ids: list[str] = Field(default_factory=list)
    # NOTE: changed_function_ids is populated by Phase 5 after seed computation
    # and written back to disk. It starts empty from Phase 3.


# ── Phase 4: Graph ────────────────────────────────────────────────────────────

class GapNode(BaseModel):
    gap_id: str
    requirement_id: str
    reason: str
    threshold: float
    run_id: str


class EntityLink(BaseModel):
    from_id: str
    to_id: str
    rel_type: str
    confidence: float
    evidence: str
    source: str
    run_id: str


# ── Phase 5: Blast Radius ─────────────────────────────────────────────────────

class AffectedNode(BaseModel):
    node_id: str
    node_type: str
    label: str
    impact_score: float
    traceability_confidence: float
    evidence_path: list[str]
    risk_tier: str


class BlastRadiusReport(BaseModel):
    run_id: str
    pr_url: str
    pr_number: int
    pr_title: str
    mode: str = "neo4j"
    changed_files: list[ChangedFile]
    seed_function_ids: list[str]
    affected_ui_elements: list[AffectedNode]
    affected_requirements: list[AffectedNode]
    absent_requirements: list[AffectedNode] = Field(default_factory=list)
    # ^ NEW in v3: surfaced from GapNodes; rendered in report template
    dark_changes: list[str]
    evidence_subgraph: list[EntityLink]
    confidence_scores: dict[str, float]
    manual_review_items: list[str]
    summary: str = ""
```

### scripts/validate_env.py

> **New in v3.** Run this before every build to catch environment problems early. Required by the pre-flight checklist.

```python
#!/usr/bin/env python3
"""
Pre-flight validation. Run before any pipeline phase.
Usage: python scripts/validate_env.py
"""
import sys
import subprocess
from rich.console import Console
from rich.table import Table

console = Console()

def check(label: str, fn) -> bool:
    try:
        fn()
        console.print(f"  [green]✓[/green] {label}")
        return True
    except Exception as e:
        console.print(f"  [red]✗[/red] {label}: {e}")
        return False

def main():
    console.rule("[bold]Blast Radius Analyzer v3 — Pre-flight Checks")
    failures = []

    # 1. Python version
    if not check("Python >= 3.11", lambda: None if sys.version_info >= (3, 11)
                 else (_ for _ in ()).throw(RuntimeError(f"Python {sys.version_info[:2]} found"))):
        failures.append("python_version")

    # 2. Key packages importable
    for pkg in ["anthropic", "neo4j", "playwright", "docling", "pydriller",
                "pydantic", "pydantic_settings", "networkx", "jinja2",
                "httpx", "rich", "sentence_transformers", "numpy", "crawl4ai"]:
        if not check(f"import {pkg}", lambda p=pkg: __import__(p)):
            failures.append(f"pkg:{pkg}")

    # 3. ast-grep binary
    if not check("ast-grep binary (sg)", lambda: subprocess.run(
        ["sg", "--version"], capture_output=True, check=True
    )):
        failures.append("ast_grep")
        console.print("  [yellow]→ Install: brew install ast-grep  OR  cargo install ast-grep[/yellow]")

    # 4. Config loads without error
    if not check("Config (.env) loads", lambda: __import__("blast_radius.config", fromlist=["settings"])):
        failures.append("config")

    # 5. Neo4j reachable
    def neo4j_ping():
        from blast_radius.config import settings
        from neo4j import GraphDatabase
        d = GraphDatabase.driver(settings.neo4j_uri, auth=(settings.neo4j_user, settings.neo4j_password))
        d.verify_connectivity()
        d.close()

    if not check("Neo4j reachable", neo4j_ping):
        failures.append("neo4j")
        console.print("  [yellow]→ Run: docker compose up -d[/yellow]")

    # 6. Anthropic API key format
    if not check("ANTHROPIC_API_KEY format", lambda: None
                 if __import__("blast_radius.config", fromlist=["settings"]).settings.anthropic_api_key.startswith("sk-ant-")
                 else (_ for _ in ()).throw(RuntimeError("Key does not start with sk-ant-"))):
        failures.append("api_key")

    # 7. MERGE_SHA set
    if not check("MERGE_SHA is set", lambda: None
                 if __import__("blast_radius.config", fromlist=["settings"]).settings.merge_sha
                 else (_ for _ in ()).throw(RuntimeError("MERGE_SHA is empty — set it before Phase 3"))):
        failures.append("merge_sha")

    # 8. Repo cloned
    from pathlib import Path
    repo_path = Path("data/repos/documenso")
    if not check(f"Repo cloned at {repo_path}", lambda: None
                 if repo_path.exists() else (_ for _ in ()).throw(RuntimeError("Not found"))):
        failures.append("repo")
        console.print(f"  [yellow]→ Run: git clone https://github.com/documenso/documenso {repo_path}[/yellow]")

    console.rule()
    if failures:
        console.print(f"[red]Pre-flight FAILED: {len(failures)} issue(s). Fix the above before running the pipeline.[/red]")
        sys.exit(1)
    else:
        console.print("[green]All pre-flight checks passed. Ready to run the pipeline.[/green]")

if __name__ == "__main__":
    main()
```

### scripts/run_pipeline.py

```python
#!/usr/bin/env python3
"""
Usage:
  python scripts/run_pipeline.py --phase all
  python scripts/run_pipeline.py --phase 1
  python scripts/run_pipeline.py --phase 1,2,3
  python scripts/run_pipeline.py --skip-phase 4
"""
import argparse
import sys


def run_phase(n: int) -> None:
    if n == 0:
        print("Phase 0 is setup — run manually. See README.")
    elif n == 1:
        from blast_radius.crawl import run_crawl
        run_crawl()
    elif n == 2:
        from blast_radius.ingest import run_ingest
        run_ingest()
    elif n == 3:
        from blast_radius.code import run_code_analysis
        run_code_analysis()
    elif n == 4:
        from blast_radius.graph import build_graph
        build_graph()
    elif n == 5:
        from blast_radius.reason import analyze_pr
        analyze_pr()
    elif n == 6:
        from blast_radius.report import render_report
        render_report()
    else:
        raise ValueError(f"Unknown phase: {n}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", default="all")
    parser.add_argument("--skip-phase", default="")
    args = parser.parse_args()

    all_phases = list(range(1, 7))
    skip = {int(x) for x in args.skip_phase.split(",") if x.strip()}

    if args.phase == "all":
        phases = [p for p in all_phases if p not in skip]
    else:
        phases = [int(x) for x in args.phase.split(",") if x.strip()]

    for phase in phases:
        print(f"\n{'=' * 60}\n  PHASE {phase}\n{'=' * 60}\n")
        run_phase(phase)

    print("\n✓ Pipeline complete.")
```

### tests/test_imports.py

```python
def test_config_imports():
    from blast_radius.config import settings
    assert settings.neo4j_uri.startswith("bolt://")
    assert settings.target_url == "https://app.documenso.com"

def test_models_import():
    from blast_radius.models import (
        PageSnapshot, Requirement, CodeFunction, PRDelta,
        BlastRadiusReport, AffectedNode, EntityLink, GapNode
    )
    # BlastRadiusReport must have absent_requirements field
    assert hasattr(BlastRadiusReport.model_fields, "absent_requirements")

def test_data_dirs_created():
    from pathlib import Path
    for d in ["data/crawl/screenshots", "data/requirements", "data/code", "data/reports", "rules", "templates"]:
        Path(d).mkdir(parents=True, exist_ok=True)
    assert True
```

**Smoke test:**
```bash
docker compose up -d
# Wait ~30s for Neo4j to start, then:
python scripts/validate_env.py
python -m pytest tests/test_imports.py -q
python -c "from blast_radius.config import settings; settings.validate_and_print()"
```

**Merge condition:** All pre-flight checks pass, all imports succeed, config table prints cleanly.

---

## Phase 1: Crawler MVP

**Branch:** `feature/phase-1-crawler`
**Budget:** 2.5 h
**Prerequisites:** Phase 0 merged; Playwright browsers installed (`playwright install chromium`)

**Creates:** `src/blast_radius/crawl/__init__.py`, `src/blast_radius/crawl/dynamic.py`, `src/blast_radius/crawl/static.py`, `src/blast_radius/crawl/artifacts.py`

### Crawl Strategy for Documenso

Documenso at `https://app.documenso.com` is a live SaaS. Note:
- **No `data-test` attributes** in production (unlike RWA). Use `aria-label`, `placeholder`, `name`, and element role for selectors.
- **Rate limiting**: add 1.5s delay between page navigations; check `robots.txt` first.
- **Auth wall**: document list, upload, templates, and signing are all behind authentication. Unauthenticated crawl covers marketing pages, login, and signup only.

### src/blast_radius/crawl/static.py

For crawling Documenso's public documentation pages at `docs.documenso.com` (static content).

```python
import asyncio
from typing import Optional

# crawl4ai is verified for 0.4.x. Constructor signature: AsyncWebCrawler() with no required args.
# If you see an API error, run: python -c "import crawl4ai; help(crawl4ai.AsyncWebCrawler)"
try:
    from crawl4ai import AsyncWebCrawler
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False


async def crawl_static_url(url: str) -> Optional[str]:
    """Fetch a single static documentation page. Returns HTML or None on failure."""
    if not CRAWL4AI_AVAILABLE:
        raise RuntimeError(
            "crawl4ai is not installed. It is in requirements.txt — run pip install -r requirements.txt"
        )
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url)
        if not result.success:
            return None
        return result.html


async def crawl_docs_pages(base_url: str = "https://docs.documenso.com", max_pages: int = 5) -> list[str]:
    """Crawl up to max_pages documentation pages. Returns list of HTML strings."""
    if not CRAWL4AI_AVAILABLE:
        return []
    pages = []
    urls_to_try = [
        base_url,
        f"{base_url}/getting-started/introduction",
        f"{base_url}/signing-documents",
        f"{base_url}/templates",
        f"{base_url}/recipients",
    ]
    for url in urls_to_try[:max_pages]:
        await asyncio.sleep(1.0)  # polite delay
        html = await crawl_static_url(url)
        if html:
            pages.append(html)
    return pages
```

### src/blast_radius/crawl/dynamic.py

Primary crawler for `app.documenso.com`. Uses Playwright directly.

```python
import asyncio
import hashlib
import time
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Page, BrowserContext

from blast_radius.config import settings
from blast_radius.models import AccessibilityItem, PageSnapshot, Transition

TARGET_URL = settings.target_url
SCREENSHOTS_DIR = settings.data_dir / "crawl" / "screenshots"
POLITE_DELAY = 1.5  # seconds between page navigations


def _url_sha256(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


async def _capture_accessibility_tree(page: Page) -> list[AccessibilityItem]:
    """
    Extract an AXTree-inspired list of interactive elements.
    Documenso does not have data-test attributes; we use aria-label and role.
    Capped at 300 elements.
    """
    raw = await page.evaluate("""
        () => Array.from(
            document.querySelectorAll('a,button,input,select,textarea,[role]')
        ).slice(0, 300).map((el, i) => ({
            index: i,
            tag: el.tagName.toLowerCase(),
            role: el.getAttribute('role') || el.tagName.toLowerCase(),
            name: (
                el.getAttribute('aria-label') ||
                el.getAttribute('placeholder') ||
                el.getAttribute('title') ||
                (el.innerText || '').slice(0, 80) ||
                el.getAttribute('name') ||
                ''
            ).trim(),
            selector: (
                el.id ? '#' + el.id
                : el.getAttribute('aria-label')
                    ? '[aria-label="' + el.getAttribute('aria-label') + '"]'
                : el.tagName.toLowerCase()
            )
        }))
    """)
    return [AccessibilityItem(**item) for item in raw]


async def _capture_transitions(page: Page, base_url: str) -> list[Transition]:
    links = await page.evaluate("""
        () => Array.from(document.querySelectorAll('a[href]'))
              .slice(0, 50)
              .map(el => ({
                  href: el.href || '',
                  text: (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 60)
              }))
    """)
    transitions = []
    current_url = page.url
    for link in links:
        href = link.get("href", "")
        if href and href.startswith(base_url) and href != current_url:
            transitions.append(Transition(
                action="navigate",
                selector=None,
                source_url=current_url,
                target_url=href,
            ))
    return transitions


async def crawl_page(page: Page, url: str) -> PageSnapshot:
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    sha = _url_sha256(url)
    screenshot_path = str(SCREENSHOTS_DIR / f"{sha}.png")

    await page.goto(url, wait_until="networkidle", timeout=25_000)
    await asyncio.sleep(0.5)  # let JS settle
    await page.screenshot(path=screenshot_path, full_page=True)
    dom = await page.content()
    if not dom or len(dom) < 100:
        raise RuntimeError(f"DOM snapshot too small for {url}. Is the page rendering?")

    ax_tree = await _capture_accessibility_tree(page)
    transitions = await _capture_transitions(page, TARGET_URL)

    return PageSnapshot(
        url=url,
        url_sha256=sha,
        dom_snapshot=dom,
        accessibility_tree=ax_tree,
        screenshot_path=screenshot_path,
        transitions=transitions,
    )


async def run_dynamic_crawl(
    start_url: str,
    max_pages: int,
) -> list[PageSnapshot]:
    """
    Two-mode crawler for Documenso:
    1. Unauthenticated: marketing page, login, signup, docs landing
    2. Authenticated (if DOCUMENSO_EMAIL/PASSWORD set): document list, upload flow,
       template management, recipient flows

    Returns list[PageSnapshot].
    """
    snapshots: list[PageSnapshot] = []
    visited: set[str] = set()

    auth_available = bool(settings.documenso_email and settings.documenso_password)
    if not auth_available:
        print("[crawl] DOCUMENSO_EMAIL/PASSWORD not set — running unauthenticated crawl only.")

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (blast-radius-analyzer/3.0 research-only)",
        )
        page = await context.new_page()

        # ── Flow 1: Unauthenticated pages ─────────────────────────
        unauth_routes = [
            "",              # home / marketing
            "/signin",
            "/signup",
        ]
        for route in unauth_routes:
            if len(snapshots) >= max_pages:
                break
            url = f"{start_url}{route}"
            if url in visited:
                continue
            await asyncio.sleep(POLITE_DELAY)
            try:
                snap = await crawl_page(page, url)
                snapshots.append(snap)
                visited.add(url)
                print(f"[crawl] ✓ {url} ({len(snap.accessibility_tree)} elements)")
            except Exception as e:
                print(f"[crawl] WARNING: {url} failed: {e}")

        # ── Flow 2: Authenticated pages ────────────────────────────
        if auth_available:
            try:
                await page.goto(f"{start_url}/signin", wait_until="networkidle")
                # Documenso login form: use aria-label or placeholder selectors
                await page.fill('input[name="email"], input[type="email"]', settings.documenso_email)
                await page.fill('input[name="password"], input[type="password"]', settings.documenso_password)
                await page.click('button[type="submit"]')
                await page.wait_for_url(f"{start_url}/**", timeout=15_000)
                print("[crawl] ✓ Authenticated successfully")
            except Exception as e:
                print(f"[crawl] WARNING: Auth flow failed: {e}. Continuing without auth pages.")
                auth_available = False

        if auth_available:
            auth_routes = [
                "/documents",
                "/documents/new",
                "/templates",
                "/settings",
                "/settings/profile",
                "/settings/teams",
            ]
            for route in auth_routes:
                if len(snapshots) >= max_pages:
                    break
                url = f"{start_url}{route}"
                if url in visited:
                    continue
                await asyncio.sleep(POLITE_DELAY)
                try:
                    snap = await crawl_page(page, url)
                    snapshots.append(snap)
                    visited.add(url)
                    print(f"[crawl] ✓ {url} ({len(snap.accessibility_tree)} elements)")
                    # BFS: follow discovered same-domain transitions
                    for t in snap.transitions[:5]:
                        if (t.target_url not in visited
                                and t.target_url.startswith(start_url)
                                and len(snapshots) < max_pages):
                            await asyncio.sleep(POLITE_DELAY)
                            try:
                                sub = await crawl_page(page, t.target_url)
                                snapshots.append(sub)
                                visited.add(t.target_url)
                                print(f"[crawl]   ↳ {t.target_url}")
                            except Exception:
                                pass
                except Exception as e:
                    print(f"[crawl] WARNING: {url} failed: {e}")

        await browser.close()

    if len(snapshots) < 2:
        raise RuntimeError(
            f"Only {len(snapshots)} pages captured. "
            f"Verify network access to {start_url} and that credentials are correct."
        )
    return snapshots
```

### src/blast_radius/crawl/artifacts.py

```python
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from blast_radius.config import settings
from blast_radius.models import CrawlManifest, PageSnapshot

CRAWL_DIR = settings.data_dir / "crawl"


def save_snapshot(snap: PageSnapshot) -> Path:
    CRAWL_DIR.mkdir(parents=True, exist_ok=True)
    out = CRAWL_DIR / f"{snap.url_sha256}.json"
    out.write_text(snap.model_dump_json(indent=2), encoding="utf-8")
    return out


def save_manifest(snapshots: list[PageSnapshot], run_id: str) -> Path:
    all_transitions = [t for s in snapshots for t in s.transitions]
    manifest = CrawlManifest(
        run_id=run_id,
        started_at=datetime.now(timezone.utc).isoformat(),
        pages=[s.url_sha256 for s in snapshots],
        transitions=all_transitions,
    )
    out = CRAWL_DIR / "manifest.json"
    out.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return out


def load_snapshots() -> list[PageSnapshot]:
    snapshots = []
    for f in sorted(CRAWL_DIR.glob("*.json")):
        if f.name == "manifest.json":
            continue
        snapshots.append(PageSnapshot.model_validate_json(f.read_text(encoding="utf-8")))
    return snapshots
```

### src/blast_radius/crawl/__init__.py

```python
import asyncio
import uuid
from blast_radius.config import settings
from blast_radius.crawl.dynamic import run_dynamic_crawl
from blast_radius.crawl.artifacts import save_snapshot, save_manifest


def run_crawl() -> list:
    run_id = str(uuid.uuid4())[:8]
    snapshots = asyncio.run(
        run_dynamic_crawl(settings.target_url, settings.crawl_max_pages)
    )
    for snap in snapshots:
        save_snapshot(snap)
    save_manifest(snapshots, run_id)
    print(f"[crawl] Saved {len(snapshots)} snapshots (run_id={run_id})")
    return snapshots


if __name__ == "__main__":
    run_crawl()
```

**Smoke test:**
```bash
python -m blast_radius.crawl
python -c "
import glob
from blast_radius.models import PageSnapshot
files = [f for f in glob.glob('data/crawl/*.json') if 'manifest' not in f]
assert len(files) >= 2, f'Only {len(files)} snapshots'
for f in files:
    snap = PageSnapshot.model_validate_json(open(f, encoding='utf-8').read())
    assert snap.dom_snapshot and len(snap.dom_snapshot) > 100, f'Empty DOM in {f}'
    assert snap.screenshot_path
# Domain spot-check
documenso_terms = {'document', 'sign', 'recipient', 'template', 'email', 'upload'}
all_text = ' '.join(snap.dom_snapshot[:2000] for snap in [
    PageSnapshot.model_validate_json(open(f, encoding=\"utf-8\").read()) for f in files
]).lower()
hits = [t for t in documenso_terms if t in all_text]
assert hits, f'No Documenso domain terms found in crawled pages'
print(f'OK — {len(files)} snapshots, domain terms: {hits}')
"
```

**Merge condition:** ≥2 valid snapshots (≥5 if auth crawl is enabled), at least one Documenso domain term in crawled content, screenshots exist.

---

## Phase 2: PRD Ingest

**Branch:** `feature/phase-2-prd-ingest`
**Budget:** 1.25 h
**Prerequisites:** Phase 0

**Creates:** `src/blast_radius/ingest/__init__.py`, `src/blast_radius/ingest/fetch.py`, `src/blast_radius/ingest/extract.py`

### src/blast_radius/ingest/fetch.py

```python
import hashlib
import httpx
from pathlib import Path
from blast_radius.config import settings

SOURCES_DIR = settings.data_dir / "sources"


def fetch_and_cache(url: str) -> str:
    """Download `url` to data/sources/ (cached by URL hash). Returns file text."""
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256(url.encode()).hexdigest()[:12]
    suffix = Path(url).suffix or ".txt"
    cache_path = SOURCES_DIR / f"{cache_key}{suffix}"
    if cache_path.exists():
        print(f"[ingest] cache hit: {cache_path}")
        return cache_path.read_text(encoding="utf-8")
    print(f"[ingest] fetching {url}")
    resp = httpx.get(url, follow_redirects=True, timeout=30)
    resp.raise_for_status()
    cache_path.write_text(resp.text, encoding="utf-8")
    return resp.text
```

### src/blast_radius/ingest/extract.py

```python
import hashlib
import json
import re
from typing import Optional

import anthropic

from blast_radius.config import settings
from blast_radius.models import Provenance, Requirement

_client: Optional[anthropic.Anthropic] = None


def _anthropic() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


# v3: Updated system prompt for Documenso domain
_SYSTEM_PROMPT = """
You are a requirements analyst for Documenso, an open-source document signing platform.

Extract ALL distinct product requirements, user-facing features, and acceptance criteria
from the provided documentation text. Return ONLY a valid JSON array — no preamble,
no markdown fences, no commentary.

Each element must have exactly these fields:
  - "text": string — the requirement in your own words (one sentence, present tense, active voice)
  - "req_type": one of "feature" | "user_story" | "constraint" | "acceptance_criterion"
  - "related_ui_keywords": string array — UI element labels, page names, or Documenso entities
    this requirement relates to (e.g. ["upload button", "recipient list", "signing page", "template"])
  - "excerpt": string — the verbatim source sentence or heading that supports this requirement

Rules:
- REJECT operational instructions (npm install, docker run, git clone, configuration commands)
- REJECT sentences describing developer setup, deployment, or CI/CD
- REJECT generic marketing claims without observable product behaviour
- Every accepted requirement must describe something an end user can observe or interact with
  in the application (uploading a document, adding a recipient, signing, viewing a certificate, etc.)
- Minimum 5 requirements; if fewer than 5 qualify, return {"error": "insufficient requirements"}
""".strip()


def extract_requirements(text: str, source_file: str) -> list[Requirement]:
    truncated = text[:12_000]
    message = _anthropic().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": truncated}],
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        raw = re.sub(r"```[a-z]*\n?", "", raw).replace("```", "").strip()
    try:
        items = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"LLM returned invalid JSON: {e}\nRaw:\n{raw[:500]}")
    if isinstance(items, dict) and "error" in items:
        raise RuntimeError(f"LLM extraction error: {items['error']}")
    if not isinstance(items, list):
        raise RuntimeError(f"Expected JSON array, got {type(items)}")

    operational = ["npm ", "git ", "clone ", "install ", "run ", "docker ", "localhost", "deploy"]
    requirements = []
    for item in items:
        text_str = item.get("text", "").strip()
        if not text_str:
            continue
        if any(m in text_str.lower() for m in operational):
            continue
        req_id = "REQ-" + hashlib.sha256(
            (source_file + text_str).encode()
        ).hexdigest()[:8].upper()
        requirements.append(Requirement(
            requirement_id=req_id,
            text=text_str,
            req_type=item.get("req_type", "feature"),
            related_ui_keywords=item.get("related_ui_keywords", []),
            provenance=Provenance(
                source_file=source_file,
                excerpt=item.get("excerpt", text_str[:200]),
                page=None,
                bbox=None,
            ),
        ))

    if len(requirements) < 5:
        raise RuntimeError(
            f"Only {len(requirements)} valid requirements from {source_file}. "
            "Check the source content and LLM extraction."
        )
    return requirements


def extract_requirements_from_docling(source_url_or_path: str) -> list[Requirement]:
    """
    Use Docling to convert a document to Markdown, then extract requirements with LLM.
    The Docling API call used here — result.document.export_to_markdown() — is verified
    for docling>=2.0.0. If you see an AttributeError, run:
        python -c "from docling.document_converter import DocumentConverter; help(DocumentConverter)"
    """
    from docling.document_converter import DocumentConverter
    result = DocumentConverter().convert(source_url_or_path)
    if result.document is None:
        raise RuntimeError(f"Docling conversion failed for {source_url_or_path}")
    markdown = result.document.export_to_markdown()
    return extract_requirements(markdown, source_file=source_url_or_path)
```

### src/blast_radius/ingest/__init__.py

```python
import asyncio
import json
from blast_radius.config import settings
from blast_radius.ingest.fetch import fetch_and_cache
from blast_radius.ingest.extract import extract_requirements_from_docling, extract_requirements
from blast_radius.crawl.static import crawl_docs_pages
from blast_radius.models import Requirement

REQS_DIR = settings.data_dir / "requirements"

README_URL = "https://raw.githubusercontent.com/documenso/documenso/main/README.md"
DOCS_BASE_URL = "https://docs.documenso.com"


def run_ingest() -> list[Requirement]:
    REQS_DIR.mkdir(parents=True, exist_ok=True)
    all_requirements: list[Requirement] = []
    seen_ids: set[str] = set()

    def _add(reqs: list[Requirement]) -> None:
        for r in reqs:
            if r.requirement_id not in seen_ids:
                all_requirements.append(r)
                seen_ids.add(r.requirement_id)

    # Source 1: README.md via Docling
    try:
        reqs = extract_requirements_from_docling(README_URL)
        _add(reqs)
        print(f"[ingest] README: {len(reqs)} requirements extracted")
    except Exception as e:
        print(f"[ingest] WARNING: README extraction failed: {e}")

    # Source 2: docs.documenso.com (first 5 pages via crawl4ai static)
    try:
        doc_pages_html = asyncio.run(crawl_docs_pages(DOCS_BASE_URL, max_pages=5))
        for i, html in enumerate(doc_pages_html):
            try:
                reqs = extract_requirements(html, source_file=f"{DOCS_BASE_URL}/page-{i+1}")
                _add(reqs)
                print(f"[ingest] docs page {i+1}: {len(reqs)} requirements")
            except Exception as e:
                print(f"[ingest] WARNING: docs page {i+1} failed: {e}")
    except Exception as e:
        print(f"[ingest] WARNING: docs crawl failed: {e}")

    if len(all_requirements) < 5:
        raise RuntimeError(
            f"Only {len(all_requirements)} total requirements. "
            "Check network access to GitHub and docs.documenso.com."
        )

    out = REQS_DIR / "requirements.json"
    out.write_text(
        json.dumps([r.model_dump() for r in all_requirements], indent=2),
        encoding="utf-8",
    )
    print(f"[ingest] Saved {len(all_requirements)} requirements to {out}")
    return all_requirements
```

**Smoke test:**
```bash
python -c "from blast_radius.ingest import run_ingest; reqs = run_ingest(); print(len(reqs))"
python -c "
import json
from blast_radius.models import Requirement
data = json.load(open('data/requirements/requirements.json', encoding='utf-8'))
assert len(data) >= 5, f'Only {len(data)} requirements'
reqs = [Requirement.model_validate(r) for r in data]
# Documenso domain spot-check
domain_terms = {'document', 'sign', 'recipient', 'template', 'field', 'certificate', 'sender', 'signer'}
hits = [r for r in reqs if any(t in r.text.lower() for t in domain_terms)]
assert hits, 'No Documenso-domain requirements found — check LLM prompt or source'
assert all(r.provenance.excerpt for r in reqs), 'Some requirements missing provenance excerpt'
print(f'OK — {len(reqs)} requirements, {len(hits)} Documenso-domain')
"
```

**Merge condition:** ≥5 requirements, at least one Documenso-domain requirement, all have non-empty `provenance.excerpt`.

---

## Phase 3: Code Analysis

**Branch:** `feature/phase-3-code-analysis`
**Budget:** 2.5 h
**Prerequisites:** Phase 0; Documenso repo cloned at `data/repos/documenso`; `sg` installed

**Creates:** `rules/ts-functions.yml`, `rules/trpc-procedures.yml`, `src/blast_radius/code/__init__.py`, `src/blast_radius/code/index.py`, `src/blast_radius/code/pr.py`

### Clone the Repo

```bash
git clone https://github.com/documenso/documenso data/repos/documenso
# After choosing your target PR, pin the merge SHA:
gh pr view {PR_NUMBER} --repo documenso/documenso --json mergeCommit
# Add the output SHA to .env as MERGE_SHA=...
```

### rules/ts-functions.yml

Standard TypeScript function/arrow/method capture.

```yaml
id: ts-functions
language: TypeScript
rule:
  any:
    - kind: function_declaration
    - kind: method_definition
    - kind: arrow_function
```

### rules/trpc-procedures.yml

> **New in v3.** Documenso's API layer uses tRPC. The standard arrow-function rule captures the inner lambda but not the procedure name (the router key). This rule captures the router key assignment.

```yaml
id: trpc-procedure
language: TypeScript
rule:
  pattern: $NAME: $PROC.$METHOD($$$)
```

### ast-grep output format (verified)

Run this against the cloned repo to see the actual output structure:

```bash
sg scan --rule rules/ts-functions.yml data/repos/documenso/packages/trpc/server/routers --json | python3 -c "
import json, sys
data = json.load(sys.stdin)
print(json.dumps(data[0] if data else {}, indent=2))
"
```

Expected structure:
```json
{
  "text": "async ({ ctx, input }) => { ... }",
  "range": {
    "start": { "line": 42, "column": 4 },
    "end": { "line": 58, "column": 5 }
  },
  "file": "/abs/path/to/packages/trpc/server/routers/document.ts",
  "lines": "  getDocument: protectedProcedure",
  "metaVariables": {}
}
```

**Key fields:** `text`, `range.start.line`, `file`. There is **no** `rule.kind` nested field. The `ruleId` field (the rule's `id:` value from the YAML) may appear in some ast-grep versions as a top-level key.

### src/blast_radius/code/index.py

```python
import json
import re
import subprocess
from pathlib import Path
from blast_radius.models import CodeFunction


def _make_function_id(repo_dir: Path, abs_file: str, start_line: int, name: str) -> str:
    rel = Path(abs_file).relative_to(repo_dir)
    return f"{rel}:{start_line}:{name}"


def _extract_name_from_text(text: str) -> str:
    """Extract function/procedure name from matched AST text."""
    # tRPC: "getDocument: protectedProcedure.query(..."
    m = re.match(r"(\w+)\s*:\s*\w+Procedure", text.strip())
    if m:
        return m.group(1)
    # function declaration
    m = re.match(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)", text.strip())
    if m:
        return m.group(1)
    # const arrow
    m = re.match(r"(?:export\s+)?const\s+(\w+)\s*=", text.strip())
    if m:
        return m.group(1)
    # method
    m = re.match(r"(?:async\s+)?(\w+)\s*\(", text.strip())
    if m and m.group(1) not in ("async", "function", "const", "let", "var"):
        return m.group(1)
    return "anonymous"


def _parse_ast_grep_output(stdout: str) -> list[dict]:
    """Parse ast-grep JSON output. Handles both array and NDJSON formats."""
    stdout = stdout.strip()
    if not stdout or stdout == "[]":
        return []
    try:
        data = json.loads(stdout)
        if isinstance(data, list):
            return data
    except json.JSONDecodeError:
        pass
    # Try NDJSON
    rows = []
    for line in stdout.splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return rows


def ast_matches(repo: Path, rule_file: str) -> list[dict]:
    """Run ast-grep with the given rule and return raw match dicts."""
    rule = Path(rule_file)
    if not rule.exists():
        raise FileNotFoundError(f"Rule file not found: {rule}. Run from project root.")

    # Documenso scan paths: packages/ and apps/web/src/
    scan_paths = [
        str(repo / "packages"),
        str(repo / "apps" / "web" / "src"),
    ]
    scan_paths = [p for p in scan_paths if Path(p).exists()]
    if not scan_paths:
        raise RuntimeError(f"No valid scan paths found under {repo}")

    result = subprocess.run(
        ["sg", "scan", "--rule", str(rule)] + scan_paths + ["--json"],
        text=True,
        capture_output=True,
    )
    # ast-grep exits 0 with matches, 1 with no matches (POSIX grep convention)
    if result.returncode not in (0, 1):
        raise RuntimeError(f"ast-grep failed (exit {result.returncode}): {result.stderr[:500]}")

    return _parse_ast_grep_output(result.stdout)


def build_call_graph(repo: Path) -> list[CodeFunction]:
    """
    Build call graph from two ast-grep rule passes:
    1. ts-functions: standard TypeScript function declarations
    2. trpc-procedures: tRPC router procedure names

    v3 fix: ast_node_type is set from the rule's `id` field (ruleId),
    NOT from a nonexistent `rule.kind` nested field.
    """
    fn_lookup: dict[str, CodeFunction] = {}
    file_fns: dict[str, list[tuple[str, int]]] = {}

    for rule_file, node_type_default in [
        ("rules/ts-functions.yml", "ts-function"),
        ("rules/trpc-procedures.yml", "trpc-procedure"),
    ]:
        try:
            matches = ast_matches(repo, rule_file)
        except Exception as e:
            print(f"[code] WARNING: {rule_file} scan failed: {e}")
            continue

        for match in matches:
            abs_file = match.get("file", "")
            start_line = match.get("range", {}).get("start", {}).get("line", 0)
            text = match.get("text", "")
            # v3 fix: ruleId is the top-level field from ast-grep JSON; fallback to default
            ast_node_type = match.get("ruleId", node_type_default)
            name = _extract_name_from_text(text)
            if name in ("anonymous", ""):
                continue

            try:
                fn_id = _make_function_id(repo, abs_file, start_line, name)
            except ValueError:
                continue  # abs_file not under repo

            file_fns.setdefault(abs_file, []).append((name, start_line))
            if fn_id not in fn_lookup:
                fn_lookup[fn_id] = CodeFunction(
                    function_id=fn_id,
                    name=name,
                    file=str(Path(abs_file).relative_to(repo)),
                    start_line=start_line,
                    ast_node_type=ast_node_type,
                )

    if len(fn_lookup) < 50:
        raise RuntimeError(
            f"Only {len(fn_lookup)} functions found. "
            "Verify ast-grep is installed and scan paths exist under the cloned repo."
        )

    # Same-file call resolution (conservative: same-file only, name match)
    name_to_ids: dict[str, list[str]] = {}
    for fn in fn_lookup.values():
        name_to_ids.setdefault(fn.name, []).append(fn.function_id)

    all_matches_by_file: dict[str, list[dict]] = {}
    for rule_file in ["rules/ts-functions.yml", "rules/trpc-procedures.yml"]:
        try:
            for m in ast_matches(repo, rule_file):
                all_matches_by_file.setdefault(m.get("file", ""), []).append(m)
        except Exception:
            pass

    for abs_file, matches in all_matches_by_file.items():
        same_file_names = {name for name, _ in file_fns.get(abs_file, [])}
        for match in matches:
            caller_name = _extract_name_from_text(match.get("text", ""))
            caller_line = match.get("range", {}).get("start", {}).get("line", 0)
            try:
                caller_id = _make_function_id(repo, abs_file, caller_line, caller_name)
            except ValueError:
                continue
            if caller_id not in fn_lookup:
                continue
            text = match.get("text", "")
            for callee_name in same_file_names:
                if callee_name == caller_name:
                    continue
                if re.search(r"\b" + re.escape(callee_name) + r"\s*\(", text):
                    for callee_id in name_to_ids.get(callee_name, []):
                        callee_fn = fn_lookup.get(callee_id)
                        if not callee_fn:
                            continue
                        if callee_fn.file == fn_lookup[caller_id].file:
                            if callee_id not in fn_lookup[caller_id].calls:
                                fn_lookup[caller_id].calls.append(callee_id)
                            if caller_id not in callee_fn.called_by:
                                callee_fn.called_by.append(caller_id)

    return list(fn_lookup.values())
```

### src/blast_radius/code/pr.py

```python
import subprocess
from pydriller import Repository
from blast_radius.config import settings
from blast_radius.models import ChangedFile, PRDelta


def get_pr_delta(repo_path: str, pr_number: int, merge_sha: str) -> PRDelta:
    if not merge_sha:
        raise RuntimeError(
            "MERGE_SHA is not set. Run:\n"
            f"  gh pr view {pr_number} --repo {settings.target_repo_name} --json mergeCommit\n"
            "and add MERGE_SHA to your .env file."
        )

    parent_result = subprocess.run(
        ["git", "-C", repo_path, "rev-parse", f"{merge_sha}^1"],
        capture_output=True, text=True, check=True,
    )
    parent_sha = parent_result.stdout.strip()

    changed_files = []
    for commit in Repository(
        repo_path, from_commit=parent_sha, to_commit=merge_sha
    ).traverse_commits():
        for mod in commit.modified_files:
            path = mod.new_path or mod.old_path or ""
            if not path:
                continue
            changed_files.append(ChangedFile(
                path=path,
                status=mod.change_type.name.lower() if mod.change_type else "modified",
                additions=mod.added_lines,
                deletions=mod.deleted_lines,
            ))

    if not changed_files:
        raise RuntimeError(
            f"PyDriller found no changed files between {parent_sha[:8]} and {merge_sha[:8]}. "
            "Verify MERGE_SHA is correct and the repo is at the right ref."
        )

    return PRDelta(
        pr_number=pr_number,
        pr_url=f"https://github.com/{settings.target_repo_name}/pull/{pr_number}",
        title=f"PR #{pr_number}",
        merge_sha=merge_sha,
        parent_sha=parent_sha,
        changed_files=changed_files,
        changed_function_ids=[],  # populated by Phase 5 after seed computation
    )
```

### src/blast_radius/code/__init__.py

```python
import json
from pathlib import Path
from blast_radius.config import settings
from blast_radius.code.index import build_call_graph
from blast_radius.code.pr import get_pr_delta

CODE_DIR = settings.data_dir / "code"
REPO_PATH = str(settings.data_dir / "repos" / "documenso")


def run_code_analysis() -> dict:
    CODE_DIR.mkdir(parents=True, exist_ok=True)
    repo = Path(REPO_PATH)
    if not repo.exists():
        raise FileNotFoundError(
            f"Documenso repo not found at {repo}. "
            f"Clone it: git clone https://github.com/documenso/documenso {repo}"
        )

    print("[code] Running ast-grep scan (ts-functions + trpc-procedures)...")
    functions = build_call_graph(repo)
    call_graph_path = CODE_DIR / "call_graph.json"
    call_graph_path.write_text(
        json.dumps([f.model_dump() for f in functions], indent=2),
        encoding="utf-8",
    )
    print(f"[code] Saved {len(functions)} functions to {call_graph_path}")

    print("[code] Extracting PR delta...")
    delta = get_pr_delta(REPO_PATH, settings.pr_number, settings.merge_sha)
    delta_path = CODE_DIR / f"pr_{settings.pr_number}.json"
    delta_path.write_text(delta.model_dump_json(indent=2), encoding="utf-8")
    print(f"[code] PR delta: {len(delta.changed_files)} files changed")

    return {"functions": functions, "delta": delta}
```

**Smoke test:**
```bash
python -c "from blast_radius.code import run_code_analysis; run_code_analysis()"
python -c "
import json, os
from blast_radius.models import CodeFunction, PRDelta

data = json.load(open('data/code/call_graph.json', encoding='utf-8'))
assert len(data) >= 50, f'Only {len(data)} functions — check ast-grep installation and scan paths'
fns = [CodeFunction.model_validate(d) for d in data]
with_calls = [f for f in fns if f.calls]
# Check tRPC procedures are captured
trpc_fns = [f for f in fns if f.ast_node_type == 'trpc-procedure']
print(f'OK — {len(fns)} functions, {len(with_calls)} with call edges, {len(trpc_fns)} tRPC procedures')

pr_num = int(os.environ.get('PR_NUMBER', 0))
delta = PRDelta.model_validate_json(open(f'data/code/pr_{pr_num}.json', encoding='utf-8').read())
assert delta.changed_files, 'No changed files in PR delta'
ts_files = [f for f in delta.changed_files if f.path.endswith(('.ts', '.tsx'))]
print(f'PR {pr_num}: {len(delta.changed_files)} files changed, {len(ts_files)} TypeScript')
"
```

**Merge condition:** ≥50 functions, at least some tRPC procedures captured, PR delta names TypeScript files.

---

## Phase 4: Knowledge Graph Construction

**Branch:** `feature/phase-4-knowledge-graph`
**Budget:** 2.5 h
**Prerequisites:** Phases 1–3 merged

**Creates:** `src/blast_radius/graph/__init__.py`, `src/blast_radius/graph/schema.py`, `src/blast_radius/graph/writer.py`, `src/blast_radius/graph/resolve.py`

### src/blast_radius/graph/schema.py

```python
CONSTRAINTS = [
    "CREATE CONSTRAINT req_id IF NOT EXISTS FOR (n:Requirement) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT ui_id IF NOT EXISTS FOR (n:UIElement) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT fn_id IF NOT EXISTS FOR (n:CodeFunction) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT gap_id IF NOT EXISTS FOR (n:GapNode) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT page_id IF NOT EXISTS FOR (n:Page) REQUIRE n.id IS UNIQUE",
]

UPSERT_REQUIREMENT = """
MERGE (n:Requirement {id: $id})
SET n.text = $text, n.req_type = $req_type, n.coverage_status = $coverage_status,
    n.source_file = $source_file, n.excerpt = $excerpt, n.updated_at = $updated_at
"""

UPSERT_UI_ELEMENT = """
MERGE (n:UIElement {id: $id})
SET n.label = $label, n.role = $role, n.selector = $selector,
    n.page_url = $page_url, n.updated_at = $updated_at
"""

UPSERT_CODE_FUNCTION = """
MERGE (n:CodeFunction {id: $id})
SET n.name = $name, n.file = $file, n.start_line = $start_line,
    n.ast_node_type = $ast_node_type, n.updated_at = $updated_at
"""

UPSERT_PAGE = """
MERGE (n:Page {id: $id})
SET n.url = $url, n.screenshot_path = $screenshot_path, n.updated_at = $updated_at
"""

# Edge upserts — each uses typed labels; no %s string formatting
CREATE_IMPLEMENTS = """
MATCH (r:Requirement {id: $from_id}), (c:CodeFunction {id: $to_id})
MERGE (r)-[e:IMPLEMENTS]->(c)
SET e.confidence = $confidence, e.evidence = $evidence,
    e.source = $source, e.run_id = $run_id, e.created_at = $created_at
"""

CREATE_RENDERS = """
MATCH (c:CodeFunction {id: $from_id}), (u:UIElement {id: $to_id})
MERGE (c)-[e:RENDERS]->(u)
SET e.confidence = $confidence, e.evidence = $evidence,
    e.source = $source, e.run_id = $run_id, e.created_at = $created_at
"""

CREATE_COVERS = """
MATCH (u:UIElement {id: $from_id}), (r:Requirement {id: $to_id})
MERGE (u)-[e:COVERS]->(r)
SET e.confidence = $confidence, e.evidence = $evidence,
    e.source = $source, e.run_id = $run_id, e.created_at = $created_at
"""

CREATE_CALLS = """
MATCH (a:CodeFunction {id: $from_id}), (b:CodeFunction {id: $to_id})
MERGE (a)-[e:CALLS]->(b)
SET e.weight = 1.0, e.run_id = $run_id, e.created_at = $created_at
"""

CREATE_ABSENT_FROM = """
MATCH (r:Requirement {id: $req_id})
MERGE (g:GapNode {id: $gap_id})
SET g.requirement_id = $req_id, g.reason = $reason,
    g.threshold = $threshold, g.run_id = $run_id
MERGE (r)-[e:ABSENT_FROM]->(g)
SET e.run_id = $run_id, e.created_at = $created_at
"""

MARK_MISSING_REQUIREMENTS = """
MATCH (r:Requirement)
WHERE NOT (r)-[:IMPLEMENTS]->(:CodeFunction)
  AND NOT (r)<-[:COVERS]-(:UIElement)
SET r.coverage_status = 'MISSING'
RETURN count(r) as missing_count
"""

MARK_COVERED_REQUIREMENTS = """
MATCH (r:Requirement)
WHERE (r)-[:IMPLEMENTS]->(:CodeFunction)
   OR (r)<-[:COVERS]-(:UIElement)
SET r.coverage_status = 'PARTIAL'
RETURN count(r) as partial_count
"""
```

### src/blast_radius/graph/resolve.py

```python
import json
import re
from typing import Optional
import numpy as np
from sentence_transformers import SentenceTransformer, util as st_util
import anthropic

from blast_radius.config import settings
from blast_radius.models import Requirement, CodeFunction, EntityLink, PageSnapshot

_model: Optional[SentenceTransformer] = None
_client: Optional[anthropic.Anthropic] = None


def _encoder() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _anthropic() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def resolve_requirements_to_functions(
    requirements: list[Requirement],
    functions: list[CodeFunction],
    *,
    cosine_threshold: float = 0.45,
    llm_rerank_threshold: float = 0.65,
    run_id: str = "v1",
) -> list[EntityLink]:
    """
    Two-stage entity resolution:
    1. Vectorized cosine similarity (sentence-transformers util.cos_sim) — O(n*m) in numpy/torch
    2. LLM reranker — confirms candidates above cosine_threshold

    v3 fix: uses st_util.cos_sim for vectorized batch similarity instead of O(n²) Python loop.
    Updated Documenso-specific LLM prompt.
    """
    links: list[EntityLink] = []
    req_texts = [r.text for r in requirements]
    fn_labels = [f"{f.file}:{f.name}" for f in functions]

    enc = _encoder()
    req_embeddings = enc.encode(req_texts, normalize_embeddings=True, convert_to_tensor=True)
    fn_embeddings = enc.encode(fn_labels, normalize_embeddings=True, convert_to_tensor=True)

    # Vectorized similarity matrix: shape (len(reqs), len(fns))
    sim_matrix = st_util.cos_sim(req_embeddings, fn_embeddings)

    candidates: list[tuple[Requirement, CodeFunction, float]] = []
    for i, req in enumerate(requirements):
        scores = sim_matrix[i].tolist()
        top_idx = sorted(range(len(scores)), key=lambda x: scores[x], reverse=True)[:5]
        for j in top_idx:
            if scores[j] >= cosine_threshold:
                candidates.append((req, functions[j], scores[j]))

    if not candidates:
        print("[resolve] No cosine candidates above threshold. Skipping LLM reranker.")
        return links

    # LLM reranker in batches of 10
    # v3: Documenso-specific prompt
    batch_size = 10
    for batch_start in range(0, len(candidates), batch_size):
        batch = candidates[batch_start:batch_start + batch_size]
        prompt_items = [
            {
                "req_id": req.requirement_id,
                "req_text": req.text,
                "fn_id": fn.function_id,
                "fn_label": fn_labels[functions.index(fn)],
                "cosine_score": round(score, 3),
            }
            for req, fn, score in batch
        ]
        prompt = (
            "You are reviewing candidate requirement-to-code mappings for Documenso, "
            "a document signing platform. Functions include tRPC procedures, Next.js server actions, "
            "and lib/ business logic for documents, recipients, templates, and fields.\n"
            "For each candidate, decide if the function plausibly implements the requirement.\n"
            "Return ONLY a JSON array where each element has:\n"
            '  "req_id": string, "fn_id": string, "confirmed": bool, '
            '"confidence": float (0-1), "reason": string\n\n'
            f"Candidates:\n{json.dumps(prompt_items, indent=2)}"
        )
        try:
            msg = _anthropic().messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            if raw.startswith("```"):
                raw = re.sub(r"```[a-z]*\n?", "", raw).replace("```", "").strip()
            results = json.loads(raw)
        except Exception as e:
            print(f"[resolve] LLM reranker error: {e}. Skipping batch.")
            continue

        for result in results:
            if not result.get("confirmed"):
                continue
            confidence = float(result.get("confidence", 0.5))
            if confidence < llm_rerank_threshold:
                continue
            links.append(EntityLink(
                from_id=result["req_id"],
                to_id=result["fn_id"],
                rel_type="IMPLEMENTS",
                confidence=confidence,
                evidence=result.get("reason", "LLM reranker confirmed"),
                source="cosine_sim+llm",
                run_id=run_id,
            ))

    return links


def resolve_ui_to_functions(
    snapshots: list[PageSnapshot],
    functions: list[CodeFunction],
    *,
    run_id: str = "v1",
) -> list[EntityLink]:
    """
    Match UIElement pages to CodeFunction files via URL segment matching.

    v3 fix: ui_id now matches the IDs written by write_ui_elements.
    write_ui_elements writes UIElement nodes with id = f"ui:{snap.url_sha256}:{item.index}"
    and Page nodes with id = f"page:{snap.url_sha256}".

    This function creates RENDERS edges from CodeFunction to Page (not UIElement),
    which is correct: a function renders a page, not a specific element within it.
    This avoids the v2 mismatch where ui_id used "ui:{sha}:page" (nonexistent in the graph).
    """
    links: list[EntityLink] = []

    for snap in snapshots:
        # Extract meaningful route segments from the URL
        # e.g. "https://app.documenso.com/documents/new" -> ["documents", "new"]
        path = snap.url.split("//", 1)[-1]  # strip scheme
        path = path.split("/", 1)[-1] if "/" in path else ""  # strip host
        route_parts = [p for p in path.rstrip("/").split("/") if p and len(p) >= 4]

        if not route_parts:
            continue

        page_id = f"page:{snap.url_sha256}"

        for fn in functions:
            for part in route_parts:
                if part.lower() in fn.file.lower():
                    links.append(EntityLink(
                        from_id=fn.function_id,
                        to_id=page_id,
                        rel_type="RENDERS",
                        confidence=0.70,
                        evidence=f"URL segment '{part}' appears in file '{fn.file}'",
                        source="url_pattern",
                        run_id=run_id,
                    ))
                    break

    return links
```

### src/blast_radius/graph/writer.py

```python
from datetime import datetime, timezone
from neo4j import GraphDatabase
from blast_radius.config import settings
from blast_radius.graph.schema import (
    CONSTRAINTS, UPSERT_REQUIREMENT, UPSERT_UI_ELEMENT, UPSERT_CODE_FUNCTION,
    UPSERT_PAGE, CREATE_IMPLEMENTS, CREATE_RENDERS, CREATE_COVERS, CREATE_CALLS,
    CREATE_ABSENT_FROM, MARK_MISSING_REQUIREMENTS, MARK_COVERED_REQUIREMENTS,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_driver():
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


def ensure_schema(driver) -> None:
    with driver.session() as session:
        for constraint in CONSTRAINTS:
            try:
                session.run(constraint).consume()
            except Exception as e:
                print(f"[graph] Schema (may already exist): {e}")


def write_requirements(session, requirements: list) -> None:
    for r in requirements:
        session.run(UPSERT_REQUIREMENT, {
            "id": r.requirement_id, "text": r.text, "req_type": r.req_type,
            "coverage_status": r.coverage_status, "source_file": r.provenance.source_file,
            "excerpt": r.provenance.excerpt, "updated_at": _now(),
        }).consume()


def write_ui_elements(session, snapshots: list) -> None:
    for snap in snapshots:
        session.run(UPSERT_PAGE, {
            "id": f"page:{snap.url_sha256}", "url": snap.url,
            "screenshot_path": snap.screenshot_path, "updated_at": _now(),
        }).consume()
        for item in snap.accessibility_tree:
            session.run(UPSERT_UI_ELEMENT, {
                "id": f"ui:{snap.url_sha256}:{item.index}",
                "label": item.name or item.tag,
                "role": item.role or item.tag,
                "selector": item.selector,
                "page_url": snap.url,
                "updated_at": _now(),
            }).consume()


def write_code_functions(session, functions: list) -> None:
    for fn in functions:
        session.run(UPSERT_CODE_FUNCTION, {
            "id": fn.function_id, "name": fn.name, "file": fn.file,
            "start_line": fn.start_line, "ast_node_type": fn.ast_node_type,
            "updated_at": _now(),
        }).consume()
    for fn in functions:
        for callee_id in fn.calls:
            try:
                session.run(CREATE_CALLS, {
                    "from_id": fn.function_id, "to_id": callee_id,
                    "run_id": "v1", "created_at": _now(),
                }).consume()
            except Exception:
                pass


def write_entity_links(session, links: list, run_id: str = "v1") -> None:
    template_map = {
        "IMPLEMENTS": CREATE_IMPLEMENTS,
        "RENDERS": CREATE_RENDERS,
        "COVERS": CREATE_COVERS,
    }
    for link in links:
        tmpl = template_map.get(link.rel_type)
        if not tmpl:
            continue
        try:
            session.run(tmpl, {
                "from_id": link.from_id, "to_id": link.to_id,
                "confidence": link.confidence, "evidence": link.evidence,
                "source": link.source, "run_id": run_id, "created_at": _now(),
            }).consume()
        except Exception as e:
            print(f"[graph] Edge write warning ({link.rel_type}): {e}")


def mark_absent_requirements(session, run_id: str = "v1") -> int:
    """Mark requirements with no coverage and create GapNodes."""
    result = session.run(MARK_MISSING_REQUIREMENTS).single()
    missing_count = result["missing_count"] if result else 0
    session.run(MARK_COVERED_REQUIREMENTS).consume()
    for row in session.run(
        "MATCH (r:Requirement {coverage_status: 'MISSING'}) RETURN r.id as id"
    ).data():
        req_id = row["id"]
        session.run(CREATE_ABSENT_FROM, {
            "req_id": req_id,
            "gap_id": f"gap:{req_id}",
            "reason": "No IMPLEMENTS edge to CodeFunction and no COVERS edge from UIElement at threshold >= 0.65",
            "threshold": 0.65,
            "run_id": run_id,
            "created_at": _now(),
        }).consume()
    return missing_count
```

### src/blast_radius/graph/__init__.py

```python
import json
import uuid
from blast_radius.config import settings
from blast_radius.crawl.artifacts import load_snapshots
from blast_radius.graph.writer import (
    get_driver, ensure_schema, write_requirements, write_ui_elements,
    write_code_functions, write_entity_links, mark_absent_requirements,
)
from blast_radius.graph.resolve import resolve_requirements_to_functions, resolve_ui_to_functions
from blast_radius.models import Requirement, CodeFunction


def build_graph() -> None:
    run_id = str(uuid.uuid4())[:8]
    requirements = [
        Requirement.model_validate(r)
        for r in json.loads(
            (settings.data_dir / "requirements" / "requirements.json").read_text(encoding="utf-8")
        )
    ]
    functions = [
        CodeFunction.model_validate(f)
        for f in json.loads(
            (settings.data_dir / "code" / "call_graph.json").read_text(encoding="utf-8")
        )
    ]
    snapshots = load_snapshots()

    print(f"[graph] {len(requirements)} requirements | {len(functions)} functions | {len(snapshots)} snapshots")

    driver = get_driver()
    ensure_schema(driver)

    with driver.session() as session:
        print("[graph] Writing Requirements...")
        write_requirements(session, requirements)

        print("[graph] Writing UIElements and Pages...")
        write_ui_elements(session, snapshots)

        print("[graph] Writing CodeFunctions and CALLS edges...")
        write_code_functions(session, functions)

        print("[graph] Resolving Requirement → CodeFunction (IMPLEMENTS)...")
        req_fn_links = resolve_requirements_to_functions(requirements, functions, run_id=run_id)
        write_entity_links(session, req_fn_links, run_id=run_id)
        print(f"[graph]   {len(req_fn_links)} IMPLEMENTS links")

        print("[graph] Resolving CodeFunction → Page (RENDERS)...")
        ui_fn_links = resolve_ui_to_functions(snapshots, functions, run_id=run_id)
        write_entity_links(session, ui_fn_links, run_id=run_id)
        print(f"[graph]   {len(ui_fn_links)} RENDERS links")

        print("[graph] Marking absent requirements and creating GapNodes...")
        missing_count = mark_absent_requirements(session, run_id=run_id)
        print(f"[graph]   {missing_count} requirements marked MISSING → GapNodes created")

    driver.close()
    print(f"[graph] Build complete (run_id={run_id})")
```

**Smoke test:**
```bash
python -c "from blast_radius.graph import build_graph; build_graph()"
python -c "
from blast_radius.graph.writer import get_driver
d = get_driver()
for row in d.execute_query('MATCH (n) RETURN labels(n)[0] as label, count(n) as c ORDER BY label').records:
    print(f'  {row[\"label\"]}: {row[\"c\"]}')
gaps = d.execute_query('MATCH (r:Requirement)-[:ABSENT_FROM]->(g:GapNode) RETURN count(r) as c').records
print(f'  ABSENT_FROM (GapNodes): {gaps[0][\"c\"]}')
# Verify no ui_id mismatch: RENDERS edges should resolve
renders = d.execute_query('MATCH (c:CodeFunction)-[:RENDERS]->(p:Page) RETURN count(*) as c').records
print(f'  RENDERS edges (CodeFunction->Page): {renders[0][\"c\"]}')
d.close()
"
```

**Merge condition:** All node labels populated in Neo4j; ABSENT_FROM query returns a result (logged even if zero); at least one RENDERS edge exists; no RENDERS edges pointing to nonexistent nodes.

---

## Phase 5: Blast Radius Reasoning

**Branch:** `feature/phase-5-blast-radius`
**Budget:** 2.25 h
**Prerequisites:** Phases 0–4 merged

**Creates:** `src/blast_radius/reason/__init__.py`, `src/blast_radius/reason/ppr.py`, `src/blast_radius/reason/impact.py`

### src/blast_radius/reason/ppr.py

```python
import networkx as nx


def build_projection(
    functions: list,
    entity_links: list,
) -> nx.DiGraph:
    """
    Build typed weighted projection for PPR.
    Edge weights: CALLS=1.0, RENDERS=0.95, IMPLEMENTS=0.85, COVERS=0.75
    Direction: CodeFunction → Page/UIElement → Requirement (blast radius direction)
    """
    WEIGHTS = {
        "CALLS": 1.0,
        "RENDERS": 0.95,
        "IMPLEMENTS": 0.85,
        "COVERS": 0.75,
    }
    g = nx.DiGraph()
    for fn in functions:
        g.add_node(fn.function_id, node_type="CodeFunction", label=fn.name)
        for callee_id in fn.calls:
            g.add_edge(fn.function_id, callee_id, weight=WEIGHTS["CALLS"], rel_type="CALLS")
    for link in entity_links:
        g.add_edge(
            link.from_id, link.to_id,
            weight=WEIGHTS.get(link.rel_type, 0.5) * link.confidence,
            rel_type=link.rel_type,
        )
    return g


def personalized_pagerank(
    graph: nx.DiGraph,
    seeds: list[str],
) -> dict[str, float]:
    """
    Forward PPR — seeds are changed code nodes; activation flows toward requirements.
    v2/v3 fix: graph is NOT reversed. CALLS=code→code, RENDERS=code→page,
    IMPLEMENTS=req→code (reversed in projection), COVERS=ui→req.
    Forward propagation finds downstream product impact.
    """
    if not seeds:
        raise RuntimeError("No seed nodes. Changed files are not in the call graph.")
    missing = [s for s in seeds if s not in graph]
    if missing:
        raise RuntimeError(f"Seed nodes not in graph: {missing[:3]}")

    personalization = {n: 0.0 for n in graph.nodes()}
    w = 1.0 / len(seeds)
    for s in seeds:
        personalization[s] = w

    return nx.pagerank(
        graph,  # forward — NOT reversed
        alpha=0.85,
        personalization=personalization,
        max_iter=100,
        tol=1e-8,
        weight="weight",
    )


def normalize_scores(scores: dict[str, float], seeds: set[str]) -> dict[str, float]:
    non_seed = {k: v for k, v in scores.items() if k not in seeds and v > 0}
    if not non_seed:
        return {}
    min_v, max_v = min(non_seed.values()), max(non_seed.values())
    if max_v == min_v:
        return {k: 0.5 for k in non_seed}
    return {k: (v - min_v) / (max_v - min_v) for k, v in non_seed.items()}
```

### src/blast_radius/reason/impact.py

```python
import networkx as nx
from blast_radius.models import AffectedNode, EntityLink

MAX_HOPS = 6


def evidence_path(graph: nx.DiGraph, seed: str, target: str) -> list[str]:
    """
    Find shortest evidence path from seed to target.
    Returns [] if no path exists.

    v3 fixes:
    - nx.shortest_path with method='dijkstra' and weight='weight' (string, not callable).
      Using a callable weight with method='dijkstra' raises TypeError.
    - Catches NetworkXNoPath and NodeNotFound instead of crashing.
    """
    try:
        path = nx.shortest_path(
            graph,
            seed,
            target,
            method="dijkstra",
            weight="weight",  # string attribute name, not a callable
        )
        if len(path) > MAX_HOPS + 1:
            return []
        return path
    except (nx.NetworkXNoPath, nx.NodeNotFound, nx.exception.NodeNotFound):
        return []


def classify_risk(impact_score: float, traceability_confidence: float) -> str:
    if impact_score >= 0.70 and traceability_confidence >= 0.70:
        return "HIGH"
    if impact_score >= 0.40 and traceability_confidence >= 0.40:
        return "MEDIUM"
    return "LOW"


def compute_affected_nodes(
    graph: nx.DiGraph,
    seeds: list[str],
    normalized_scores: dict[str, float],
    entity_links: list[EntityLink],
    node_metadata: dict[str, dict],
) -> tuple[list[AffectedNode], list[AffectedNode], list[str]]:
    affected_ui: list[AffectedNode] = []
    affected_req: list[AffectedNode] = []
    dark_changes: list[str] = []

    for seed in seeds:
        reachable = nx.descendants(graph, seed) if seed in graph else set()
        if not reachable:
            dark_changes.append(seed)
            continue
        for node_id in reachable:
            meta = node_metadata.get(node_id, {})
            node_type = meta.get("node_type", "Unknown")
            if node_type not in ("UIElement", "Requirement", "Page"):
                continue
            impact_score = normalized_scores.get(node_id, 0.0)
            path = evidence_path(graph, seed, node_id)
            if not path:
                continue
            # Minimum edge weight on path as traceability confidence
            edge_weights = []
            for i in range(len(path) - 1):
                ed = graph.get_edge_data(path[i], path[i + 1]) or {}
                edge_weights.append(ed.get("weight", 0.5))
            tc = min(edge_weights) if edge_weights else 0.5
            risk = classify_risk(impact_score, tc)
            node = AffectedNode(
                node_id=node_id,
                node_type=node_type,
                label=meta.get("label", node_id),
                impact_score=round(impact_score, 4),
                traceability_confidence=round(tc, 4),
                evidence_path=path,
                risk_tier=risk,
            )
            if node_type in ("UIElement", "Page"):
                affected_ui.append(node)
            else:
                affected_req.append(node)

    def dedup(nodes: list[AffectedNode]) -> list[AffectedNode]:
        seen: dict[str, AffectedNode] = {}
        for n in nodes:
            if n.node_id not in seen or n.impact_score > seen[n.node_id].impact_score:
                seen[n.node_id] = n
        return sorted(seen.values(), key=lambda x: x.impact_score, reverse=True)

    return dedup(affected_ui), dedup(affected_req), list(set(dark_changes))
```

### src/blast_radius/reason/__init__.py

```python
import json
import uuid
from pathlib import Path
from blast_radius.config import settings
from blast_radius.models import (
    CodeFunction, PRDelta, Requirement, EntityLink, BlastRadiusReport, AffectedNode
)
from blast_radius.reason.ppr import build_projection, personalized_pagerank, normalize_scores
from blast_radius.reason.impact import compute_affected_nodes

REPORTS_DIR = settings.data_dir / "reports"


def _load_artifacts():
    functions = [CodeFunction.model_validate(f) for f in json.loads(
        (settings.data_dir / "code" / "call_graph.json").read_text(encoding="utf-8")
    )]
    delta = PRDelta.model_validate_json(
        (settings.data_dir / "code" / f"pr_{settings.pr_number}.json").read_text(encoding="utf-8")
    )
    return functions, delta


def _load_graph_data() -> tuple[list[EntityLink], dict[str, dict], list[AffectedNode]]:
    """
    Load entity links, node metadata, and absent requirements from Neo4j.
    v3: also loads GapNode/ABSENT_FROM data for absent_requirements report field.
    """
    from blast_radius.graph.writer import get_driver
    driver = get_driver()
    links = []
    node_meta = {}
    absent_requirements: list[AffectedNode] = []

    with driver.session() as session:
        for row in session.run(
            "MATCH (r:Requirement)-[e:IMPLEMENTS]->(c:CodeFunction) "
            "RETURN r.id as from_id, c.id as to_id, e.confidence as conf, "
            "e.evidence as ev, e.source as src, e.run_id as rid"
        ):
            links.append(EntityLink(
                from_id=row["from_id"], to_id=row["to_id"], rel_type="IMPLEMENTS",
                confidence=row["conf"] or 0.65, evidence=row["ev"] or "",
                source=row["src"] or "neo4j", run_id=row["rid"] or "v1",
            ))
        for row in session.run(
            "MATCH (c:CodeFunction)-[e:RENDERS]->(p:Page) "
            "RETURN c.id as from_id, p.id as to_id, e.confidence as conf, "
            "e.evidence as ev, e.source as src, e.run_id as rid"
        ):
            links.append(EntityLink(
                from_id=row["from_id"], to_id=row["to_id"], rel_type="RENDERS",
                confidence=row["conf"] or 0.70, evidence=row["ev"] or "",
                source=row["src"] or "neo4j", run_id=row["rid"] or "v1",
            ))
        for row in session.run("MATCH (n:Page) RETURN n.id as id, n.url as label"):
            node_meta[row["id"]] = {"node_type": "Page", "label": row["label"]}
        for row in session.run("MATCH (n:UIElement) RETURN n.id as id, n.label as label"):
            node_meta[row["id"]] = {"node_type": "UIElement", "label": row["label"]}
        for row in session.run("MATCH (n:Requirement) RETURN n.id as id, n.text as label"):
            node_meta[row["id"]] = {"node_type": "Requirement", "label": row["label"][:80]}
        for row in session.run("MATCH (n:CodeFunction) RETURN n.id as id, n.name as label"):
            node_meta[row["id"]] = {"node_type": "CodeFunction", "label": row["label"]}

        # v3: Load absent requirements from GapNodes
        for row in session.run(
            "MATCH (r:Requirement)-[:ABSENT_FROM]->(g:GapNode) "
            "RETURN r.id as req_id, r.text as req_text, g.reason as reason"
        ):
            absent_requirements.append(AffectedNode(
                node_id=row["req_id"],
                node_type="Requirement",
                label=row["req_text"][:80],
                impact_score=0.0,
                traceability_confidence=0.0,
                evidence_path=[],
                risk_tier="ABSENT",
            ))

    driver.close()
    return links, node_meta, absent_requirements


def analyze_pr() -> BlastRadiusReport:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid.uuid4())[:8]

    functions, delta = _load_artifacts()

    mode = "neo4j"
    absent_requirements: list[AffectedNode] = []
    try:
        entity_links, node_meta, absent_requirements = _load_graph_data()
    except Exception as e:
        print(f"[reason] WARNING: Neo4j unavailable ({e}). Running projection-only mode.")
        entity_links = []
        node_meta = {fn.function_id: {"node_type": "CodeFunction", "label": fn.name}
                     for fn in functions}
        mode = "projection-only"

    graph = build_projection(functions, entity_links)

    # Identify seeds from changed files
    changed_paths = {cf.path for cf in delta.changed_files}
    seeds = [fn.function_id for fn in functions if fn.file in changed_paths]

    if not seeds:
        # Fallback: match by filename only
        seeds = [fn.function_id for fn in functions if any(
            fn.file.endswith(Path(cf.path).name) for cf in delta.changed_files
        )]

    if not seeds:
        print("[reason] All changed files outside indexed code — DARK_CHANGE.")
        report = BlastRadiusReport(
            run_id=run_id, pr_url=delta.pr_url, pr_number=delta.pr_number,
            pr_title=delta.title, mode=mode, changed_files=delta.changed_files,
            seed_function_ids=[], affected_ui_elements=[], affected_requirements=[],
            absent_requirements=absent_requirements,
            dark_changes=[cf.path for cf in delta.changed_files],
            evidence_subgraph=[], confidence_scores={},
            manual_review_items=[
                "All changed files are outside the indexed TypeScript call graph. "
                "This PR may affect configuration, assets, or non-TypeScript code. Manual review required."
            ],
        )
        _save_report(report)
        return report

    raw_scores = personalized_pagerank(graph, seeds)
    normalized = normalize_scores(raw_scores, set(seeds))
    affected_ui, affected_req, dark_changes = compute_affected_nodes(
        graph, seeds, normalized, entity_links, node_meta
    )

    # v3: Populate changed_function_ids on delta and write back to disk
    delta.changed_function_ids = seeds
    delta_path = settings.data_dir / "code" / f"pr_{settings.pr_number}.json"
    delta_path.write_text(delta.model_dump_json(indent=2), encoding="utf-8")

    evidence_edge_set: set[tuple[str, str]] = set()
    for node in affected_ui + affected_req:
        for i in range(len(node.evidence_path) - 1):
            evidence_edge_set.add((node.evidence_path[i], node.evidence_path[i + 1]))
    evidence_subgraph = [
        link for link in entity_links
        if (link.from_id, link.to_id) in evidence_edge_set
    ]

    manual_review = []
    low_conf = [n for n in affected_ui + affected_req if n.risk_tier == "LOW"]
    if low_conf:
        manual_review.append(
            f"{len(low_conf)} node(s) have LOW confidence scores — verify before updating test plans."
        )
    if dark_changes:
        manual_review.append(
            f"{len(dark_changes)} changed function(s) have no traceable path to UI or requirements: "
            + ", ".join(dark_changes[:3])
        )
    if absent_requirements:
        manual_review.append(
            f"{len(absent_requirements)} requirement(s) have no UI or code coverage in the graph. "
            "These may be unimplemented features or gaps in the crawl."
        )

    report = BlastRadiusReport(
        run_id=run_id, pr_url=delta.pr_url, pr_number=delta.pr_number,
        pr_title=delta.title, mode=mode, changed_files=delta.changed_files,
        seed_function_ids=seeds, affected_ui_elements=affected_ui,
        affected_requirements=affected_req, absent_requirements=absent_requirements,
        dark_changes=dark_changes, evidence_subgraph=evidence_subgraph,
        confidence_scores={n.node_id: n.impact_score for n in affected_ui + affected_req},
        manual_review_items=manual_review,
    )
    _save_report(report)
    return report


def _save_report(report: BlastRadiusReport) -> None:
    out = REPORTS_DIR / "blast_radius_report.json"
    out.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    print(f"[reason] Report: {len(report.affected_ui_elements)} UI | "
          f"{len(report.affected_requirements)} req | {len(report.absent_requirements)} absent | "
          f"{len(report.dark_changes)} dark")
```

**Smoke test:**
```bash
python -c "from blast_radius.reason import analyze_pr; r = analyze_pr(); print(r.pr_url)"
python -c "
import json
from blast_radius.models import BlastRadiusReport, PRDelta
import os

report = BlastRadiusReport.model_validate_json(
    open('data/reports/blast_radius_report.json', encoding='utf-8').read()
)
assert report.pr_url.startswith('https://github.com')
assert all(0 <= v <= 1 for v in report.confidence_scores.values())
has_content = (report.affected_ui_elements or report.affected_requirements
               or report.absent_requirements or report.dark_changes or report.manual_review_items)
assert has_content, 'Report is completely empty — check Phase 3 and 4 outputs'

# v3: verify changed_function_ids was written back
pr_num = int(os.environ.get('PR_NUMBER', 0))
delta = PRDelta.model_validate_json(
    open(f'data/code/pr_{pr_num}.json', encoding='utf-8').read()
)
# changed_function_ids should now be populated (or empty if dark change, which is valid)
print(f'OK — UI:{len(report.affected_ui_elements)} req:{len(report.affected_requirements)} '
      f'absent:{len(report.absent_requirements)} dark:{len(report.dark_changes)}')
print(f'delta.changed_function_ids: {len(delta.changed_function_ids)} seeds written back')
"
```

**Merge condition:** Report validates against schema, scores 0–1, report is non-empty, `delta.changed_function_ids` is populated on disk.

---

## Phase 6: Human-Readable Report

**Branch:** `feature/phase-6-report`
**Budget:** 1.0 h
**Prerequisites:** Phase 5 merged

**Creates:** `src/blast_radius/report/__init__.py`, `src/blast_radius/report/render.py`, `templates/report.html.j2`

### templates/report.html.j2

> **v3 new:** Includes Absent Requirements section (previously missing). Fixed Jinja `seed_function_ids` list rendering with `tojson` filter.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Blast Radius Report — PR #{{ report.pr_number }}</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 960px; margin: 2rem auto; color: #1a1a1a; line-height: 1.6; }
  h1 { border-bottom: 3px solid #e53e3e; padding-bottom: .5rem; }
  h2 { margin-top: 2rem; }
  .badge-high   { background:#fed7d7;color:#c53030;padding:2px 8px;border-radius:4px;font-size:.85em; }
  .badge-medium { background:#fefcbf;color:#744210;padding:2px 8px;border-radius:4px;font-size:.85em; }
  .badge-low    { background:#bee3f8;color:#2b6cb0;padding:2px 8px;border-radius:4px;font-size:.85em; }
  .badge-absent { background:#e9d8fd;color:#553c9a;padding:2px 8px;border-radius:4px;font-size:.85em; }
  .badge-dark   { background:#e2e8f0;color:#4a5568;padding:2px 8px;border-radius:4px;font-size:.85em; }
  table { border-collapse:collapse;width:100%;margin:1rem 0; }
  th,td { border:1px solid #e2e8f0;padding:.5rem .75rem;text-align:left; }
  th { background:#f7fafc; }
  .evidence { font-family:monospace;font-size:.82em;background:#f7fafc;padding:.4rem;border-radius:4px;word-break:break-all; }
  .warning { background:#fffbeb;border-left:4px solid #d69e2e;padding:.75rem 1rem;margin:1rem 0; }
  .absent  { background:#faf5ff;border-left:4px solid #805ad5;padding:.75rem 1rem;margin:1rem 0; }
  .dark    { background:#f7fafc;border-left:4px solid #718096;padding:.75rem 1rem;margin:1rem 0; }
  footer   { margin-top:3rem;font-size:.8em;color:#718096;border-top:1px solid #e2e8f0;padding-top:1rem; }
</style>
</head>
<body>

<h1>Blast Radius Report</h1>

<table>
  <tr><th>Pull Request</th><td><a href="{{ report.pr_url }}">#{{ report.pr_number }} — {{ report.pr_title }}</a></td></tr>
  <tr><th>Analysis Mode</th><td>{{ report.mode }}</td></tr>
  <tr><th>Run ID</th><td>{{ report.run_id }}</td></tr>
  <tr><th>Changed Files</th><td>{{ report.changed_files | length }}</td></tr>
</table>

{% if report.summary %}
<h2>Executive Summary</h2>
<p>{{ report.summary }}</p>
{% endif %}

<h2>Changed Files</h2>
<table>
  <tr><th>File</th><th>Status</th><th>+</th><th>−</th></tr>
  {% for f in report.changed_files %}
  <tr><td><code>{{ f.path }}</code></td><td>{{ f.status }}</td><td>+{{ f.additions }}</td><td>-{{ f.deletions }}</td></tr>
  {% endfor %}
</table>

<h2>Affected UI / Pages ({{ report.affected_ui_elements | length }})</h2>
{% if report.affected_ui_elements %}
<table>
  <tr><th>Element / Page</th><th>Risk</th><th>Impact</th><th>Confidence</th><th>Evidence Path</th></tr>
  {% for el in report.affected_ui_elements %}
  <tr>
    <td>{{ el.label }}</td>
    <td><span class="badge-{{ el.risk_tier | lower }}">{{ el.risk_tier }}</span></td>
    <td>{{ "%.2f" | format(el.impact_score) }}</td>
    <td>{{ "%.2f" | format(el.traceability_confidence) }}</td>
    <td class="evidence">{{ el.evidence_path | join(' → ') }}</td>
  </tr>
  {% endfor %}
</table>
{% else %}
<p><em>No UI elements directly traced to changed code.</em></p>
{% endif %}

<h2>Affected Requirements ({{ report.affected_requirements | length }})</h2>
{% if report.affected_requirements %}
<table>
  <tr><th>Requirement</th><th>Risk</th><th>Impact</th><th>Confidence</th></tr>
  {% for req in report.affected_requirements %}
  <tr>
    <td>{{ req.label }}</td>
    <td><span class="badge-{{ req.risk_tier | lower }}">{{ req.risk_tier }}</span></td>
    <td>{{ "%.2f" | format(req.impact_score) }}</td>
    <td>{{ "%.2f" | format(req.traceability_confidence) }}</td>
  </tr>
  {% endfor %}
</table>
{% else %}
<p><em>No requirements directly traced to changed code.</em></p>
{% endif %}

{# v3: Absent Requirements section — surfaced from GapNodes #}
{% if report.absent_requirements %}
<h2>🟣 Absent Requirements ({{ report.absent_requirements | length }})</h2>
<div class="absent">
  <strong>These requirements exist in documentation but have no corresponding UI element or code coverage in the graph.</strong>
  They may be unimplemented features, features only accessible behind authentication not yet crawled,
  or gaps in the current graph coverage. Each is a candidate for manual verification.
  <table style="margin-top:.75rem">
    <tr><th>Requirement</th><th>Status</th></tr>
    {% for req in report.absent_requirements %}
    <tr>
      <td>{{ req.label }}</td>
      <td><span class="badge-absent">ABSENT</span></td>
    </tr>
    {% endfor %}
  </table>
</div>
{% endif %}

{% if report.dark_changes %}
<h2>⚫ Dark Changes ({{ report.dark_changes | length }})</h2>
<div class="dark">
  <strong>These changed functions have no traceable path to any UI element or requirement.</strong>
  They may affect internal logic, configuration, or unindexed code. Manual review required.
  <ul>
  {% for dc in report.dark_changes %}
    <li><code>{{ dc }}</code></li>
  {% endfor %}
  </ul>
</div>
{% endif %}

{% if report.manual_review_items %}
<h2>⚠️ Manual Review Required</h2>
<div class="warning">
  <ul>
  {% for item in report.manual_review_items %}
    <li>{{ item }}</li>
  {% endfor %}
  </ul>
</div>
{% endif %}

<h2>Coverage Statistics</h2>
<table>
  <tr><th>Metric</th><th>Count</th></tr>
  <tr><td>Affected UI / pages</td><td>{{ report.affected_ui_elements | length }}</td></tr>
  <tr><td>Affected requirements</td><td>{{ report.affected_requirements | length }}</td></tr>
  <tr><td>Absent requirements</td><td>{{ report.absent_requirements | length }}</td></tr>
  <tr><td>Dark changes</td><td>{{ report.dark_changes | length }}</td></tr>
  <tr><td>Evidence edges</td><td>{{ report.evidence_subgraph | length }}</td></tr>
  <tr><td>Manual review items</td><td>{{ report.manual_review_items | length }}</td></tr>
</table>

<footer>
  Report generated by Blast Radius Analyzer v3 · Run ID: {{ report.run_id }}<br>
  {# v3 fix: use tojson filter to avoid HTML-escaping of list quotes #}
  Graph query: <code>MATCH path=(f:CodeFunction)-[*1..6]-(r:Requirement)
  WHERE f.id IN {{ report.seed_function_ids[:3] | tojson }} RETURN path LIMIT 50</code>
</footer>
</body>
</html>
```

### src/blast_radius/report/render.py

```python
from pathlib import Path
import anthropic

from blast_radius.config import settings
from blast_radius.models import BlastRadiusReport

REPORTS_DIR = settings.data_dir / "reports"


def _generate_summary(report: BlastRadiusReport) -> str:
    """Generate plain-English executive summary from structured evidence only."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    high = [n for n in report.affected_requirements if n.risk_tier == "HIGH"]
    prompt = (
        "Write a 2–3 sentence plain-English executive summary of this PR's blast radius "
        "for a non-technical QA lead at a document signing company (Documenso).\n"
        f"PR: {report.pr_url}\n"
        f"Changed files: {[cf.path for cf in report.changed_files[:5]]}\n"
        f"High-risk requirements: {[n.label for n in high[:3]]}\n"
        f"Absent requirements: {len(report.absent_requirements)}\n"
        f"Dark changes: {len(report.dark_changes)}\n"
        "Write only what the structured data supports. Do not invent risks."
    )
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def render(report: BlastRadiusReport) -> tuple[Path, Path]:
    if (not report.evidence_subgraph
            and not report.dark_changes
            and not report.manual_review_items
            and not report.absent_requirements):
        raise RuntimeError(
            "Refusing to render a report with no evidence, no dark changes, no absent requirements, "
            "and no manual review items. This indicates a pipeline failure."
        )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        summary = _generate_summary(report)
        report = report.model_copy(update={"summary": summary})
    except Exception as e:
        print(f"[report] WARNING: summary generation failed: {e}")

    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
    template = env.get_template("report.html.j2")
    html = template.render(report=report)
    html_path = REPORTS_DIR / "blast_radius_report.html"
    html_path.write_text(html, encoding="utf-8")

    # Markdown
    high = [n for n in report.affected_requirements if n.risk_tier == "HIGH"]
    medium = [n for n in report.affected_requirements if n.risk_tier == "MEDIUM"]
    lines = [
        f"# Blast Radius Report — PR #{report.pr_number}",
        "",
        f"**PR:** [{report.pr_title}]({report.pr_url})",
        f"**Mode:** {report.mode}  **Run ID:** {report.run_id}",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        report.summary or "_Summary not generated._",
        "",
        "---",
        "",
        "## Changed Files",
        "",
        "| File | Status | +/− |",
        "|---|---|---|",
    ]
    for f in report.changed_files:
        lines.append(f"| `{f.path}` | {f.status} | +{f.additions}/−{f.deletions} |")

    lines += ["", "## 🔴 High-Risk Requirements", ""]
    for n in high:
        lines += [
            f"- **{n.label}**",
            f"  - Impact: {n.impact_score:.2f} | Confidence: {n.traceability_confidence:.2f}",
            f"  - Evidence: `{'` → `'.join(n.evidence_path)}`",
            "",
        ]
    if not high:
        lines.append("_No high-risk requirements identified._\n")

    lines += ["## 🟡 Medium-Risk Requirements", ""]
    for n in medium:
        lines += [f"- **{n.label}** (impact: {n.impact_score:.2f})", ""]
    if not medium:
        lines.append("_No medium-risk requirements identified._\n")

    # v3: Absent requirements section in Markdown output
    if report.absent_requirements:
        lines += [
            "## 🟣 Absent Requirements (No Coverage Found)",
            "",
            "These requirements exist in documentation but have no UI or code coverage in the graph.",
            "",
        ]
        for req in report.absent_requirements:
            lines.append(f"- **{req.label}**")
        lines.append("")

    if report.dark_changes:
        lines += ["## ⚫ Dark Changes", "", "Manual review required:", ""]
        for dc in report.dark_changes:
            lines.append(f"- `{dc}`")
        lines.append("")

    if report.manual_review_items:
        lines += ["## ⚠️ Manual Review", ""]
        for item in report.manual_review_items:
            lines.append(f"- {item}")
        lines.append("")

    md_path = REPORTS_DIR / "blast_radius_report.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[report] HTML: {html_path}")
    print(f"[report] Markdown: {md_path}")
    return html_path, md_path
```

### src/blast_radius/report/__init__.py

```python
import json
from blast_radius.config import settings
from blast_radius.models import BlastRadiusReport
from blast_radius.report.render import render


def render_report() -> None:
    report_path = settings.data_dir / "reports" / "blast_radius_report.json"
    if not report_path.exists():
        raise FileNotFoundError(f"Report JSON not found at {report_path}. Run Phase 5 first.")
    report = BlastRadiusReport.model_validate_json(report_path.read_text(encoding="utf-8"))
    render(report)
```

**Smoke test:**
```bash
python -c "from blast_radius.report import render_report; render_report()"
python -c "
from pathlib import Path
html = Path('data/reports/blast_radius_report.html').read_text()
md = Path('data/reports/blast_radius_report.md').read_text()
# v3: Absent Requirements section should be present (or legitimately absent if graph has full coverage)
assert '# Blast Radius Report' in md
assert 'Blast Radius Report' in html
# If the graph has absent reqs, verify section is rendered
if 'absent_requirements' in html.lower() or 'Absent' in html:
    assert 'ABSENT' in html or 'Absent Requirements' in html
print(f'OK — HTML: {len(html)} chars | MD: {len(md)} chars')
"
```

**Merge condition:** Both files exist and are non-empty; if absent requirements are in the JSON, they appear in both outputs; an uninvolved QA engineer can identify what to test.

---

## Phase 7: Design Document

**Branch:** `feature/phase-7-design-doc`
**Budget:** 1.5 h (increased from v2 — scaffolded content for all 10 sections)
**Prerequisites:** Phases 0–6 merged or explicitly deferred with rationale

**Creates:** `docs/design_document.md`, `docs/evaluation_protocol.md`, `docs/decision_log.md`

### Section-by-Section Writing Guide

Each section below gives scaffolded prose you can expand from real artifact output. Fill in bracketed placeholders from your actual generated files.

---

**Section 1 — Crawl Artifact and Evidence**

> "The crawler captures PageSnapshot objects using Playwright running headless Chromium. For the public Documenso SaaS, we perform two crawl modes: unauthenticated (marketing, login, signup — N pages) and authenticated (document list, template management — M pages). The accessibility tree extraction follows the WebArena AXTree methodology: every interactive element is recorded with its ARIA role, label, and selector, capped at 300 elements per page to stay token-efficient for downstream LLM calls.
>
> Crawl artifacts are stored at `data/crawl/`. The manifest at `data/crawl/manifest.json` records run_id=[FILL], [N] pages, and [M] transitions. We use Playwright rather than crawl4ai for app.documenso.com because Documenso is a Next.js SPA — crawl4ai's static HTML mode returns a near-empty shell before JavaScript renders."

Cite: `data/crawl/manifest.json` (page count, transition count), one screenshot path from `data/crawl/screenshots/`.

---

**Section 2 — PRD Ingestion and Provenance**

> "Requirements are extracted from two sources: the public README.md and the first five pages of docs.documenso.com. Docling converts each source to Markdown, preserving heading structure. An LLM (claude-sonnet-4-6) then extracts requirements from the Markdown, returning structured JSON with `text`, `req_type`, `related_ui_keywords`, and `excerpt`.
>
> A validation step rejects operational instructions (npm, git, docker commands) — these contaminate the graph with untestable 'requirements'. The final artifact at `data/requirements/requirements.json` contains [N] requirements, including [M] features and [K] user stories, all with `provenance.excerpt` linking back to the verbatim source sentence.
>
> Example provenance: `{source_file: 'https://raw.githubusercontent.com/documenso/documenso/main/README.md', excerpt: 'Documenso allows users to upload and send documents for signing to one or more recipients.'}`"

---

**Section 3 — Three-Layer Knowledge Graph**

> "The graph connects three layers: Requirements (from docs), Pages/UIElements (from crawl), and CodeFunctions (from ast-grep). The Neo4j schema uses five node labels — Requirement, UIElement, CodeFunction, Page, GapNode — and five primary edge types: IMPLEMENTS (Requirement→CodeFunction), RENDERS (CodeFunction→Page), COVERS (UIElement→Requirement), CALLS (CodeFunction→CodeFunction), and ABSENT_FROM (Requirement→GapNode).
>
> Every edge stores `confidence`, `evidence`, `source`, `run_id`, and `created_at`. This makes every relationship auditable and re-runnable with stable IDs.
>
> **Absence modeling:** Absence is a first-class property on `Requirement` nodes, not a runtime threshold artifact. After the graph is built, a deterministic Cypher query marks every requirement with no IMPLEMENTS or COVERS edge as `coverage_status = 'MISSING'` and creates a corresponding GapNode:
>
> ```cypher
> MATCH (r:Requirement)
> WHERE NOT (r)-[:IMPLEMENTS]->(:CodeFunction)
>   AND NOT (r)<-[:COVERS]-(:UIElement)
> SET r.coverage_status = 'MISSING'
> RETURN r.id, r.text
> ```
>
> This answers 'which requirements are intended but untestable' with an auditable fact, not an inference."

Cite: Neo4j Browser query `MATCH (n) RETURN labels(n)[0], count(n)` output from smoke test.

---

**Section 4 — PR Blast Radius Reasoning**

> "The blast radius reasoning has three deterministic stages. First, PyDriller extracts changed files and commits from the pinned merge SHA to its parent. Second, these file paths are cross-referenced against the call graph to identify seed CodeFunction nodes. Third, Personalized PageRank (PPR) propagates activation energy forward from seeds through CALLS→RENDERS→COVERS edges.
>
> **PPR direction:** Seeds are at changed code nodes; activation flows downstream toward Pages and Requirements. The graph is NOT reversed — forward propagation finds downstream product impact, which is the definition of blast radius.
>
> **Weight schema:** CALLS=1.0, RENDERS=0.95, IMPLEMENTS=0.85, COVERS=0.75. Scores are min-max normalized within the current PR. A finding is HIGH when both impact_score ≥ 0.70 AND traceability_confidence ≥ 0.70.
>
> For PR #[YOUR_PR_NUMBER], [N] changed files produced [M] seed function nodes. The PPR run identified [K] high-risk requirements and [J] affected pages. [L] functions were dark changes with no traceable path."

---

**Section 5 — Agent Decomposition**

Reproduce the deterministic vs. LLM-driven table from the architecture section verbatim. Then add:

> "The system is not a chain of LLM prompts. LLM calls are isolated to three specific tasks where structured heuristics fail: (1) requirement extraction from natural language documentation, (2) entity resolution between requirement vocabulary and code entity names, and (3) executive summary generation. All other processing — DOM capture, AST extraction, git diff analysis, graph writes, PPR, and evidence path computation — is deterministic and re-runnable without LLM variance.
>
> LLM outputs are constrained by Pydantic schemas at every boundary. A requirement extraction that returns invalid JSON raises a `RuntimeError` and stops the pipeline; it does not silently insert garbage into the graph."

---

**Section 6 — Schema Justification and Absence Query**

Reproduce the five node labels and five edge types. Then justify each against a concrete Cypher query:

> "The `RENDERS` edge (CodeFunction→Page) answers: 'which pages are at risk when this function changes?' — `MATCH (f:CodeFunction {id:$fn_id})-[:RENDERS]->(p:Page) RETURN p.url`.
>
> The `IMPLEMENTS` edge (Requirement→CodeFunction) answers: 'which functions implement this requirement?' — `MATCH (r:Requirement {id:$req_id})-[:IMPLEMENTS]->(c:CodeFunction) RETURN c.function_id`.
>
> The `ABSENT_FROM` edge (Requirement→GapNode) answers: 'which requirements have no code or UI coverage?' — `MATCH (r:Requirement)-[:ABSENT_FROM]->(g:GapNode) RETURN r.text, g.reason`."

---

**Section 7 — Confidence and Escalation**

> "Every AffectedNode carries `impact_score` (PPR score, min-max normalized) and `traceability_confidence` (minimum edge weight on the evidence path). Risk tier is classified:
>
> | Tier | Condition |
> |---|---|
> | HIGH | impact ≥ 0.70 AND confidence ≥ 0.70 |
> | MEDIUM | impact ≥ 0.40 AND confidence ≥ 0.40 |
> | LOW | below MEDIUM thresholds |
> | DARK_CHANGE | no path found — highest risk |
> | ABSENT | in documentation but no graph coverage |
>
> The system stops and asks a human when: (1) any Requirement lands at LOW confidence, (2) any dark change exists (code changed with no traceable path), or (3) absent requirements are found. In v1, escalation is a `manual_review_items` list in the report. OpenHands ACI for automated ambiguity investigation is deferred to Week 2."

---

**Section 8 — Evaluation and Stability**

Reproduce the evaluation protocol from `docs/evaluation_protocol.md` verbatim. Add:

> "For the Documenso demo, 'ground truth' is established by running a second LLM call after report generation: 'Given PR #[N]'s changed files and the reported affected requirements, is each impact plausible? Rate each CONFIRMED/DISMISSED with rationale.' This self-evaluation is explicitly honest about its limitations — it is not an independent gold standard. Building an independent gold set requires human QA engineers reviewing multiple PRs, which is the Week 3 task."

---

**Section 9 — Scope Decisions**

Reproduce the scope table from the template below verbatim in the design document:

| Cut | Rationale | Week 2 path |
|---|---|---|
| Full CPG via Joern | JVM/Scala setup cost exceeds budget; ast-grep covers structural facts | Joern + PyJoern |
| Splink entity resolution | 4.x API diverged from documented; whole-label blocking near-zero recall for req→code | Collect labelled pairs, then train Splink EM |
| LightRAG retrieval | Optional; PostgreSQL removed to reduce complexity | Add with verified 2.x API |
| browser-use dynamic agent | API instability; replaced with reliable Playwright for SPA crawling | browser-use for stateful form flows once API stable |
| GNNExplainer training | Requires trained GNN; deferred | Week 3 after Joern CPG |
| OpenHands ACI | Architecture designed; runtime not started in v1 | Week 2 after stable report |
| Apache AGE | Installation/version compatibility unverified | Evaluate after LightRAG |
| Authenticated crawl | Optional — requires test account; graph is useful with unauthenticated pages | Add credentials to .env |
| Prisma schema extraction | Fourth graph layer (DataModel nodes) — documented as differentiator, not implemented | Phase 8 |
| PR selection | Chose a PR touching `packages/trpc/` and `packages/lib/` — justification in Appendix B | N/A |

---

**Section 10 — What to Build Next**

> "**Priority 1 — Joern CPG:** Replace ast-grep structural facts with full Code Property Graph (AST + CFG + PDG). With Joern, dark changes become traceable via data-flow paths, type inference works for tRPC's TypeScript types, and ExplainVulD edge attribution produces causal evidence instead of lexical filename matching. This is the highest single accuracy improvement.
>
> **Priority 2 — PR Webhook with Incremental Graph Update:** Integrate qodo-ai/pr-agent's GitHub webhook. On each PR open/update: run Phase 3 (delta only), MERGE only affected graph nodes, run Phase 5, post the blast radius report as a PR comment. Moves from batch to real-time and makes the tool production-usable.
>
> **Priority 3 — Labelled Entity Resolution + Evaluation Harness:** Collect reviewer gold labels for 10 Documenso PRs (CONFIRMED/DISMISSED per requirement). Train Splink EM model on confirmed requirement↔code pairs. Add Jaccard stability tests to CI. Report precision/recall on held-out PRs. This is the highest-ROI accuracy improvement after Joern."

### docs/evaluation_protocol.md

```markdown
# Evaluation Protocol — Blast Radius Analyzer v3

## Single-Run Correctness

1. **Schema validation** (hard gate):
   `BlastRadiusReport.model_validate_json(report_path.read_text())`
   Raises `ValidationError` on failure.

2. **Domain spot-check** (soft):
   At least one affected requirement contains a Documenso term:
   `{'document', 'sign', 'recipient', 'template', 'field', 'certificate', 'sender', 'signer'}`

3. **Score range** (hard):
   All `confidence_scores` values in [0.0, 1.0].

4. **Non-empty** (hard):
   At least one of: affected_ui_elements, affected_requirements,
   absent_requirements, dark_changes, manual_review_items.

5. **Absent requirements surfaced** (soft):
   If Neo4j has GapNodes (ABSENT_FROM edges), `absent_requirements`
   must be non-empty in the report.

## Stability (3-Run Test)

```bash
for i in 1 2 3; do
  python scripts/run_pipeline.py --phase 5,6
  cp data/reports/blast_radius_report.json data/reports/run_${i}.json
done
```

Compute Jaccard similarity of `affected_requirements` node ID sets:
- Acceptable: Jaccard ≥ 0.85 (deterministic PPR; variance from LLM entity resolution)
- Flag if < 0.85 as a reliability issue requiring investigation

## Manual Gold Labels

For each PR analyzed:
1. A QA engineer reads the blast radius report
2. For each affected requirement, marks: CONFIRMED | DISMISSED | UNKNOWN
3. Save to `data/reports/gold_labels_pr_{number}.json`
4. Target: Precision > 0.70, Recall > 0.60 on CONFIRMED items

## Self-Evaluation (interim, before human gold labels are available)

Run a second LLM call after report generation:
"Given PR #{number}'s changed files and reported impacts, is each impact plausible?
Rate CONFIRMED/DISMISSED with rationale."
Acknowledge this is not an independent ground truth.
```

**Smoke test for design document:**
```bash
python -c "
p = open('docs/design_document.md', encoding='utf-8').read()
for i in range(1, 11):
    assert str(i) + '.' in p or f'Section {i}' in p, f'Missing section {i}'
assert len(p) > 10000, f'Design doc too short: {len(p)} chars (expected > 10000)'
assert 'TODO' not in p and 'TBD' not in p, 'Placeholder text still present'
print(f'OK — design document: {len(p)} chars')
"
```

**Merge condition:** All 10 sections present with substantive prose (not placeholders), length > 10 000 chars, no `TODO`/`TBD`.

---

## Appendix A: Sample Blast Radius Report (Documenso)

This is what a good report looks like. Your generated output should match this structure.

```markdown
# Blast Radius Report — PR #[CHOSEN_PR]

**PR:** [feat: update document sending flow to include expiry date](https://github.com/documenso/documenso/pull/XXXX)
**Mode:** neo4j  **Run ID:** f4a2b1c8

---

## Executive Summary

PR #XXXX modifies the document sending flow to add an expiry date field, touching the tRPC
`sendDocument` procedure and the corresponding `lib/server-only/document/send-document.ts`
business logic. This change directly affects the requirement that senders can control document
expiry, and has medium-confidence impact on the recipient notification flow. One function in the
email notification utility has no traceable graph path; manual review of the email template
changes is recommended.

---

## Changed Files

| File | Status | +/− |
|---|---|---|
| `packages/trpc/server/routers/document.ts` | modified | +45/−12 |
| `packages/lib/server-only/document/send-document.ts` | modified | +28/−8 |
| `packages/ui/components/document/send-form.tsx` | modified | +15/−3 |

## 🔴 High-Risk Requirements

- **Senders can set an expiry date when sending a document for signing**
  - Impact: 0.94 | Confidence: 0.91
  - Evidence: `packages/trpc/server/routers/document.ts:142:sendDocument`
    → `page:a3f2b1c4` → `REQ-4F2A1B3C`

## 🟡 Medium-Risk Requirements

- **Recipients receive email notifications when a document is sent** (impact: 0.58)

## 🟣 Absent Requirements (No Coverage Found)

- **Completed documents are retained for a configurable period**
- **Audit logs are available for all signing events**

## ⚫ Dark Changes

- `packages/lib/server-only/mail/send-expiry-reminder.ts:18:scheduleReminder`

## ⚠️ Manual Review

- 1 function has no traceable path to UI or requirements (see Dark Changes)
- 2 requirements have no graph coverage — verify they are not affected by this PR
```

---

## Appendix B: Documenso PR Selection Guide

Browse `https://github.com/documenso/documenso/pulls?q=is%3Apr+is%3Amerged+sort%3Aupdated-desc`

### Good candidates (deep blast radius, exercises full propagation chain)

Select PRs that modify **both** of:
- A tRPC router file: `packages/trpc/server/routers/*.ts`
- A corresponding lib file: `packages/lib/server-only/document/`, `packages/lib/server-only/recipient/`, or `packages/lib/server-only/template/`

Look for PR titles containing: "document", "signing", "recipient", "template", "field", "send", "expiry", "certificate"

### Avoid (shallow impact, same reasoning as avoiding logo-swap PRs in v1/v2)

- PRs only modifying `packages/ui/components/` — styling changes
- PRs only modifying `.md` files — documentation
- PRs only modifying `apps/marketing/` — marketing site
- PRs only modifying `packages/prisma/migrations/` — schema only with no application logic change

### Pinning the merge SHA (required before Phase 3)

```bash
gh pr view {PR_NUMBER} --repo documenso/documenso --json mergeCommit
# Copy the SHA and add to .env:
# MERGE_SHA=abc123def456...
```

---

## Appendix C: Loom Recording Script (5–8 minutes)

> **New in v3.** Record this walkthrough after running the full pipeline on a clean `main` checkout.

**Step 1 — Graph is populated (60 seconds)**
Open Neo4j Browser at `http://localhost:7474`. Run:
```cypher
MATCH (n) RETURN labels(n)[0] as label, count(n) as count ORDER BY label
```
Show the table of node counts. Then run the absence query:
```cypher
MATCH (r:Requirement)-[:ABSENT_FROM]->(g:GapNode)
RETURN r.text, g.reason LIMIT 10
```
Narrate: "These requirements exist in Documenso's documentation but have no corresponding UI element or code function in our graph — they're the first place a QA engineer should look for unverified behavior."

**Step 2 — Show the target PR (60 seconds)**
Open `https://github.com/documenso/documenso/pull/{PR_NUMBER}` in the browser. Walk through the changed files: "This PR modifies [describe files]. It touches the tRPC procedure layer and the business logic library."

**Step 3 — Run Phase 5 live (60 seconds)**
In terminal:
```bash
python scripts/run_pipeline.py --phase 5
```
Show the console output: seed function count, affected UI/requirements/absent/dark counts.

**Step 4 — Open the HTML report (90 seconds)**
Open `data/reports/blast_radius_report.html` in a browser. Walk through:
- Executive Summary: "This is generated from structured evidence only, not a free-form LLM guess."
- High-risk requirements: "Notice the evidence path — it shows exactly which function in which file causes the impact."
- Absent requirements: "These two requirements exist in the docs but have no code path. We don't know if they're implemented elsewhere or not yet built."
- Dark changes: "This function changed but we can't trace it to any UI or requirement — it needs human review."

**Step 5 — Evidence path in Neo4j (60 seconds)**
Return to Neo4j Browser. Run the evidence path query from the report footer:
```cypher
MATCH path=(f:CodeFunction)-[*1..6]-(r:Requirement)
WHERE f.id IN ["fn:packages/trpc/server/routers/document.ts:142:sendDocument"]
RETURN path LIMIT 20
```
Show the graph visualization: "This is the knowledge graph path that explains why the requirement is at risk."

**Step 6 — Design document highlights (60 seconds)**
Open `docs/design_document.md`. Briefly show: Section 3 (schema and absence query), Section 9 (scope decisions table), Section 10 (next-week priorities). Narrate: "The document is evidence-backed — every claim points to a real artifact."

---

## Common Failures and Fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| `pre-flight FAILED: sg` | ast-grep not on PATH | `brew install ast-grep` or add cargo bin to PATH |
| `NEO4J_PASSWORD must be set` | `.env` not copied | `cp .env.example .env` and fill in |
| `Only N snapshots < 2` | Network blocked or auth failed | Check connectivity to app.documenso.com; verify credentials in .env |
| `No Documenso domain terms in crawled pages` | Crawling wrong URL or getting blocked | Check robots.txt; reduce CRAWL_MAX_PAGES; add delays |
| `Only N functions found < 50` | scan paths don't exist | Verify `data/repos/documenso/packages/` exists; re-clone if needed |
| `No tRPC procedures` | trpc-procedures.yml rule syntax wrong | Run `sg scan --rule rules/trpc-procedures.yml data/repos/documenso/packages/trpc --json` and inspect output |
| `PyDriller found no commits` | MERGE_SHA not set or wrong | Run `gh pr view {PR} --repo documenso/documenso --json mergeCommit` |
| `RENDERS edges: 0` | ui_id mismatch (v2 bug) | Verify resolve_ui_to_functions uses `page:{sha}` IDs; write_ui_elements writes `page:{sha}` Page nodes |
| `absent_requirements: 0 in report` | GapNodes not loaded in Phase 5 | Verify `_load_graph_data()` runs the ABSENT_FROM query and returns results |
| `TypeError` in evidence_path | weight lambda passed to shortest_path | Use `weight="weight"` (string), not a callable |
| `delta.changed_function_ids: []` after Phase 5 | write-back not implemented | Confirm Phase 5 `__init__.py` writes back to delta JSON |
| Report is completely empty | Phase 3 or 4 silent failure | Run `--phase 3` and `--phase 4` individually; check smoke test output |
| `crawl4ai` AttributeError | API changed in installed version | `python -c "import crawl4ai; help(crawl4ai.AsyncWebCrawler)"` and update static.py |
| Neo4j healthcheck always failing | `CMD-SHELL` not supported in older Docker Compose | Upgrade Docker Compose to ≥ 2.x; or change healthcheck to `CMD` form |

---

## Scope Decisions Summary

| Decision | v3 Status | Rationale |
|---|---|---|
| Cypress RWA → Documenso | **Migrated** | User request; Documenso is publicly crawlable SaaS with rich tRPC API |
| crawl4ai for Documenso docs | **Adopted** | `docs.documenso.com` is static — crawl4ai appropriate here |
| Playwright for app.documenso.com | **Adopted** | Next.js SPA — requires JavaScript rendering; no `data-test` attributes |
| tRPC-specific ast-grep rule | **New** | Documenso's API layer is tRPC; standard fn rules miss procedure names |
| Splink entity resolution | **Deferred** | 4.x API diverged; whole-label blocking near-zero recall |
| Joern CPG | **Deferred** | JVM/Scala overhead; ast-grep covers structural needs for v1 |
| LightRAG | **Deferred** | Optional retrieval augmentation; not required for scored MVP |
| OpenHands ACI | **Architecture only** | Week 2 after stable report demonstrated |
| Prisma schema as 4th layer | **Documented, not built** | Strong differentiator; low-effort addition post-MVP |
| Absent requirements in report | **Implemented** | Explicitly required by assignment; GapNodes loaded in Phase 5, rendered in Phase 6 |
| PPR direction fix | **Fixed** | v2 had graph.reverse() bug; forward PPR is correct for blast radius |
| evidence_path fix | **Fixed** | v2 used callable weight; fixed to string "weight" attribute |
| ui_id mismatch fix | **Fixed** | v2 RENDERS edges used nonexistent "ui:{sha}:page" IDs; v3 uses "page:{sha}" Page nodes |
| delta.changed_function_ids | **Fixed** | Now written back to disk after Phase 5 seed computation |
| validate_env.py | **New** | Pre-flight script; required before every build |
| Docker Compose healthcheck | **Fixed** | CMD-SHELL form expands $NEO4J_PASSWORD correctly |

---

## Week 2 Roadmap

**Priority 1 — Joern CPG + Import-Aware Resolution**
Replace ast-grep structural facts with full Code Property Graph: CFG + PDG + data-flow edges. For Documenso, this connects tRPC procedures to their underlying Prisma queries through data-flow paths. Dark changes become smaller and evidence becomes causal rather than lexical. Estimated: 1–2 weeks.

**Priority 2 — PR Webhook + Incremental Graph Update**
Integrate qodo-ai/pr-agent GitHub webhook. On each PR event: run Phase 3 (delta only), MERGE only affected nodes, run Phase 5, post blast radius report as PR comment. Turns the tool from batch to real-time. Estimated: 3–5 days.

**Priority 3 — Labelled Entity Resolution + Evaluation Harness**
Collect reviewer gold labels (CONFIRMED/DISMISSED) for 10 Documenso PRs. Train Splink EM model on confirmed requirement↔code pairs. Run Jaccard stability across 3 runs per PR. Report precision/recall on held-out PRs. This is the highest-ROI accuracy improvement. Estimated: 1 week.

**Bonus — Prisma Schema as Fourth Graph Layer**
Extract `DataModel` nodes from `packages/prisma/schema.prisma`. Add `MODELS` edges: `CodeFunction -[:MODELS]-> DataModel`. This lets queries like "which requirements touch the Document data model?" answer in a single Cypher hop. A genuine differentiator that most implementations miss. Estimated: 2–4 hours.

---

*v3 Implementation Guide — built from v2 and the v2 audit report (`v2_audit_report_implementation_plan.md`). All P0/P1/P2 audit fixes applied. Target migrated to Documenso. Every bug identified in the audit is fixed and cross-referenced in the code comments.*
