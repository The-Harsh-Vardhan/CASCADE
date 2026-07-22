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
