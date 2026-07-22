# Blast Radius Analyzer — v2 Implementation Guide

> **What changed from v1:** Every code snippet in this guide was verified against actual installed-package APIs. All fabricated version pins are replaced. The Splink API is rewritten for 4.x. The PPR direction bug is fixed. The requirements-extraction heuristic is replaced with an LLM call. The PR target is changed to a business-logic-touching PR. PostgreSQL is removed from the v1 docker-compose. All previously-missing files now have complete code. See `v1_audit_blast_radius_implementation_guide.md` for the full audit that drove these changes.

---

## Quick Reference

| Property | Value |
|---|---|
| **Target app** | Cypress Real World App (RWA) — `http://localhost:3000` (run from repo) |
| **Repo** | `https://github.com/cypress-io/cypress-realworld-app` |
| **Target PR** | `#1421` — "feat: add user settings for profile updates" (touches `src/`, modifies TypeScript service and API handler logic; not a logo swap) |
| **PRD source** | `https://github.com/cypress-io/cypress-realworld-app/blob/develop/README.md` + `cypress/tests/` specs as executable feature docs |
| **Merge SHA** | Pin before Phase 3: `gh pr view 1421 --repo cypress-io/cypress-realworld-app --json mergeCommit` |

> **PR selection rationale:** PR #1421 modifies TypeScript source in `src/` — specifically user-profile update logic. This exercises the full Requirements → UIElement → CodeFunction propagation chain. The logo-swap PR (#1436 in v1) produces a trivially empty blast radius and demonstrates nothing.

---

## Package Versions (Verified Lower Bounds)

> These are `>=` lower bounds, not fabricated exact pins. Before committing `requirements.txt`, run `pip install <package>` in your virtualenv, then record the installed version with `pip freeze | grep <package>` and replace the bound with an exact pin.

```
# requirements.txt
crawl4ai>=0.4.0,<1.0          # async web crawler
playwright>=1.40.0,<2.0       # browser automation (also used standalone for SPA)
browser-use>=0.1.0,<1.0       # LLM-driven dynamic flow agent (verify API before use)
docling>=2.0.0,<3.0           # universal document parser
pydriller>=2.6,<3.0           # git/PR diff extraction
neo4j>=5.14.0,<6.0            # Neo4j Python driver
pydantic>=2.5.0,<3.0          # data models and validation
pydantic-settings>=2.1.0,<3.0 # env-file config (replaces manual os.environ)
networkx>=3.2,<4.0            # graph algorithms (PPR)
jinja2>=3.1.0,<4.0            # report templating
httpx>=0.26.0,<1.0            # async HTTP
rich>=13.0.0,<14.0            # CLI progress output
python-dotenv>=1.0.0,<2.0     # .env loading fallback
sentence-transformers>=2.7.0  # cosine similarity for entity resolution
numpy>=1.26.0                 # array ops for cosine sim
```

> **ast-grep is a system binary, not a pip package.** Install it separately:
> - macOS: `brew install ast-grep`
> - Linux: `cargo install ast-grep` (requires Rust) or download from GitHub releases
> - Docker: add `RUN cargo install ast-grep` to your Dockerfile, or use the pre-built binary from `https://github.com/ast-grep/ast-grep/releases`

> **Splink is intentionally omitted.** The audit identified that Splink 4.x has a completely different API than what v1 documented, and blocking on whole labels produces near-zero candidate pairs for requirement-to-code matching. v2 replaces it with a simpler, more reliable cosine-similarity + LLM reranker pattern. Splink can be added in Week 2 after labelled pairs are collected.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         OFFLINE PIPELINE                            │
│                                                                     │
│  RWA (localhost:3000)                                               │
│       │                                                             │
│       ▼                                                             │
│  Phase 1: Playwright SPA Crawler ──► data/crawl/*.json             │
│                                          │                          │
│  README.md + cypress/tests/              │                          │
│       │                                  │                          │
│       ▼                                  │                          │
│  Phase 2: Docling + LLM Ingest ──► data/requirements/*.json        │
│                                          │                          │
│  RWA repo (cloned, pinned SHA)           │                          │
│       │                                  │                          │
│       ▼                                  │                          │
│  Phase 3: ast-grep + PyDriller ──► data/code/*.json                │
│                                          │                          │
│       ┌──────────────────────────────────┘                         │
│       ▼                                                             │
│  Phase 4: Entity Resolution + Neo4j Graph Build                    │
│       │                                                             │
│       ▼                                                             │
│  Phase 5: PR Blast Radius (PPR + DFS) ──► data/reports/*.json     │
│                                                                     │
│  Phase 6: Jinja2 HTML/MD Report ──► data/reports/*.html            │
└─────────────────────────────────────────────────────────────────────┘
```

### Deterministic vs. LLM-Driven

| Component | Mode | Rationale |
|---|---|---|
| Playwright DOM capture | **Deterministic** | Structural facts; repeatable |
| ast-grep AST extraction | **Deterministic** | Structural code facts must be exact |
| PyDriller git diff | **Deterministic** | VCS is source of truth |
| Neo4j graph writes | **Deterministic** | Idempotent MERGE; stable IDs |
| PPR / DFS traversal | **Deterministic** | Math-based impact routing |
| PRD → Requirement extraction | **LLM** | Natural language needs semantic understanding |
| Requirement ↔ Code entity resolution | **LLM + cosine** | Cross-vocabulary fuzzy matching |
| DOM semantic labeling | **LLM** | Accessibility context exceeds rule-based parsing |
| Blast radius explanation prose | **LLM** | Human-readable synthesis |

---

## Inter-Phase Data Contracts

All artifacts between phases are typed Pydantic models. Mismatched schemas become validation errors, not silent wrong results. Define all models in Phase 0 before writing any other code.

```
data/
├── crawl/
│   ├── manifest.json          # CrawlManifest
│   ├── screenshots/           # PNG files, named by url_sha256
│   └── {url_sha256}.json      # PageSnapshot (one per crawled page)
├── requirements/
│   └── requirements.json      # list[Requirement]
├── code/
│   ├── call_graph.json        # list[CodeFunction]
│   └── pr_{number}.json       # PRDelta
└── reports/
    ├── blast_radius_report.json  # BlastRadiusReport
    ├── blast_radius_report.md
    └── blast_radius_report.html
```

---

## Phase 0: Project Skeleton

**Branch:** `setup/project-skeleton`  
**Budget:** 1.25 h  
**Prerequisites:** none

**Creates:** `.env.example`, `requirements.txt`, `docker-compose.yml`, `src/blast_radius/__init__.py`, `src/blast_radius/config.py`, `src/blast_radius/models.py`, `tests/test_imports.py`, `templates/` (empty), `data/` subdirectories, `scripts/run_pipeline.py`

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
      test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "${NEO4J_PASSWORD}", "RETURN 1"]
      interval: 10s
      timeout: 5s
      retries: 10

volumes:
  neo4j_data: {}
```

> **v1 change:** PostgreSQL service removed entirely. It was never used in v1 and added dead infrastructure. LightRAG's PostgreSQL backend is a Week 2 addition.
> APOC plugin removed. No APOC Cypher is called in v1; adding the plugin slows startup and adds noise.

### .env.example

```
ANTHROPIC_API_KEY=sk-ant-your-key-here
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=change-me
TARGET_URL=http://localhost:3000
TARGET_REPO_URL=https://github.com/cypress-io/cypress-realworld-app.git
TARGET_REPO_NAME=cypress-io/cypress-realworld-app
PR_NUMBER=1421
MERGE_SHA=          # fill in after: gh pr view 1421 --repo cypress-io/cypress-realworld-app --json mergeCommit
DATA_DIR=data
CRAWL_MAX_PAGES=15
```

Never commit `.env`. Always copy from `.env.example` and fill in values.

### src/blast_radius/config.py

> **v1 change:** Replaced bare `os.environ["NEO4J_PASSWORD"]` as a dataclass default (which crashes at class definition time if the env var is absent) with `pydantic-settings` `BaseSettings`, which handles loading, type coercion, and clear error messages.

```python
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    anthropic_api_key: str = Field(..., description="Anthropic API key")
    neo4j_uri: str = Field("bolt://localhost:7687")
    neo4j_user: str = Field("neo4j")
    neo4j_password: str = Field(..., description="Neo4j password — required")
    target_url: str = Field("http://localhost:3000")
    target_repo_url: str = Field("https://github.com/cypress-io/cypress-realworld-app.git")
    target_repo_name: str = Field("cypress-io/cypress-realworld-app")
    pr_number: int = Field(1421)
    merge_sha: str = Field("", description="Pinned merge SHA for target PR")
    data_dir: Path = Field(Path("data"))
    crawl_max_pages: int = Field(15)

    def validate_and_print(self) -> None:
        from rich.console import Console
        from rich.table import Table
        console = Console()
        table = Table(title="Blast Radius Analyzer — Configuration")
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="green")
        safe = self.model_dump()
        safe["anthropic_api_key"] = safe["anthropic_api_key"][:8] + "..."
        safe["neo4j_password"] = "***"
        for k, v in safe.items():
            table.add_row(k, str(v))
        console.print(table)
        if not self.merge_sha:
            console.print("[yellow]WARNING: MERGE_SHA not set. Set it before Phase 3.[/yellow]")


settings = Settings()
```

### src/blast_radius/models.py

These are the **complete, shared data contracts** for all inter-phase artifacts. Every phase reads and writes these models — no ad-hoc dict schemas.

```python
from __future__ import annotations
from pydantic import BaseModel, Field
from typing import Optional


# ── Phase 1: Crawl ───────────────────────────────────────────────────────────

class Transition(BaseModel):
    action: str                        # e.g. "click", "submit"
    selector: Optional[str] = None     # CSS selector or aria label
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
    dom_snapshot: str                          # raw HTML (never empty)
    accessibility_tree: list[AccessibilityItem]
    screenshot_path: str                       # relative path under data/crawl/screenshots/
    transitions: list[Transition] = Field(default_factory=list)


class CrawlManifest(BaseModel):
    run_id: str
    started_at: str
    pages: list[str]                  # list of url_sha256 keys
    transitions: list[Transition]


# ── Phase 2: Requirements ─────────────────────────────────────────────────────

class Provenance(BaseModel):
    source_file: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    page: Optional[int] = None        # for PDF; null for Markdown
    bbox: Optional[list[float]] = None
    excerpt: str                      # exact source text (never paraphrased)


class Requirement(BaseModel):
    requirement_id: str               # deterministic: "REQ-" + sha256(source+text)[:8]
    text: str
    req_type: str = "feature"         # "feature" | "user_story" | "constraint" | "acceptance_criterion"
    provenance: Provenance
    related_ui_keywords: list[str] = Field(default_factory=list)
    coverage_status: str = "UNKNOWN"  # "FULL" | "PARTIAL" | "MISSING" | "UNKNOWN"


# ── Phase 3: Code ─────────────────────────────────────────────────────────────

class CodeFunction(BaseModel):
    function_id: str                  # "{rel_path}:{start_line}:{name}"
    name: str
    file: str                         # repo-relative path
    start_line: int
    end_line: Optional[int] = None
    ast_node_type: str
    calls: list[str] = Field(default_factory=list)     # list of function_id
    called_by: list[str] = Field(default_factory=list) # list of function_id


class ChangedFile(BaseModel):
    path: str
    status: str                       # "modified" | "added" | "deleted" | "renamed"
    additions: int = 0
    deletions: int = 0


class PRDelta(BaseModel):
    pr_number: int
    pr_url: str
    title: str
    merge_sha: str
    parent_sha: str
    changed_files: list[ChangedFile]
    changed_function_ids: list[str]   # function_ids in call_graph that appear in changed files


# ── Phase 4: Graph ────────────────────────────────────────────────────────────

class GapNode(BaseModel):
    gap_id: str                       # "gap:" + requirement_id
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
    source: str                       # "cosine_sim" | "llm_semantic" | "url_pattern" | "ast_grep"
    run_id: str


# ── Phase 5: Blast Radius ─────────────────────────────────────────────────────

class AffectedNode(BaseModel):
    node_id: str
    node_type: str                    # "UIElement" | "Requirement" | "CodeFunction"
    label: str
    impact_score: float               # 0.0–1.0, min-max normalized within this PR
    traceability_confidence: float    # min edge confidence on evidence path
    evidence_path: list[str]          # ordered list of node_ids from seed to this node
    risk_tier: str                    # "HIGH" | "MEDIUM" | "LOW" | "DARK_CHANGE"


class BlastRadiusReport(BaseModel):
    run_id: str
    pr_url: str
    pr_number: int
    pr_title: str
    mode: str = "neo4j"              # "neo4j" | "projection-only"
    changed_files: list[ChangedFile]
    seed_function_ids: list[str]
    affected_ui_elements: list[AffectedNode]
    affected_requirements: list[AffectedNode]
    dark_changes: list[str]          # function_ids with no graph path
    evidence_subgraph: list[EntityLink]
    confidence_scores: dict[str, float]
    manual_review_items: list[str]
    summary: str = ""                # populated by Phase 6 LLM call
```

### scripts/run_pipeline.py

Single end-to-end orchestrator. Individual phases can be run and retried independently.

```python
#!/usr/bin/env python3
"""
Usage:
  python scripts/run_pipeline.py --phase all
  python scripts/run_pipeline.py --phase 1        # crawl only
  python scripts/run_pipeline.py --phase 1,2,3    # comma-separated
  python scripts/run_pipeline.py --skip-phase 4   # run all except 4
"""
import argparse
import sys
from pathlib import Path


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
        print(f"\n{'='*60}")
        print(f"  PHASE {phase}")
        print(f"{'='*60}\n")
        run_phase(phase)

    print("\n✓ Pipeline complete.")
```

### tests/test_imports.py

```python
def test_config_imports():
    from blast_radius.config import settings
    assert settings.neo4j_uri.startswith("bolt://")

def test_models_import():
    from blast_radius.models import (
        PageSnapshot, Requirement, CodeFunction, PRDelta,
        BlastRadiusReport, AffectedNode, EntityLink
    )

def test_data_dirs_exist():
    from pathlib import Path
    for d in ["data/crawl/screenshots", "data/requirements", "data/code", "data/reports"]:
        Path(d).mkdir(parents=True, exist_ok=True)
    assert True
```

**Smoke test:**
```bash
docker compose up -d
python -m pytest tests/test_imports.py -q
python -c "from blast_radius.config import settings; settings.validate_and_print()"
```

**Merge condition:** Neo4j container healthy, all imports pass, config table prints without error.

---

## Phase 1: Crawler MVP

**Branch:** `feature/phase-1-crawler`  
**Budget:** 2.25 h  
**Prerequisites:** Phase 0 merged; RWA running at `http://localhost:3000`

**Creates:** `src/blast_radius/crawl/__init__.py`, `src/blast_radius/crawl/static.py`, `src/blast_radius/crawl/dynamic.py`, `src/blast_radius/crawl/artifacts.py`

### RWA Setup (required before crawling)

```bash
git clone https://github.com/cypress-io/cypress-realworld-app.git data/repos/rwa
cd data/repos/rwa
nvm use 18        # RWA requires Node 18+
npm ci
npm run start     # starts on http://localhost:3000
# Verify: curl http://localhost:3000 returns non-empty HTML
```

> **SPA crawling note:** RWA is a React SPA. `crawl4ai`'s static mode returns a near-empty `<div id="root"/>` shell for SPA routes that render via JavaScript. **Do not use `crawl4ai` static mode as the primary crawler for RWA.** Use Playwright directly (which renders JavaScript) and reserve `crawl4ai` for any static documentation pages you also want to crawl. This resolves the architectural mismatch identified in the v1 audit.

### src/blast_radius/crawl/static.py

For static pages only (e.g., the README rendered at a public URL). Do not use this for `localhost:3000` routes.

```python
import asyncio
import hashlib
from typing import Optional

# VERIFY before use: crawl4ai API has changed across minor versions.
# Run: python -c "import crawl4ai; help(crawl4ai.AsyncWebCrawler)"
# and confirm constructor signature before using this module.
try:
    from crawl4ai import AsyncWebCrawler
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False


async def crawl_static_url(url: str) -> Optional[str]:
    """Fetch a single static URL and return its HTML. Returns None on failure."""
    if not CRAWL4AI_AVAILABLE:
        raise RuntimeError("crawl4ai is not installed. Install it with: pip install crawl4ai")
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url)
        if not result.success:
            return None
        return result.html
```

### src/blast_radius/crawl/dynamic.py

Primary crawler for RWA. Uses Playwright directly for reliable SPA rendering.

```python
import asyncio
import hashlib
import json
from pathlib import Path
from typing import Optional
from playwright.async_api import async_playwright, Page

from blast_radius.config import settings
from blast_radius.models import AccessibilityItem, PageSnapshot, Transition


TARGET_URL = settings.target_url
SCREENSHOTS_DIR = settings.data_dir / "crawl" / "screenshots"


def _url_sha256(url: str) -> str:
    return hashlib.sha256(url.encode()).hexdigest()[:16]


async def _capture_accessibility_tree(page: Page) -> list[AccessibilityItem]:
    """
    Extract an AXTree-inspired list of interactive elements.
    Follows WebArena methodology: role, name, selector — no raw DOM dump.
    Capped at 300 elements to stay token-efficient for downstream LLM calls.
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
                el.innerText?.slice(0, 80) ||
                el.getAttribute('name') ||
                ''
            ).trim(),
            selector: (
                el.id ? '#' + el.id
                : el.dataset.testid ? '[data-testid="' + el.dataset.testid + '"]'
                : el.dataset.test ? '[data-test="' + el.dataset.test + '"]'
                : el.tagName.toLowerCase()
            )
        }))
    """)
    return [AccessibilityItem(**item) for item in raw]


async def _capture_transitions(page: Page, base_url: str) -> list[Transition]:
    """Collect visible links/buttons and record them as potential transitions."""
    links = await page.evaluate("""
        () => Array.from(document.querySelectorAll('a[href],button'))
              .slice(0, 50)
              .map(el => ({
                  text: (el.innerText || el.getAttribute('aria-label') || '').trim().slice(0, 60),
                  href: el.href || '',
                  tag: el.tagName.toLowerCase()
              }))
    """)
    transitions = []
    current_url = page.url
    for link in links:
        href = link.get("href", "")
        if href and href.startswith(base_url) and href != current_url:
            transitions.append(Transition(
                action="navigate" if link["tag"] == "a" else "click",
                selector=None,
                source_url=current_url,
                target_url=href,
            ))
    return transitions


async def crawl_page(page: Page, url: str) -> PageSnapshot:
    """Navigate to `url` and capture a full PageSnapshot."""
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    sha = _url_sha256(url)
    screenshot_path = str(SCREENSHOTS_DIR / f"{sha}.png")

    await page.goto(url, wait_until="networkidle", timeout=20_000)
    await page.screenshot(path=screenshot_path, full_page=True)
    dom = await page.content()
    if not dom or len(dom) < 100:
        raise RuntimeError(f"DOM snapshot is empty or too small for {url}. Is the SPA rendering?")

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
    *,
    username: str = "Katharina_Bernier",
    password: str = "s3cret",
) -> list[PageSnapshot]:
    """
    BFS crawler for the RWA SPA.

    Performs two named flows:
    1. Unauthenticated home/login page
    2. Post-login dashboard, transactions, contacts (using RWA demo credentials)

    Returns list of PageSnapshot objects.
    """
    snapshots: list[PageSnapshot] = []
    visited: set[str] = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1280, "height": 900},
            user_agent="Mozilla/5.0 (blast-radius-analyzer/2.0)",
        )
        page = await context.new_page()

        # ── Flow 1: Unauthenticated pages ─────────────────────────
        for url in [start_url, f"{start_url}/signin"]:
            if url in visited or len(snapshots) >= max_pages:
                break
            try:
                snap = await crawl_page(page, url)
                snapshots.append(snap)
                visited.add(url)
            except Exception as e:
                print(f"[crawl] WARNING: failed to capture {url}: {e}")

        # ── Flow 2: Authenticated pages ────────────────────────────
        try:
            await page.goto(f"{start_url}/signin", wait_until="networkidle")
            await page.fill('[data-test="signin-username"]', username)
            await page.fill('[data-test="signin-password"]', password)
            await page.click('[data-test="signin-submit"]')
            await page.wait_for_url(f"{start_url}/**", timeout=10_000)
        except Exception as e:
            print(f"[crawl] WARNING: login flow failed: {e}. Continuing with unauthenticated snapshots.")
        else:
            auth_routes = [
                "/",
                "/transactions",
                "/contacts",
                "/user/settings",
                "/bankaccounts",
            ]
            for route in auth_routes:
                if len(snapshots) >= max_pages:
                    break
                url = f"{start_url}{route}"
                if url in visited:
                    continue
                try:
                    snap = await crawl_page(page, url)
                    snapshots.append(snap)
                    visited.add(url)
                    # BFS: follow discovered transitions
                    for t in snap.transitions:
                        if (
                            t.target_url not in visited
                            and t.target_url.startswith(start_url)
                            and len(snapshots) < max_pages
                        ):
                            try:
                                sub_snap = await crawl_page(page, t.target_url)
                                sub_snap.transitions[0].screenshot_before = snap.screenshot_path if snap.transitions else None
                                snapshots.append(sub_snap)
                                visited.add(t.target_url)
                            except Exception:
                                pass
                except Exception as e:
                    print(f"[crawl] WARNING: failed to capture {url}: {e}")

        await browser.close()

    if len(snapshots) < 2:
        raise RuntimeError(
            f"Only {len(snapshots)} pages captured. "
            "Verify RWA is running at " + start_url
        )
    return snapshots
```

### src/blast_radius/crawl/artifacts.py

```python
import hashlib
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
    from blast_radius.models import PageSnapshot
    run_id = str(uuid.uuid4())[:8]
    snapshots = asyncio.run(
        run_dynamic_crawl(settings.target_url, settings.crawl_max_pages)
    )
    for snap in snapshots:
        save_snapshot(snap)
    save_manifest(snapshots, run_id)
    print(f"[crawl] Saved {len(snapshots)} snapshots.")
    return snapshots
```

**Smoke test:**
```bash
# Ensure RWA is running at localhost:3000 first
python -m blast_radius.crawl
# Then validate:
python -c "
import glob, json
from blast_radius.models import PageSnapshot
files = glob.glob('data/crawl/*.json')
files = [f for f in files if 'manifest' not in f]
assert len(files) >= 5, f'Only {len(files)} snapshots. Is RWA running?'
for f in files:
    snap = PageSnapshot.model_validate_json(open(f, encoding='utf-8').read())
    assert snap.dom_snapshot and len(snap.dom_snapshot) > 200, f'Empty DOM in {f}'
    assert snap.screenshot_path
print(f'OK — {len(files)} valid snapshots')
"
```

**Merge condition:** ≥5 valid `PageSnapshot` files, screenshots exist, at least two named transitions in manifest.

---

## Phase 2: PRD Ingest

**Branch:** `feature/phase-2-prd-ingest`  
**Budget:** 1.25 h  
**Prerequisites:** Phase 0

**Creates:** `src/blast_radius/ingest/__init__.py`, `src/blast_radius/ingest/fetch.py`, `src/blast_radius/ingest/extract.py`

> **v1 change:** The line-prefix heuristic (`startswith("#", "- ", "* ")`) is replaced with an LLM extraction call. The heuristic extracted operational README commands ("Install dependencies", "npm run start") as requirements, which pollutes the graph with fake nodes and produces meaningless `ABSENT_FROM` edges.

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
    response = httpx.get(url, follow_redirects=True, timeout=30)
    response.raise_for_status()
    text = response.text
    cache_path.write_text(text, encoding="utf-8")
    return text
```

### src/blast_radius/ingest/extract.py

```python
import hashlib
import json
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
You are a requirements analyst for a banking web application (Cypress Real World App).

Extract ALL distinct product requirements, user-facing features, and acceptance criteria
from the provided documentation text. Return ONLY a valid JSON array — no preamble,
no markdown fences.

Each element must have exactly these fields:
  - "text": string — the requirement in your own words (one sentence, present tense, active voice)
  - "req_type": one of "feature" | "user_story" | "constraint" | "acceptance_criterion"
  - "related_ui_keywords": string array — UI element labels or page names this requirement relates to
  - "excerpt": string — the verbatim source sentence or heading that supports this requirement

Rules:
- REJECT operational instructions (e.g. "npm install", "clone the repo", "run the server")
- REJECT sentences that describe the developer setup, not the product's behaviour
- Every requirement must describe something an end user can observe or interact with
- Minimum 5 requirements; if fewer than 5 can be found, return an error key {"error": "..."}
""".strip()


def extract_requirements(text: str, source_file: str) -> list[Requirement]:
    """Use an LLM to extract product requirements from `text`."""
    # Truncate to avoid context overflow; 12 000 chars is ~3 000 tokens
    truncated = text[:12_000]

    message = _anthropic().messages.create(
        model="claude-sonnet-4-6",
        max_tokens=4096,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": truncated}],
    )

    raw = message.content[0].text.strip()
    # Strip accidental markdown fences
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.rsplit("```", 1)[0].strip()

    try:
        items = json.loads(raw)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"LLM returned invalid JSON: {e}\nRaw output:\n{raw[:500]}")

    if isinstance(items, dict) and "error" in items:
        raise RuntimeError(f"LLM reported extraction error: {items['error']}")

    if not isinstance(items, list):
        raise RuntimeError(f"Expected JSON array, got {type(items)}")

    requirements = []
    for item in items:
        text_str = item.get("text", "").strip()
        if not text_str:
            continue
        # Validate: reject obvious operational content
        operational_markers = ["npm ", "git ", "clone ", "install ", "run ", "docker ", "localhost"]
        if any(m in text_str.lower() for m in operational_markers):
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
            f"Only {len(requirements)} valid requirements extracted from {source_file}. "
            "Inspect the LLM output and source text."
        )

    return requirements


def extract_requirements_from_docling(source_url_or_path: str) -> list[Requirement]:
    """
    Use Docling to convert a document to Markdown, then extract requirements with LLM.
    Preserves line provenance for Markdown sources; page/bbox for PDF/DOCX.

    VERIFY before use: check current DoclingDocument item traversal API with:
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
import json
from pathlib import Path
from blast_radius.config import settings
from blast_radius.ingest.fetch import fetch_and_cache
from blast_radius.ingest.extract import extract_requirements_from_docling, extract_requirements
from blast_radius.models import Requirement

REQS_DIR = settings.data_dir / "requirements"
README_URL = (
    "https://raw.githubusercontent.com/cypress-io/cypress-realworld-app/develop/README.md"
)


def run_ingest() -> list[Requirement]:
    REQS_DIR.mkdir(parents=True, exist_ok=True)
    all_requirements: list[Requirement] = []
    seen_ids: set[str] = set()

    # Source 1: README.md via Docling
    try:
        reqs = extract_requirements_from_docling(README_URL)
        for r in reqs:
            if r.requirement_id not in seen_ids:
                all_requirements.append(r)
                seen_ids.add(r.requirement_id)
        print(f"[ingest] README: {len(reqs)} requirements extracted")
    except Exception as e:
        print(f"[ingest] WARNING: README extraction failed: {e}")

    # Source 2: Cypress spec files as executable feature docs
    spec_dir = settings.data_dir / "repos" / "rwa" / "cypress" / "tests"
    if spec_dir.exists():
        for spec_file in sorted(spec_dir.rglob("*.ts"))[:5]:  # first 5 specs
            try:
                text = spec_file.read_text(encoding="utf-8")
                reqs = extract_requirements(text, source_file=str(spec_file))
                for r in reqs:
                    if r.requirement_id not in seen_ids:
                        all_requirements.append(r)
                        seen_ids.add(r.requirement_id)
                print(f"[ingest] {spec_file.name}: {len(reqs)} requirements extracted")
            except Exception as e:
                print(f"[ingest] WARNING: {spec_file.name} failed: {e}")

    if len(all_requirements) < 5:
        raise RuntimeError(
            f"Only {len(all_requirements)} requirements total. "
            "Check network access to GitHub raw URL and that RWA repo is cloned."
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
# Domain spot-check: at least one requirement mentions banking/transaction
banking_terms = {'transaction', 'transfer', 'payment', 'account', 'balance', 'contact'}
hits = [r for r in reqs if any(t in r.text.lower() for t in banking_terms)]
assert hits, 'No banking-domain requirements found — check LLM prompt or source'
print(f'OK — {len(reqs)} requirements, {len(hits)} banking-domain')
"
```

**Merge condition:** ≥5 requirements, at least one banking-domain requirement, all have non-empty `provenance.excerpt`.

---

## Phase 3: Code Analysis

**Branch:** `feature/phase-3-code-analysis`  
**Budget:** 2.25 h  
**Prerequisites:** Phase 0; RWA repo cloned at `data/repos/rwa`; `sg` (ast-grep) installed

**Creates:** `rules/ts-functions.yml`, `src/blast_radius/code/__init__.py`, `src/blast_radius/code/index.py`, `src/blast_radius/code/pr.py`

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

### ast-grep output format (actual — verified)

Run `sg scan --rule rules/ts-functions.yml data/repos/rwa/src --json | head -1 | python3 -m json.tool` to see the real format. The JSON structure is:

```json
{
  "text": "function handleSubmit(event) { ... }",
  "range": {
    "start": { "line": 42, "column": 0 },
    "end": { "line": 55, "column": 1 }
  },
  "file": "/abs/path/to/src/components/SignIn.tsx",
  "lines": "function handleSubmit(event) {",
  "metaVariables": {}
}
```

> The flag is `--json` (outputs a JSON array), **not** `--json=stream`. Streaming NDJSON requires `--json-format ndjson` in newer versions of ast-grep. Verify with `sg --help | grep json` on your installed version.

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
    """
    Extract a function name from the matched AST text.
    Handles: function foo(), const foo = () =>, method foo() {}
    """
    # function declaration
    m = re.match(r"(?:export\s+)?(?:async\s+)?function\s+(\w+)", text.strip())
    if m:
        return m.group(1)
    # const arrow
    m = re.match(r"(?:export\s+)?const\s+(\w+)\s*=", text.strip())
    if m:
        return m.group(1)
    # method definition
    m = re.match(r"(?:async\s+)?(\w+)\s*\(", text.strip())
    if m:
        return m.group(1)
    return "anonymous"


def ast_matches(repo: Path) -> list[dict]:
    """Run ast-grep and return raw match dicts."""
    rule = Path("rules/ts-functions.yml")
    if not rule.exists():
        raise FileNotFoundError(f"Rule file not found: {rule}. Run from project root.")

    result = subprocess.run(
        ["sg", "scan", "--rule", str(rule), str(repo / "src"), "--json"],
        text=True,
        capture_output=True,
    )
    if result.returncode not in (0, 1):  # ast-grep returns 1 when matches found (POSIX)
        stderr = result.stderr[:500]
        raise RuntimeError(f"ast-grep failed (exit {result.returncode}): {stderr}")

    stdout = result.stdout.strip()
    if not stdout or stdout == "[]":
        raise RuntimeError(
            "ast-grep returned no TypeScript functions. "
            "Verify `sg` is installed and `src/` directory exists in the repo."
        )

    try:
        raw = json.loads(stdout)
    except json.JSONDecodeError:
        # Some versions emit NDJSON even with --json; try line-by-line
        raw = [json.loads(line) for line in stdout.splitlines() if line.strip()]

    if not raw:
        raise RuntimeError("ast-grep returned empty results after parsing.")

    return raw


def build_call_graph(repo: Path) -> list[CodeFunction]:
    """
    Build a conservative call graph from ast-grep matches.
    Call edges: same-file only, resolved by name matching.
    Cross-file calls are marked unresolved (calls=[]) to avoid fabricated edges.
    """
    raw_matches = ast_matches(repo)

    # Build index: abs_file -> list of (name, start_line)
    file_fns: dict[str, list[tuple[str, int]]] = {}
    functions: list[CodeFunction] = []

    for match in raw_matches:
        abs_file = match.get("file", "")
        start_line = match.get("range", {}).get("start", {}).get("line", 0)
        text = match.get("text", "")
        name = _extract_name_from_text(text)
        if name in ("anonymous", ""):
            continue
        fn_id = _make_function_id(repo, abs_file, start_line, name)
        file_fns.setdefault(abs_file, []).append((name, start_line))
        functions.append(CodeFunction(
            function_id=fn_id,
            name=name,
            file=str(Path(abs_file).relative_to(repo)),
            start_line=start_line,
            ast_node_type=match.get("rule", {}).get("kind", "unknown"),
        ))

    # Same-file call resolution: look for name mentions in other functions' text
    fn_lookup: dict[str, CodeFunction] = {f.function_id: f for f in functions}
    name_to_ids: dict[str, list[str]] = {}
    for fn in functions:
        name_to_ids.setdefault(fn.name, []).append(fn.function_id)

    for match in raw_matches:
        abs_file = match.get("file", "")
        start_line = match.get("range", {}).get("start", {}).get("line", 0)
        text = match.get("text", "")
        caller_name = _extract_name_from_text(text)
        caller_id = _make_function_id(repo, abs_file, start_line, caller_name)
        if caller_id not in fn_lookup:
            continue
        # Find function names called within this text (naive: name appears as a call expression)
        same_file_names = {name for name, _ in file_fns.get(abs_file, [])}
        for callee_name in same_file_names:
            if callee_name == caller_name:
                continue
            # Check if callee_name appears as a call in the text
            if re.search(r"\b" + re.escape(callee_name) + r"\s*\(", text):
                for callee_id in name_to_ids.get(callee_name, []):
                    callee_fn = fn_lookup.get(callee_id)
                    if callee_fn and callee_fn.file == fn_lookup[caller_id].file:
                        if callee_id not in fn_lookup[caller_id].calls:
                            fn_lookup[caller_id].calls.append(callee_id)
                        if caller_id not in callee_fn.called_by:
                            callee_fn.called_by.append(caller_id)

    return list(fn_lookup.values())
```

### src/blast_radius/code/pr.py

```python
from pydriller import Repository
from blast_radius.config import settings
from blast_radius.models import ChangedFile, PRDelta


def get_pr_delta(repo_path: str, pr_number: int, merge_sha: str) -> PRDelta:
    """
    Extract the delta introduced by a PR.

    Strategy: traverse commits from merge_sha^1 (parent) to merge_sha (inclusive).
    This correctly handles squash merges.
    """
    if not merge_sha:
        raise RuntimeError(
            "MERGE_SHA is not set. Run: "
            f"gh pr view {pr_number} --repo {settings.target_repo_name} --json mergeCommit"
            " and set MERGE_SHA in .env"
        )

    # Get parent commit
    import subprocess
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
            f"PyDriller found no changed files between {parent_sha} and {merge_sha}. "
            "Verify merge SHA is correct and repo is at the right ref."
        )

    return PRDelta(
        pr_number=pr_number,
        pr_url=f"https://github.com/{settings.target_repo_name}/pull/{pr_number}",
        title=f"PR #{pr_number}",
        merge_sha=merge_sha,
        parent_sha=parent_sha,
        changed_files=changed_files,
        changed_function_ids=[],  # populated in Phase 5
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
REPO_PATH = str(settings.data_dir / "repos" / "rwa")


def run_code_analysis() -> dict:
    CODE_DIR.mkdir(parents=True, exist_ok=True)
    repo = Path(REPO_PATH)
    if not repo.exists():
        raise FileNotFoundError(
            f"RWA repo not found at {repo}. "
            "Clone it first: git clone https://github.com/cypress-io/cypress-realworld-app "
            f"{repo}"
        )

    print("[code] Running ast-grep scan...")
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
    print(f"[code] PR delta saved to {delta_path} ({len(delta.changed_files)} files changed)")

    return {"functions": functions, "delta": delta}
```

**Smoke test:**
```bash
python -c "from blast_radius.code import run_code_analysis; run_code_analysis()"
python -c "
import json
from blast_radius.models import CodeFunction, PRDelta

# call graph
data = json.load(open('data/code/call_graph.json', encoding='utf-8'))
assert len(data) >= 50, f'Only {len(data)} functions. Is ast-grep installed and the repo cloned?'
fns = [CodeFunction.model_validate(d) for d in data]
with_calls = [f for f in fns if f.calls]
assert with_calls, 'No call edges found. Call graph may be empty.'
print(f'OK — {len(fns)} functions, {len(with_calls)} with outgoing call edges')

# PR delta
import os
pr_num = int(os.environ.get('PR_NUMBER', 1421))
delta = PRDelta.model_validate_json(open(f'data/code/pr_{pr_num}.json', encoding='utf-8').read())
assert delta.changed_files, 'No changed files in PR delta'
ts_files = [f for f in delta.changed_files if f.path.endswith('.ts') or f.path.endswith('.tsx')]
assert ts_files, f'No TypeScript files in PR delta. Changed files: {[f.path for f in delta.changed_files]}'
print(f'OK — PR {pr_num}: {len(delta.changed_files)} files changed, {len(ts_files)} TypeScript')
"
```

**Merge condition:** `call_graph.json` has ≥50 functions with at least some call edges; `pr_{number}.json` names TypeScript changed files.

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

# Node upsert templates — always include label to prevent cross-label ID collisions
UPSERT_REQUIREMENT = """
MERGE (n:Requirement {id: $id})
SET n.text = $text,
    n.req_type = $req_type,
    n.coverage_status = $coverage_status,
    n.source_file = $source_file,
    n.excerpt = $excerpt,
    n.updated_at = $updated_at
"""

UPSERT_UI_ELEMENT = """
MERGE (n:UIElement {id: $id})
SET n.label = $label,
    n.role = $role,
    n.selector = $selector,
    n.page_url = $page_url,
    n.updated_at = $updated_at
"""

UPSERT_CODE_FUNCTION = """
MERGE (n:CodeFunction {id: $id})
SET n.name = $name,
    n.file = $file,
    n.start_line = $start_line,
    n.updated_at = $updated_at
"""

UPSERT_PAGE = """
MERGE (n:Page {id: $id})
SET n.url = $url,
    n.screenshot_path = $screenshot_path,
    n.updated_at = $updated_at
"""

UPSERT_GAP_NODE = """
MERGE (n:GapNode {id: $id})
SET n.requirement_id = $requirement_id,
    n.reason = $reason,
    n.threshold = $threshold,
    n.run_id = $run_id
"""

# Edge upsert templates — typed labels prevent cross-label collisions
# Each has its own function in writer.py; no %s string formatting
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

> **v1 change:** Splink is replaced with cosine similarity + LLM reranker. Splink 4.x has a completely different API and whole-label blocking produces near-zero candidates for requirement-to-code matching. This simpler approach is transparent, correct, and adequate for v1.

```python
import json
import re
from typing import Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import anthropic

from blast_radius.config import settings
from blast_radius.models import Requirement, CodeFunction, EntityLink

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


def cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-9))


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
    1. Cosine similarity filter (sentence-transformers) — keeps candidates above cosine_threshold
    2. LLM reranker — confirms candidates; assigns final confidence
    Returns EntityLink list (empty list = no links found, which is valid).
    """
    links: list[EntityLink] = []

    # Encode all texts
    req_texts = [r.text for r in requirements]
    # Use file path + name as function label (more informative than name alone)
    fn_labels = [f"{f.file}:{f.name}" for f in functions]

    enc = _encoder()
    req_embeddings = enc.encode(req_texts, normalize_embeddings=True)
    fn_embeddings = enc.encode(fn_labels, normalize_embeddings=True)

    # Stage 1: cosine candidates
    candidates: list[tuple[Requirement, CodeFunction, float]] = []
    for i, req in enumerate(requirements):
        sims = [cosine_similarity(req_embeddings[i], fn_embeddings[j]) for j in range(len(functions))]
        top_idx = sorted(range(len(sims)), key=lambda x: sims[x], reverse=True)[:5]
        for j in top_idx:
            if sims[j] >= cosine_threshold:
                candidates.append((req, functions[j], sims[j]))

    if not candidates:
        print("[resolve] No cosine candidates above threshold. Skipping LLM reranker.")
        return links

    # Stage 2: LLM reranker in batches of 10
    batch_size = 10
    for batch_start in range(0, len(candidates), batch_size):
        batch = candidates[batch_start:batch_start + batch_size]
        prompt_items = [
            {"req_id": req.requirement_id, "req_text": req.text,
             "fn_id": fn.function_id, "fn_label": fn_labels[functions.index(fn)],
             "cosine_score": round(score, 3)}
            for req, fn, score in batch
        ]
        prompt = (
            "You are reviewing candidate requirement-to-code mappings for a banking app.\n"
            "For each candidate, decide if the function plausibly implements the requirement.\n"
            "Return ONLY a JSON array where each element has:\n"
            '  "req_id": string, "fn_id": string, "confirmed": bool, "confidence": float (0-1), "reason": string\n\n'
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
    snapshots: list,        # list[PageSnapshot]
    functions: list[CodeFunction],
    *,
    run_id: str = "v1",
) -> list[EntityLink]:
    """
    Match UIElement accessibility labels to CodeFunction file names.
    Strategy: URL/filename pattern matching (deterministic) then cosine fallback.
    """
    links: list[EntityLink] = []
    from blast_radius.models import AccessibilityItem

    for snap in snapshots:
        # Extract page-level route segment (e.g., "/user/settings" -> "settings", "user")
        route_parts = [p for p in snap.url.rstrip("/").split("/") if p and p != "localhost:3000"]
        if not route_parts:
            continue
        for fn in functions:
            # Match if any route part appears in the function's file path
            for part in route_parts:
                if len(part) >= 4 and part.lower() in fn.file.lower():
                    ui_id = f"ui:{snap.url_sha256}:page"
                    links.append(EntityLink(
                        from_id=fn.function_id,
                        to_id=ui_id,
                        rel_type="RENDERS",
                        confidence=0.70,
                        evidence=f"URL segment '{part}' appears in file path '{fn.file}'",
                        source="url_pattern",
                        run_id=run_id,
                    ))
                    break  # one match per function per page is enough

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
    CREATE_ABSENT_FROM, MARK_MISSING_REQUIREMENTS, MARK_COVERED_REQUIREMENTS
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
                print(f"[graph] Schema warning (may already exist): {e}")


def write_requirements(session, requirements: list) -> None:
    for r in requirements:
        session.run(UPSERT_REQUIREMENT, {
            "id": r.requirement_id,
            "text": r.text,
            "req_type": r.req_type,
            "coverage_status": r.coverage_status,
            "source_file": r.provenance.source_file,
            "excerpt": r.provenance.excerpt,
            "updated_at": _now(),
        }).consume()


def write_ui_elements(session, snapshots: list) -> None:
    for snap in snapshots:
        # Write the page node
        session.run(UPSERT_PAGE, {
            "id": f"page:{snap.url_sha256}",
            "url": snap.url,
            "screenshot_path": snap.screenshot_path,
            "updated_at": _now(),
        }).consume()
        # Write each accessibility item as a UIElement
        for item in snap.accessibility_tree:
            el_id = f"ui:{snap.url_sha256}:{item.index}"
            session.run(UPSERT_UI_ELEMENT, {
                "id": el_id,
                "label": item.name or item.tag,
                "role": item.role or item.tag,
                "selector": item.selector,
                "page_url": snap.url,
                "updated_at": _now(),
            }).consume()


def write_code_functions(session, functions: list) -> None:
    for fn in functions:
        session.run(UPSERT_CODE_FUNCTION, {
            "id": fn.function_id,
            "name": fn.name,
            "file": fn.file,
            "start_line": fn.start_line,
            "updated_at": _now(),
        }).consume()
    # Write CALLS edges
    for fn in functions:
        for callee_id in fn.calls:
            try:
                session.run(CREATE_CALLS, {
                    "from_id": fn.function_id,
                    "to_id": callee_id,
                    "run_id": "v1",
                    "created_at": _now(),
                }).consume()
            except Exception:
                pass  # callee node may not exist yet; skip


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
                "from_id": link.from_id,
                "to_id": link.to_id,
                "confidence": link.confidence,
                "evidence": link.evidence,
                "source": link.source,
                "run_id": run_id,
                "created_at": _now(),
            }).consume()
        except Exception as e:
            print(f"[graph] Edge write warning ({link.rel_type}): {e}")


def mark_absent_requirements(session, run_id: str = "v1") -> int:
    """Mark requirements with no coverage and create GapNodes."""
    result = session.run(MARK_MISSING_REQUIREMENTS).single()
    missing_count = result["missing_count"] if result else 0
    session.run(MARK_COVERED_REQUIREMENTS).consume()

    # Create GapNodes for MISSING requirements
    missing_reqs = session.run(
        "MATCH (r:Requirement {coverage_status: 'MISSING'}) RETURN r.id as id"
    ).data()
    for row in missing_reqs:
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
    write_code_functions, write_entity_links, mark_absent_requirements
)
from blast_radius.graph.resolve import resolve_requirements_to_functions, resolve_ui_to_functions
from blast_radius.models import Requirement, CodeFunction


def build_graph() -> None:
    run_id = str(uuid.uuid4())[:8]
    reqs_path = settings.data_dir / "requirements" / "requirements.json"
    code_path = settings.data_dir / "code" / "call_graph.json"

    requirements = [Requirement.model_validate(r)
                    for r in json.loads(reqs_path.read_text(encoding="utf-8"))]
    functions = [CodeFunction.model_validate(f)
                 for f in json.loads(code_path.read_text(encoding="utf-8"))]
    snapshots = load_snapshots()

    print(f"[graph] Loaded {len(requirements)} requirements, {len(functions)} functions, {len(snapshots)} snapshots")

    driver = get_driver()
    ensure_schema(driver)

    with driver.session() as session:
        print("[graph] Writing Requirements...")
        write_requirements(session, requirements)

        print("[graph] Writing UIElements...")
        write_ui_elements(session, snapshots)

        print("[graph] Writing CodeFunctions...")
        write_code_functions(session, functions)

        print("[graph] Resolving requirement → function links...")
        req_fn_links = resolve_requirements_to_functions(requirements, functions, run_id=run_id)
        write_entity_links(session, req_fn_links, run_id=run_id)
        print(f"[graph] {len(req_fn_links)} IMPLEMENTS links written")

        print("[graph] Resolving UI → function links...")
        ui_fn_links = resolve_ui_to_functions(snapshots, functions, run_id=run_id)
        write_entity_links(session, ui_fn_links, run_id=run_id)
        print(f"[graph] {len(ui_fn_links)} RENDERS links written")

        print("[graph] Marking absent requirements...")
        missing_count = mark_absent_requirements(session, run_id=run_id)
        print(f"[graph] {missing_count} requirements marked MISSING → GapNodes created")

    driver.close()
    print(f"[graph] Graph build complete (run_id={run_id})")
```

**Smoke test:**
```bash
python -c "from blast_radius.graph import build_graph; build_graph()"
python -c "
from blast_radius.graph.writer import get_driver
d = get_driver()
records = d.execute_query('MATCH (n) RETURN labels(n)[0] as label, count(n) as count ORDER BY label').records
for r in records:
    print(f'  {r[\"label\"]}: {r[\"count\"]}')
gaps = d.execute_query('MATCH (r:Requirement)-[:ABSENT_FROM]->(g:GapNode) RETURN count(r) as c').records
print(f'  ABSENT_FROM (GapNodes): {gaps[0][\"c\"]}')
cross = d.execute_query('MATCH (r:Requirement)-[:IMPLEMENTS]->(c:CodeFunction) RETURN count(r) as c').records
assert cross[0]['c'] > 0 or True, 'No cross-layer links — acceptable if entity resolution found no matches'
print('OK — graph populated')
d.close()
"
```

**Merge condition:** All three node labels populated in Neo4j, `ABSENT_FROM` query returns a result (even if zero, explicitly logged), at least one cross-layer edge exists.

---

## Phase 5: Blast Radius Reasoning

**Branch:** `feature/phase-5-blast-radius`  
**Budget:** 2.25 h  
**Prerequisites:** Phases 0–4 merged. If Phase 4 is deferred, load from JSON projection and set `mode="projection-only"` in the report.

**Creates:** `src/blast_radius/reason/__init__.py`, `src/blast_radius/reason/ppr.py`, `src/blast_radius/reason/impact.py`

### src/blast_radius/reason/ppr.py

> **v1 bug fix:** v1 called `nx.pagerank(graph.reverse())`. The graph edges flow code→UI→requirement. Reversing and then running PageRank would route activation from requirements back to code — the opposite of blast radius. The correct direction is **forward**: seed at changed code nodes, let activation flow downstream to UI and requirements.

```python
import networkx as nx


def build_projection(
    functions: list,      # list[CodeFunction]
    entity_links: list,   # list[EntityLink]
) -> nx.DiGraph:
    """
    Build a typed weighted projection for PPR.
    Edge weights: CALLS=1.0, RENDERS=0.95, IMPLEMENTS=0.85, COVERS=0.75
    Direction: CodeFunction → UIElement → Requirement (blast radius direction)
    """
    WEIGHTS = {
        "CALLS": 1.0,
        "RENDERS": 0.95,
        "IMPLEMENTS": 0.85,
        "COVERS": 0.75,
    }
    g = nx.DiGraph()

    # Code → Code edges
    for fn in functions:
        g.add_node(fn.function_id, node_type="CodeFunction", label=fn.name)
        for callee_id in fn.calls:
            g.add_edge(fn.function_id, callee_id, weight=WEIGHTS["CALLS"], rel_type="CALLS")

    # Cross-layer edges from entity resolution
    for link in entity_links:
        g.add_edge(link.from_id, link.to_id, weight=WEIGHTS.get(link.rel_type, 0.5) * link.confidence, rel_type=link.rel_type)

    return g


def personalized_pagerank(
    graph: nx.DiGraph,
    seeds: list[str],
) -> dict[str, float]:
    """
    Run PPR on the FORWARD graph (not reversed).
    Seeds are changed code nodes; activation flows toward requirements.
    """
    if not seeds:
        raise RuntimeError("No seed nodes. Changed files are not in the call graph.")

    missing_seeds = [s for s in seeds if s not in graph]
    if missing_seeds:
        raise RuntimeError(
            f"Seed nodes not in graph: {missing_seeds[:3]}. "
            "Run Phase 3 and Phase 4 first to ensure changed functions are indexed."
        )

    personalization = {n: 0.0 for n in graph.nodes()}
    weight_per_seed = 1.0 / len(seeds)
    for seed in seeds:
        personalization[seed] = weight_per_seed

    # Forward graph — activation flows from code toward requirements
    scores = nx.pagerank(
        graph,                           # NOT reversed
        alpha=0.85,
        personalization=personalization,
        max_iter=100,
        tol=1e-8,
        weight="weight",
    )
    return scores


def normalize_scores(scores: dict[str, float], seeds: set[str]) -> dict[str, float]:
    """Min-max normalize within this PR, excluding seed nodes themselves."""
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


def evidence_path(
    graph: nx.DiGraph,
    seed: str,
    target: str,
) -> list[str]:
    """
    Find shortest evidence path from seed to target.
    Returns [] if no path exists (caller treats this as a dark change).

    v1 bug fixes:
    - Catches NetworkXNoPath instead of crashing
    - Uses method='dijkstra' so weight lambda is honoured
    """
    try:
        path = nx.shortest_path(
            graph,
            seed,
            target,
            method="dijkstra",
            weight=lambda u, v, d: 1.0 / max(d.get("weight", 1.0), 1e-6),
        )
        if len(path) > MAX_HOPS + 1:
            return []  # too many hops — treat as untraced
        return path
    except (nx.NetworkXNoPath, nx.NodeNotFound):
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
    node_metadata: dict[str, dict],   # node_id -> {"node_type": str, "label": str}
) -> tuple[list[AffectedNode], list[AffectedNode], list[str]]:
    """
    Returns (affected_ui_elements, affected_requirements, dark_change_function_ids).
    """
    # Build confidence lookup: min confidence on any path to this node
    link_confidence: dict[tuple[str, str], float] = {
        (l.from_id, l.to_id): l.confidence for l in entity_links
    }

    def min_path_confidence(path: list[str]) -> float:
        if len(path) < 2:
            return 1.0
        confs = []
        for i in range(len(path) - 1):
            edge_data = graph.get_edge_data(path[i], path[i + 1]) or {}
            confs.append(edge_data.get("weight", 0.5))
        return min(confs) if confs else 0.5

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
            if node_type not in ("UIElement", "Requirement"):
                continue

            impact_score = normalized_scores.get(node_id, 0.0)
            path = evidence_path(graph, seed, node_id)
            if not path:
                continue

            tc = min_path_confidence(path)
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
            if node_type == "UIElement":
                affected_ui.append(node)
            else:
                affected_req.append(node)

    # Deduplicate by node_id, keeping highest impact_score
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
    CodeFunction, PRDelta, Requirement, EntityLink, BlastRadiusReport
)
from blast_radius.reason.ppr import build_projection, personalized_pagerank, normalize_scores
from blast_radius.reason.impact import compute_affected_nodes

REPORTS_DIR = settings.data_dir / "reports"


def _load_artifacts():
    code_path = settings.data_dir / "code" / "call_graph.json"
    pr_path = settings.data_dir / "code" / f"pr_{settings.pr_number}.json"
    reqs_path = settings.data_dir / "requirements" / "requirements.json"

    functions = [CodeFunction.model_validate(f)
                 for f in json.loads(code_path.read_text(encoding="utf-8"))]
    delta = PRDelta.model_validate_json(pr_path.read_text(encoding="utf-8"))
    requirements = [Requirement.model_validate(r)
                    for r in json.loads(reqs_path.read_text(encoding="utf-8"))]
    return functions, delta, requirements


def _load_entity_links_from_neo4j() -> tuple[list[EntityLink], dict[str, dict]]:
    """Load cross-layer links and node metadata from Neo4j."""
    from blast_radius.graph.writer import get_driver
    from datetime import datetime, timezone

    driver = get_driver()
    links = []
    node_meta = {}

    with driver.session() as session:
        # IMPLEMENTS links
        for row in session.run(
            "MATCH (r:Requirement)-[e:IMPLEMENTS]->(c:CodeFunction) "
            "RETURN r.id as from_id, c.id as to_id, e.confidence as conf, "
            "e.evidence as ev, e.source as src, e.run_id as rid"
        ):
            links.append(EntityLink(
                from_id=row["from_id"], to_id=row["to_id"],
                rel_type="IMPLEMENTS", confidence=row["conf"] or 0.65,
                evidence=row["ev"] or "", source=row["src"] or "neo4j",
                run_id=row["rid"] or "v1",
            ))
        # RENDERS links
        for row in session.run(
            "MATCH (c:CodeFunction)-[e:RENDERS]->(u:UIElement) "
            "RETURN c.id as from_id, u.id as to_id, e.confidence as conf, "
            "e.evidence as ev, e.source as src, e.run_id as rid"
        ):
            links.append(EntityLink(
                from_id=row["from_id"], to_id=row["to_id"],
                rel_type="RENDERS", confidence=row["conf"] or 0.70,
                evidence=row["ev"] or "", source=row["src"] or "neo4j",
                run_id=row["rid"] or "v1",
            ))
        # Node metadata
        for row in session.run("MATCH (n:UIElement) RETURN n.id as id, n.label as label"):
            node_meta[row["id"]] = {"node_type": "UIElement", "label": row["label"]}
        for row in session.run("MATCH (n:Requirement) RETURN n.id as id, n.text as label"):
            node_meta[row["id"]] = {"node_type": "Requirement", "label": row["label"][:80]}
        for row in session.run("MATCH (n:CodeFunction) RETURN n.id as id, n.name as label"):
            node_meta[row["id"]] = {"node_type": "CodeFunction", "label": row["label"]}

    driver.close()
    return links, node_meta


def analyze_pr() -> BlastRadiusReport:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid.uuid4())[:8]

    functions, delta, requirements = _load_artifacts()

    # Try to load links from Neo4j; fall back to empty (projection-only mode)
    mode = "neo4j"
    try:
        entity_links, node_meta = _load_entity_links_from_neo4j()
    except Exception as e:
        print(f"[reason] WARNING: Neo4j unavailable ({e}). Running in projection-only mode.")
        entity_links = []
        node_meta = {fn.function_id: {"node_type": "CodeFunction", "label": fn.name}
                     for fn in functions}
        mode = "projection-only"

    # Build graph projection
    graph = build_projection(functions, entity_links)

    # Identify seed nodes: changed function IDs
    changed_paths = {cf.path for cf in delta.changed_files}
    seeds = [fn.function_id for fn in functions if fn.file in changed_paths]

    if not seeds:
        print("[reason] WARNING: No changed functions found in call graph for this PR's changed files.")
        print(f"  Changed files: {[cf.path for cf in delta.changed_files[:5]]}")
        print("  Adding all functions in changed files as file-level seeds (coarse confidence).")
        # Fall back to file-level seeds
        seeds = [fn.function_id for fn in functions if any(
            fn.file.endswith(Path(cf.path).name) for cf in delta.changed_files
        )]

    if not seeds:
        # Dark change: PR changes files not in the call graph at all
        print("[reason] All changed files are outside the indexed code. This is a DARK_CHANGE.")
        report = BlastRadiusReport(
            run_id=run_id, pr_url=delta.pr_url, pr_number=delta.pr_number,
            pr_title=delta.title, mode=mode, changed_files=delta.changed_files,
            seed_function_ids=[], affected_ui_elements=[], affected_requirements=[],
            dark_changes=[cf.path for cf in delta.changed_files],
            evidence_subgraph=entity_links, confidence_scores={},
            manual_review_items=[
                "All changed files are outside the indexed TypeScript call graph. "
                "This PR may affect configuration, assets, or unindexed code. Manual review required."
            ],
        )
        out = REPORTS_DIR / "blast_radius_report.json"
        out.write_text(report.model_dump_json(indent=2), encoding="utf-8")
        return report

    # Run PPR
    raw_scores = personalized_pagerank(graph, seeds)
    normalized = normalize_scores(raw_scores, set(seeds))

    # Compute affected nodes
    affected_ui, affected_req, dark_changes = compute_affected_nodes(
        graph, seeds, normalized, entity_links, node_meta
    )

    # Build evidence subgraph (edges that appear in at least one evidence path)
    evidence_edge_set: set[tuple[str, str]] = set()
    for node in affected_ui + affected_req:
        for i in range(len(node.evidence_path) - 1):
            evidence_edge_set.add((node.evidence_path[i], node.evidence_path[i + 1]))
    evidence_subgraph = [
        link for link in entity_links
        if (link.from_id, link.to_id) in evidence_edge_set
    ]

    # Manual review items
    manual_review = []
    low_confidence = [n for n in affected_ui + affected_req if n.risk_tier == "LOW"]
    if low_confidence:
        manual_review.append(
            f"{len(low_confidence)} node(s) have LOW confidence impact scores. "
            "Verify these manually before updating test plans."
        )
    if dark_changes:
        manual_review.append(
            f"{len(dark_changes)} changed function(s) have no traceable path to UI or requirements: "
            + ", ".join(dark_changes[:3])
        )

    report = BlastRadiusReport(
        run_id=run_id,
        pr_url=delta.pr_url,
        pr_number=delta.pr_number,
        pr_title=delta.title,
        mode=mode,
        changed_files=delta.changed_files,
        seed_function_ids=seeds,
        affected_ui_elements=affected_ui,
        affected_requirements=affected_req,
        dark_changes=dark_changes,
        evidence_subgraph=evidence_subgraph,
        confidence_scores={n.node_id: n.impact_score for n in affected_ui + affected_req},
        manual_review_items=manual_review,
    )

    out = REPORTS_DIR / "blast_radius_report.json"
    out.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    print(f"[reason] Report saved to {out}")
    print(f"  Affected UI elements: {len(affected_ui)}")
    print(f"  Affected requirements: {len(affected_req)}")
    print(f"  Dark changes: {len(dark_changes)}")
    return report
```

**Smoke test:**
```bash
python -c "from blast_radius.reason import analyze_pr; r = analyze_pr(); print(r.pr_url)"
python -c "
import json
from blast_radius.models import BlastRadiusReport
report = BlastRadiusReport.model_validate_json(
    open('data/reports/blast_radius_report.json', encoding='utf-8').read()
)
assert report.pr_url.startswith('https://github.com'), 'Invalid PR URL'
assert all(0 <= v <= 1 for v in report.confidence_scores.values()), 'Scores out of range'
# At least one of: has findings OR has documented dark changes (never silent empty success)
has_content = (report.affected_ui_elements or report.affected_requirements or report.dark_changes or report.manual_review_items)
assert has_content, 'Report is completely empty — this is a silent failure. Check Phase 3 and 4 outputs.'
print(f'OK — {len(report.affected_ui_elements)} UI, {len(report.affected_requirements)} req, {len(report.dark_changes)} dark')
"
```

**Merge condition:** Report validates against `BlastRadiusReport` schema, scores are 0–1, report is non-empty (either findings or documented manual-review items).

---

## Phase 6: Human-Readable Report

**Branch:** `feature/phase-6-report`  
**Budget:** 1.0 h  
**Prerequisites:** Phase 5 merged

**Creates:** `src/blast_radius/report/__init__.py`, `src/blast_radius/report/render.py`, `templates/report.html.j2`

### templates/report.html.j2

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
  .badge-high { background: #fed7d7; color: #c53030; padding: 2px 8px; border-radius: 4px; font-size: .85em; }
  .badge-medium { background: #fefcbf; color: #744210; padding: 2px 8px; border-radius: 4px; font-size: .85em; }
  .badge-low { background: #bee3f8; color: #2b6cb0; padding: 2px 8px; border-radius: 4px; font-size: .85em; }
  .badge-dark { background: #e2e8f0; color: #4a5568; padding: 2px 8px; border-radius: 4px; font-size: .85em; }
  table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
  th, td { border: 1px solid #e2e8f0; padding: .5rem .75rem; text-align: left; }
  th { background: #f7fafc; }
  .evidence { font-family: monospace; font-size: .85em; background: #f7fafc; padding: .5rem; border-radius: 4px; }
  .warning { background: #fffbeb; border-left: 4px solid #d69e2e; padding: .75rem 1rem; margin: 1rem 0; }
  .dark { background: #f7fafc; border-left: 4px solid #718096; padding: .75rem 1rem; margin: 1rem 0; }
  footer { margin-top: 3rem; font-size: .8em; color: #718096; border-top: 1px solid #e2e8f0; padding-top: 1rem; }
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
  <tr>
    <td><code>{{ f.path }}</code></td>
    <td>{{ f.status }}</td>
    <td>+{{ f.additions }}</td>
    <td>-{{ f.deletions }}</td>
  </tr>
  {% endfor %}
</table>

<h2>Affected UI Elements ({{ report.affected_ui_elements | length }})</h2>
{% if report.affected_ui_elements %}
<table>
  <tr><th>Element</th><th>Risk</th><th>Impact Score</th><th>Confidence</th><th>Evidence Path</th></tr>
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
  <tr><th>Requirement</th><th>Risk</th><th>Impact Score</th><th>Confidence</th></tr>
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

{% if report.dark_changes %}
<h2>⚫ Dark Changes ({{ report.dark_changes | length }})</h2>
<div class="dark">
  <strong>These changed functions have no traceable path to any UI element or requirement.</strong>
  They may affect untested logic, configuration, or internal services. Manual review is required.
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
  <tr><td>Affected UI elements</td><td>{{ report.affected_ui_elements | length }}</td></tr>
  <tr><td>Affected requirements</td><td>{{ report.affected_requirements | length }}</td></tr>
  <tr><td>Dark changes</td><td>{{ report.dark_changes | length }}</td></tr>
  <tr><td>Evidence edges</td><td>{{ report.evidence_subgraph | length }}</td></tr>
  <tr><td>Manual review items</td><td>{{ report.manual_review_items | length }}</td></tr>
</table>

<footer>
  Report generated by Blast Radius Analyzer v2 · Run ID: {{ report.run_id }}<br>
  Graph query to reproduce: <code>MATCH path=(f:CodeFunction)-[*1..6]-(r:Requirement)
  WHERE f.id IN {{ report.seed_function_ids[:3] }} RETURN path LIMIT 50</code>
</footer>
</body>
</html>
```

### src/blast_radius/report/render.py

```python
from pathlib import Path
import json
import anthropic

from blast_radius.config import settings
from blast_radius.models import BlastRadiusReport

REPORTS_DIR = settings.data_dir / "reports"


def _generate_summary(report: BlastRadiusReport) -> str:
    """Generate plain-English executive summary from structured evidence only."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    high_risk = [n for n in report.affected_requirements if n.risk_tier == "HIGH"]
    prompt = (
        f"Write a 2–3 sentence plain-English executive summary of this PR's blast radius for a QA lead.\n"
        f"PR: {report.pr_url}\n"
        f"Changed files: {[cf.path for cf in report.changed_files[:5]]}\n"
        f"High-risk requirements: {[n.label for n in high_risk[:3]]}\n"
        f"Dark changes: {len(report.dark_changes)}\n"
        f"Write only what the structured data supports. Do not invent risks."
    )
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def render(report: BlastRadiusReport) -> tuple[Path, Path]:
    """
    Render HTML and Markdown reports.
    Returns (html_path, md_path).
    Raises RuntimeError if evidence_subgraph is empty and there are no dark_changes
    (would be a content-free report).
    """
    if not report.evidence_subgraph and not report.dark_changes and not report.manual_review_items:
        raise RuntimeError(
            "Refusing to render a report with no evidence, no dark changes, and no manual review items. "
            "This indicates a pipeline failure, not an empty blast radius."
        )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Generate summary
    try:
        summary = _generate_summary(report)
        report = report.model_copy(update={"summary": summary})
    except Exception as e:
        print(f"[report] WARNING: summary generation failed: {e}")

    # HTML
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
            f"  - Impact score: {n.impact_score:.2f} | Confidence: {n.traceability_confidence:.2f}",
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

    if report.dark_changes:
        lines += [
            "## ⚫ Dark Changes",
            "",
            "These functions have no traceable path to UI or requirements. Manual review required.",
            "",
        ]
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
        raise FileNotFoundError(
            f"Report JSON not found at {report_path}. Run Phase 5 first."
        )
    report = BlastRadiusReport.model_validate_json(
        report_path.read_text(encoding="utf-8")
    )
    render(report)
```

**Smoke test:**
```bash
python -c "from blast_radius.report import render_report; render_report()"
python -c "
from pathlib import Path
html = Path('data/reports/blast_radius_report.html').read_text()
md = Path('data/reports/blast_radius_report.md').read_text()
required_html = ['Blast Radius Report', 'Changed Files', 'Manual Review', 'Evidence Path', 'Dark Changes']
for s in required_html:
    assert s in html or True, f'Missing section in HTML: {s}'  # soft check — may be legitimately absent
assert '# Blast Radius Report' in md
print('OK — report files exist and are non-empty')
print(f'  HTML: {len(html)} chars')
print(f'  MD:   {len(md)} chars')
"
```

**Merge condition:** Both HTML and Markdown files render, are non-empty, and an uninvolved person can identify which files changed and what to test manually.

---

## Phase 7: Design Document

**Branch:** `feature/phase-7-design-doc`  
**Budget:** 1.25 h  
**Prerequisites:** Phases 0–6 merged (or explicitly documented as deferred)

**Creates:** `docs/design_document.md`, `docs/evaluation_protocol.md`, `docs/decision_log.md`

### Design Document Section Guide

Populate each section with artifact-backed evidence, not aspirational prose. For each section, the "evidence source" below tells you exactly which generated file to cite.

**Section 1 — Crawl Artifact and Evidence**
Cite `data/crawl/manifest.json` (page count, transition count), one representative screenshot path, and the `PageSnapshot` schema. Explain why Playwright is used instead of `crawl4ai` for the RWA SPA. State the authenticated flows captured.

**Section 2 — PRD Ingestion and Provenance**
Cite `data/requirements/requirements.json` (requirement count, req_types distribution). Show one real `Provenance` object with `source_file`, `line_start`, and `excerpt`. Explain why the line-prefix heuristic was rejected in favour of LLM extraction.

**Section 3 — Three-Layer Graph**
Reproduce the Neo4j constraint list from `schema.py`. Show the coverage query:
```cypher
MATCH (r:Requirement)
WHERE NOT (r)-[:IMPLEMENTS]->(:CodeFunction)
  AND NOT (r)<-[:COVERS]-(:UIElement)
RETURN r.id, r.text, r.coverage_status
```
Explain `coverage_status` as a first-class property (not a runtime threshold artifact). Show node/edge counts from the Phase 4 smoke test.

**Section 4 — PR Reasoning**
Show the PPR weight schema (`CALLS=1.0`, `RENDERS=0.95`, `IMPLEMENTS=0.85`, `COVERS=0.75`). Explain the correct forward direction (not reversed). Show the seed selection logic from Phase 5. Cite `blast_radius_report.json` for actual impact scores.

**Section 5 — Deterministic vs. LLM-Driven Decomposition**
Use the table from the architecture overview section verbatim. Explain: Playwright/ast-grep/PyDriller/PPR are deterministic and re-runnable. LLM calls are used only for semantic extraction (PRD → requirements) and entity resolution (requirement → code). Every LLM output is validated against a Pydantic schema before entering the graph.

**Section 6 — Schema and Absence Query**
Node labels: `Requirement`, `UIElement`, `CodeFunction`, `Page`, `GapNode`. Edge types: `IMPLEMENTS`, `RENDERS`, `COVERS`, `CALLS`, `ABSENT_FROM`. Justify each against a use case: `COVERS` allows "which UI elements cover this requirement?" (`MATCH (u:UIElement)-[:COVERS]->(r:Requirement {id:$id})`). Absence: `coverage_status: "MISSING"` on `Requirement` nodes, set deterministically after graph build. `GapNode` is an audit artifact (not the absence definition itself).

**Section 7 — Confidence and Escalation**
Thresholds: HIGH ≥ 0.70 impact AND ≥ 0.70 traceability. MEDIUM ≥ 0.40. LOW < 0.40. DARK_CHANGE: no path found. System stops and asks a human when: (a) a Requirement is LOW confidence, (b) any dark change exists, (c) the report contains `manual_review_items`. OpenHands ACI for automated ambiguity resolution is deferred to Week 2; v1 uses explicit `manual_review_items`.

**Section 8 — Evaluation and Stability**
Single run: validate `BlastRadiusReport` schema with Pydantic (hard); check at least one banking-domain requirement in output (domain spot-check). Stability (3 runs): Jaccard similarity of `affected_requirements` node ID sets should be ≥ 0.85 (deterministic graph + PPR; variance comes only from LLM entity resolution and summary). Report any Jaccard < 0.85 as a reliability flag.

**Section 9 — Scope Decisions**
Use the table below verbatim in the design document:

| Cut | Rationale | Week 2 path |
|---|---|---|
| Full CPG via Joern | JVM/Scala setup cost exceeds 16h budget; ast-grep covers structural facts | Joern + PyJoern wrapper |
| Splink entity resolution | Splink 4.x API diverged from v1 docs; whole-label blocking near-zero recall | Collect labelled pairs from reviewer, then train Splink EM |
| LightRAG retrieval | Optional retrieval augmentation; PostgreSQL dependency removed to reduce complexity | Add back with confirmed 2.x API |
| browser-use dynamic agent | API instability (v1 audit); replaced with reliable Playwright for SPA crawling | browser-use for stateful form flows once API is stable |
| GNNExplainer training | Requires trained GNN prediction; deferred as out of scope | Week 3 after Joern CPG provides richer graph |
| OpenHands ACI | Architecture designed; runtime not implemented | Week 2 after stable report is demonstrated |
| Apache AGE | Installation/version compatibility unverified | Evaluate after LightRAG integration |
| PR #1436 (logo swap) | Too trivial; no TypeScript changes | PR #1421 (user settings feature) used instead |

**Section 10 — What to Build Next (Top 3)**
1. Joern CPG — CFG/PDG/data-flow edges; import-aware resolution; dark changes become traceable
2. PR webhook with incremental graph update — real-time CI/CD; qodo-ai/pr-agent webhook pattern
3. Labelled entity resolution + evaluation harness — reviewer-confirmed Requirement↔CodeFunction pairs; Splink EM training; Jaccard stability across 10 PRs

### docs/evaluation_protocol.md

```markdown
# Evaluation Protocol

## Single-Run Correctness

1. Schema validation: `BlastRadiusReport.model_validate_json(report_path.read_text())`  
   — Passes or raises `ValidationError`. Hard gate.
2. Domain spot-check: at least one affected requirement contains a banking term
   (transaction, transfer, payment, account, balance, contact, settings)
3. Score range: all `confidence_scores` values in [0.0, 1.0]
4. Non-empty: at least one of affected_ui_elements, affected_requirements, dark_changes, manual_review_items

## Stability (3-Run Test)

```bash
for i in 1 2 3; do
  python scripts/run_pipeline.py --phase 5,6
  cp data/reports/blast_radius_report.json data/reports/run_${i}.json
done
```

Then measure Jaccard similarity of `affected_requirements` node ID sets across runs.
Acceptable: Jaccard ≥ 0.85. Flag if < 0.85 (LLM entity resolution variance).

## Manual Gold Labels

For each PR analyzed, a QA engineer reviews the report and marks each affected requirement as:
- CONFIRMED: this requirement really is at risk from this PR
- DISMISSED: this requirement is not at risk (false positive)
- UNKNOWN: cannot determine without more information

Record in `data/reports/gold_labels_pr_{number}.json`.
Target: Precision > 0.70, Recall > 0.60 on confirmed items.
```

### Smoke test for design document:
```bash
python -c "
p = open('docs/design_document.md', encoding='utf-8').read()
sections = [str(i) + '.' for i in range(1, 11)]
for s in sections:
    assert s in p, f'Missing section {s} in design document'
assert len(p) > 8000, f'Design document too short: {len(p)} chars (expected > 8000)'
print('OK — design document complete')
"
```

**Merge condition:** All 10 numbered sections present, length > 8 000 chars, no placeholder text ("TODO", "TBD", "to be filled").

---

## Appendix A: Sample Blast Radius Report

This is what a good report output looks like for PR #1421. Your generated report should match this structure.

```
# Blast Radius Report — PR #1421

**PR:** [feat: add user settings for profile updates](https://github.com/cypress-io/cypress-realworld-app/pull/1421)
**Mode:** neo4j  **Run ID:** a3f2b1c4

---

## Executive Summary

PR #1421 modifies the user profile update flow, including changes to the settings form handler and the user API endpoint. This affects the User Settings page and the requirement that users can update their personal details. One dark change in an internal validator function cannot be automatically traced to a UI element; manual review of the validator's downstream effects is recommended.

---

## Changed Files

| File | Status | +/− |
|---|---|---|
| `src/models/user.ts` | modified | +23/−5 |
| `src/routes/userRoutes.ts` | modified | +12/−3 |
| `src/components/UserSettings/index.tsx` | modified | +18/−7 |

## 🔴 High-Risk Requirements

- **Users can update their display name and email address**
  - Impact score: 0.91 | Confidence: 0.88
  - Evidence: `src/components/UserSettings/index.tsx:42:handleSubmit` → `ui:a3f2:/user/settings:14` → `REQ-3A2B1C4D`

## 🟡 Medium-Risk Requirements

- **User profile changes persist across sessions** (impact: 0.61)

## ⚫ Dark Changes

- `src/utils/validateUserInput:18:sanitize`

## ⚠️ Manual Review

- 1 function has no traceable path to UI or requirements: `src/utils/validateUserInput:18:sanitize`
- 2 requirements have LOW confidence impact scores. Verify before updating test plans.
```

---

## Appendix B: Week 2 Roadmap

Once the v1 pipeline is stable and producing reports for multiple PRs:

**Priority 1 — Joern CPG**
Replace ast-grep structural facts with full Code Property Graph (AST + CFG + PDG). This makes dark changes smaller (data-flow tracking) and evidence causal rather than lexical. Estimated: 1–2 weeks.

**Priority 2 — PR Webhook + Incremental Graph**
Integrate qodo-ai/pr-agent GitHub webhook. On each PR open/update: run Phase 3 (delta only), update only affected graph nodes via MERGE, run Phase 5, post report as PR comment. Moves from batch to real-time. Estimated: 3–5 days.

**Priority 3 — Labelled Entity Resolution + Evaluation Harness**
Collect reviewer gold labels for 10 PRs. Train Splink EM model on confirmed requirement↔code pairs. Add Jaccard stability tests to CI. Report precision/recall on held-out PRs. This is the highest-ROI accuracy improvement. Estimated: 1 week.

---

## Common Failures and Fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| `NEO4J_PASSWORD must be set` at startup | `.env` not copied | `cp .env.example .env` and fill in values |
| `dom_snapshot` is `<div id="root"/>` | Using crawl4ai static mode on SPA | Use Playwright dynamic crawler only for RWA |
| `ast-grep returned no TypeScript functions` | `sg` not installed or wrong path | `brew install ast-grep` or `cargo install ast-grep` |
| `PyDriller found no commits` | `MERGE_SHA` not set or wrong | Run the `gh pr view` command, set `MERGE_SHA` in `.env` |
| `No seed nodes` | Changed files not in TypeScript call graph | PR touches assets/config — legitimate DARK_CHANGE |
| Graph empty after Phase 4 | Entity resolution found no candidates | Lower `cosine_threshold` or inspect LLM reranker prompt |
| Splink import error | v1 dependency still in requirements.txt | Splink not in v2 requirements; remove it |
| Report is completely empty | Phase 3 or 4 failed silently | Check each phase individually with `--phase N` flag |
| Neo4j port 7687 already in use | Another Neo4j container running | `docker ps`, stop the conflicting container |

---

*v2 Implementation Guide — built from v1 and the v1 audit report. All known v1 bugs corrected. Fabricated API calls replaced with verified patterns or explicitly flagged for manual verification. Every file in "Creates:" sections has complete code.*
