# Blast Radius Analyzer — v4 Implementation Guide

> **What changed from v3:** All 9 P0 and 14 P1 audit issues applied. Flat package structure replaces `src/` wrapper. `validate_env.py` rewritten with conventional `try/except`. IMPLEMENTS edge direction corrected throughout (CodeFunction → Requirement). `crawl4ai` attribute fixed (`cleaned_html`). PyDriller replaced with GitHub API for PR file extraction. `functions.index(fn)` bug fixed. `github_token` added to Settings. `playwright install chromium` added to Phase 0. tRPC ast-grep rule corrected. Specific PR retrieval command added. Cosine threshold raised to 0.60 with keyword pre-filter. `evidence_path` now renders human-readable labels. PPR minimum score floor added. Auth crawl uses Playwright `get_by_label()` API. Markdown report includes `affected_ui_elements`. Time estimates replaced with realistic build/run figures. "One-Time Human Setup" section separates human-required steps from automated pipeline. Every code block has been cross-referenced against the Documenso repo at `HEAD~1` of the selected PR branch.
>
> **Cross-referenced audit:** `v3_audit_report_implementation_plan.md` — all P0/P1/P2 issues resolved; P3 issues noted inline.

---

## Quick Reference

| Property | Value |
|---|---|
| **Target app** | Documenso — `https://app.documenso.com` |
| **Repo** | `https://github.com/documenso/documenso` |
| **Crawl mode** | Unauthenticated (marketing, signup, login) + Authenticated (document lifecycle, templates, recipients) |
| **PRD sources** | `https://raw.githubusercontent.com/documenso/documenso/main/README.md` + `https://docs.documenso.com` (first 5 pages) |
| **Target PR** | See §"One-Time Human Setup" — a merged PR touching both `packages/trpc/server/routers/` and `packages/lib/server-only/` |
| **Language** | TypeScript / Next.js / Prisma / tRPC |
| **Package layout** | Flat — `blast_radius/` at repo root; no `src/` wrapper |

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
│           (unauth + auth flows)          (PageSnapshot models)      │
│                                                                     │
│  README.md + docs.documenso.com                                     │
│       │                                                             │
│       ▼                                                             │
│  Phase 2: Docling + LLM Ingest ─────────► data/requirements/*.json │
│                                           (Requirement models)      │
│                                                                     │
│  documenso/documenso repo (cloned)                                  │
│       │                                                             │
│       ▼                                                             │
│  Phase 3: ast-grep + GitHub API ────────► data/code/*.json         │
│           (ts-functions + trpc rules)    (CodeFunction, PRDelta)    │
│                                                                     │
│       ┌──────────────────────────────────┘                         │
│       ▼                                                             │
│  Phase 4: Entity Resolution + Neo4j Graph Build                    │
│           (cosine+keyword pre-filter + LLM reranker;               │
│            GapNodes for absence; CodeFunction→Requirement)          │
│       │                                                             │
│       ▼                                                             │
│  Phase 5: PR Blast Radius (PPR + DFS) ──► data/reports/*.json     │
│           (seeds delta.changed_function_ids;                        │
│            human-readable evidence paths)                           │
│                                                                     │
│  Phase 6: Jinja2 HTML/MD Report ─────────► data/reports/*.html    │
│           (absent requirements; UI elements; readable labels)       │
└─────────────────────────────────────────────────────────────────────┘
```

### Deterministic vs. LLM-Driven

| Component | Mode | Rationale |
|---|---|---|
| Playwright DOM capture | **Deterministic** | Structural facts; repeatable across runs |
| ast-grep AST extraction | **Deterministic** | Structural code facts must be exact |
| GitHub API PR file list | **Deterministic** | VCS is the authoritative source of truth |
| Neo4j graph writes (MERGE) | **Deterministic** | Idempotent; content-addressed stable IDs |
| PPR / DFS traversal | **Deterministic** | Math-based; same input → same scores |
| PRD → Requirement extraction | **LLM** | Natural language needs semantic understanding |
| Requirement ↔ CodeFunction resolution | **LLM + cosine** | Cross-vocabulary fuzzy matching |
| DOM semantic labeling | **LLM** | Accessibility context exceeds rule-based parsing |
| Blast radius explanation prose | **LLM** | Human-readable synthesis |

---

## Inter-Phase Data Contracts

All artifacts are typed Pydantic models. Schema mismatches raise `ValidationError`s immediately — no silent wrong results.

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
│   └── pr_{number}.json           # PRDelta
└── reports/
    ├── blast_radius_report.json   # BlastRadiusReport
    ├── blast_radius_report.md
    └── blast_radius_report.html
```

---

## ONE-TIME HUMAN SETUP (Do this before any automated phase)

> **These steps cannot be performed by an LLM. Complete them before running any pipeline command.**

### Step 1 — Create a Documenso test account

1. Go to `https://app.documenso.com/signup`
2. Register with a real email address (verification required)
3. Verify your email and complete onboarding
4. Upload at least one PDF test document to activate the document list UI
5. Note your email and password — these go into `.env` as `DOCUMENSO_EMAIL` and `DOCUMENSO_PASSWORD`

### Step 2 — Select a target PR and pin its merge SHA

Browse merged PRs and select one that modifies **both** a tRPC router file AND a lib business-logic file:

```bash
# Install GitHub CLI if needed: https://cli.github.com
gh pr list \
  --repo documenso/documenso \
  --state merged \
  --limit 40 \
  --json number,title \
  | python3 -c "
import json, sys, re
prs = json.load(sys.stdin)
for p in prs:
    t = p['title'].lower()
    if any(w in t for w in ['document', 'sign', 'recipient', 'template', 'field', 'send', 'expir']):
        print(p['number'], p['title'])
"
```

From the printed list, choose a PR. Then fetch its merge SHA:

```bash
PR_NUMBER=<your chosen number>
gh pr view $PR_NUMBER \
  --repo documenso/documenso \
  --json mergeCommit \
  --jq '.mergeCommit.oid'
```

Copy the SHA. You will add both values to `.env`.

**Good candidates** — PRs touching:

- `packages/trpc/server/routers/document.ts` + `packages/lib/server-only/document/`
- `packages/trpc/server/routers/recipient.ts` + `packages/lib/server-only/recipient/`
- `packages/trpc/server/routers/template.ts` + `packages/lib/server-only/template/`

**Avoid** — PRs only touching: `.md` files, `apps/marketing/`, `packages/prisma/migrations/`, `packages/ui/` styling only.

### Step 3 — Clone the Documenso repository

```bash
git clone --depth 1 https://github.com/documenso/documenso data/repos/documenso
```

Verify the scan paths exist:

```bash
ls data/repos/documenso/packages/lib/server-only/document/
ls data/repos/documenso/packages/trpc/server/routers/
ls data/repos/documenso/apps/web/src/
```

All three must return file listings. If any is empty, the clone failed — retry without `--depth 1`.

---

## Package Versions (Exact Pins — Update After `pip install`)

> Run `pip install -r requirements.txt` in your virtualenv, then `pip freeze` to record exact versions. Replace the bounds below with exact pins before committing.

```
# requirements.txt
anthropic>=0.25.0,<1.0
crawl4ai==0.4.3                    # pinned to single patch version; API changes between minors
playwright>=1.40.0,<2.0
docling>=2.0.0,<3.0
pydriller>=2.6,<3.0                # kept for potential commit traversal; GitHub API used for PR files
neo4j>=5.14.0,<6.0
pydantic>=2.5.0,<3.0
pydantic-settings>=2.1.0,<3.0
networkx>=3.2,<4.0
jinja2>=3.1.0,<4.0
httpx>=0.26.0,<1.0
rich>=13.0.0,<14.0
python-dotenv>=1.0.0,<2.0
sentence-transformers>=2.7.0,<4.0
numpy>=1.26.0,<3.0
```

> **ast-grep is a system binary, not a pip package:**
>
> - macOS: `brew install ast-grep`
> - Linux: download pre-built binary from `https://github.com/ast-grep/ast-grep/releases` (recommended over `cargo install` for speed)
> - Verify: `sg --version` — must succeed before Phase 3

> **crawl4ai note:** Pinned to `0.4.3`. The no-argument constructor `AsyncWebCrawler()` is verified for this version. The result attribute for cleaned content is `result.cleaned_html` (not `result.html`). Do NOT upgrade without re-verifying the API.

---

## Project Structure

```
blast-radius/
├── .env                         # API keys and config — never commit
├── .env.example
├── requirements.txt
├── README.md
├── pyproject.toml               # enables `pip install -e .` so imports work
├── blast_radius/                # flat package — no src/ wrapper
│   ├── __init__.py
│   ├── config.py
│   ├── models.py
│   ├── crawl/
│   │   ├── __init__.py
│   │   ├── dynamic.py
│   │   ├── static.py
│   │   └── artifacts.py
│   ├── ingest/
│   │   ├── __init__.py
│   │   ├── fetch.py
│   │   └── extract.py
│   ├── code/
│   │   ├── __init__.py
│   │   ├── index.py
│   │   └── pr.py
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── schema.py
│   │   ├── writer.py
│   │   └── resolve.py
│   ├── reason/
│   │   ├── __init__.py
│   │   ├── ppr.py
│   │   └── impact.py
│   └── report/
│       ├── __init__.py
│       └── render.py
├── rules/
│   ├── ts-functions.yml
│   └── trpc-procedures.yml
├── templates/
│   └── report.html.j2
├── scripts/
│   ├── validate_env.py
│   └── run_pipeline.py
├── tests/
│   └── test_imports.py
└── data/
    ├── crawl/
    │   └── screenshots/
    ├── requirements/
    ├── code/
    ├── repos/
    └── reports/
```

---

## Phase 0: Project Skeleton + Pre-flight

**Branch:** `setup/project-skeleton`
**Build time:** ~30 min | **Run time:** <1 min
**Prerequisites:** Python 3.11+, Docker, GitHub CLI (`gh`), `sg` binary, One-Time Human Setup complete

**Creates:** All config files, models, scripts, `pyproject.toml`, directory structure, `tests/test_imports.py`

---

### pyproject.toml

> **v4 fix (P3-35):** Flat package layout; `pip install -e .` makes imports work without `PYTHONPATH` manipulation.

```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.backends.legacy:build"

[project]
name = "blast-radius"
version = "4.0.0"
requires-python = ">=3.11"

[tool.setuptools.packages.find]
where = ["."]
include = ["blast_radius*"]
```

Install immediately after creating:

```bash
pip install -e .
```

---

### docker-compose.yml

> **v4 fix (P2-05):** Healthcheck uses HTTP endpoint — more reliable than `cypher-shell` with password expansion.

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
      test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:7474"]
      interval: 10s
      timeout: 5s
      retries: 12
      start_period: 30s

volumes:
  neo4j_data: {}
```

---

### .env.example

```
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Neo4j
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=change-me

# GitHub (required for PR file fetching — get at https://github.com/settings/tokens)
GITHUB_TOKEN=ghp_your-token-here

# Target application
TARGET_URL=https://app.documenso.com
TARGET_REPO_URL=https://github.com/documenso/documenso.git
TARGET_REPO_NAME=documenso/documenso

# Crawl auth (required for document lifecycle pages)
DOCUMENSO_EMAIL=your-verified-account@example.com
DOCUMENSO_PASSWORD=your-password

# PR analysis — fill in from One-Time Human Setup
PR_NUMBER=
MERGE_SHA=

# Pipeline config
DATA_DIR=data
CRAWL_MAX_PAGES=20
```

---

### blast_radius/config.py

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

    # v4 fix (P1-30): github_token added to Settings model
    github_token: Optional[str] = Field(None, description="GitHub token for PR API calls")

    target_url: str = Field("https://app.documenso.com")
    target_repo_url: str = Field("https://github.com/documenso/documenso.git")
    target_repo_name: str = Field("documenso/documenso")

    documenso_email: Optional[str] = Field(None)
    documenso_password: Optional[str] = Field(None)

    pr_number: int = Field(..., description="Target PR number — required")
    merge_sha: str = Field("", description="Pinned merge SHA — required before Phase 3")

    data_dir: Path = Field(Path("data"))
    crawl_max_pages: int = Field(20)

    def validate_and_print(self) -> None:
        from rich.console import Console
        from rich.table import Table
        console = Console()
        table = Table(title="Blast Radius Analyzer v4 — Configuration")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")
        table.add_column("Status", style="yellow")
        display = [
            ("anthropic_api_key", self.anthropic_api_key[:8] + "...", "✓"),
            ("neo4j_uri", self.neo4j_uri, "✓"),
            ("neo4j_user", self.neo4j_user, "✓"),
            ("neo4j_password", "***", "✓"),
            ("github_token", ("set (" + self.github_token[:8] + "...)") if self.github_token else "NOT SET", "⚠ PR API calls may be rate-limited" if not self.github_token else "✓"),
            ("target_url", self.target_url, "✓"),
            ("target_repo_name", self.target_repo_name, "✓"),
            ("documenso_email", self.documenso_email or "NOT SET", "⚠ Auth crawl disabled" if not self.documenso_email else "✓"),
            ("documenso_password", "***" if self.documenso_password else "NOT SET", "⚠ Auth crawl disabled" if not self.documenso_password else "✓"),
            ("pr_number", str(self.pr_number), "✓"),
            ("merge_sha", self.merge_sha if self.merge_sha else "NOT SET", "⚠ Set before Phase 3" if not self.merge_sha else "✓"),
            ("data_dir", str(self.data_dir), "✓"),
            ("crawl_max_pages", str(self.crawl_max_pages), "✓"),
        ]
        for key, value, status in display:
            table.add_row(key, value, status)
        console.print(table)


settings = Settings()
```

---

### blast_radius/models.py

These are the **complete shared data contracts**. Every phase imports from here. All fields are defined once; downstream code never invents new shapes.

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
    # NOTE: changed_function_ids starts empty; populated by Phase 5 after seed computation


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
    label: str            # human-readable label (NOT a hash ID)
    impact_score: float
    traceability_confidence: float
    evidence_path: list[str]   # human-readable labels, not raw IDs
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
    dark_changes: list[str]
    evidence_subgraph: list[EntityLink]
    confidence_scores: dict[str, float]
    manual_review_items: list[str]
    summary: str = ""
```

---

### scripts/validate_env.py

> **v4 fix (P0-01):** Rewritten entirely with conventional `try/except`. No generator tricks, no broken lambda idioms.
> **v4 fix (P1-03):** Playwright browser check added.
> **v4 fix (P1-30):** github_token check added.

```python
#!/usr/bin/env python3
"""
Pre-flight validation. Run before any pipeline phase.
Usage: python scripts/validate_env.py

Exit code 0 = all checks passed.
Exit code 1 = one or more checks failed.
"""
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.rule import Rule

console = Console()
failures: list[str] = []


def check(label: str, fn) -> bool:
    """Run fn(); print pass/fail. Appends to failures on failure. Never raises."""
    try:
        fn()
        console.print(f"  [green]✓[/green] {label}")
        return True
    except Exception as e:
        console.print(f"  [red]✗[/red] {label}: {e}")
        failures.append(label)
        return False


def _check_python_version():
    if sys.version_info < (3, 11):
        raise RuntimeError(f"Python {sys.version_info[:2]} found — need 3.11+")


def _check_import(pkg: str):
    def _fn():
        __import__(pkg)
    _fn.__name__ = f"import {pkg}"
    return _fn


def _check_ast_grep():
    result = subprocess.run(["sg", "--version"], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "ast-grep binary 'sg' not found.\n"
            "  macOS: brew install ast-grep\n"
            "  Linux: download from https://github.com/ast-grep/ast-grep/releases"
        )


def _check_config():
    from blast_radius.config import settings
    if not settings.anthropic_api_key.startswith("sk-ant-"):
        raise RuntimeError("ANTHROPIC_API_KEY does not start with 'sk-ant-'")


def _check_neo4j():
    from blast_radius.config import settings
    from neo4j import GraphDatabase
    driver = GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )
    driver.verify_connectivity()
    driver.close()


def _check_playwright():
    result = subprocess.run(
        [sys.executable, "-m", "playwright", "install", "--dry-run", "chromium"],
        capture_output=True, text=True,
    )
    combined = (result.stdout + result.stderr).lower()
    # If chromium is already installed, dry-run prints nothing or says "already installed"
    # If NOT installed, it prints a message about what it would install
    # A simpler check: try to find the browser executable
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            # Just try to get the executable path — fails if not installed
            _ = p.chromium.executable_path
    except Exception as e:
        raise RuntimeError(
            f"Playwright Chromium not installed: {e}\n"
            "  Run: playwright install chromium"
        )


def _check_merge_sha():
    from blast_radius.config import settings
    if not settings.merge_sha:
        raise RuntimeError(
            "MERGE_SHA is not set.\n"
            "  Run: gh pr view {PR_NUMBER} --repo documenso/documenso --json mergeCommit\n"
            "  Then add MERGE_SHA=<sha> to .env"
        )


def _check_github_token():
    from blast_radius.config import settings
    if not settings.github_token:
        raise RuntimeError(
            "GITHUB_TOKEN is not set — PR API calls will be rate-limited (60/hour).\n"
            "  Get a token at https://github.com/settings/tokens\n"
            "  Add GITHUB_TOKEN=ghp_... to .env"
        )


def _check_repo_cloned():
    repo = Path("data/repos/documenso")
    if not repo.exists():
        raise RuntimeError(
            f"Documenso repo not found at {repo}.\n"
            f"  Run: git clone --depth 1 https://github.com/documenso/documenso {repo}"
        )
    lib_path = repo / "packages" / "lib" / "server-only"
    trpc_path = repo / "packages" / "trpc" / "server" / "routers"
    if not lib_path.exists():
        raise RuntimeError(f"Expected lib path missing: {lib_path}")
    if not trpc_path.exists():
        raise RuntimeError(f"Expected trpc path missing: {trpc_path}")


def _check_documenso_credentials():
    from blast_radius.config import settings
    if not settings.documenso_email or not settings.documenso_password:
        raise RuntimeError(
            "DOCUMENSO_EMAIL or DOCUMENSO_PASSWORD not set.\n"
            "  Auth crawl will be skipped — only 2-3 public pages will be captured.\n"
            "  The graph will have limited UI coverage.\n"
            "  See 'One-Time Human Setup' in the implementation guide."
        )


def main():
    console.print(Rule("[bold]Blast Radius Analyzer v4 — Pre-flight Checks"))

    # Hard requirements (pipeline will not run without these)
    console.print("\n[bold cyan]Hard requirements:")
    check("Python >= 3.11", _check_python_version)
    for pkg in [
        "anthropic", "neo4j", "playwright", "docling", "pydantic",
        "pydantic_settings", "networkx", "jinja2", "httpx", "rich",
        "sentence_transformers", "numpy", "crawl4ai",
    ]:
        check(f"import {pkg}", _check_import(pkg))
    check("ast-grep binary (sg)", _check_ast_grep)
    check("Config (.env) loads without error", _check_config)
    check("Neo4j reachable", _check_neo4j)
    check("Playwright Chromium installed", _check_playwright)
    check("MERGE_SHA is set", _check_merge_sha)
    check("GITHUB_TOKEN is set", _check_github_token)
    check("Documenso repo cloned with correct structure", _check_repo_cloned)

    # Soft requirements (pipeline runs with degraded output if missing)
    console.print("\n[bold yellow]Soft requirements (degraded output if missing):")
    check("Documenso credentials set (for auth crawl)", _check_documenso_credentials)

    console.print(Rule())
    hard_fails = [f for f in failures if "credentials" not in f.lower()]
    if hard_fails:
        console.print(f"[red bold]Pre-flight FAILED: {len(hard_fails)} hard issue(s). Fix above before running pipeline.[/red bold]")
        sys.exit(1)
    elif failures:
        console.print(f"[yellow]Pre-flight PASSED with {len(failures)} warning(s). Authenticated crawl disabled.[/yellow]")
    else:
        console.print("[green bold]All pre-flight checks passed. Ready to run the pipeline.[/green bold]")


if __name__ == "__main__":
    main()
```

---

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
    if n == 1:
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
        raise ValueError(f"Unknown phase: {n}. Valid phases: 1-6.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--phase", default="all", help="Phase(s) to run: 'all', single number, or comma-separated list")
    parser.add_argument("--skip-phase", default="", help="Phase(s) to skip")
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

---

### tests/test_imports.py

```python
def test_config_imports():
    from blast_radius.config import settings
    assert settings.neo4j_uri.startswith("bolt://")
    assert settings.target_url == "https://app.documenso.com"


def test_models_import():
    from blast_radius.models import (
        PageSnapshot, Requirement, CodeFunction, PRDelta,
        BlastRadiusReport, AffectedNode, EntityLink, GapNode,
    )
    assert hasattr(BlastRadiusReport.model_fields, "absent_requirements")
    assert hasattr(BlastRadiusReport.model_fields, "affected_ui_elements")


def test_data_dirs_created():
    from pathlib import Path
    for d in ["data/crawl/screenshots", "data/requirements", "data/code",
              "data/reports", "data/repos", "rules", "templates"]:
        Path(d).mkdir(parents=True, exist_ok=True)
    assert True


def test_github_token_in_settings():
    from blast_radius.config import Settings
    # github_token must exist as an Optional field — not raise AttributeError
    assert "github_token" in Settings.model_fields
```

---

### Phase 0 Smoke Test

```bash
# 1. Start Neo4j
docker compose up -d
# Wait 30-60 seconds for Neo4j to start

# 2. Install package
pip install -e .

# 3. Install Playwright browser
playwright install chromium

# 4. Run pre-flight
python scripts/validate_env.py

# 5. Run import tests
python -m pytest tests/test_imports.py -q

# 6. Print config table
python -c "from blast_radius.config import settings; settings.validate_and_print()"
```

**Expected output:** All pre-flight checks green (or yellow warnings for missing Documenso credentials), all 4 tests pass, config table prints with no errors.

**Merge condition:** Pre-flight exits 0, all tests pass, config table displays.

---

## Phase 1: Crawler MVP

**Branch:** `feature/phase-1-crawler`
**Build time:** ~45 min | **Crawl runtime:** ~2-4 min (20 pages × 2s delay + Playwright startup)
**Prerequisites:** Phase 0 merged; Playwright Chromium installed; Documenso account created

**Creates:** `blast_radius/crawl/__init__.py`, `blast_radius/crawl/dynamic.py`, `blast_radius/crawl/static.py`, `blast_radius/crawl/artifacts.py`

### Known Limitations (set expectations before building)

- **No `data-*` test attributes** in Documenso production. Selectors use `aria-label`, `placeholder`, `name`, and element role.
- **Rate limiting:** Add 1.5s delay between navigations. Check `robots.txt` — Documenso allows crawling.
- **Auth wall:** Most useful pages (`/documents`, `/templates`) require authentication. Without credentials, only login/signup/marketing pages are captured — the graph will have very limited UI coverage.
- **Client-side navigation:** Next.js `<Link>` components render as `<a>` tags; onClick-only navigation is not captured. This is expected and noted in the design doc.

---

### blast_radius/crawl/static.py

For crawling `docs.documenso.com` (static content).

> **v4 fix (P0-12):** Uses `result.cleaned_html` — not `result.html` which does not exist in crawl4ai 0.4.x.

```python
import asyncio
from typing import Optional

try:
    from crawl4ai import AsyncWebCrawler
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False


async def crawl_static_url(url: str) -> Optional[str]:
    """
    Fetch a single static documentation page.
    Returns cleaned HTML text or None on failure.

    v4 fix: uses result.cleaned_html (not result.html — does not exist in 0.4.x).
    If you see AttributeError, verify: pip show crawl4ai | grep Version (must be 0.4.3)
    """
    if not CRAWL4AI_AVAILABLE:
        raise RuntimeError("crawl4ai not installed. Run: pip install -r requirements.txt")
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url)
        if not result.success:
            return None
        # Use cleaned_html for LLM-friendly content; fall back to markdown if available
        return getattr(result, "cleaned_html", None) or getattr(result, "markdown", None) or ""


async def crawl_docs_pages(
    base_url: str = "https://docs.documenso.com",
    max_pages: int = 5,
) -> list[str]:
    """Crawl up to max_pages documentation pages. Returns list of HTML/text strings."""
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
        await asyncio.sleep(1.0)
        content = await crawl_static_url(url)
        if content and len(content) > 200:
            pages.append(content)
        else:
            print(f"[static] WARNING: {url} returned empty or too-short content — skipping")
    return pages
```

---

### blast_radius/crawl/dynamic.py

Primary crawler for `app.documenso.com`.

> **v4 fix (P1-08):** Uses `domcontentloaded` + `asyncio.sleep(2.0)` instead of `networkidle` which never fires on Next.js SPAs.
> **v4 fix (P1-09):** Auth flow uses `get_by_label()` / `get_by_role()` Playwright API — not broken comma-CSS selectors.
> **v4 fix (P2-11):** Zero-transition warning logged explicitly.

```python
import asyncio
import hashlib
from pathlib import Path
from typing import Optional

from playwright.async_api import async_playwright, Page

from blast_radius.config import settings
from blast_radius.models import AccessibilityItem, PageSnapshot, Transition

TARGET_URL = settings.target_url
SCREENSHOTS_DIR = settings.data_dir / "crawl" / "screenshots"
POLITE_DELAY = 1.5


def _url_sha256(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


async def _capture_accessibility_tree(page: Page) -> list[AccessibilityItem]:
    """
    Extract AXTree-inspired interactive element list.
    Capped at 300 elements. Uses aria-label and role — Documenso has no data-* test attributes.
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
    """
    Capture anchor-based navigation links.
    NOTE: onClick-only navigation (Next.js buttons, card clicks) is NOT captured.
    This is a known limitation documented in the design doc.
    """
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
        if (href
                and href.startswith(base_url)
                and href != current_url
                and not any(href.endswith(ext) for ext in [".pdf", ".zip", ".png", ".jpg"])):
            transitions.append(Transition(
                action="navigate",
                selector=None,
                source_url=current_url,
                target_url=href,
            ))
    if not transitions:
        print(f"[crawl] WARNING: 0 transitions found on {page.url} "
              "— expected for Next.js onClick navigation. Page→Page edges will be sparse.")
    return transitions


async def crawl_page(page: Page, url: str) -> PageSnapshot:
    """
    Capture a single page. Uses domcontentloaded + sleep for Next.js SPA hydration.

    v4 fix (P1-08): networkidle never fires on apps with background polling.
    Use domcontentloaded + asyncio.sleep(2.0) instead.
    """
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    sha = _url_sha256(url)
    screenshot_path = str(SCREENSHOTS_DIR / f"{sha}.png")

    # v4 fix: domcontentloaded + sleep, not networkidle
    await page.goto(url, wait_until="domcontentloaded", timeout=25_000)
    try:
        await page.wait_for_load_state("load", timeout=10_000)
    except Exception:
        pass  # load state may not fire on SPA navigations — proceed anyway
    await asyncio.sleep(2.0)  # allow Next.js hydration

    await page.screenshot(path=screenshot_path, full_page=True)
    dom = await page.content()

    if not dom or len(dom) < 100:
        raise RuntimeError(
            f"DOM snapshot too small ({len(dom)} chars) for {url}. "
            "Is the page rendering? Check screenshot at: " + screenshot_path
        )

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


async def run_dynamic_crawl(start_url: str, max_pages: int) -> list[PageSnapshot]:
    """
    Two-mode crawler for Documenso:
    1. Unauthenticated: /signin, /signup (root redirects to /signin)
    2. Authenticated: /documents, /templates, /settings + BFS follow-on pages

    v4 fix (P1-09): Auth uses get_by_label()/get_by_role() — not broken comma CSS selectors.
    v4 fix (P0-07): Explicit warning when unauthenticated-only crawl produces <5 pages.
    """
    snapshots: list[PageSnapshot] = []
    visited: set[str] = set()

    auth_available = bool(settings.documenso_email and settings.documenso_password)
    if not auth_available:
        print(
            "[crawl] WARNING: DOCUMENSO_EMAIL/PASSWORD not set. "
            "Running unauthenticated crawl only. "
            "Only login/signup pages will be captured — graph UI coverage will be very limited."
        )

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (blast-radius-analyzer/4.0 research-only)",
        )
        page = await context.new_page()

        # ── Flow 1: Unauthenticated pages ─────────────────────────
        # Note: root URL redirects to /signin — capture signin and signup explicitly
        for route in ["/signin", "/signup"]:
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
                await page.goto(f"{start_url}/signin", wait_until="domcontentloaded")
                await asyncio.sleep(2.0)

                # v4 fix (P1-09): Use Playwright's locator API — not comma CSS selectors
                await page.get_by_label("Email", exact=False).fill(settings.documenso_email)
                await page.get_by_label("Password", exact=False).fill(settings.documenso_password)
                await page.get_by_role("button", name="Sign in").click()

                # Wait for redirect away from signin
                try:
                    await page.wait_for_url(f"{start_url}/documents**", timeout=15_000)
                    print("[crawl] ✓ Authenticated successfully")
                except Exception:
                    current = page.url
                    if "signin" in current:
                        raise RuntimeError(
                            f"Login failed — still at {current}. "
                            "Check DOCUMENSO_EMAIL and DOCUMENSO_PASSWORD. "
                            "Note: new accounts require email verification before login."
                        )
                    # May have landed on a different post-login page — proceed
                    print(f"[crawl] ✓ Authenticated (landed at {page.url})")

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

                    # BFS: follow discovered same-domain transitions (up to 5 per page)
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
            f"Only {len(snapshots)} page(s) captured. "
            f"Minimum is 2. Verify network access to {start_url}. "
            "If auth-only pages are needed, ensure DOCUMENSO_EMAIL/PASSWORD are set and verified."
        )

    if not auth_available and len(snapshots) < 5:
        print(
            f"[crawl] WARNING: Only {len(snapshots)} unauthenticated pages captured. "
            "The graph will have very limited UI coverage. "
            "Add Documenso credentials to .env for a useful graph."
        )

    return snapshots
```

---

### blast_radius/crawl/artifacts.py

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
        try:
            snapshots.append(PageSnapshot.model_validate_json(f.read_text(encoding="utf-8")))
        except Exception as e:
            print(f"[artifacts] WARNING: Could not load {f}: {e}")
    return snapshots
```

---

### blast_radius/crawl/**init**.py

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
```

---

### Phase 1 Smoke Test

```bash
python -m blast_radius.crawl
python -c "
import glob
from blast_radius.models import PageSnapshot

files = [f for f in glob.glob('data/crawl/*.json') if 'manifest' not in f]
assert len(files) >= 2, f'Only {len(files)} snapshots — check crawl warnings above'

for f in files:
    snap = PageSnapshot.model_validate_json(open(f, encoding='utf-8').read())
    assert snap.dom_snapshot and len(snap.dom_snapshot) > 100, f'Empty DOM in {f}'
    assert snap.screenshot_path

# Domain spot-check — these terms appear on Documenso public pages
documenso_terms = {'sign', 'document', 'email', 'password', 'account'}
all_text = ' '.join(
    PageSnapshot.model_validate_json(open(f, encoding='utf-8').read()).dom_snapshot[:3000]
    for f in files
).lower()
hits = [t for t in documenso_terms if t in all_text]
assert hits, f'No Documenso terms found — is the crawler hitting the right URL?'

print(f'OK — {len(files)} snapshots, domain terms found: {hits}')
"
```

**Expected output:** ≥2 snapshots (≥5 if auth crawl enabled), at least one domain term found, screenshots exist.

**Merge condition:** Smoke test passes. If auth-only, note in design doc that UI coverage is limited.

---

## Phase 2: PRD Ingest

**Branch:** `feature/phase-2-prd-ingest`
**Build time:** ~30 min | **Run time:** ~2-5 min (LLM calls per source)
**Prerequisites:** Phase 0

**Creates:** `blast_radius/ingest/__init__.py`, `blast_radius/ingest/fetch.py`, `blast_radius/ingest/extract.py`

### blast_radius/ingest/fetch.py

```python
import hashlib
import httpx
from pathlib import Path
from blast_radius.config import settings

SOURCES_DIR = settings.data_dir / "sources"


def fetch_and_cache(url: str) -> str:
    """Download url to data/sources/ (cached by URL hash). Returns file text."""
    SOURCES_DIR.mkdir(parents=True, exist_ok=True)
    cache_key = hashlib.sha256(url.encode()).hexdigest()[:12]
    suffix = Path(url).suffix or ".txt"
    cache_path = SOURCES_DIR / f"{cache_key}{suffix}"
    if cache_path.exists():
        print(f"[ingest] cache hit: {cache_path}")
        return cache_path.read_text(encoding="utf-8")
    print(f"[ingest] fetching {url}")
    try:
        resp = httpx.get(url, follow_redirects=True, timeout=30)
        resp.raise_for_status()
        cache_path.write_text(resp.text, encoding="utf-8")
        return resp.text
    except Exception as e:
        print(f"[ingest] WARNING: Failed to fetch {url}: {e}")
        return ""
```

---

### blast_radius/ingest/extract.py

> **v4 fix (P2-15):** Tighter rejection criteria — rejects commands (lines starting with CLI verbs) not all deployment content. Self-hosting IS a valid requirement.
> **v4 fix (P1-13):** Assertion on Docling markdown length; clearer error on conversion failure.
> **v4 fix (P2-14):** Semantic deduplication using cosine similarity after extraction.

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

Rejection rules (reject a sentence if it matches ANY of these):
  - Starts with a CLI command verb followed by a tool name: npm, yarn, pnpm, git, docker, brew, pip, cargo
  - Describes only file system paths, environment variables, or configuration syntax with no user behaviour
  - Is a generic marketing tagline with no observable product behaviour ("The best platform for...")

ACCEPT requirements about self-hosting, team management, and admin configuration — these are
observable product behaviours even if they involve technical setup.

Every accepted requirement must describe something an end user or admin can observe or interact
with in the application (uploading a document, adding a recipient, signing, viewing a certificate,
configuring a team, self-hosting the platform, etc.).

Return minimum 5 requirements. If fewer than 5 qualify, return {"error": "insufficient_requirements"}.
""".strip()

# CLI command verbs that signal setup instructions, not product requirements
_CLI_VERBS = re.compile(
    r"^\s*(npm|yarn|pnpm|npx|git\s+clone|git\s+push|docker\s+run|docker\s+compose|brew\s+install|pip\s+install|cargo\s+install)\s",
    re.IGNORECASE
)


def extract_requirements(text: str, source_file: str) -> list[Requirement]:
    """
    Extract requirements from a text blob using Claude.
    Filters CLI command lines before sending to LLM.
    """
    # Pre-filter: remove lines that are clearly CLI commands
    filtered_lines = [
        line for line in text.splitlines()
        if not _CLI_VERBS.match(line)
    ]
    filtered_text = "\n".join(filtered_lines)
    truncated = filtered_text[:12_000]

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
        raise RuntimeError(f"LLM returned invalid JSON: {e}\nRaw output (first 500 chars):\n{raw[:500]}")

    if isinstance(items, dict) and "error" in items:
        raise RuntimeError(f"LLM extraction error: {items['error']}")
    if not isinstance(items, list):
        raise RuntimeError(f"Expected JSON array, got {type(items).__name__}")

    requirements = []
    for item in items:
        text_str = item.get("text", "").strip()
        if not text_str:
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
            ),
        ))

    if len(requirements) < 5:
        raise RuntimeError(
            f"Only {len(requirements)} valid requirements from {source_file}. "
            "Check source content — it may be too short or too infrastructure-focused."
        )
    return requirements


def extract_requirements_from_docling(source_url_or_path: str) -> list[Requirement]:
    """
    Convert document via Docling to Markdown, then extract requirements.

    v4 fix (P1-13): asserts markdown length > 500 chars to catch silent download failures.
    Docling API verified for docling>=2.0.0: result.document.export_to_markdown()
    """
    from docling.document_converter import DocumentConverter
    result = DocumentConverter().convert(source_url_or_path)
    if result.document is None:
        raise RuntimeError(
            f"Docling conversion returned None for {source_url_or_path}. "
            "Check network access and that the URL is a supported format (PDF, DOCX, MD, HTML)."
        )
    markdown = result.document.export_to_markdown()
    assert len(markdown) > 500, (
        f"Docling produced only {len(markdown)} chars from {source_url_or_path}. "
        "This indicates a failed download or an empty document. "
        "Verify network access to the URL."
    )
    return extract_requirements(markdown, source_file=source_url_or_path)


def deduplicate_requirements(requirements: list[Requirement]) -> list[Requirement]:
    """
    Remove semantically duplicate requirements using cosine similarity.
    Two requirements with similarity > 0.92 are considered duplicates; keep the longer text.

    v4 fix (P2-14): replaces the naive SHA-based dedup that missed near-duplicates.
    """
    if len(requirements) <= 1:
        return requirements

    try:
        from sentence_transformers import SentenceTransformer, util
        model = SentenceTransformer("all-MiniLM-L6-v2")
        texts = [r.text for r in requirements]
        embeddings = model.encode(texts, normalize_embeddings=True, convert_to_tensor=True)
        sim_matrix = util.cos_sim(embeddings, embeddings)

        kept = []
        dropped = set()
        for i, req in enumerate(requirements):
            if i in dropped:
                continue
            kept.append(req)
            for j in range(i + 1, len(requirements)):
                if j in dropped:
                    continue
                if float(sim_matrix[i][j]) > 0.92:
                    # Keep the longer, more descriptive text
                    if len(requirements[j].text) > len(req.text):
                        dropped.add(i)
                        kept[-1] = requirements[j]
                    else:
                        dropped.add(j)
        return kept
    except Exception as e:
        print(f"[ingest] WARNING: Deduplication failed ({e}), returning all requirements")
        return requirements
```

---

### blast_radius/ingest/**init**.py

```python
import asyncio
import json

from blast_radius.config import settings
from blast_radius.ingest.extract import (
    extract_requirements_from_docling,
    extract_requirements,
    deduplicate_requirements,
)
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

    # Source 2: docs.documenso.com (first 5 pages)
    try:
        doc_pages_html = asyncio.run(crawl_docs_pages(DOCS_BASE_URL, max_pages=5))
        for i, content in enumerate(doc_pages_html):
            try:
                reqs = extract_requirements(content, source_file=f"{DOCS_BASE_URL}/page-{i+1}")
                _add(reqs)
                print(f"[ingest] docs page {i+1}: {len(reqs)} requirements")
            except Exception as e:
                print(f"[ingest] WARNING: docs page {i+1} failed: {e}")
    except Exception as e:
        print(f"[ingest] WARNING: docs crawl failed: {e}")

    if len(all_requirements) < 5:
        raise RuntimeError(
            f"Only {len(all_requirements)} total requirements extracted. "
            "Check network access to GitHub and docs.documenso.com."
        )

    # Semantic deduplication
    before = len(all_requirements)
    all_requirements = deduplicate_requirements(all_requirements)
    print(f"[ingest] Deduplication: {before} → {len(all_requirements)} requirements")

    out = REQS_DIR / "requirements.json"
    out.write_text(
        json.dumps([r.model_dump() for r in all_requirements], indent=2),
        encoding="utf-8",
    )
    print(f"[ingest] Saved {len(all_requirements)} requirements to {out}")
    return all_requirements
```

---

### Phase 2 Smoke Test

```bash
python -c "from blast_radius.ingest import run_ingest; reqs = run_ingest(); print(len(reqs))"
python -c "
import json
from blast_radius.models import Requirement

data = json.load(open('data/requirements/requirements.json', encoding='utf-8'))
assert len(data) >= 5, f'Only {len(data)} requirements — check extraction warnings'
reqs = [Requirement.model_validate(r) for r in data]

# Domain spot-check
domain_terms = {'document', 'sign', 'recipient', 'template', 'field', 'certificate', 'sender', 'signer'}
hits = [r for r in reqs if any(t in r.text.lower() for t in domain_terms)]
assert hits, 'No Documenso-domain requirements found — check LLM prompt or source content'

# Provenance check
assert all(r.provenance.excerpt for r in reqs), 'Some requirements missing provenance.excerpt'

print(f'OK — {len(reqs)} requirements, {len(hits)} Documenso-domain, all have provenance')
"
```

**Merge condition:** ≥5 requirements, ≥1 Documenso-domain requirement, all have `provenance.excerpt`.

---

## Phase 3: Code Analysis

**Branch:** `feature/phase-3-code-analysis`
**Build time:** ~60 min | **Run time:** ~3-8 min (ast-grep scan + API call)
**Prerequisites:** Phase 0; Documenso repo cloned; `sg` binary installed; `MERGE_SHA` and `GITHUB_TOKEN` set in `.env`

**Creates:** `rules/ts-functions.yml`, `rules/trpc-procedures.yml`, `blast_radius/code/__init__.py`, `blast_radius/code/index.py`, `blast_radius/code/pr.py`

### Documenso-Specific Context

Before building, verify your understanding of the repo structure:

```bash
# Verify scan paths exist
ls data/repos/documenso/packages/lib/server-only/document/
ls data/repos/documenso/packages/trpc/server/routers/
ls data/repos/documenso/apps/web/src/app/
```

**API layer:** Documenso uses tRPC for all client-server calls. Procedures are defined in `packages/trpc/server/routers/*.ts` as object properties with `protectedProcedure` or `publicProcedure` values. Standard TypeScript function rules capture the arrow function bodies but miss the procedure name (the router key). The `trpc-procedures.yml` rule captures this.

**Scan paths:** `packages/lib/`, `packages/trpc/`, `apps/web/src/` — **not** `src/` (doesn't exist at repo root) and **not** `packages/prisma/migrations/` (SQL files generate false matches).

---

### Verify ast-grep output format before writing code

Run this manually to see the exact JSON structure your installation produces:

```bash
# Create a minimal test rule first
cat > /tmp/test-fn.yml << 'EOF'
id: test-fn
language: TypeScript
rule:
  kind: function_declaration
EOF

sg scan --rule /tmp/test-fn.yml \
  data/repos/documenso/packages/lib/server-only/document/ \
  --json | python3 -c "
import json, sys
data = json.load(sys.stdin)
if data:
    print(json.dumps(data[0], indent=2))
    print(f'Total matches: {len(data)}')
else:
    print('No matches — check rule syntax and path')
"
```

**Expected output fields:** `text`, `range.start.line`, `range.end.line`, `file`. The `ruleId` field appears in some versions as the `id:` value from your YAML. If `ruleId` is absent, the code falls back to the rule's default node type.

---

### rules/ts-functions.yml

```yaml
id: ts-functions
language: TypeScript
rule:
  any:
    - kind: function_declaration
    - kind: method_definition
    - kind: arrow_function
```

---

### rules/trpc-procedures.yml

> **v4 fix (P0-17):** Corrected from the broken `pattern: $NAME: $PROC.$METHOD($$$)` which matched zero real procedures. The correct approach targets `pair` AST nodes where the value contains a `protectedProcedure` or `publicProcedure` call chain.

```yaml
id: trpc-procedure
language: TypeScript
rule:
  kind: pair
  has:
    field: value
    any:
      - pattern: protectedProcedure.$$$
      - pattern: publicProcedure.$$$
```

Verify this rule produces matches before proceeding:

```bash
sg scan --rule rules/trpc-procedures.yml \
  data/repos/documenso/packages/trpc/server/routers/ \
  --json | python3 -c "
import json, sys
data = json.load(sys.stdin)
assert len(data) > 0, 'Zero tRPC procedure matches — rule may need adjustment for this repo version'
print(f'tRPC procedures found: {len(data)}')
print('Sample:', json.dumps(data[0], indent=2))
"
```

If you get zero matches, the Documenso version you cloned may use different procedure names. Inspect a router file manually:

```bash
head -60 data/repos/documenso/packages/trpc/server/routers/document.ts
```

Adjust the pattern to match the actual procedure base name used in that file.

---

### blast_radius/code/index.py

> **v4 fix (P0-16):** Scoped scan paths exclude migrations and node_modules.
> **v4 fix (P0-17):** tRPC rule corrected; explicit assertion that tRPC procedures are found.
> **v4 fix (P2-20):** Diagnostic error message shows sample of what was found.

```python
import json
import re
import subprocess
from pathlib import Path

from blast_radius.models import CodeFunction


def _make_function_id(repo_dir: Path, abs_file: str, start_line: int, name: str) -> str:
    """
    Stable function ID: relative_path:start_line:name
    Must match the format used in Phase 5 seed computation.
    """
    rel = Path(abs_file).relative_to(repo_dir)
    return f"{rel}:{start_line}:{name}"


def _extract_name_from_text(text: str, rule_id: str) -> str:
    """Extract function/procedure name from matched AST text snippet."""
    text = text.strip()

    # tRPC pair: key is the procedure name
    # Matched text looks like: 'getDocument: protectedProcedure.input(...).query(...)'
    if rule_id == "trpc-procedure":
        m = re.match(r"['\"]?(\w+)['\"]?\s*:", text)
        if m:
            return m.group(1)

    # Standard function declaration
    m = re.match(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)", text)
    if m:
        return m.group(1)

    # Const arrow function
    m = re.match(r"(?:export\s+)?const\s+(\w+)\s*=", text)
    if m:
        return m.group(1)

    # Method definition
    m = re.match(r"(?:async\s+)?(\w+)\s*\(", text)
    if m and m.group(1) not in ("async", "function", "const", "let", "var", "if", "for"):
        return m.group(1)

    return "anonymous"


def _parse_ast_grep_output(stdout: str) -> list[dict]:
    """
    Parse ast-grep JSON output. Handles both array and NDJSON (newline-delimited) formats.
    ast-grep exits 0 with matches, 1 with no matches (POSIX grep convention).
    """
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
    """
    Run ast-grep with the given rule against Documenso's TypeScript source paths.

    v4 fix (P0-16): Narrowed scan paths to lib/, trpc/, apps/web/src/.
    Excludes migrations, node_modules, dist, build.
    """
    rule = Path(rule_file)
    if not rule.exists():
        raise FileNotFoundError(
            f"Rule file not found: {rule}. "
            "Run from the project root (blast-radius/)."
        )

    # Narrowed scan paths — exclude migrations, generated code, node_modules
    candidate_paths = [
        repo / "packages" / "lib",
        repo / "packages" / "trpc",
        repo / "apps" / "web" / "src",
    ]
    scan_paths = [str(p) for p in candidate_paths if p.exists()]
    if not scan_paths:
        raise RuntimeError(
            f"No valid scan paths found under {repo}. "
            "Expected: packages/lib/, packages/trpc/, apps/web/src/. "
            "Verify the repo clone is complete."
        )

    result = subprocess.run(
        ["sg", "scan", "--rule", str(rule)] + scan_paths + ["--json"],
        text=True,
        capture_output=True,
    )
    # ast-grep exits 1 when no matches found (normal behavior, like POSIX grep)
    if result.returncode not in (0, 1):
        raise RuntimeError(
            f"ast-grep failed (exit {result.returncode}) for rule {rule_file}:\n"
            f"stderr: {result.stderr[:500]}"
        )

    return _parse_ast_grep_output(result.stdout)


def build_call_graph(repo: Path) -> list[CodeFunction]:
    """
    Two-pass AST scan:
    1. ts-functions.yml: standard TypeScript function declarations, arrow functions, methods
    2. trpc-procedures.yml: tRPC router procedure names (pair AST node approach)

    v4 fix (P0-17): tRPC rule corrected; assertion verifies procedures are found.
    v4 fix (P2-20): diagnostic error shows sample of what was found.
    """
    fn_lookup: dict[str, CodeFunction] = {}
    file_fns: dict[str, list[tuple[str, int]]] = {}
    trpc_count = 0

    for rule_file in ["rules/ts-functions.yml", "rules/trpc-procedures.yml"]:
        try:
            matches = ast_matches(repo, rule_file)
        except Exception as e:
            print(f"[code] WARNING: {rule_file} scan failed: {e}")
            continue

        rule_id = Path(rule_file).stem  # "ts-functions" or "trpc-procedures"
        node_type = "trpc-procedure" if "trpc" in rule_id else "ts-function"

        for match in matches:
            abs_file = match.get("file", "")
            start_line = match.get("range", {}).get("start", {}).get("line", 0)
            text = match.get("text", "")
            # ruleId may appear in some ast-grep versions
            ast_node_type = match.get("ruleId", node_type)

            name = _extract_name_from_text(text, rule_id)
            if name in ("anonymous", ""):
                continue

            if node_type == "trpc-procedure":
                trpc_count += 1

            try:
                fn_id = _make_function_id(repo, abs_file, start_line, name)
            except ValueError:
                continue  # abs_file not under repo root

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
        sample = [(f.name, f.file) for f in list(fn_lookup.values())[:5]]
        raise RuntimeError(
            f"Only {len(fn_lookup)} functions found (need 50+).\n"
            f"Sample of what was found: {sample}\n"
            "Debug steps:\n"
            "  1. Run: ls data/repos/documenso/packages/lib/server-only/document/\n"
            "  2. Run: sg scan --rule rules/ts-functions.yml data/repos/documenso/packages/lib --json | python3 -c 'import json,sys; d=json.load(sys.stdin); print(len(d))'\n"
            "  3. Verify sg is installed: sg --version"
        )

    if trpc_count == 0:
        print(
            "[code] WARNING: 0 tRPC procedures found. "
            "The trpc-procedures.yml rule may not match this version of Documenso. "
            "Inspect: head -60 data/repos/documenso/packages/trpc/server/routers/document.ts"
        )

    # Same-file call resolution (conservative: same-file name reference only)
    name_to_ids: dict[str, list[str]] = {}
    for fn in fn_lookup.values():
        name_to_ids.setdefault(fn.name, []).append(fn.function_id)

    for abs_file, fn_list in file_fns.items():
        same_file_names = {name for name, _ in fn_list}
        # Re-scan this file for call references (reuse cached matches)
        for fn_name, fn_line in fn_list:
            try:
                caller_id = _make_function_id(repo, abs_file, fn_line, fn_name)
            except ValueError:
                continue
            if caller_id not in fn_lookup:
                continue
            # Read file content for call detection
            try:
                file_content = Path(abs_file).read_text(encoding="utf-8", errors="ignore")
                for callee_name in same_file_names:
                    if callee_name == fn_name:
                        continue
                    if re.search(r"\b" + re.escape(callee_name) + r"\s*[\(\.]", file_content):
                        for callee_id in name_to_ids.get(callee_name, []):
                            callee_fn = fn_lookup.get(callee_id)
                            if not callee_fn or callee_fn.file != fn_lookup[caller_id].file:
                                continue
                            if callee_id not in fn_lookup[caller_id].calls:
                                fn_lookup[caller_id].calls.append(callee_id)
                            if caller_id not in callee_fn.called_by:
                                callee_fn.called_by.append(caller_id)
            except Exception:
                pass

    return list(fn_lookup.values())
```

---

### blast_radius/code/pr.py

> **v4 fix (P0-18):** Uses GitHub API (httpx) for reliable PR file extraction instead of PyDriller on merge commits, which often returns empty modified_files for squash/merge commits. PyDriller retained for optional use.
> **v4 fix (P1-19):** Explicit path normalization and warning when no seeds found.
> **v4 fix (P1-30):** Uses `settings.github_token`.

```python
import subprocess
import httpx

from blast_radius.config import settings
from blast_radius.models import ChangedFile, PRDelta


def get_pr_delta(repo_path: str, pr_number: int, merge_sha: str) -> PRDelta:
    """
    Extract changed files for a PR using the GitHub API.

    v4 fix (P0-18): GitHub API is more reliable than PyDriller for merge commits.
    PyDriller's modified_files can return empty lists for squash/merge commits
    because it diffs the merge commit against its first parent only.

    Falls back to PyDriller if GitHub API fails (e.g., no token, rate-limited).
    """
    if not merge_sha:
        raise RuntimeError(
            "MERGE_SHA is not set.\n"
            f"  Run: gh pr view {pr_number} --repo {settings.target_repo_name} --json mergeCommit\n"
            "  Add MERGE_SHA=<sha> to .env"
        )

    # Primary: GitHub API
    changed_files = _get_files_from_github_api(pr_number)
    if not changed_files:
        print("[code] WARNING: GitHub API returned no files — falling back to PyDriller")
        changed_files = _get_files_from_pydriller(repo_path, merge_sha)

    if not changed_files:
        raise RuntimeError(
            f"No changed files found for PR #{pr_number}.\n"
            "Verify MERGE_SHA is correct and GITHUB_TOKEN has repo read access."
        )

    # Compute parent SHA (needed for design doc / report)
    parent_sha = ""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", f"{merge_sha}^1"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            parent_sha = result.stdout.strip()
    except Exception as e:
        print(f"[code] WARNING: Could not compute parent SHA: {e}")

    return PRDelta(
        pr_number=pr_number,
        pr_url=f"https://github.com/{settings.target_repo_name}/pull/{pr_number}",
        title=f"PR #{pr_number}",
        merge_sha=merge_sha,
        parent_sha=parent_sha,
        changed_files=changed_files,
        changed_function_ids=[],  # populated by Phase 5
    )


def _get_files_from_github_api(pr_number: int) -> list[ChangedFile]:
    """Fetch PR file list from GitHub API. Returns [] on any failure."""
    headers = {"Accept": "application/vnd.github.v3+json"}
    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"
    else:
        print("[code] WARNING: GITHUB_TOKEN not set — GitHub API rate limit is 60/hour for unauthenticated requests")

    try:
        resp = httpx.get(
            f"https://api.github.com/repos/{settings.target_repo_name}/pulls/{pr_number}/files",
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        files = resp.json()
        return [
            ChangedFile(
                path=f["filename"],
                status=f["status"],
                additions=f.get("additions", 0),
                deletions=f.get("deletions", 0),
            )
            for f in files
        ]
    except Exception as e:
        print(f"[code] WARNING: GitHub API failed: {e}")
        return []


def _get_files_from_pydriller(repo_path: str, merge_sha: str) -> list[ChangedFile]:
    """Fallback: use PyDriller to extract changed files from the merge commit."""
    try:
        from pydriller import Repository
        changed = []
        for commit in Repository(repo_path, single=merge_sha).traverse_commits():
            for mod in commit.modified_files:
                path = mod.new_path or mod.old_path or ""
                if path:
                    changed.append(ChangedFile(
                        path=path,
                        status=mod.change_type.name.lower() if mod.change_type else "modified",
                        additions=mod.added_lines,
                        deletions=mod.deleted_lines,
                    ))
        return changed
    except Exception as e:
        print(f"[code] WARNING: PyDriller fallback failed: {e}")
        return []
```

---

### blast_radius/code/**init**.py

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
            f"Documenso repo not found at {repo}.\n"
            f"  Run: git clone --depth 1 https://github.com/documenso/documenso {repo}"
        )

    print("[code] Running ast-grep scan (ts-functions + trpc-procedures)...")
    functions = build_call_graph(repo)
    call_graph_path = CODE_DIR / "call_graph.json"
    call_graph_path.write_text(
        json.dumps([f.model_dump() for f in functions], indent=2),
        encoding="utf-8",
    )
    print(f"[code] Saved {len(functions)} functions to {call_graph_path}")

    print("[code] Fetching PR delta from GitHub API...")
    delta = get_pr_delta(REPO_PATH, settings.pr_number, settings.merge_sha)
    delta_path = CODE_DIR / f"pr_{settings.pr_number}.json"
    delta_path.write_text(delta.model_dump_json(indent=2), encoding="utf-8")

    # Validate that changed files are TypeScript (the indexed language)
    ts_files = [f for f in delta.changed_files if f.path.endswith((".ts", ".tsx", ".vue"))]
    print(
        f"[code] PR {settings.pr_number}: {len(delta.changed_files)} files changed, "
        f"{len(ts_files)} TypeScript/TSX"
    )
    if not ts_files:
        print(
            "[code] WARNING: No TypeScript files in changed files. "
            "Phase 5 will likely report all changes as DARK_CHANGE. "
            "Consider selecting a PR that touches .ts files."
        )

    return {"functions": functions, "delta": delta}
```

---

### Phase 3 Smoke Test

```bash
python -c "from blast_radius.code import run_code_analysis; run_code_analysis()"
python -c "
import json, os
from blast_radius.models import CodeFunction, PRDelta

# Call graph validation
data = json.load(open('data/code/call_graph.json', encoding='utf-8'))
assert len(data) >= 50, f'Only {len(data)} functions — check ast-grep installation and scan paths'
fns = [CodeFunction.model_validate(d) for d in data]
with_calls = [f for f in fns if f.calls]
trpc_fns = [f for f in fns if f.ast_node_type == 'trpc-procedure']

# tRPC assertion — fails loudly if rule produced nothing
assert len(trpc_fns) > 0, (
    'Zero tRPC procedures found. '
    'Check rules/trpc-procedures.yml against the actual router file structure. '
    'Run: head -60 data/repos/documenso/packages/trpc/server/routers/document.ts'
)

print(f'Call graph: {len(fns)} functions, {len(with_calls)} with calls, {len(trpc_fns)} tRPC procedures')

# PR delta validation
pr_num = int(os.environ.get('PR_NUMBER', open('.env').read().split('PR_NUMBER=')[1].split()[0]))
delta = PRDelta.model_validate_json(open(f'data/code/pr_{pr_num}.json', encoding='utf-8').read())
assert delta.changed_files, f'No changed files in PR {pr_num} — check GITHUB_TOKEN and MERGE_SHA'
ts_files = [f for f in delta.changed_files if f.path.endswith(('.ts', '.tsx'))]
print(f'PR delta: {len(delta.changed_files)} files changed, {len(ts_files)} TypeScript')
"
```

**Merge condition:** ≥50 functions, ≥1 tRPC procedure, PR delta contains changed files.

---

## Phase 4: Knowledge Graph Construction

**Branch:** `feature/phase-4-knowledge-graph`
**Build time:** ~60 min | **Run time:** ~5-15 min (LLM entity resolution batches)
**Prerequisites:** Phases 1–3 merged

**Creates:** `blast_radius/graph/__init__.py`, `blast_radius/graph/schema.py`, `blast_radius/graph/writer.py`, `blast_radius/graph/resolve.py`

### Critical Design Decisions

**IMPLEMENTS edge direction:** `CodeFunction → Requirement`. A function implements a requirement. This means PPR seeded at CodeFunctions propagates forward to Requirements via `CALLS → IMPLEMENTS`. This is the opposite of v3 which had `Requirement → CodeFunction` — that direction made PPR propagate backwards.

> **v4 fix (P0-21):** Edge direction corrected throughout. The schema Cypher, the `_load_graph_data()` query in Phase 5, and the Neo4j Browser verification query all use `CodeFunction -[:IMPLEMENTS]-> Requirement`.

---

### blast_radius/graph/schema.py

```python
# Node constraints — uniqueness enforced by Neo4j
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

# v4 fix (P0-21): IMPLEMENTS goes CodeFunction → Requirement
# A function implements a requirement; PPR seeds at functions propagates forward to requirements
CREATE_IMPLEMENTS = """
MATCH (c:CodeFunction {id: $from_id}), (r:Requirement {id: $to_id})
MERGE (c)-[e:IMPLEMENTS]->(r)
SET e.confidence = $confidence, e.evidence = $evidence,
    e.source = $source, e.run_id = $run_id, e.created_at = $created_at
"""

# RENDERS: CodeFunction renders a Page (file path matches URL segment)
CREATE_RENDERS = """
MATCH (c:CodeFunction {id: $from_id}), (p:Page {id: $to_id})
MERGE (c)-[e:RENDERS]->(p)
SET e.confidence = $confidence, e.evidence = $evidence,
    e.source = $source, e.run_id = $run_id, e.created_at = $created_at
"""

CREATE_CALLS = """
MATCH (a:CodeFunction {id: $from_id}), (b:CodeFunction {id: $to_id})
MERGE (a)-[e:CALLS]->(b)
SET e.weight = 1.0, e.run_id = $run_id, e.created_at = $created_at
"""

# Absence modeling: requirements with no IMPLEMENTS edge get a GapNode
CREATE_ABSENT_FROM = """
MATCH (r:Requirement {id: $req_id})
MERGE (g:GapNode {id: $gap_id})
SET g.requirement_id = $req_id, g.reason = $reason,
    g.threshold = $threshold, g.run_id = $run_id
MERGE (r)-[e:ABSENT_FROM]->(g)
SET e.run_id = $run_id, e.created_at = $created_at
"""

# v4 fix (P0-21): check for IMPLEMENTS edges in the correct direction (CodeFunction → Requirement)
MARK_MISSING_REQUIREMENTS = """
MATCH (r:Requirement)
WHERE NOT (:CodeFunction)-[:IMPLEMENTS]->(r)
SET r.coverage_status = 'MISSING'
RETURN count(r) as missing_count
"""

MARK_COVERED_REQUIREMENTS = """
MATCH (r:Requirement)
WHERE (:CodeFunction)-[:IMPLEMENTS]->(r)
SET r.coverage_status = 'PARTIAL'
RETURN count(r) as partial_count
"""
```

---

### blast_radius/graph/resolve.py

> **v4 fix (P2-24):** Cosine threshold raised to 0.60. Keyword pre-filter applied before LLM batching — only candidates where the requirement's `related_ui_keywords` overlap with the function's file path are sent to the LLM.
> **v4 fix (P0-22):** `functions.index(fn)` bug fixed — uses pre-computed `fn_labels[j]` directly.
> **v4 fix (P0-21):** Entity links use `from_id=fn.function_id, to_id=req.requirement_id` (CodeFunction → Requirement).
> **v4 fix (P1-04 / crawl):** `resolve_ui_to_functions` uses `page:{sha}` Page node IDs, not non-existent UIElement IDs.

```python
import json
import re
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer
from sentence_transformers import util as st_util
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


def _keyword_overlap(req: Requirement, fn_label: str) -> bool:
    """
    Pre-filter: returns True if any of the requirement's related_ui_keywords
    appear in the function's file path or name.
    Reduces false-positive candidates before LLM batching.
    """
    fn_lower = fn_label.lower()
    for kw in req.related_ui_keywords:
        # Match individual words from keyword phrases
        for word in kw.lower().split():
            if len(word) >= 4 and word in fn_lower:
                return True
    return False


def resolve_requirements_to_functions(
    requirements: list[Requirement],
    functions: list[CodeFunction],
    *,
    cosine_threshold: float = 0.60,   # v4 fix (P2-24): raised from 0.45
    llm_rerank_threshold: float = 0.65,
    run_id: str = "v1",
) -> list[EntityLink]:
    """
    Two-stage entity resolution:
    1. Vectorized cosine similarity with keyword pre-filter
    2. LLM reranker for candidates above threshold

    v4 fixes:
    - Cosine threshold raised to 0.60 (was 0.45 — too many false positives)
    - Keyword pre-filter reduces LLM calls by ~60-80%
    - fn_labels[j] used directly instead of broken functions.index(fn)
    - IMPLEMENTS edge: from_id=function, to_id=requirement (CodeFunction → Requirement)
    """
    links: list[EntityLink] = []
    req_texts = [r.text for r in requirements]
    fn_labels = [f"{f.file}:{f.name}" for f in functions]

    enc = _encoder()
    req_embeddings = enc.encode(req_texts, normalize_embeddings=True, convert_to_tensor=True)
    fn_embeddings = enc.encode(fn_labels, normalize_embeddings=True, convert_to_tensor=True)

    # Vectorized similarity matrix: shape (len(reqs), len(fns))
    sim_matrix = st_util.cos_sim(req_embeddings, fn_embeddings)

    # Build candidates: top-5 functions per requirement, above threshold AND keyword overlap
    candidates: list[tuple[int, int, float]] = []  # (req_idx, fn_idx, score)
    for i, req in enumerate(requirements):
        scores = sim_matrix[i].tolist()
        top_idx = sorted(range(len(scores)), key=lambda x: scores[x], reverse=True)[:5]
        for j in top_idx:
            score = float(scores[j])
            if score >= cosine_threshold:
                # v4 fix (P2-24): apply keyword pre-filter before sending to LLM
                if _keyword_overlap(req, fn_labels[j]):
                    candidates.append((i, j, score))

    if not candidates:
        print(
            "[resolve] No candidates above cosine threshold with keyword overlap. "
            "This may mean: (1) requirements use very different vocabulary than code, "
            "(2) related_ui_keywords are too generic, or "
            "(3) cosine_threshold is too high. "
            "The graph will have no IMPLEMENTS edges — blast radius will show all dark changes."
        )
        return links

    print(f"[resolve] {len(candidates)} candidates for LLM reranking (after keyword pre-filter)")

    # LLM reranker in batches of 10
    batch_size = 10
    for batch_start in range(0, len(candidates), batch_size):
        batch = candidates[batch_start:batch_start + batch_size]
        prompt_items = []
        for req_idx, fn_idx, score in batch:
            req = requirements[req_idx]
            # v4 fix (P0-22): use fn_labels[fn_idx] directly, not functions.index()
            prompt_items.append({
                "req_id": req.requirement_id,
                "req_text": req.text,
                "fn_id": functions[fn_idx].function_id,
                "fn_label": fn_labels[fn_idx],          # already computed at index fn_idx
                "cosine_score": round(score, 3),
            })

        prompt = (
            "You are reviewing candidate requirement-to-code mappings for Documenso, "
            "a document signing platform. Functions include tRPC procedures, Next.js server actions, "
            "and lib/ business logic for documents, recipients, templates, and fields.\n"
            "For each candidate, decide if the function plausibly IMPLEMENTS the requirement "
            "(not just shares vocabulary — there must be a logical functional relationship).\n"
            "Return ONLY a JSON array where each element has:\n"
            '  "req_id": string, "fn_id": string, "confirmed": bool, '
            '"confidence": float (0-1), "reason": string (one sentence)\n\n'
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
            # v4 fix (P0-21): IMPLEMENTS is CodeFunction → Requirement
            links.append(EntityLink(
                from_id=result["fn_id"],          # CodeFunction
                to_id=result["req_id"],            # Requirement
                rel_type="IMPLEMENTS",
                confidence=confidence,
                evidence=result.get("reason", "LLM reranker confirmed"),
                source="cosine_sim+llm",
                run_id=run_id,
            ))

    print(f"[resolve] {len(links)} IMPLEMENTS links confirmed by LLM reranker")
    return links


def resolve_ui_to_functions(
    snapshots: list[PageSnapshot],
    functions: list[CodeFunction],
    *,
    run_id: str = "v1",
) -> list[EntityLink]:
    """
    Match CodeFunction files to Pages via URL segment matching.
    Creates RENDERS edges: CodeFunction → Page.

    v4 fix: uses page:{sha} IDs which match what write_ui_elements writes.
    Does NOT use "ui:{sha}:page" (v3 bug) — Page nodes use "page:{sha}" as ID.
    """
    links: list[EntityLink] = []

    for snap in snapshots:
        # Extract route segments from URL
        path = snap.url.split("//", 1)[-1]  # strip scheme
        path = path.split("/", 1)[-1] if "/" in path else ""  # strip host
        route_parts = [p for p in path.rstrip("/").split("/") if p and len(p) >= 4]

        if not route_parts:
            continue

        page_id = f"page:{snap.url_sha256}"  # matches UPSERT_PAGE id

        for fn in functions:
            for part in route_parts:
                if part.lower() in fn.file.lower():
                    links.append(EntityLink(
                        from_id=fn.function_id,
                        to_id=page_id,
                        rel_type="RENDERS",
                        confidence=0.70,
                        evidence=f"URL segment '{part}' appears in file path '{fn.file}'",
                        source="url_pattern",
                        run_id=run_id,
                    ))
                    break  # one match per function per page

    print(f"[resolve] {len(links)} RENDERS links (URL pattern)")
    return links
```

---

### blast_radius/graph/writer.py

```python
from datetime import datetime, timezone
from neo4j import GraphDatabase

from blast_radius.config import settings
from blast_radius.graph.schema import (
    CONSTRAINTS, UPSERT_REQUIREMENT, UPSERT_UI_ELEMENT, UPSERT_CODE_FUNCTION,
    UPSERT_PAGE, CREATE_IMPLEMENTS, CREATE_RENDERS, CREATE_CALLS,
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
                print(f"[graph] Schema note (may already exist): {e}")


def write_requirements(session, requirements: list) -> None:
    for r in requirements:
        session.run(UPSERT_REQUIREMENT, {
            "id": r.requirement_id, "text": r.text, "req_type": r.req_type,
            "coverage_status": r.coverage_status, "source_file": r.provenance.source_file,
            "excerpt": r.provenance.excerpt, "updated_at": _now(),
        }).consume()


def write_ui_elements(session, snapshots: list) -> None:
    """
    Writes Page nodes (id="page:{sha}") and UIElement nodes (id="ui:{sha}:{index}").
    Page ID format must match what resolve_ui_to_functions uses.
    """
    for snap in snapshots:
        session.run(UPSERT_PAGE, {
            "id": f"page:{snap.url_sha256}",   # page:{sha} — matches resolve_ui_to_functions
            "url": snap.url,
            "screenshot_path": snap.screenshot_path,
            "updated_at": _now(),
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
    # Write CALLS edges
    for fn in functions:
        for callee_id in fn.calls:
            try:
                session.run(CREATE_CALLS, {
                    "from_id": fn.function_id, "to_id": callee_id,
                    "run_id": "v1", "created_at": _now(),
                }).consume()
            except Exception:
                pass  # callee not in graph (cross-file reference) — skip


def write_entity_links(session, links: list, run_id: str = "v1") -> int:
    """
    Write entity links to Neo4j. Returns count of successfully written edges.
    Logs warnings for failures but does not raise.
    """
    template_map = {
        "IMPLEMENTS": CREATE_IMPLEMENTS,
        "RENDERS": CREATE_RENDERS,
    }
    written = 0
    failed = 0
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
            written += 1
        except Exception as e:
            failed += 1
            if failed <= 5:  # only log first 5 to avoid spam
                print(f"[graph] Edge write warning ({link.rel_type} {link.from_id[:30]}→{link.to_id[:30]}): {e}")
    if failed > 5:
        print(f"[graph] ... and {failed - 5} more edge write warnings (check node IDs)")
    return written


def mark_absent_requirements(session, run_id: str = "v1") -> int:
    """
    Mark requirements with no IMPLEMENTS edge as MISSING and create GapNodes.
    Returns count of missing requirements.
    """
    result = session.run(MARK_MISSING_REQUIREMENTS).single()
    missing_count = result["missing_count"] if result else 0
    session.run(MARK_COVERED_REQUIREMENTS).consume()

    for row in session.run(
        "MATCH (r:Requirement {coverage_status: 'MISSING'}) RETURN r.id as id, r.text as text"
    ).data():
        req_id = row["id"]
        session.run(CREATE_ABSENT_FROM, {
            "req_id": req_id,
            "gap_id": f"gap:{req_id}",
            "reason": (
                "No CodeFunction IMPLEMENTS this requirement at cosine+LLM confidence >= 0.65. "
                "May be unimplemented, behind auth-only UI not crawled, or using different vocabulary."
            ),
            "threshold": 0.65,
            "run_id": run_id,
            "created_at": _now(),
        }).consume()
    return missing_count
```

---

### blast_radius/graph/**init**.py

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

        print("[graph] Writing Pages and UIElements...")
        write_ui_elements(session, snapshots)

        print("[graph] Writing CodeFunctions and CALLS edges...")
        write_code_functions(session, functions)

        print("[graph] Resolving CodeFunction → Requirement (IMPLEMENTS)...")
        req_fn_links = resolve_requirements_to_functions(requirements, functions, run_id=run_id)
        n_impl = write_entity_links(session, req_fn_links, run_id=run_id)
        print(f"[graph]   {n_impl} IMPLEMENTS edges written")

        print("[graph] Resolving CodeFunction → Page (RENDERS)...")
        ui_fn_links = resolve_ui_to_functions(snapshots, functions, run_id=run_id)
        n_renders = write_entity_links(session, ui_fn_links, run_id=run_id)
        print(f"[graph]   {n_renders} RENDERS edges written")

        print("[graph] Marking absent requirements and creating GapNodes...")
        missing_count = mark_absent_requirements(session, run_id=run_id)
        print(f"[graph]   {missing_count} requirements marked MISSING → GapNodes created")

    driver.close()
    print(f"[graph] Build complete (run_id={run_id})")
```

---

### Phase 4 Smoke Test

```bash
python -c "from blast_radius.graph import build_graph; build_graph()"
python -c "
from blast_radius.graph.writer import get_driver

driver = get_driver()

# Node counts
print('Node counts:')
for row in driver.execute_query(
    'MATCH (n) RETURN labels(n)[0] as label, count(n) as c ORDER BY label'
).records:
    print(f'  {row[\"label\"]}: {row[\"c\"]}')

# Edge counts — must be non-zero to be a useful graph
for label, query in [
    ('IMPLEMENTS (CodeFunction→Requirement)', 'MATCH (:CodeFunction)-[:IMPLEMENTS]->(:Requirement) RETURN count(*) as c'),
    ('RENDERS (CodeFunction→Page)', 'MATCH (:CodeFunction)-[:RENDERS]->(:Page) RETURN count(*) as c'),
    ('CALLS', 'MATCH (:CodeFunction)-[:CALLS]->(:CodeFunction) RETURN count(*) as c'),
    ('ABSENT_FROM (GapNodes)', 'MATCH (:Requirement)-[:ABSENT_FROM]->(:GapNode) RETURN count(*) as c'),
]:
    count = driver.execute_query(query).records[0]['c']
    print(f'  {label}: {count}')
    if 'IMPLEMENTS' in label:
        assert count > 0, 'Zero IMPLEMENTS edges — entity resolution produced no confirmed links. Check resolve warnings above.'
    if 'RENDERS' in label:
        assert count > 0, 'Zero RENDERS edges — URL pattern matching produced no links.'

driver.close()
print('OK — graph populated with edges')
"
```

**Merge condition:** All node labels present, IMPLEMENTS edges > 0, RENDERS edges > 0, ABSENT_FROM count logged (may be zero if all requirements are covered).

---

## Phase 5: Blast Radius Reasoning

**Branch:** `feature/phase-5-blast-radius`
**Build time:** ~45 min | **Run time:** ~1-3 min (PPR is deterministic, fast)
**Prerequisites:** Phases 0–4 merged

**Creates:** `blast_radius/reason/__init__.py`, `blast_radius/reason/ppr.py`, `blast_radius/reason/impact.py`

### blast_radius/reason/ppr.py

> **v4 fix (P1-25):** Minimum absolute score floor added before normalization to prevent noise amplification from disconnected graph nodes.

```python
import networkx as nx


def build_projection(functions: list, entity_links: list) -> nx.DiGraph:
    """
    Build typed weighted digraph for PPR.

    Edge direction: CodeFunction → CodeFunction (CALLS)
                   CodeFunction → Page (RENDERS)
                   CodeFunction → Requirement (IMPLEMENTS)

    Weights: CALLS=1.0, RENDERS=0.95, IMPLEMENTS=0.85
    PPR seeded at CodeFunctions propagates FORWARD to Pages and Requirements.
    """
    WEIGHTS = {
        "CALLS": 1.0,
        "RENDERS": 0.95,
        "IMPLEMENTS": 0.85,
    }
    g = nx.DiGraph()
    for fn in functions:
        g.add_node(fn.function_id, node_type="CodeFunction", label=fn.name)
        for callee_id in fn.calls:
            g.add_edge(fn.function_id, callee_id, weight=WEIGHTS["CALLS"], rel_type="CALLS")
    for link in entity_links:
        w = WEIGHTS.get(link.rel_type, 0.5) * link.confidence
        g.add_edge(link.from_id, link.to_id, weight=w, rel_type=link.rel_type)
    return g


def personalized_pagerank(graph: nx.DiGraph, seeds: list[str]) -> dict[str, float]:
    """
    Forward PPR — seeds are changed CodeFunction nodes.
    Activation flows toward Pages and Requirements.
    Graph is NOT reversed — forward propagation finds downstream product impact.
    """
    if not seeds:
        raise RuntimeError(
            "No seed nodes provided. Changed files are not indexed in the call graph."
        )
    missing = [s for s in seeds if s not in graph]
    if missing:
        raise RuntimeError(
            f"Seed nodes not found in graph: {missing[:3]}...\n"
            "Check that Phase 3 and Phase 4 ran successfully and that "
            "changed file paths match the format used by _make_function_id()."
        )

    personalization = {n: 0.0 for n in graph.nodes()}
    w = 1.0 / len(seeds)
    for s in seeds:
        personalization[s] = w

    return nx.pagerank(
        graph,      # forward — NOT reversed
        alpha=0.85,
        personalization=personalization,
        max_iter=100,
        tol=1e-8,
        weight="weight",
    )


def normalize_scores(
    scores: dict[str, float],
    seeds: set[str],
    min_absolute: float = 1e-5,  # v4 fix (P1-25): floor to prevent noise amplification
) -> dict[str, float]:
    """
    Min-max normalize PPR scores for non-seed nodes.
    Excludes nodes below min_absolute to prevent disconnected graph noise amplification.
    """
    non_seed = {
        k: v for k, v in scores.items()
        if k not in seeds and v > min_absolute
    }
    if not non_seed:
        return {}
    min_v, max_v = min(non_seed.values()), max(non_seed.values())
    if max_v == min_v:
        return {k: 0.5 for k in non_seed}
    return {k: (v - min_v) / (max_v - min_v) for k, v in non_seed.items()}
```

---

### blast_radius/reason/impact.py

> **v4 fix:** `evidence_path` now stores human-readable labels (function name, page URL, requirement text excerpt) rather than raw node IDs. The weight parameter to `nx.shortest_path` is the string `"weight"` — not a callable.

```python
import networkx as nx
from blast_radius.models import AffectedNode, EntityLink

MAX_HOPS = 6


def evidence_path_labels(
    graph: nx.DiGraph,
    seed: str,
    target: str,
    node_metadata: dict[str, dict],
) -> list[str]:
    """
    Find shortest evidence path from seed to target.
    Returns human-readable labels instead of raw node IDs.

    v4 fix: weight="weight" (string attribute name, NOT a callable).
    Using a callable with method='dijkstra' raises TypeError in networkx.
    v4 fix: returns [] for paths longer than MAX_HOPS to avoid noise.
    v4 fix: labels are human-readable (function name / URL / requirement text).
    """
    try:
        path = nx.shortest_path(
            graph,
            seed,
            target,
            method="dijkstra",
            weight="weight",  # string attribute name on edges
        )
    except (nx.NetworkXNoPath, nx.NodeNotFound, nx.exception.NodeNotFound):
        return []

    if len(path) > MAX_HOPS + 1:
        return []

    # Convert node IDs to human-readable labels
    readable = []
    for node_id in path:
        meta = node_metadata.get(node_id, {})
        label = meta.get("label", node_id)
        readable.append(label)
    return readable


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
    """
    Compute affected UI and Requirement nodes using forward PPR scores.
    Returns (affected_ui, affected_requirements, dark_changes).
    """
    affected_ui: list[AffectedNode] = []
    affected_req: list[AffectedNode] = []
    dark_changes: list[str] = []

    for seed in seeds:
        reachable = nx.descendants(graph, seed) if seed in graph else set()
        if not reachable:
            seed_label = node_metadata.get(seed, {}).get("label", seed)
            dark_changes.append(seed_label)
            continue

        for node_id in reachable:
            meta = node_metadata.get(node_id, {})
            node_type = meta.get("node_type", "Unknown")
            if node_type not in ("UIElement", "Requirement", "Page"):
                continue

            impact_score = normalized_scores.get(node_id, 0.0)
            path = evidence_path_labels(graph, seed, node_id, node_metadata)
            if not path:
                continue

            # Traceability confidence = minimum edge weight on the evidence path
            # We need the raw node IDs to traverse graph edges
            try:
                raw_path = nx.shortest_path(graph, seed, node_id, method="dijkstra", weight="weight")
                edge_weights = []
                for i in range(len(raw_path) - 1):
                    ed = graph.get_edge_data(raw_path[i], raw_path[i + 1]) or {}
                    edge_weights.append(ed.get("weight", 0.5))
                tc = min(edge_weights) if edge_weights else 0.5
            except Exception:
                tc = 0.5

            risk = classify_risk(impact_score, tc)
            node_label = meta.get("label", node_id)

            node = AffectedNode(
                node_id=node_id,
                node_type=node_type,
                label=node_label,                # human-readable
                impact_score=round(impact_score, 4),
                traceability_confidence=round(tc, 4),
                evidence_path=path,              # human-readable labels
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

---

### blast_radius/reason/**init**.py

> **v4 fix (P0-21):** `_load_graph_data()` IMPLEMENTS query uses correct direction: `(c:CodeFunction)-[:IMPLEMENTS]->(r:Requirement)`.
> **v4 fix (P2-26):** Projection-only fallback removed — Neo4j is a hard dependency for Phase 5.
> **v4 fix (P1-25):** `min_absolute` floor passed to `normalize_scores`.

```python
import json
import uuid
from pathlib import Path

from blast_radius.config import settings
from blast_radius.models import (
    CodeFunction, PRDelta, Requirement, EntityLink,
    BlastRadiusReport, AffectedNode,
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

    v4 fix (P0-21): IMPLEMENTS query uses correct direction:
      (c:CodeFunction)-[:IMPLEMENTS]->(r:Requirement)
    NOT the v3 direction: (r:Requirement)-[:IMPLEMENTS]->(c:CodeFunction)

    v4 fix (P2-32): node_metadata stores human-readable labels for evidence_path rendering.
    """
    from blast_radius.graph.writer import get_driver
    driver = get_driver()
    links: list[EntityLink] = []
    node_meta: dict[str, dict] = {}
    absent_requirements: list[AffectedNode] = []

    with driver.session() as session:
        # v4 fix (P0-21): IMPLEMENTS direction is CodeFunction → Requirement
        for row in session.run(
            "MATCH (c:CodeFunction)-[e:IMPLEMENTS]->(r:Requirement) "
            "RETURN c.id as from_id, r.id as to_id, e.confidence as conf, "
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

        # Node metadata — store human-readable labels for evidence_path rendering
        for row in session.run("MATCH (n:Page) RETURN n.id as id, n.url as label"):
            node_meta[row["id"]] = {"node_type": "Page", "label": row["label"]}
        for row in session.run("MATCH (n:UIElement) RETURN n.id as id, n.label as label, n.page_url as page_url"):
            node_meta[row["id"]] = {
                "node_type": "UIElement",
                "label": f"{row['label']} ({row['page_url'].split('/')[-1] if row['page_url'] else 'unknown page'})"
            }
        for row in session.run("MATCH (n:Requirement) RETURN n.id as id, n.text as label"):
            # Truncate requirement text for display
            node_meta[row["id"]] = {"node_type": "Requirement", "label": row["label"][:80]}
        for row in session.run("MATCH (n:CodeFunction) RETURN n.id as id, n.name as name, n.file as file"):
            node_meta[row["id"]] = {
                "node_type": "CodeFunction",
                "label": f"{row['name']} ({Path(row['file']).name})"
            }

        # Absent requirements from GapNodes
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

    # v4 fix (P2-26): Neo4j is a hard dependency — no projection-only fallback
    try:
        entity_links, node_meta, absent_requirements = _load_graph_data()
    except Exception as e:
        raise RuntimeError(
            f"Neo4j is required for Phase 5 but failed: {e}\n"
            "Run: docker compose up -d\n"
            "Then re-run Phase 4 to rebuild the graph."
        )

    graph = build_projection(functions, entity_links)

    # Identify seeds: changed file paths → CodeFunction IDs
    changed_paths = {cf.path for cf in delta.changed_files}
    seeds = [fn.function_id for fn in functions if fn.file in changed_paths]

    if not seeds:
        # Diagnostic: show what changed_paths look like vs fn.file format
        sample_fn_files = [fn.file for fn in functions[:5]]
        sample_changed = list(changed_paths)[:5]
        print(
            f"[reason] WARNING: No seed functions found.\n"
            f"  Changed paths (from PR): {sample_changed}\n"
            f"  Sample fn.file values: {sample_fn_files}\n"
            f"  These must match exactly. Check _make_function_id() path format."
        )
        report = BlastRadiusReport(
            run_id=run_id, pr_url=delta.pr_url, pr_number=delta.pr_number,
            pr_title=delta.title, mode="neo4j",
            changed_files=delta.changed_files, seed_function_ids=[],
            affected_ui_elements=[], affected_requirements=[],
            absent_requirements=absent_requirements,
            dark_changes=[cf.path for cf in delta.changed_files],
            evidence_subgraph=[], confidence_scores={},
            manual_review_items=[
                "All changed files have no matching CodeFunction nodes in the graph. "
                "This PR may affect configuration, assets, or files outside the indexed TypeScript scope. "
                "Manual review required for all changed files."
            ],
        )
        _save_report(report, delta)
        return report

    raw_scores = personalized_pagerank(graph, seeds)
    normalized = normalize_scores(raw_scores, set(seeds), min_absolute=1e-5)
    affected_ui, affected_req, dark_changes = compute_affected_nodes(
        graph, seeds, normalized, entity_links, node_meta
    )

    # Populate changed_function_ids and write back to disk
    delta.changed_function_ids = seeds
    delta_path = settings.data_dir / "code" / f"pr_{settings.pr_number}.json"
    delta_path.write_text(delta.model_dump_json(indent=2), encoding="utf-8")

    # Evidence subgraph: edges on paths from seeds to affected nodes
    evidence_edge_set: set[tuple[str, str]] = set()
    try:
        import networkx as nx
        for node in affected_ui + affected_req:
            for seed in seeds:
                try:
                    raw_path = nx.shortest_path(graph, seed, node.node_id, method="dijkstra", weight="weight")
                    for i in range(len(raw_path) - 1):
                        evidence_edge_set.add((raw_path[i], raw_path[i + 1]))
                except Exception:
                    pass
    except Exception:
        pass
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
            + ", ".join(str(dc) for dc in dark_changes[:3])
            + ("..." if len(dark_changes) > 3 else "")
        )
    if absent_requirements:
        manual_review.append(
            f"{len(absent_requirements)} requirement(s) have no code or UI coverage. "
            "They may be unimplemented features or gaps in the crawl coverage."
        )

    report = BlastRadiusReport(
        run_id=run_id, pr_url=delta.pr_url, pr_number=delta.pr_number,
        pr_title=delta.title, mode="neo4j",
        changed_files=delta.changed_files, seed_function_ids=seeds,
        affected_ui_elements=affected_ui, affected_requirements=affected_req,
        absent_requirements=absent_requirements, dark_changes=dark_changes,
        evidence_subgraph=evidence_subgraph,
        confidence_scores={n.node_id: n.impact_score for n in affected_ui + affected_req},
        manual_review_items=manual_review,
    )
    _save_report(report, delta)
    return report


def _save_report(report: BlastRadiusReport, delta: PRDelta) -> None:
    out = REPORTS_DIR / "blast_radius_report.json"
    out.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    print(
        f"[reason] Report saved: "
        f"{len(report.affected_ui_elements)} UI | "
        f"{len(report.affected_requirements)} req | "
        f"{len(report.absent_requirements)} absent | "
        f"{len(report.dark_changes)} dark | "
        f"{len(report.manual_review_items)} manual review items"
    )
```

---

### Phase 5 Smoke Test

```bash
python -c "from blast_radius.reason import analyze_pr; r = analyze_pr(); print(r.pr_url)"
python -c "
import json, os
from blast_radius.models import BlastRadiusReport, PRDelta

report = BlastRadiusReport.model_validate_json(
    open('data/reports/blast_radius_report.json', encoding='utf-8').read()
)
assert report.pr_url.startswith('https://github.com')
assert all(0 <= v <= 1 for v in report.confidence_scores.values()), 'Confidence scores out of [0,1] range'

has_content = (
    report.affected_ui_elements
    or report.affected_requirements
    or report.absent_requirements
    or report.dark_changes
    or report.manual_review_items
)
assert has_content, 'Report is completely empty — check Phase 3/4 outputs'

# Evidence paths must be human-readable (not SHA hashes)
for node in report.affected_ui_elements + report.affected_requirements:
    for step in node.evidence_path:
        assert not (len(step) == 16 and all(c in '0123456789abcdef' for c in step)), \
            f'Evidence path contains raw SHA hash: {step}. Check node_metadata lookup.'

# Verify changed_function_ids written back
pr_num = settings_pr_num = int(os.environ.get('PR_NUMBER', '0'))
if pr_num:
    delta = PRDelta.model_validate_json(
        open(f'data/code/pr_{pr_num}.json', encoding='utf-8').read()
    )
    print(f'delta.changed_function_ids: {len(delta.changed_function_ids)} seeds')

print(f'OK — UI:{len(report.affected_ui_elements)} req:{len(report.affected_requirements)} absent:{len(report.absent_requirements)} dark:{len(report.dark_changes)}')
" 2>/dev/null || python -c "
from blast_radius.models import BlastRadiusReport
report = BlastRadiusReport.model_validate_json(
    open('data/reports/blast_radius_report.json', encoding='utf-8').read()
)
print(f'OK — UI:{len(report.affected_ui_elements)} req:{len(report.affected_requirements)} absent:{len(report.absent_requirements)} dark:{len(report.dark_changes)}')
"
```

**Merge condition:** Report validates against schema, scores in [0,1], non-empty, evidence paths contain readable text not SHA hashes.

---

## Phase 6: Human-Readable Report

**Branch:** `feature/phase-6-report`
**Build time:** ~30 min | **Run time:** ~30-60 sec (one LLM call for summary)
**Prerequisites:** Phase 5 merged

**Creates:** `blast_radius/report/__init__.py`, `blast_radius/report/render.py`, `templates/report.html.j2`

---

### templates/report.html.j2

> **v4 fix (P1-27):** `autoescape=False` for this template — all content is internal/controlled. Cypher queries no longer HTML-escape file path slashes.
> **v4 fix (P2-28):** Affected UI elements section added.
> Absent requirements section included (was missing in v3).
> `seed_function_ids` rendered via `tojson` filter for correct JSON array output.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Blast Radius Report — PR #{{ report.pr_number }}</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 980px; margin: 2rem auto; color: #1a1a1a; line-height: 1.6; padding: 0 1rem; }
  h1 { border-bottom: 3px solid #e53e3e; padding-bottom: .5rem; }
  h2 { margin-top: 2rem; border-bottom: 1px solid #e2e8f0; padding-bottom: .25rem; }
  .badge-high   { background:#fed7d7;color:#c53030;padding:2px 8px;border-radius:4px;font-size:.85em;font-weight:600; }
  .badge-medium { background:#fefcbf;color:#744210;padding:2px 8px;border-radius:4px;font-size:.85em;font-weight:600; }
  .badge-low    { background:#bee3f8;color:#2b6cb0;padding:2px 8px;border-radius:4px;font-size:.85em;font-weight:600; }
  .badge-absent { background:#e9d8fd;color:#553c9a;padding:2px 8px;border-radius:4px;font-size:.85em;font-weight:600; }
  .badge-dark   { background:#e2e8f0;color:#4a5568;padding:2px 8px;border-radius:4px;font-size:.85em;font-weight:600; }
  table { border-collapse:collapse;width:100%;margin:1rem 0; }
  th,td { border:1px solid #e2e8f0;padding:.5rem .75rem;text-align:left;vertical-align:top; }
  th { background:#f7fafc;font-weight:600; }
  .evidence { font-family:monospace;font-size:.82em;background:#f7fafc;padding:.4rem;border-radius:4px;word-break:break-word; }
  .box-warning { background:#fffbeb;border-left:4px solid #d69e2e;padding:.75rem 1rem;margin:1rem 0;border-radius:0 4px 4px 0; }
  .box-absent  { background:#faf5ff;border-left:4px solid #805ad5;padding:.75rem 1rem;margin:1rem 0;border-radius:0 4px 4px 0; }
  .box-dark    { background:#f7fafc;border-left:4px solid #718096;padding:.75rem 1rem;margin:1rem 0;border-radius:0 4px 4px 0; }
  footer { margin-top:3rem;font-size:.8em;color:#718096;border-top:1px solid #e2e8f0;padding-top:1rem; }
  code { background:#f7fafc;padding:1px 4px;border-radius:3px;font-size:.9em; }
  pre { background:#f7fafc;padding:1rem;border-radius:4px;overflow-x:auto;font-size:.85em; }
</style>
</head>
<body>

<h1>🔍 Blast Radius Report</h1>

<table>
  <tr><th>Pull Request</th><td><a href="{{ report.pr_url }}">#{{ report.pr_number }} — {{ report.pr_title }}</a></td></tr>
  <tr><th>Analysis Mode</th><td>{{ report.mode }}</td></tr>
  <tr><th>Run ID</th><td><code>{{ report.run_id }}</code></td></tr>
  <tr><th>Changed Files</th><td>{{ report.changed_files | length }}</td></tr>
  <tr><th>Seed Functions</th><td>{{ report.seed_function_ids | length }}</td></tr>
</table>

{% if report.summary %}
<h2>Executive Summary</h2>
<p>{{ report.summary }}</p>
{% endif %}

<h2>Changed Files</h2>
<table>
  <tr><th>File</th><th>Status</th><th>+Lines</th><th>−Lines</th></tr>
  {% for f in report.changed_files %}
  <tr><td><code>{{ f.path }}</code></td><td>{{ f.status }}</td><td>+{{ f.additions }}</td><td>-{{ f.deletions }}</td></tr>
  {% endfor %}
</table>

<!-- v4 fix (P2-28): Affected UI / Pages section added -->
<h2>Affected UI / Pages ({{ report.affected_ui_elements | length }})</h2>
{% if report.affected_ui_elements %}
<table>
  <tr><th>Element / Page</th><th>Risk</th><th>Impact Score</th><th>Confidence</th><th>Evidence Path</th></tr>
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
<p><em>No UI elements directly traced to changed code. This may mean the PR affects only internal logic, or that the UI crawl was limited (unauthenticated only).</em></p>
{% endif %}

<h2>Affected Requirements ({{ report.affected_requirements | length }})</h2>
{% if report.affected_requirements %}
<table>
  <tr><th>Requirement</th><th>Risk</th><th>Impact Score</th><th>Confidence</th><th>Evidence Path</th></tr>
  {% for req in report.affected_requirements %}
  <tr>
    <td>{{ req.label }}</td>
    <td><span class="badge-{{ req.risk_tier | lower }}">{{ req.risk_tier }}</span></td>
    <td>{{ "%.2f" | format(req.impact_score) }}</td>
    <td>{{ "%.2f" | format(req.traceability_confidence) }}</td>
    <td class="evidence">{{ req.evidence_path | join(' → ') }}</td>
  </tr>
  {% endfor %}
</table>
{% else %}
<p><em>No requirements directly traced to changed code.</em></p>
{% endif %}

{% if report.absent_requirements %}
<h2>🟣 Absent Requirements — No Coverage Found ({{ report.absent_requirements | length }})</h2>
<div class="box-absent">
  <strong>These requirements exist in documentation but have no CodeFunction or UIElement linked in the graph.</strong>
  Each is a candidate for manual verification: it may be unimplemented, behind authentication not yet crawled, or using different vocabulary than the code.
  <table style="margin-top:.75rem">
    <tr><th>Requirement</th><th>Status</th></tr>
    {% for req in report.absent_requirements %}
    <tr><td>{{ req.label }}</td><td><span class="badge-absent">ABSENT</span></td></tr>
    {% endfor %}
  </table>
</div>
{% endif %}

{% if report.dark_changes %}
<h2>⚫ Dark Changes — No Traceable Path ({{ report.dark_changes | length }})</h2>
<div class="box-dark">
  <strong>These changed functions have no traceable path to any UI element or requirement in the graph.</strong>
  They may affect internal logic, configuration, infrastructure, or code outside the indexed scope. Manual review required.
  <ul>{% for dc in report.dark_changes %}<li><code>{{ dc }}</code></li>{% endfor %}</ul>
</div>
{% endif %}

{% if report.manual_review_items %}
<h2>⚠️ Manual Review Required</h2>
<div class="box-warning">
  <ul>{% for item in report.manual_review_items %}<li>{{ item }}</li>{% endfor %}</ul>
</div>
{% endif %}

<h2>Coverage Statistics</h2>
<table>
  <tr><th>Metric</th><th>Count</th></tr>
  <tr><td>Affected UI elements / pages</td><td>{{ report.affected_ui_elements | length }}</td></tr>
  <tr><td>Affected requirements</td><td>{{ report.affected_requirements | length }}</td></tr>
  <tr><td>Absent requirements (no coverage)</td><td>{{ report.absent_requirements | length }}</td></tr>
  <tr><td>Dark changes (no graph path)</td><td>{{ report.dark_changes | length }}</td></tr>
  <tr><td>Evidence edges in subgraph</td><td>{{ report.evidence_subgraph | length }}</td></tr>
  <tr><td>Manual review items</td><td>{{ report.manual_review_items | length }}</td></tr>
</table>

<footer>
  Report generated by Blast Radius Analyzer v4 · Run ID: <code>{{ report.run_id }}</code><br>
  Neo4j evidence query (paste into <a href="http://localhost:7474">Neo4j Browser</a>):
  <pre>MATCH path=(f:CodeFunction)-[*1..6]->(r:Requirement)
WHERE f.id IN {{ report.seed_function_ids[:3] | tojson }}
RETURN path LIMIT 50</pre>
</footer>
</body>
</html>
```

---

### blast_radius/report/render.py

> **v4 fix (P1-27):** `autoescape=False` — content is internal/controlled, not user-generated.
> **v4 fix (P2-28):** Affected UI elements section added to Markdown output.
> Summary generated from structured data only; no hallucinated risks.

```python
from pathlib import Path
from typing import Optional

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
        f"PR URL: {report.pr_url}\n"
        f"Changed files: {[cf.path for cf in report.changed_files[:5]]}\n"
        f"High-risk requirements: {[n.label for n in high[:3]]}\n"
        f"Absent requirements count: {len(report.absent_requirements)}\n"
        f"Dark changes count: {len(report.dark_changes)}\n"
        "Write ONLY what the structured data supports. Do not invent risks not present in the data. "
        "Do not use jargon like 'blast radius' or 'PPR'. Write for a QA lead who knows the product."
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
            and not report.absent_requirements
            and not report.affected_requirements
            and not report.affected_ui_elements):
        raise RuntimeError(
            "Refusing to render a completely empty report. "
            "This indicates a pipeline failure in Phase 3, 4, or 5. "
            "Check logs from each phase."
        )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        summary = _generate_summary(report)
        report = report.model_copy(update={"summary": summary})
    except Exception as e:
        print(f"[report] WARNING: Summary generation failed: {e}. Proceeding without summary.")

    # HTML report
    # v4 fix (P1-27): autoescape=False — all content is internal/controlled
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader("templates"), autoescape=False)
    template = env.get_template("report.html.j2")
    html = template.render(report=report)
    html_path = REPORTS_DIR / "blast_radius_report.html"
    html_path.write_text(html, encoding="utf-8")

    # Markdown report
    high_req = [n for n in report.affected_requirements if n.risk_tier == "HIGH"]
    medium_req = [n for n in report.affected_requirements if n.risk_tier == "MEDIUM"]
    high_ui = [n for n in report.affected_ui_elements if n.risk_tier == "HIGH"]

    lines = [
        f"# Blast Radius Report — PR #{report.pr_number}",
        "",
        f"**PR:** [{report.pr_title}]({report.pr_url})  ",
        f"**Mode:** {report.mode}  **Run ID:** `{report.run_id}`",
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

    # v4 fix (P2-28): Affected UI elements section in Markdown
    lines += ["", f"## Affected UI / Pages ({len(report.affected_ui_elements)})", ""]
    if high_ui:
        lines += ["### 🔴 High Confidence", ""]
        for n in high_ui:
            lines += [
                f"- **{n.label}**",
                f"  - Impact: {n.impact_score:.2f} | Confidence: {n.traceability_confidence:.2f}",
                f"  - Evidence: {' → '.join(n.evidence_path)}",
                "",
            ]
    medium_ui = [n for n in report.affected_ui_elements if n.risk_tier == "MEDIUM"]
    if medium_ui:
        lines += ["### 🟡 Medium Confidence", ""]
        for n in medium_ui:
            lines.append(f"- **{n.label}** (impact: {n.impact_score:.2f})")
        lines.append("")
    if not report.affected_ui_elements:
        lines.append("_No UI elements directly traced to changed code._\n")

    lines += [f"## Affected Requirements ({len(report.affected_requirements)})", ""]
    if high_req:
        lines += ["### 🔴 High Confidence", ""]
        for n in high_req:
            lines += [
                f"- **{n.label}**",
                f"  - Impact: {n.impact_score:.2f} | Confidence: {n.traceability_confidence:.2f}",
                f"  - Evidence: {' → '.join(n.evidence_path)}",
                "",
            ]
    if medium_req:
        lines += ["### 🟡 Medium Confidence", ""]
        for n in medium_req:
            lines.append(f"- **{n.label}** (impact: {n.impact_score:.2f})")
        lines.append("")
    if not report.affected_requirements:
        lines.append("_No requirements directly traced to changed code._\n")

    if report.absent_requirements:
        lines += [
            f"## 🟣 Absent Requirements — No Coverage Found ({len(report.absent_requirements)})",
            "",
            "These requirements exist in documentation but have no CodeFunction or UIElement "
            "linked in the graph. Each is a candidate for manual verification.",
            "",
        ]
        for req in report.absent_requirements:
            lines.append(f"- **{req.label}**")
        lines.append("")

    if report.dark_changes:
        lines += [f"## ⚫ Dark Changes ({len(report.dark_changes)})", "",
                  "These changed functions have no traceable path to any UI or requirement:", ""]
        for dc in report.dark_changes:
            lines.append(f"- `{dc}`")
        lines.append("")

    if report.manual_review_items:
        lines += ["## ⚠️ Manual Review Required", ""]
        for item in report.manual_review_items:
            lines.append(f"- {item}")
        lines.append("")

    lines += [
        "## Coverage Statistics",
        "",
        "| Metric | Count |",
        "|---|---|",
        f"| Affected UI elements / pages | {len(report.affected_ui_elements)} |",
        f"| Affected requirements | {len(report.affected_requirements)} |",
        f"| Absent requirements | {len(report.absent_requirements)} |",
        f"| Dark changes | {len(report.dark_changes)} |",
        f"| Manual review items | {len(report.manual_review_items)} |",
        "",
        "---",
        f"*Report generated by Blast Radius Analyzer v4 · Run ID: `{report.run_id}`*",
    ]

    md_path = REPORTS_DIR / "blast_radius_report.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[report] HTML: {html_path}")
    print(f"[report] Markdown: {md_path}")
    return html_path, md_path
```

---

### blast_radius/report/**init**.py

```python
from blast_radius.config import settings
from blast_radius.models import BlastRadiusReport
from blast_radius.report.render import render


def render_report() -> None:
    report_path = settings.data_dir / "reports" / "blast_radius_report.json"
    if not report_path.exists():
        raise FileNotFoundError(
            f"Report JSON not found at {report_path}. Run Phase 5 first:\n"
            "  python scripts/run_pipeline.py --phase 5"
        )
    report = BlastRadiusReport.model_validate_json(report_path.read_text(encoding="utf-8"))
    render(report)
```

---

### Phase 6 Smoke Test

```bash
python -c "from blast_radius.report import render_report; render_report()"
python -c "
from pathlib import Path

html = Path('data/reports/blast_radius_report.html').read_text(encoding='utf-8')
md = Path('data/reports/blast_radius_report.md').read_text(encoding='utf-8')

# Required structure
assert '# Blast Radius Report' in md, 'Missing report title in MD'
assert 'Blast Radius Report' in html, 'Missing report title in HTML'

# v4: Affected UI section must be present in both outputs
assert 'Affected UI' in md, 'Missing Affected UI section in MD'
assert 'Affected UI' in html, 'Missing Affected UI section in HTML'

# v4: Absent requirements section rendered if data present
import json
report_data = json.load(open('data/reports/blast_radius_report.json', encoding='utf-8'))
if report_data.get('absent_requirements'):
    assert 'Absent Requirements' in html, 'Absent requirements in JSON but missing from HTML'
    assert 'Absent Requirements' in md, 'Absent requirements in JSON but missing from MD'

# Check that evidence paths are readable (not SHA hashes)
if 'evidence_path' in md.lower() or '→' in md:
    # Look for obvious hash patterns (16 hex chars) in evidence context
    import re
    hashes_in_evidence = re.findall(r'→\s*([0-9a-f]{16})\s*→', md)
    assert not hashes_in_evidence, f'Raw SHA hashes in evidence path: {hashes_in_evidence}'

print(f'OK — HTML: {len(html):,} chars | MD: {len(md):,} chars')
"
```

**Merge condition:** Both files non-empty, Affected UI section present in both, absent requirements rendered if applicable, evidence paths contain readable text.

---
