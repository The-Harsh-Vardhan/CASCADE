# Blast Radius Analyzer — v1 Implementation Guide: Critical Audit Report

> **Purpose:** A frank, evidence-based audit of `v1_implementation_guide.md` for the Testsigma AI Engineer take-home assignment. Written so that an LLM building v2 understands every failure mode before writing a single line of code.

---

## Verdict Summary

| Dimension | Score | Verdict |
|---|:---:|---|
| Structural completeness | 6/10 | Phases exist but are not self-contained enough for LLM execution |
| Code correctness | 4/10 | Several snippets have outright bugs or fabricated APIs |
| LLM-followability | 4/10 | Too much ambiguity, too many `# VERIFY` comments, missing glue |
| Scope honesty | 8/10 | Cuts are named; rationale is mostly good |
| Assignment alignment | 7/10 | Hits the spirit; misses some explicit criteria |
| Dependency hygiene | 3/10 | Version pins are aspirational; several packages don't exist as pinned |

**The core problem:** v1 reads as a design memo written by a human who understands the full system, not as an execution script an LLM can follow without a human co-pilot. An LLM following it literally will hit ambiguous imports, broken API calls, incomplete glue code, and missing files on every phase. v2 must be a complete recipe, not a sketch with confidence.

---

## Section 1: Structural Issues

### 1.1 Phases Are Not Self-Contained

Every phase says "Create these files" but then provides only partial code snippets. A typical phase shows 60–80% of the module's code; the rest is implied by vague prose. An LLM filling in the gaps will do so inconsistently across phases.

**Specific gaps:**
- Phase 1 defines `static.py` and `dynamic.py` but `artifacts.py` is described in two sentences with no code. The `manifest.json` format is never specified.
- Phase 2 shows `docling_ingest.py` but `requirements.py` and `__init__.py` have zero code. The `ingest_prd.py` script is not written.
- Phase 3 shows `code/pr.py` and `code/index.py` but `__init__.py`, `scripts/index_repo.py`, and `scripts/inspect_pr.py` are not provided.
- Phase 4's `graph/load.py` is listed in "Create:" but contains zero code.
- Phase 5's `reason/impact.py` is listed but contains zero code.
- Phase 6's Jinja template (`templates/report.html.j2`) is referenced but not included.

**Fix for v2:** Every file listed under "Create:" must have its complete content — or, if partial, must state exactly what the LLM must add and why.

### 1.2 Missing Global Entrypoint / Pipeline Orchestration

d2's `pipeline/offline.py` and `pipeline/online.py` were clear end-to-end runners. v1 has `scripts/crawl.py`, `scripts/ingest_prd.py`, etc., but no single script that orchestrates all phases. An evaluator following the README will not know the correct invocation order. The `run_offline_pipeline()` and `run_online_pipeline()` equivalents are absent.

**Fix for v2:** Add a `scripts/run_pipeline.py --phase all` that calls phases 0–6 in order, with clear `--skip-phase N` flags for retrying.

### 1.3 The `data/` Directory Structure Is Underspecified

Multiple phases write to `data/crawl/`, `data/requirements/`, `data/code/`, `data/reports/` — but the directory tree is never formally specified. When Phase 5 tries to load Phase 3's output with `json.load(open('data/code/call_graph.json'))`, an LLM won't know if that file was created by `scripts/index_repo.py` or `scripts/inspect_pr.py`, or what its exact schema is.

**Fix for v2:** Provide a full `data/` directory tree in Phase 0 with file names, owners (which script creates them), and JSON schemas for every inter-phase artifact.

### 1.4 Branch Strategy Adds Complexity Without Benefit for LLMs

The document enforces a branch-per-phase git strategy (`feature/phase-1-crawler`, `feature/phase-2-prd-ingest`, etc.). For a human team, this is sensible. For an LLM executing sequentially, it creates unnecessary friction: the LLM must track which branch it's on, merge conditions, and whether `main` is up to date. An LLM that misses a merge will silently build on a stale branch.

**Fix for v2:** Either remove the branch strategy entirely (a single `main` branch with phases executed sequentially is fine for a 16-hour assignment) or add an explicit `git` command block at the start and end of every phase.

---

## Section 2: Code Bugs and Fabricated APIs

This is the most critical section. Several code snippets will not run as written.

### 2.1 `crawl4ai` API Mismatch

```python
# v1 Phase 1 — static.py
async with AsyncWebCrawler(config=config) as crawler:
    results = await crawler.arun_many(urls, cache_mode=CacheMode.BYPASS)
```

`crawl4ai==0.7.7` does not have `AsyncWebCrawler(config=BrowserConfig(...))` as its constructor signature. In current crawl4ai (0.4.x–0.6.x lineage), the crawler is constructed with keyword arguments directly, not a `BrowserConfig` object. `arun_many` exists but its signature and return type have changed across minor versions. `CacheMode.BYPASS` may not exist under that exact import path.

**Fix for v2:** Pin a specific version, run `pip install crawl4ai==X.Y.Z`, then read the actual `AsyncWebCrawler.__init__` signature and `CrawlResult` fields and reproduce them verbatim in the guide.

### 2.2 `browser-use` API Is Marked `# VERIFY` But Code Is Still Wrong

```python
# v1 Phase 1 — dynamic.py
from browser_use import Agent, BrowserSession
session = BrowserSession()
agent = Agent(task=task, llm=llm, browser_session=session)
```

The `# VERIFY: check current browser-use README` comment is honest, but the code is still presented as if it will work. `BrowserSession` is not the current constructor name in browser-use 0.12.x; it uses `Browser` and `BrowserConfig`. More critically, the `llm` parameter is typed as `object` — the guide never shows how to construct the LLM provider, which is a non-trivial setup step in browser-use.

**Fix for v2:** Either commit to a specific browser-use version and provide the correct constructor, or replace browser-use with a plain Playwright script for the dynamic flow (simpler, more reproducible, no LLM dependency for crawling). Browser-use is great for exploration but its API instability is a real risk in a 16-hour build.

### 2.3 `ast-grep` JSON Output Format Is Assumed, Not Verified

```python
# v1 Phase 3 — index.py
p = subprocess.run(["sg", "scan", "--rule", "rules/typescript-functions.yml",
                    str(repo), "--json=stream"], ...)
rows = [json.loads(line) for line in p.stdout.splitlines() if line.strip()]
```

`ast-grep` CLI (`sg`) does not use `--json=stream` as a flag. The correct flag is `--json` (outputs a JSON array to stdout) or `--json-format=...` depending on version. The streaming NDJSON format is not the default. The guide says "parse ast-grep JSON location fields after verifying the installed `sg --help` output" — but an LLM cannot do that without running the tool. This will fail at import time for an LLM that doesn't check.

Additionally, `function_id = repo_relative_path + ':' + start_line + ':' + name` is a custom format that must be constructed from ast-grep's actual output fields (`range.start.line`, `text`, `metaVariables`). The guide never shows the actual ast-grep JSON structure.

**Fix for v2:** Run `sg scan --rule rules/typescript-functions.yml . --json | head -5` and include the actual output in the guide. Write the parsing code from that real output, not from imagination.

### 2.4 Splink API Is Wrong for Version 4.x

```python
# v1 Phase 4 — resolve.py
from splink import DuckDBAPI, Linker, SettingsCreator, block_on
import splink.comparison_library as cl

settings = SettingsCreator(link_type="link_only", unique_id_column_name="id",
  source_dataset_column_name="dataset",
  comparisons=[cl.JaroAtThresholds("label", [0.85, 0.95])],
  blocking_rules_to_generate_predictions=[block_on("label")])
linker = Linker([left, right], settings, db_api=DuckDBAPI())
return linker.inference.deterministic_link().as_pandas_dataframe()
```

In Splink 4.x:
- `SettingsCreator` is the correct class, but `source_dataset_column_name` is not a parameter; it's inferred from `link_type="link_only"` when multiple DataFrames are passed.
- `cl.JaroAtThresholds` does not exist in Splink 4.x. The correct name is `cl.jaro_at_thresholds` (lowercase function, not class).
- `linker.inference.deterministic_link()` is not the correct path; it's `linker.predict(threshold_match_probability=0.85)` for probabilistic linking.
- `block_on("label")` blocks on exact label values — for requirement text vs. function IDs, this will return near-zero candidate pairs.

This code will raise an `AttributeError` on the first run.

**Fix for v2:** Either drop Splink entirely and use a simple cosine similarity + LLM reranker (simpler, works), or write the Splink code against its actual 4.x API after reading the official quickstart.

### 2.5 PPR Direction Is Inverted

```python
# v1 Phase 5 — ppr.py
return nx.pagerank(graph.reverse(copy=False), alpha=0.85, personalization=personalization, ...)
```

The guide says "code→UI→requirement" is the edge direction, which means the graph already flows from code to requirements. PPR on the **reversed** graph would route from requirements back to code — i.e., finding what code is relevant to a given requirement, not which requirements are affected by code changes. For blast radius (code change → downstream impact), the graph should **not** be reversed. PageRank on the forward graph, personalized to seed code nodes, propagates activation downstream to UI and requirements, which is the correct direction.

**Fix for v2:** Remove `graph.reverse()`. Use forward graph direction. Add a comment explicitly stating the semantic: "seed at changed code nodes; activation flows toward requirements."

### 2.6 `evidence_path` Will Silently Fail for Disconnected Nodes

```python
# v1 Phase 5 — evidence.py
def evidence_path(g: nx.DiGraph, seed: str, target: str) -> list[str]:
    path = nx.shortest_path(g, seed, target, weight=lambda u,v,d: 1/d.get("weight",1.0))
    if len(path) > 7: raise RuntimeError("evidence path exceeded six-hop cap")
    return path
```

`nx.shortest_path` raises `nx.NetworkXNoPath` when no path exists between `seed` and `target`. This exception is not caught, so any requirement with no code path will crash the entire reasoning phase. For a demo where graph coverage is sparse (as acknowledged in the scope decisions), this will happen frequently.

Additionally, the weight lambda `1/d.get("weight", 1.0)` inverts the weight, which is correct for "lower weight = shorter path" in Dijkstra. But `nx.shortest_path` without `method=` uses BFS when weight is a callable — it ignores the callable entirely. You need `nx.shortest_path(g, seed, target, method='dijkstra', weight=weight_fn)` for weighted shortest paths.

**Fix for v2:** Wrap in `try/except nx.NetworkXNoPath` and return `[]` (which the caller treats as a dark change). Fix the `method=` argument.

### 2.7 Neo4j UPSERT Query Is Label-Agnostic (and Therefore Wrong)

```python
# v1 Phase 4 — schema.py
UPSERT = """MERGE (a {id:$from_id}) MERGE (b {id:$to_id})
MERGE (a)-[r:%s]->(b) SET r.confidence=..."""
```

`MERGE (a {id:$from_id})` without a label will match any node with that ID, regardless of label. If a `Requirement` and a `CodeFunction` share the same `id` value (possible with hash collisions or poor ID design), this query will create incorrect edges. Neo4j best practice is `MERGE (a:Requirement {id:$from_id})`.

More critically, `%s` string formatting into Cypher is a SQL-injection-style vulnerability and won't work with the Neo4j Python driver's parameterized query mechanism. Use separate typed MERGE functions per edge type.

**Fix for v2:** Write one explicit Cypher function per edge type with typed labels. Never format edge type names via `%s`.

### 2.8 `requirements_from_markdown` Heuristic Will Produce Garbage

```python
# v1 Phase 2 — docling_ingest.py
for line_no, line in enumerate(markdown.splitlines(), 1):
    if line.startswith(("#", "- ", "* ")) and len(line.strip("# -*")) > 12:
        text = line.strip("# -*")
        out.append(Requirement(...))
```

The Cypress RWA README's headings and bullet points include things like "Install dependencies", "Start the server", and "npm install". These are not product requirements. The heuristic will extract dozens of operational notes as `Requirement` nodes with high confidence. The downstream graph will be polluted with fake requirements, and `ABSENT_FROM` edges will be created for operational instructions nobody intends to test.

This is also a good example of a case where an LLM caller (Claude) should extract requirements, not a line-prefix heuristic.

**Fix for v2:** Use an LLM extraction step for all requirement parsing. The heuristic is not adequate for a real README. Provide a specific system prompt and a JSON schema the LLM must return. Include a validation step that rejects any requirement whose text is an imperative command (install, run, cd, npm, git).

### 2.9 `Settings` Dataclass Will Crash at Import if `NEO4J_PASSWORD` is Unset

```python
# v1 Phase 0 — config.py
neo4j_password: str = os.environ["NEO4J_PASSWORD"]
```

A `@dataclass(frozen=True)` with `os.environ["NEO4J_PASSWORD"]` as a default value executes `os.environ["NEO4J_PASSWORD"]` at class definition time, before any instance is created. If the variable is missing, the module import raises `KeyError` before `load_dotenv()` has had a chance to run (because `load_dotenv()` is called at module level before the class, but only if the import order is correct). More critically, this pattern makes the `Settings` class impossible to unit test without setting the environment variable.

**Fix for v2:** Use `pydantic-settings` `BaseSettings`, which handles env loading, type coercion, and missing-value errors cleanly and testably.

---

## Section 3: Assignment Alignment Gaps

### 3.1 The Chosen PR Is Too Trivial to Demonstrate Anything

PR #1436 ("fix: update cypress logo on login page") changes a logo image file. This PR:
- Likely has zero TypeScript function changes (it's a static asset swap)
- Will produce an empty `call_graph.json` seed set from `ast-grep`
- Will generate a blast radius report that essentially says "the login page logo changed"
- Will not exercise the Requirements → UI → Code propagation chain at all

This is a "safe" choice that makes the system look like it works while demonstrating nothing impressive. A panel of senior engineers will see through it immediately.

**Fix for v2:** Choose a PR that changes actual TypeScript business logic — something touching `src/`, modifying a service or API handler, with at least 2–3 changed functions. Good candidates in the RWA repo are PRs that touch `src/app.ts`, `src/database.ts`, or any file in `src/models/`. This makes the blast radius non-trivial and the report actually interesting.

### 3.2 The `GapNode` Absence Model Is Weaker Than Required

The assignment explicitly asks: "how do you model absence — the requirements that should be testable but aren't reflected anywhere in the captured UI?" v1's answer is a `GapNode` that's created when a requirement has no outgoing `IMPLEMENTS` edge at confidence ≥ 0.60. This is technically correct but has two problems:

1. It's a **threshold-dependent artifact**, not a structural schema decision. Change the threshold and gaps appear or disappear. The assignment wants absence to be a first-class fact, not a side effect of confidence filtering.
2. `ABSENT_FROM` pointing to `GapNode` is circular: a gap node only exists because there's no coverage. It doesn't add information. A cleaner model is a `coverage_status` property on `Requirement` with an indexed query — as specified in `d4_blast_radius_analyzer_reference.md` §8.3.

**Fix for v2:** Model absence as a `coverage_status: "MISSING" | "PARTIAL" | "FULL"` property on `Requirement` nodes, set deterministically after the graph is built. Keep `GapNode` only as an optional explanatory artifact. Add the Cypher query that finds missing requirements and include it in the design document verbatim.

### 3.3 The Design Document (Phase 7) Is a Scaffold, Not a Document

Phase 7 says "Populate the design document with ten numbered answers" but provides no content. An LLM executing Phase 7 will write placeholder text because it has nothing to synthesize from. The design document is worth 50% of the assignment score (per the assignment brief's own framing), and v1 budgets only 1.25 hours for it.

**Fix for v2:** Write the design document scaffold with section headers, specific questions to answer per section, and explicit pointers to which phase's artifacts provide the evidence. Example: "Section 6 (Schema): copy the SCHEMA constants from `graph/schema.py` and the absence query from `graph/queries.py` and explain why each node/edge type was chosen."

### 3.4 No Sample Blast Radius Report in the Document

The assignment requires "a blast radius report for a real PR you select, in the form a non-engineer QA lead would actually read" as a separate deliverable. v1 generates a report via Phase 5/6 but never shows what a good one looks like. An LLM building the reporter won't know whether its output meets the bar.

**Fix for v2:** Include a complete sample blast radius report (realistic fake data for PR #XXXX) in the guide. The LLM's generated report should match this structure section by section.

### 3.5 Confidence Handling Under Ambiguity Is Underspecified

Assignment criterion 7 asks: "when the agent isn't sure (the PRD describes a feature you can't find in the UI; the code change touches a function you can't map to a UI element), what happens?" v1 answers this structurally (dark change → manual review item) but doesn't specify what the agent actually does: does it stop and ask a human? Does it log a warning and continue? Does it escalate to the OpenHands ACI?

The OpenHands integration is described as "architecture only" — which means this criterion is essentially answered with "we didn't implement it."

**Fix for v2:** Be explicit: "When confidence < 0.40, the system writes a `manual_review_item` with the unresolved node, the evidence fragments found, and a recommended human action. No LLM inference is made. The report marks this section with ⚠️. OpenHands integration is deferred to Week 2." Then implement that behavior in `impact.py`.

---

## Section 4: Dependency and Infrastructure Issues

### 4.1 Version Pins Are Fabricated or Unverified

| Package | Pinned version in v1 | Status |
|---|---|---|
| `crawl4ai==0.7.7` | Does not exist as of mid-2025 (latest is 0.4.x–0.5.x range) | ❌ Fabricated |
| `browser-use==0.12.1` | Plausible but unverified | ⚠️ Unverified |
| `docling==2.65.0` | Implausible (Docling is in 2.x but not 2.65) | ❌ Likely fabricated |
| `ast-grep==0.39.6` | ast-grep is a CLI tool, not a pip package. Install via `cargo install ast-grep` or `brew install ast-grep` | ❌ Wrong install method |
| `lightrag-hku==1.4.9.9` | Implausible version format | ❌ Likely fabricated |
| `splink==4.0.11` | Plausible but unverified | ⚠️ Unverified |

The document acknowledges this risk ("run `pip index versions` before committing") but an LLM following it cannot do so without a live environment. The result: when an LLM writes `requirements.txt` from v1, it will write broken pins that cause `pip install` to fail immediately.

**Fix for v2:** Provide exact, verified versions or use `>=X.Y` lower bounds with `<X+1` upper bounds. For `ast-grep`, remove it from `requirements.txt` entirely and add an explicit "system dependency" section with Homebrew/apt/cargo install commands.

### 4.2 PostgreSQL + pgvector Is in `docker-compose.yml` But Never Used

Phase 0 spins up a Postgres container with pgvector. Phase 4 mentions LightRAG's PostgreSQL backend as "optional." No phase ever writes to or reads from the Postgres container. It's dead infrastructure in the docker-compose that:
- Consumes RAM/disk on the developer's machine
- Adds a `POSTGRES_PASSWORD` env var that's required but useless
- Confuses an LLM about which database is the source of truth

**Fix for v2:** Remove the Postgres service from `docker-compose.yml` for v1. Add it back in the "Week 2" section under the LightRAG integration story.

### 4.3 APOC Plugin in Neo4j Is Required But Not Explained

```yaml
# docker-compose.yml
NEO4J_PLUGINS: '["apoc"]'
```

APOC is listed in the Neo4j environment but `apoc.path.subgraphAll` or other APOC procedures are never used in the Phase 5 code (which uses NetworkX's PPR, not Neo4j's). If APOC is not needed, don't include it — it slows Neo4j startup and causes warnings. If it is needed (e.g., for subgraph traversal in Phase 4's queries), the guide must show where.

**Fix for v2:** Either use APOC in a Phase 4 traversal query (and show the Cypher), or remove the plugin line.

### 4.4 RWA Local Setup Is Non-Trivial and Under-documented

Phase 1 says "Start the public RWA repository at its pinned SHA according to its README before crawling." RWA requires Node.js 14+, `npm install`, a local SQLite database setup, and `npm run start`. For a developer who hasn't done this, "according to its README" is not enough. More importantly, the RWA development server on `localhost:3000` serves a SPA — Crawl4AI's static HTML crawler will get a nearly-empty HTML shell with a `<div id="root"></div>`, not rendered content.

This is a critical architectural mismatch: crawl4ai is optimized for multi-page static sites, not SPA routes that render via JavaScript. The guide mentions this risk briefly in the SPA BFS note but doesn't resolve it.

**Fix for v2:** Add an explicit RWA setup block in Phase 0 with exact commands (pinned Node version, `nvm use 14`, `npm ci`, `npm run start`, health check URL). For the SPA crawling problem, commit to browser-use or Playwright exclusively for RWA — not Crawl4AI static mode, which will return empty pages.

---

## Section 5: LLM-Followability Issues

### 5.1 Too Many `# VERIFY` Comments Without Resolution

v1 uses `# VERIFY: check current API` in three locations (browser-use, LightRAG, Docling traversal API). These comments are honest but useless to an LLM. An LLM cannot visit a GitHub repo, run `--help`, or execute code to verify. It will either:
a) Ignore the comment and use the code as written (which may be wrong), or
b) Hallucinate the correct API from training data (which may be outdated)

**Fix for v2:** Before writing the guide, actually run each library with its pinned version and record the working code. Replace every `# VERIFY` with confirmed working code. If you cannot verify (because the library is too new), state "this phase requires manual verification before LLM execution" and move it to a "week 2" section.

### 5.2 Inter-Phase Data Contracts Are Not Machine-Readable

Phase 5 loads `data/code/call_graph.json` and `data/requirements/requirements.json`. Phase 6 loads `data/reports/blast_radius_report.json`. But the schemas for these files are scattered across code snippets in different phases. An LLM implementing Phase 5 has no guarantee that Phase 3's output matches what Phase 5 expects.

**Fix for v2:** Define all inter-phase artifacts as Pydantic models in `src/blast_radius/models.py` (Phase 0) and reference them by name in every phase. Each phase's `artifacts.py` serializes a `List[PydanticModel]`; each phase's loader deserializes it. This makes mismatches a validation error, not a silent wrong result.

### 5.3 Smoke Tests Don't Catch the Right Failures

The smoke tests check for non-empty lists and correct JSON structure. They don't check:
- Are the requirements semantically valid (not just syntactically)?
- Do the cross-layer links make domain sense?
- Is the blast radius report non-trivially different from "everything changed"?

Example: Phase 2's smoke test checks `len(x) >= 5` requirements. But if the heuristic extracts 50 operational README lines as requirements, the test passes while the data is garbage.

**Fix for v2:** Add assertion-based spot checks: "At least one requirement must contain the word 'transaction' or 'transfer' or 'payment' for the RWA domain." Add a schema validation step that uses the Pydantic models. Make smoke tests domain-aware, not just shape-aware.

### 5.4 The Jinja Template Is a Black Box

Phase 6 uses `templates/report.html.j2` but never provides the template. An LLM will invent a template that may not match the report schema from Phase 5. The smoke test checks for four string literals in the HTML but doesn't check that evidence paths are rendered or that confidence thresholds are displayed correctly.

**Fix for v2:** Provide the complete Jinja template in the guide. It should be a literal section: "Create the file `templates/report.html.j2` with this exact content: [...]"

---

## Section 6: What v1 Gets Right (Don't Throw Away)

1. **Target application choice is correct.** Cypress RWA is the right app — TypeScript, good PR history, known domain.
2. **The four-level confidence model** (HIGH ≥ 0.70, MEDIUM ≥ 0.40, LOW < 0.40, DARK_CHANGE) is well-designed and should be kept verbatim.
3. **Separation of deterministic vs. LLM-driven components** is correctly articulated and should drive the design document's agent decomposition section.
4. **The PPR weight schema** (`CALLS=1.0`, `RENDERS=0.95`, `IMPLEMENTS=0.85`, `COVERS=0.75`) is principled and should be kept.
5. **The `run_id` on every edge** is an excellent audit/reproducibility design that most implementations miss.
6. **Scope decisions are honest.** The Joern deferral, GraphRAG deferral, and OpenHands "architecture only" are all defensible and should be stated exactly as v1 states them.
7. **The phase-based structure** is the right mental model. Keep it, fix the execution gaps.
8. **The merge SHA pinning advice** for PR #1436 is correct practice that v2 should keep.

---

## Section 7: Prioritized Fixes for v2

Listed in the order an LLM building v2 should address them.

### P0 — Blockers (the guide cannot be followed without these)

1. **Replace all fabricated version pins** with verified ones or `>=X.Y,<X+1` ranges. Run `pip index versions` for every package and record the real latest. For `ast-grep`, document it as a system binary.
2. **Fix the `crawl4ai` API** by reading the actual installed version's source and providing the correct constructor and method signatures.
3. **Fix or replace the Splink code** — either use the correct Splink 4.x API or replace with a simpler cosine similarity + threshold approach.
4. **Fix the PPR direction** — remove `graph.reverse()`.
5. **Choose a non-trivial PR** that actually changes TypeScript business logic.
6. **Complete all missing files** — every file in "Create:" must have complete code.

### P1 — High Priority (will cause wrong output without these)

7. **Replace the requirements extraction heuristic** with an LLM call + validation.
8. **Fix `evidence_path`** to catch `NetworkXNoPath` and fix the weighted shortest-path API.
9. **Fix the Neo4j UPSERT** to include typed labels and remove `%s` formatting.
10. **Add `run_pipeline.py`** as a single end-to-end orchestrator.
11. **Specify all JSON schemas** for inter-phase artifacts in `models.py`.

### P2 — Medium Priority (quality and assignment score)

12. **Write a concrete sample blast radius report** so the reporter has a target.
13. **Specify the confidence-under-ambiguity behavior** in code, not just prose.
14. **Remove the Postgres service** from `docker-compose.yml`.
15. **Fix the APOC dependency** — use it or remove it.
16. **Add domain-aware assertions** to all smoke tests.
17. **Provide the complete Jinja template** for Phase 6.

### P3 — Nice-to-Have

18. **Simplify the git branch strategy** for LLM execution.
19. **Add a `validate_env.py` script** that checks all dependencies before Phase 1.
20. **Add an RWA setup section** in Phase 0 with exact Node.js commands.

---

## Suggested v2 Document Structure

```
# Blast Radius Analyzer — v2 Implementation Guide

## 0. Pre-flight Checklist (new)
   - Environment validation script
   - Verified package versions (actually tested)
   - RWA setup commands
   - Neo4j health check

## 1. Data Contracts (new — formerly scattered)
   - All Pydantic models for inter-phase artifacts
   - JSON schemas with examples

## 2. Phase 0: Project Skeleton
   (unchanged structure, fixed config.py, removed Postgres)

## 3. Phase 1: Crawler
   (Playwright-only for RWA SPA; browser-use with verified API)

## 4. Phase 2: PRD Ingest
   (LLM-based extraction replacing heuristic; complete requirements.py)

## 5. Phase 3: Code Analysis
   (fixed ast-grep invocation with real output example; fixed pr.py)

## 6. Phase 4: Knowledge Graph
   (typed Cypher upserts; fixed Splink or replaced; coverage_status model)

## 7. Phase 5: Blast Radius Reasoning
   (fixed PPR direction; fixed evidence_path; dark change handling)

## 8. Phase 6: Report
   (complete Jinja template; sample output included)

## 9. Phase 7: Design Document
   (pre-filled section outlines pointing to real artifact paths)

## 10. run_pipeline.py (new)
   (single orchestrator with --phase flags)

## Appendix A: Sample Blast Radius Report
   (what the output should look like for a real PR)

## Appendix B: Week 2 Roadmap
   (Joern, pr-agent webhook, Splink training — currently in scope decisions)
```

---

*Audit completed against: `v1_implementation_guide.md`, `d0_AI_Engineer_Updated_-_Assignment.md`, `d2_CODING_CONTEXT_v1.md`, `d4_blast_radius_analyzer_reference.md`, `d12_Ultimate_Application_Selection_Guide_Testsigma.md`.*
