# Skill: audit-guard

## When to load this skill
Load this skill when implementing or reviewing ANY code for the Blast Radius
Analyzer pipeline. This skill is a checklist of confirmed bugs in the v4
implementation plan. Every bug listed here WILL silently produce wrong output
or crash if reproduced. Apply the fix automatically — do not copy the broken
code from the plan.

---

## P0 Blockers — Apply these fixes, no exceptions

### BUG-01: Wrong setuptools backend string
**In v4 plan:** `build-backend = "setuptools.backends.legacy:build"`
**This does not exist.** Will crash `pip install -e .` with ModuleNotFoundError.
**Correct code:**
```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

### BUG-02: crawl4ai==0.4.3 is unavailable
**In v4 plan:** `crawl4ai==0.4.3` with `AsyncWebCrawler()` no-arg constructor.
**This version is yanked from PyPI.** Do not attempt to install it.
**Fix:** Use Playwright directly for all crawling. The `dynamic.py` module
should use `async with async_playwright() as p:` directly.

### BUG-03: static.py is never called
**In v4 plan:** `static.py` is defined but `run_crawl()` in `__init__.py`
never calls it. Static doc pages are silently skipped.
**Fix:** `run_crawl()` must call both `crawl_dynamic()` AND `crawl_static()`
and merge results into the CrawlManifest.

### BUG-04: Path format mismatch → 100% dark changes
**In v4 plan:** `fn.file` from ast-grep contains paths relative to the scan
root (e.g., `packages/trpc/server/routers/document.ts`). `cf.path` in
CodeFunction models stores absolute paths or differently prefixed paths.
**This causes 100% of changed functions to appear as dark changes.**
**Fix:** Add this function and call it before Phase 5:
```python
def verify_path_alignment(functions: list[CodeFunction], delta: PRDelta) -> None:
    sample_fn = functions[0].path if functions else "N/A"
    sample_delta = delta.changed_files[0].path if delta.changed_files else "N/A"
    matches = sum(
        1 for cf in functions
        for f in delta.changed_files
        if cf.path.endswith(f.path) or f.path.endswith(cf.path)
    )
    print(f"[verify] fn.path sample: {sample_fn}")
    print(f"[verify] delta.path sample: {sample_delta}")
    print(f"[verify] Matches: {matches}/{len(delta.changed_files)} changed files")
    if matches == 0:
        raise ValueError(
            "ZERO path matches between CodeFunctions and PRDelta. "
            "Normalize paths before proceeding — all functions will be dark changes otherwise."
        )
```

### BUG-05: RENDERS assert fails without auth
**In v4 plan:** Phase 4 asserts that at least one RENDERS edge was created,
which requires authenticated Documenso pages to have been crawled.
Unauthenticated crawl only captures marketing/login pages which have no
RENDERS relationships to server-side functions.
**Fix:** Auth credentials in .env are MANDATORY. If missing, raise a clear
error at Phase 1 start, not at Phase 4 assertion.

### BUG-06: Functions silently disappear in Phase 5
**In v4 plan:** Functions that have descendants in the call graph but no
direct path to a UIElement are silently dropped from the blast radius output.
**Fix:** Use DFS fallback — if PPR score > threshold but no UI path found,
include the function in dark_changes, not silently discard it.

### BUG-07: GapNodes accumulate across runs
**In v4 plan:** Phase 4 uses MERGE for nodes but runs SET coverage_status
without clearing old GapNodes. Re-runs produce duplicate GapNodes.
**Fix:** Add this at the START of build_graph():
```python
with driver.session() as session:
    session.run("MATCH (g:GapNode) DETACH DELETE g").consume()
    session.run("MATCH (r:Requirement) SET r.coverage_status = 'UNKNOWN'").consume()
```

---

## P1 Issues — Fix before shipping

### BUG-08: Playwright install check broken
**In v4 plan:** Uses `playwright install --dry-run chromium` which doesn't exist,
then checks `p.chromium.executable_path` which was removed in Playwright 1.x.
**Fix:**
```python
def _check_playwright():
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
    except Exception as e:
        raise RuntimeError(
            f"Playwright Chromium not launchable: {e}\n"
            "Run: playwright install chromium"
        )
```

### BUG-09: PPR sink nodes always score near 0
**In v4 plan:** Requirement nodes (end of chains) score near 0 after PPR
damping. All requirements appear as LOW risk regardless of actual impact.
**Fix:** After PPR, find sink nodes (out_degree == 0) and multiply their
scores by 2.5 before tier assignment. Document this in the report footnote.

### BUG-10: config.py import fails without full .env
**In v4 plan:** `settings = Settings()` runs at module import time.
If PR_NUMBER is missing from .env, every import of config fails with a
confusing Pydantic ValidationError.
**Fix:** Give pr_number a default of 0:
```python
pr_number: int = Field(0, description="Target PR number — set before Phase 3")
```
Or make it Optional[int] = None.

### BUG-11: Missing __init__.py files
**In v4 plan:** Phase 0 creates config files but never touches __init__.py.
All `from blast_radius.X import Y` calls will fail with ImportError.
**Fix:** Phase 0 must include:
```bash
touch blast_radius/__init__.py
touch blast_radius/crawl/__init__.py
touch blast_radius/ingest/__init__.py
touch blast_radius/code/__init__.py
touch blast_radius/graph/__init__.py
touch blast_radius/reason/__init__.py
touch blast_radius/report/__init__.py
```

### BUG-12: Docling on raw Markdown URL unreliable
**In v4 plan:** Docling is called on the raw GitHub README URL.
Docling is optimized for PDFs and structured documents — raw .md files
may parse incorrectly (misidentified tables, lost structure).
**Fix:** Download the README with httpx first, then pass the local file
path to Docling. For docs.documenso.com, use httpx + BeautifulSoup4
to extract text before passing to the LLM extractor.

---

## P2 Issues — Address if time permits

### BUG-13: 8-char SHA IDs have near-certain collisions
Requirement IDs using `sha256(text)[:8]` will collide in any corpus > ~1000
items (birthday problem). Use 16 chars minimum.

### BUG-14: Keyword pre-filter too aggressive
The word "page" appears in nearly every requirement AND every code file.
Add to stoplist: page, component, module, function, service, handler, route,
type, interface, model, schema, data, item, list, user.

### BUG-15: Neo4j API inconsistency
`driver.execute_query()` (auto-commit) is used in smoke tests but
`session.run()` in explicit transactions is used in production code.
Pick one. Use `session.run()` inside transactions everywhere for consistency.

---

## Before Marking Any Phase Complete

Run the smoke test block at the end of each phase section in the v4 plan.
If the smoke test fails, do not proceed to the next phase.
Smoke test failures must be fixed in the current phase, not papered over.
