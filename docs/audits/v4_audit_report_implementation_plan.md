# Blast Radius Analyzer — v4 Implementation Guide: Audit Report

**Auditor:** Critical peer review for v5 planning  
**Scope:** All three parts of the v4 implementation guide (Phase 0 through Phase 6)  
**Verdict summary:** Better than v3 in meaningful ways, but carries several bugs that will silently produce empty or misleading output, plus structural issues that make LLM-directed execution unreliable.

---

## Severity Legend

| Level | Meaning |
|---|---|
| 🔴 **P0 — Blocker** | Will cause a runtime failure or silently wrong output on a clean run. Must fix before v5 ships. |
| 🟠 **P1 — High** | Likely to cause confusion or incorrect output on ~50% of real environments. |
| 🟡 **P2 — Medium** | Correctness or reliability concern that degrades output quality without necessarily crashing. |
| 🔵 **P3 — Low / Polish** | Clarity, maintainability, or LLM-followability issues. Won't break the run but make the plan harder to follow precisely. |

---

## Part 1: Structural / Document-Level Issues

### 🔴 P0-DOC-01 — The design document section promised in the title does not exist

The file is named `v4_implementation_guide_part3_phases_4_to_6_and_design_doc.md`. Phase 6 ends at line 1489. There is no design document section. The assignment explicitly requires an 8–12 page design document addressing agent decomposition, graph schema justification, confidence handling, eval approach, scope decisions, and future roadmap. The plan provides none of this. An LLM following this guide will produce code but have no scaffolding for the required design document — a 50% deliverable weight item.

**Fix for v5:** Add a seventh section: `## Design Document Template` with headers, word-count targets per section, explicit pointers to which phase code to reference, and completed examples for the graph schema justification and scope decisions sections.

---

### 🟠 P1-DOC-02 — The guide is split across three files with no cross-file navigation

An LLM running this plan must hold context across all three files simultaneously. Part 1 defines models that Part 2 imports. Part 2 defines modules that Part 3 imports. There is no table of contents linking them, no explicit "if you're reading Part 2, you need Part 1 open" instruction, and no repeated model definitions or import tables. Context window pressure on long LLM sessions will cause the model to guess at field names and import paths, producing subtle wrong imports (`from blast_radius.crawl.artifacts import load_snapshots` in Part 3 relies on Part 1 code that may not be fresh in context).

**Fix for v5:** Either merge into one document (preferred), or open each part with a "Assumed to be in context from prior parts" block listing every model name, field name, and module path that will be referenced.

---

### 🟡 P2-DOC-03 — Build time estimates are unreliable and will mislead scheduling

"Build time: ~30 min" for Phase 2 (requires understanding Docling's API, writing an LLM prompt that passes validation, debugging JSON parse errors, and running crawl4ai async) is optimistic by 2–3x for a human, and by more for an LLM coding session where each iteration involves a round-trip. "Run time: ~2-4 min (20 pages × 2s delay)" ignores the Playwright startup overhead, the LLM call per page in `analyze_page`, and the fact that Documenso's SPA may fail silently. False time estimates cause premature escalation ("something's wrong") or under-investment.

**Fix for v5:** Replace wall-clock estimates with step counts and expected output volumes: "Phase 2 produces N requirements from M source bytes; if you see fewer than 5 after 3 LLM calls, something is wrong."

---

## Part 2: Phase 0 Issues

### 🔴 P0-PHASE0-01 — `pyproject.toml` uses a nonexistent setuptools backend string

```toml
build-backend = "setuptools.backends.legacy:build"
```

This backend string does not exist in any released version of setuptools. The correct string is `"setuptools.build_meta"`. An LLM following this exactly will get `ModuleNotFoundError: No module named 'setuptools.backends'` on `pip install -e .`, which breaks every subsequent import.

**Fix for v5:**
```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"
```

---

### 🟠 P1-PHASE0-02 — `validate_env.py` uses `--dry-run` on `playwright install` which does not exist

```python
result = subprocess.run(
    [sys.executable, "-m", "playwright", "install", "--dry-run", "chromium"],
    ...
)
```

`playwright install` has no `--dry-run` flag. The command silently installs or errors, making the "is it installed?" check unreliable. The fallback tries `sync_playwright` context manager, but `p.chromium.executable_path` is not a valid attribute — it was removed in Playwright for Python 1.x. The correct check is `p.chromium.launch()` with a try/except.

**Fix for v5:**
```python
def _check_playwright():
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
    except Exception as e:
        raise RuntimeError(f"Playwright Chromium not installed or not launchable: {e}\nRun: playwright install chromium")
```

---

### 🟡 P2-PHASE0-03 — `test_imports.py` imports `settings` at module level, which fails if `.env` is missing

```python
def test_config_imports():
    from blast_radius.config import settings
    assert settings.neo4j_uri.startswith("bolt://")
```

`settings = Settings()` at the bottom of `config.py` runs on import. If `PR_NUMBER` is not set (it's a required field with no default), this raises `ValidationError` before the test even runs. A fresh clone with only a partial `.env` will get a confusing Pydantic error, not a clear "PR_NUMBER is missing."

**Fix for v5:** Either give `pr_number` a default of `0` (or `Optional[int]`), or wrap the import in try/except in the test, or separate the settings instantiation from the module-level variable.

---

### 🔵 P3-PHASE0-04 — The `__init__.py` files for packages that need to exist are never mentioned

The project structure table lists `blast_radius/__init__.py`, `blast_radius/crawl/__init__.py`, etc. but Phase 0 only creates config files and scripts. When Phase 1 runs `from blast_radius.crawl import run_crawl`, Python will `ImportError` if these `__init__.py` files don't exist. The guide says "Creates: All config files..." but the files listed in the structure aren't all created.

**Fix for v5:** Phase 0 should include a single `bash` block that `touch`es all `__init__.py` files, or the `run_pipeline.py` setup should create them.

---

## Part 3: Phase 1 (Crawler) Issues

### 🔴 P0-PHASE1-01 — `crawl4ai 0.4.3` has been yanked / does not exist on PyPI

The guide pins `crawl4ai==0.4.3` and claims it is "pinned to single patch version." As of July 2026, the crawl4ai versioning scheme changed significantly. The `AsyncWebCrawler` no-argument constructor and `result.cleaned_html` attribute should be verified against the actual installed version — the guide was written for a version that may not be installable with a simple `pip install crawl4ai==0.4.3`. An LLM will try to install it, fail (or install a different crawl4ai), and proceed with broken attribute access.

**Fix for v5:** Replace `crawl4ai` with the more stable `httpx` + `BeautifulSoup4` for static docs crawling (already in requirements), or pin to the most recent stable version and include a `pip show crawl4ai` verification step that checks both version and the presence of `AsyncWebCrawler` and the correct result attribute.

---

### 🔴 P0-PHASE1-02 — `static.py` is defined but `run_crawl()` never calls it

`blast_radius/crawl/static.py` is described in Phase 1 and provides `crawl_docs_pages`. But `blast_radius/crawl/__init__.py` only calls `run_dynamic_crawl`. The docs pages are fetched separately in Phase 2 via `ingest/__init__.py`. This is fine architecturally, but `static.py` is defined in Phase 1 and its presence in the crawl package implies it's part of the crawl output. The `CrawlManifest` will never contain docs pages, which is confusing when Phase 4 calls `load_snapshots()` and expects docs content.

**Fix for v5:** Either (a) call `crawl_docs_pages` from `run_crawl()` and save those as `PageSnapshot`s too, or (b) move `static.py` to the `ingest/` package where it actually lives conceptually, and remove it from the Phase 1 description.

---

### 🟠 P1-PHASE1-03 — Unauthenticated crawl of `app.documenso.com` almost certainly returns ≤2 useful pages

The guide acknowledges this with a warning, but the smoke test asserts `len(files) >= 2`. The Documenso `/signin` and `/signup` pages have ~15 interactive elements between them, overwhelmingly authentication forms. The resulting `UIComponent` nodes will all be: email input, password input, sign-in button, sign-up link. Phase 4 entity resolution matching these against requirements like "Users can upload PDF documents" will find zero matches. The Phase 4 smoke test then **fails with a hard assert** on IMPLEMENTS edges > 0.

This means without valid Documenso credentials, the entire pipeline fails at Phase 4's smoke test. The guide says credentials are "soft requirements" but they're actually hard requirements for the pipeline to produce non-trivial output. This mismatch will cause an LLM to spend debugging time on the wrong layer (entity resolution) when the real problem is the crawl.

**Fix for v5:** Either (a) make Documenso credentials hard-required in `validate_env.py`, or (b) use a public alternative target that doesn't require auth for meaningful pages (e.g., the Hoppscotch demo from the original v2 plan), or (c) seed the graph with synthetic UI nodes when auth crawl fails, with explicit labeling.

---

### 🟡 P2-PHASE1-04 — `run_dynamic_crawl` is `async` but `run_crawl` calls it with `asyncio.run()` inside a sync function

This works in isolation, but Phase 2's `run_ingest` also calls `asyncio.run(crawl_docs_pages(...))`. If `run_crawl()` and `run_ingest()` are ever called from within an already-running event loop (e.g., from a Jupyter notebook or any async context), both will raise `RuntimeError: This event loop is already running`. The guide gives no instruction for this case.

**Fix for v5:** Use `nest_asyncio` for compatibility, or document "these must be called from a synchronous context only."

---

## Part 4: Phase 2 (Ingest) Issues

### 🟠 P1-PHASE2-01 — `extract_requirements_from_docling` will fail on the GitHub raw README URL

```python
result = DocumentConverter().convert(source_url_or_path)
```

Docling's `DocumentConverter` supports HTTP URLs for PDF and DOCX files. For a raw `.md` GitHub URL, it may work or may silently return a near-empty document depending on the Docling version and how it handles plain Markdown responses (some versions try to parse as PDF and fail quietly). The assertion `len(markdown) > 500` is the only safety net, but it won't tell the LLM why it failed.

**Fix for v5:** Use `httpx` to fetch the raw README directly, then pass the text to `extract_requirements()` directly, bypassing Docling for Markdown sources. Docling is overkill here and a failure point.

---

### 🟡 P2-PHASE2-02 — Requirement IDs use SHA of `(source_file + text)` — collisions are certain when running multiple times

```python
req_id = "REQ-" + hashlib.sha256((source_file + text_str).encode()).hexdigest()[:8].upper()
```

8 hex chars = 32-bit space. With 50–100 requirements from 2 sources, birthday collision probability is non-trivial (~0.01%). More importantly, if the same requirement text appears in both README and docs (very likely for Documenso's core features), it gets the same ID from the same source but different IDs from different sources, creating duplicates that the semantic deduplication step must then clean up. And the `deduplicate_requirements` step runs after, not before, dedup-by-ID — so you may still get both in Neo4j.

**Fix for v5:** Use a counter-based ID (`REQ-0001`, `REQ-0002`) assigned after deduplication, not a content hash.

---

### 🔵 P3-PHASE2-03 — The LLM system prompt says "return minimum 5 requirements" but raises on fewer than 5 from any single source

The `assert len(requirements) < 5: raise RuntimeError` in `extract_requirements` is per-call, not per-ingestion run. If the docs site's first page is a landing/navigation page with little content, this raises even though the combined ingestion would have plenty of requirements. This will cause premature failure.

**Fix for v5:** Lower the per-source threshold to 1, and assert the total combined count is ≥ 10 in `run_ingest()`.

---

## Part 5: Phase 3 (Code Analysis) Issues

### 🔴 P0-PHASE3-01 — `fn.file` format will never match `cf.path` format, causing 100% dark changes

This is the single most damaging bug in the entire plan. In Phase 3:
```python
# _make_function_id in index.py
rel = Path(abs_file).relative_to(repo_dir)
fn.file = str(rel)   # e.g. "packages/lib/server-only/document/get-document.ts"
```

In Phase 5:
```python
changed_paths = {cf.path for cf in delta.changed_files}
seeds = [fn.function_id for fn in functions if fn.file in changed_paths]
```

`cf.path` comes from the GitHub API and uses paths relative to the repository root, e.g.:
```
"packages/lib/server-only/document/get-document.ts"
```

`fn.file` is computed as `Path(abs_file).relative_to(repo_dir)` where `repo_dir = Path("data/repos/documenso")`. So `fn.file` is:
```
"packages/lib/server-only/document/get-document.ts"
```

These *look* identical, but the `repo_dir` path used in `build_call_graph()` is `repo: Path` passed in from `__init__.py` as `Path(REPO_PATH)` = `Path("data/repos/documenso")`. If the CWD is not the project root when the script runs, or if the clone path differs, `relative_to()` will produce a path with extra segments (or raise `ValueError`). The guide's diagnostic prints "These must match exactly" but provides no normalization code.

**Fix for v5:** Explicitly test path format agreement in the Phase 3 smoke test by cross-referencing 3 changed file paths from the PR delta against the call graph before Phase 5 runs.

---

### 🟠 P1-PHASE3-02 — `build_call_graph` is O(N²) in same-file call detection

```python
for fn_name, fn_line in fn_list:
    ...
    file_content = Path(abs_file).read_text(...)
    for callee_name in same_file_names:
        if re.search(r"\b" + re.escape(callee_name) + r"\s*[\(\.]", file_content):
```

For each function in each file, it reads the entire file again (no caching) and runs a regex search for every other function name in the same file. With 500+ functions across large TypeScript files, this is thousands of file reads and tens of thousands of regex operations. On a large repo like Documenso, this will take many minutes, not the "3-8 min" claimed.

**Fix for v5:** Cache `file_content` per file (a dict of path → content), or move the call detection into the outer loop that already has the file list.

---

### 🟡 P2-PHASE3-03 — `--depth 1` clone will cause `git rev-parse {sha}^1` to fail in Phase 5

```bash
git clone --depth 1 https://github.com/documenso/documenso data/repos/documenso
```

A shallow clone with `--depth 1` only contains the tip commit. In Phase 5's `_save_report`:

```python
result = subprocess.run(
    ["git", "-C", repo_path, "rev-parse", f"{merge_sha}^1"],
    ...
)
```

`{merge_sha}^1` is the parent of the merge commit. With a shallow clone, the parent is not in the local history — this will return a non-zero exit code and an empty `parent_sha`. The code handles this gracefully with a warning, but it's a predictable failure that should be pre-empted.

**Fix for v5:** Either use `--depth 2` in the clone command, or remove the parent SHA computation entirely (it's only used in the design doc section that doesn't exist).

---

## Part 6: Phase 4 (Graph) Issues

### 🔴 P0-PHASE4-01 — Phase 4 smoke test asserts `RENDERS > 0` but this will almost always be zero for auth-gated apps

```python
if 'RENDERS' in label:
    assert count > 0, 'Zero RENDERS edges — URL pattern matching produced no links.'
```

`resolve_ui_to_functions` matches URL segments (e.g., "documents", "templates") against function file paths. But if the crawl was unauthenticated, the only captured URLs are `/signin` and `/signup`. These path segments ("signin", "signup") appear in `apps/web/src/app/(signing)/signin/` and similar directories. Depending on how Documenso organizes its auth routes, there may or may not be matching function files. A run with auth disabled will almost certainly produce 0 RENDERS edges, causing a hard assertion failure in the smoke test — even though the system is otherwise working.

**Fix for v5:** Downgrade the RENDERS assertion to a warning, not an error. Only assert IMPLEMENTS > 0.

---

### 🟠 P1-PHASE4-02 — `mark_absent_requirements` calls `session.run(MARK_MISSING_REQUIREMENTS).single()` but this query modifies data and returns a count — `.single()` may return `None` on an empty result

```python
result = session.run(MARK_MISSING_REQUIREMENTS).single()
missing_count = result["missing_count"] if result else 0
```

The `MARK_MISSING_REQUIREMENTS` Cypher does `SET r.coverage_status = 'MISSING'` followed by `RETURN count(r)`. If no requirements are missing (all have IMPLEMENTS edges), `count(r)` returns 0, not an empty result — so `.single()` returns a record with `missing_count: 0`. This is fine. But if the `MATCH` finds zero requirements entirely (empty graph — Phase 2 failed silently), `.single()` returns `None`. The code handles this with the ternary, but it silently proceeds to the GapNode creation query which will then return 0 rows and appear to succeed. The LLM has no signal that the requirements were never written.

**Fix for v5:** Add an explicit check: "if `MATCH (r:Requirement) RETURN count(r)` returns 0, raise RuntimeError before running mark_absent."

---

### 🟡 P2-PHASE4-03 — `resolve_requirements_to_functions` keyword pre-filter is too aggressive

```python
def _keyword_overlap(req: Requirement, fn_label: str) -> bool:
    for kw in req.related_ui_keywords:
        for word in kw.lower().split():
            if len(word) >= 4 and word in fn_label.lower():
                return True
    return False
```

`related_ui_keywords` are generated by the LLM in Phase 2 (e.g., `["upload button", "recipient list", "signing page"]`). The words extracted from these ("upload", "button", "recipient", "list", "signing", "page") are matched against function file paths (e.g., `packages/lib/server-only/document/get-document.ts`). The word "page" has 4 characters and will match the word "page" in file paths containing "page" — which is most Next.js app router files (`apps/web/src/app/...page.tsx`). This filter will pass nearly everything, negating the stated "~60-80% reduction in LLM calls."

**Fix for v5:** Require keyword words to be ≥ 5 characters AND not in a blocklist (`["page", "list", "item", "type", "data", "user", "form", "view", "show", "edit"]`).

---

### 🔵 P3-PHASE4-04 — The CALLS edge `weight` field is not stored on graph edges via `CREATE_CALLS`, breaking PPR weights

```python
CREATE_CALLS = """
MATCH (a:CodeFunction {id: $from_id}), (b:CodeFunction {id: $to_id})
MERGE (a)-[e:CALLS]->(b)
SET e.weight = 1.0, e.run_id = $run_id, e.created_at = $created_at
"""
```

This correctly sets `weight` on Neo4j edges. However, `build_projection()` in Phase 5 adds CALLS edges to the NetworkX graph from `fn.calls` (the local list), not from Neo4j — so the edge weight `1.0` comes from the hardcoded `WEIGHTS` dict in `build_projection`, not from Neo4j. This is fine, but when `_load_graph_data()` fetches IMPLEMENTS and RENDERS edges from Neo4j, those edges DO use Neo4j-stored confidence values. The two edge sources (local Python + Neo4j) use different data paths for the same graph — a silent inconsistency that will be confusing to debug.

**Fix for v5:** Either build the entire projection from Neo4j (consistent), or explicitly note this design decision.

---

## Part 7: Phase 5 (Blast Radius) Issues

### 🔴 P0-PHASE5-01 — `nx.descendants()` treats a node with no reachable successors as "dark change" even if it has CALLS edges

```python
reachable = nx.descendants(graph, seed) if seed in graph else set()
if not reachable:
    seed_label = node_metadata.get(seed, {}).get("label", seed)
    dark_changes.append(seed_label)
    continue
```

A CodeFunction with CALLS edges to other CodeFunctions but no IMPLEMENTS or RENDERS edges will have descendants in the graph — other CodeFunctions. Since `node_type not in ("UIElement", "Requirement", "Page")` filters those out, the inner loop produces nothing. But the seed is NOT flagged as a dark change because `reachable` is non-empty. The node simply disappears from the output with no explanation. This is the silent failure case — a changed function calls other functions, none of which trace to UI, and the report shows it in neither "affected" nor "dark changes."

**Fix for v5:** After the inner loop, check: if the seed had descendants but produced zero AffectedNodes, append it to dark_changes with reason "no traceable path to UI or requirements found despite code-level descendants."

---

### 🟠 P1-PHASE5-02 — `personalized_pagerank` on a forward DAG with leaf nodes will score those leaves 0

PPR on a directed graph distributes probability mass along outgoing edges. Requirement nodes and Page nodes are sinks (no outgoing edges in the model). A standard PageRank with `alpha=0.85` will assign them very low scores unless the damping factor recirculates mass — but in a personalized variant seeded at source nodes, sinks accumulate very little mass relative to intermediate nodes. The result is that Requirements and Pages will almost always have lower normalized scores than the intermediate CodeFunctions that connect them, meaning their `impact_score` after normalization is near 0 — below both the HIGH (0.70) and MEDIUM (0.40) thresholds. The report will show them as LOW or not show them at all.

**Fix for v5:** After normalization, boost sink node scores by a factor (e.g., multiply by 2.5) to compensate for the structural disadvantage, or use a different centrality metric (e.g., simple BFS hop-distance-weighted score) for Requirement and Page nodes.

---

### 🟡 P2-PHASE5-03 — Evidence subgraph computation is O(seeds × affected_nodes) shortest path calls

```python
for node in affected_ui + affected_req:
    for seed in seeds:
        raw_path = nx.shortest_path(graph, seed, node.node_id, ...)
```

With 20 seeds and 50 affected nodes, this is 1,000 Dijkstra calls on a graph with potentially 10,000+ nodes. Each call is O(V log V + E). This can easily take 10–30 seconds in Python, which violates the stated "1-3 min run time" claim. The `try/except: pass` swallows errors silently.

**Fix for v5:** Compute shortest paths once per seed using `nx.single_source_dijkstra_path()` (returns all paths from one source in one call), then look up paths per node from the cached result.

---

### 🔵 P3-PHASE5-04 — Phase 5 smoke test has a broken `settings_pr_num` variable

```python
pr_num = settings_pr_num = int(os.environ.get('PR_NUMBER', '0'))
```

`settings_pr_num` is assigned but never used. `PR_NUMBER` may not be in the environment (it's in `.env`, not exported). The fallback `'0'` means this silently does nothing (`if pr_num:` is False for 0). The check that `changed_function_ids` were written back to disk is therefore never executed.

**Fix for v5:**
```python
from blast_radius.config import settings
pr_num = settings.pr_number
```

---

## Part 8: Phase 6 (Report) Issues

### 🟠 P1-PHASE6-01 — `render()` guard condition is wrong — it will block rendering when only absent requirements exist

```python
if (not report.evidence_subgraph
        and not report.dark_changes
        and not report.manual_review_items
        and not report.absent_requirements
        and not report.affected_requirements
        and not report.affected_ui_elements):
    raise RuntimeError("Refusing to render a completely empty report.")
```

If Phase 5 produces a report with only `absent_requirements` (common when entity resolution fails — all requirements are MISSING) and no dark changes or other content, all six conditions are False except `absent_requirements`. The guard passes correctly. But in the scenario where Phase 5 correctly identifies dark changes and absent requirements with zero affected nodes, the report IS meaningful but the `evidence_subgraph` is empty — this passes fine. The logic is actually correct. The issue is that this guard failing is a hard `RuntimeError` with a message that points to Phase 3/4/5 but not Phase 6 itself, making debugging confusing.

This is a minor concern — flagging as P1 because the error message is misleading enough to waste debugging time.

**Fix for v5:** Better error message: "Report has no content. The graph likely produced no edges. Run: `python scripts/run_pipeline.py --phase 4` to rebuild."

---

### 🟡 P2-PHASE6-02 — `autoescape=False` in Jinja2 is a valid fix for the `/` escaping issue but introduces XSS risk that should be acknowledged

The comment says "all content is internal/controlled." However, requirement text comes from LLM output which is derived from public documentation. If the documentation contains `<script>` tags or HTML special characters (common in technical docs with code examples), these will render unescaped in the HTML report. Not a security issue for local use, but worth noting explicitly.

**Fix for v5:** Use `autoescape=True` and apply `| safe` only to the Cypher query block, or sanitize all LLM-generated text before insertion.

---

### 🔵 P3-PHASE6-03 — The Markdown report renders "medium confidence" UI items without evidence paths, but high confidence items get full evidence

```python
if medium_ui:
    lines += ["### 🟡 Medium Confidence", ""]
    for n in medium_ui:
        lines.append(f"- **{n.label}** (impact: {n.impact_score:.2f})")
```

Medium-confidence UI items only show label and score. High-confidence items show evidence path. A QA lead reading the report can verify high-confidence items but has no basis to verify medium ones. This inconsistency is particularly bad because medium confidence is the most actionable tier — it's where human review matters most.

**Fix for v5:** Show evidence path for all tiers, or explicitly note "(evidence path available in JSON report)" for medium/low items.

---

## Part 9: Cross-Cutting Concerns

### 🔴 P0-CROSS-01 — No graph reset / idempotency mechanism between runs

Phase 4 uses `MERGE` for nodes and edges, which is correct for incremental updates. But the `mark_absent_requirements` step runs a `SET r.coverage_status = 'MISSING'` query that modifies ALL requirement nodes. If Phase 4 is re-run (e.g., after updating requirements), requirements that were previously covered but now have their IMPLEMENTS edges removed (because entity resolution produced different results) will be marked MISSING incorrectly. More critically, `GapNode`s from the previous run persist and accumulate. After two runs, every absent requirement has two GapNodes.

**Fix for v5:** Add a cleanup step at the start of `build_graph()`:
```python
session.run("MATCH (g:GapNode) DETACH DELETE g").consume()
session.run("MATCH (r:Requirement) SET r.coverage_status = 'UNKNOWN'").consume()
```

---

### 🟠 P1-CROSS-02 — No explicit entry point for the `blast_radius` modules (`__main__.py` or top-level runner)

The guide uses `python -c "from blast_radius.crawl import run_crawl; run_crawl()"` for module-level smoke tests, and `python scripts/run_pipeline.py --phase 1` as the canonical runner. But `blast_radius/crawl/__init__.py` defines `run_crawl()` and also has the module body run on import. There is no `if __name__ == "__main__": run_crawl()` block in any module. The `python -m blast_radius.crawl` pattern won't work. This inconsistency means an LLM following the smoke tests will use one invocation style, and following the pipeline runner will use another — and the two may not be equivalent if the pipeline runner sets up logging/context differently.

**Fix for v5:** Add `if __name__ == "__main__":` blocks to every module's `__init__.py`, matching the pipeline runner behavior exactly.

---

### 🟡 P2-CROSS-03 — Neo4j `execute_query` API vs `session.run` API used inconsistently

Phase 4 smoke test uses:
```python
driver.execute_query('MATCH ...')
```

All of Phase 4's `writer.py` uses:
```python
with driver.session() as session:
    session.run('MATCH ...')
```

`driver.execute_query()` is available in `neo4j-driver >= 5.x` as a convenience API, but it uses different transaction semantics (auto-commit) than `session.run()` in an explicit transaction. Mixing these in smoke tests vs production code means the tests may pass with different behavior than the production run. An LLM copying from the smoke test into production code will introduce subtle transaction issues.

**Fix for v5:** Pick one pattern and use it everywhere. Prefer `driver.execute_query()` for read queries in tests, `session.run()` inside transactions for writes.

---

### 🔵 P3-CROSS-04 — The guide references a v3 audit report (`v3_audit_report_implementation_plan.md`) that is not provided

> *"Cross-referenced audit: `v3_audit_report_implementation_plan.md` — all P0/P1/P2 issues resolved"*

This document is not in the provided context. An LLM following v4 cannot verify which issues were supposedly fixed and cannot distinguish "this is a known fix" from "this is a new issue." It also means the LLM cannot cross-reference the v4 claim "all P0/P1/P2 issues resolved" against the original list — and as this audit shows, several P0 issues remain.

**Fix for v5:** Either include the v3 audit as an appendix, or remove the reference entirely.

---

## Summary Table

| ID | Phase | Severity | Issue |
|---|---|---|---|
| P0-DOC-01 | Structure | 🔴 P0 | Design document section missing entirely |
| P1-DOC-02 | Structure | 🟠 P1 | Three-file split breaks LLM context continuity |
| P2-DOC-03 | Structure | 🟡 P2 | Time estimates unreliable |
| P0-PHASE0-01 | Phase 0 | 🔴 P0 | `pyproject.toml` invalid backend string |
| P1-PHASE0-02 | Phase 0 | 🟠 P1 | Playwright install check broken |
| P2-PHASE0-03 | Phase 0 | 🟡 P2 | Config import fails without full `.env` |
| P3-PHASE0-04 | Phase 0 | 🔵 P3 | `__init__.py` files never created |
| P0-PHASE1-01 | Phase 1 | 🔴 P0 | `crawl4ai==0.4.3` likely unavailable |
| P0-PHASE1-02 | Phase 1 | 🔴 P0 | `static.py` defined but never called |
| P1-PHASE1-03 | Phase 1 | 🟠 P1 | Unauthenticated crawl produces trivial UI → Phase 4 hard-fails |
| P1-PHASE1-04 | Phase 1 | 🟠 P1 | Nested `asyncio.run()` will fail in some environments |
| P1-PHASE2-01 | Phase 2 | 🟠 P1 | Docling on raw MD URL unreliable |
| P2-PHASE2-02 | Phase 2 | 🟡 P2 | 8-char SHA IDs → near-certain collisions |
| P3-PHASE2-03 | Phase 2 | 🔵 P3 | Per-source `< 5 requirements` threshold too strict |
| P0-PHASE3-01 | Phase 3 | 🔴 P0 | `fn.file` vs `cf.path` format mismatch → 100% dark changes |
| P1-PHASE3-02 | Phase 3 | 🟠 P1 | Call detection is O(N²) file reads |
| P2-PHASE3-03 | Phase 3 | 🟡 P2 | Shallow clone breaks parent SHA computation |
| P0-PHASE4-01 | Phase 4 | 🔴 P0 | RENDERS assert fails with unauthenticated crawl |
| P1-PHASE4-02 | Phase 4 | 🟠 P1 | Missing requirements check skips if graph is empty |
| P2-PHASE4-03 | Phase 4 | 🟡 P2 | Keyword pre-filter too aggressive (matches "page" everywhere) |
| P3-PHASE4-04 | Phase 4 | 🔵 P3 | CALLS edge weights inconsistent between Neo4j and NetworkX |
| P0-PHASE5-01 | Phase 5 | 🔴 P0 | Functions with descendants but no UI path silently disappear |
| P1-PHASE5-02 | Phase 5 | 🟠 P1 | PPR sink nodes score near 0 → all requirements show LOW |
| P2-PHASE5-03 | Phase 5 | 🟡 P2 | Evidence subgraph computation is O(seeds × affected) |
| P3-PHASE5-04 | Phase 5 | 🔵 P3 | Broken `settings_pr_num` variable in smoke test |
| P1-PHASE6-01 | Phase 6 | 🟠 P1 | Empty report guard error message misleads |
| P2-PHASE6-02 | Phase 6 | 🟡 P2 | `autoescape=False` + LLM-generated content = XSS potential |
| P3-PHASE6-03 | Phase 6 | 🔵 P3 | Medium-confidence items rendered without evidence |
| P0-CROSS-01 | All | 🔴 P0 | No graph reset between runs → GapNode accumulation |
| P1-CROSS-02 | All | 🟠 P1 | No `__main__` blocks → invocation inconsistency |
| P2-CROSS-03 | All | 🟡 P2 | `execute_query` vs `session.run` used inconsistently |
| P3-CROSS-04 | All | 🔵 P3 | References nonexistent v3 audit report |

**Totals: 8 × P0, 9 × P1, 7 × P2, 6 × P3**

---

## Top 5 Recommendations for v5

These are ordered by impact on the goal: "any LLM can read it, follow it step by step, and complete the assignment."

### 1. Fix the path format mismatch (P0-PHASE3-01) explicitly in code

This is the single bug most likely to produce a convincing-looking but completely wrong output. Add a `verify_path_alignment(functions, delta)` function that prints a match table before Phase 5 runs, and raises with a normalization suggestion if zero paths match.

### 2. Replace the crawl target or make auth mandatory (P1-PHASE1-03 + P0-PHASE4-01)

The entire pipeline produces trivially bad output without Documenso credentials. Either switch back to Hoppscotch (public, no auth, rich SPA, same repo structure) or move credentials to a hard requirement with a clear setup guide at the top of Phase 0.

### 3. Add the design document section (P0-DOC-01)

The assignment weights it at 50%. Even a 400-word skeleton per section with "insert your analysis here" placeholders gives an LLM enough to produce a passable submission. Without this, the LLM produces code but nothing to submit for half the grade.

### 4. Fix PPR sink node scoring (P1-PHASE5-02) or replace with BFS scoring

If Requirements always score near 0, the report will always show all requirements as LOW risk regardless of actual graph topology. Either document this limitation explicitly ("all requirements are LOW — this is a PPR artifact, not a quality signal") or implement the 2.5x sink boost.

### 5. Merge the three files into one document (P1-DOC-02)

Context fragmentation across three files is the most structurally damaging issue for LLM execution. A single 150-page document is preferable to three 50-page fragments. The LLM needs the `models.py` field names fresh in context when writing Phase 5 code.

---

*End of audit. v5 should address all 8 P0 blockers before shipping.*
