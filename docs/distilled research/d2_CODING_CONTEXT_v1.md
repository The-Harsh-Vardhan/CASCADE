# Blast Radius Analyzer — LLM Coding Context Document

> **How to use this document:**
> Paste the relevant section (plus the Global Context block) into your LLM of choice and say
> *"Implement this module exactly as specified."*
> Each module section is self-contained. Build them in the order listed.
> After each module, run the smoke test listed at the bottom of that section before moving on.

---

## 0. Global Context (paste with EVERY prompt)

### What we are building

An AI-powered **Blast Radius Analyzer** that:
1. **Crawls** a live web application (target: **Hoppscotch** — `https://hoppscotch.io`)
2. **Ingests** Hoppscotch's public documentation/README as structured requirements
3. **Builds** a Neo4j knowledge graph across 3 layers: Requirements → UI → Code
4. **Reasons** over a real Hoppscotch Pull Request to produce a human-readable blast radius report

### Target application

| Property | Value |
|---|---|
| App | Hoppscotch |
| URL | https://hoppscotch.io |
| GitHub Repo | https://github.com/hoppscotch/hoppscotch |
| Docs | https://docs.hoppscotch.io |
| Language | TypeScript / Vue 3 |
| Why chosen | Public, crawlable without auth, rich GitHub history, clear feature set |

### Tech stack

| Component | Technology |
|---|---|
| Language | Python 3.11+ |
| Browser automation | Playwright (sync API) + Claude claude-sonnet-4-6 for semantic understanding |
| Graph database | Neo4j 5.x (local Docker) |
| Graph client | neo4j-driver (Python) |
| LLM calls | Anthropic Python SDK (`anthropic`) |
| HTTP | httpx |
| HTML parsing | BeautifulSoup4 |
| Code parsing | tree-sitter (TypeScript grammar) |
| Config | python-dotenv |
| Output | Markdown + JSON |

### Project structure

```
blast-radius/
├── .env                        # API keys and config — never commit
├── requirements.txt
├── README.md
├── config.py                   # Centralized config — loads .env
├── graph/
│   ├── __init__.py
│   ├── driver.py               # Neo4j connection singleton
│   ├── schema.py               # Cypher: constraints + indexes
│   └── queries.py              # All Cypher queries as named functions
├── crawler/
│   ├── __init__.py
│   ├── browser.py              # Playwright session management
│   ├── page_agent.py           # LLM-driven page understanding
│   └── artifacts.py            # Saves crawl artifacts to disk
├── ingestor/
│   ├── __init__.py
│   ├── fetcher.py              # Downloads docs from GitHub/URL
│   └── parser.py               # LLM parses docs → structured requirements
├── repo_analyzer/
│   ├── __init__.py
│   ├── cloner.py               # git clone / GitHub API
│   └── extractor.py            # tree-sitter extracts functions, APIs, files
├── fusion/
│   ├── __init__.py
│   └── mapper.py               # LLM maps requirements ↔ UI ↔ Code
├── pr_analyzer/
│   ├── __init__.py
│   └── diff_parser.py          # Parses GitHub PR diff via API
├── retrieval/
│   ├── __init__.py
│   └── subgraph.py             # Confidence-aware graph traversal
├── reasoning/
│   ├── __init__.py
│   └── engine.py               # LLM reasons over retrieved subgraph
├── reporter/
│   ├── __init__.py
│   └── generator.py            # Produces Markdown blast radius report
├── pipeline/
│   ├── __init__.py
│   ├── offline.py              # Runs: crawl → ingest → repo → graph build
│   └── online.py               # Runs: PR → retrieve → reason → report
└── outputs/
    ├── crawl/                  # Screenshots + DOM dumps
    ├── requirements/           # Parsed requirements JSON
    ├── repo/                   # Extracted code entities JSON
    └── reports/                # Final blast radius reports
```

### .env file (user must create this)

```
ANTHROPIC_API_KEY=sk-ant-...
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
GITHUB_TOKEN=ghp_...           # Optional but recommended to avoid rate limits
TARGET_APP_URL=https://hoppscotch.io
TARGET_REPO=hoppscotch/hoppscotch
CRAWL_MAX_PAGES=20
CRAWL_TIMEOUT_MS=10000
```

### Graph schema (reference for all modules)

#### Node types

| Label | Key Properties | Description |
|---|---|---|
| `Requirement` | `id`, `title`, `description`, `source_file`, `req_type` | From PRD/docs ingestion |
| `Feature` | `id`, `name`, `description` | High-level feature grouping requirements |
| `Page` | `id`, `url`, `title`, `screenshot_path` | Discovered application pages |
| `UIComponent` | `id`, `page_id`, `type`, `label`, `selector`, `purpose` | Buttons, inputs, nav items, etc. |
| `UserFlow` | `id`, `name`, `description`, `steps` | Inferred multi-step interaction paths |
| `CodeFile` | `id`, `path`, `language`, `module` | Source files in the repository |
| `CodeFunction` | `id`, `name`, `file_id`, `signature`, `line_start`, `line_end` | Functions/methods |
| `APIEndpoint` | `id`, `method`, `path`, `handler_function` | REST/GraphQL endpoints |
| `AbsentRequirement` | `id`, `requirement_id`, `reason`, `confidence` | Requirements with no UI match |

#### Edge types

| Type | From → To | Properties |
|---|---|---|
| `IMPLEMENTS` | `UIComponent` → `Requirement` | `confidence`, `evidence`, `source` |
| `NAVIGATES_TO` | `Page` → `Page` | `via_element`, `trigger` |
| `CONTAINS` | `Page` → `UIComponent` | `position` |
| `PART_OF` | `Requirement` → `Feature` | — |
| `HANDLES` | `CodeFunction` → `APIEndpoint` | `confidence` |
| `RENDERS` | `CodeFile` → `Page` | `confidence`, `evidence` |
| `CALLS` | `CodeFunction` → `CodeFunction` | `call_type` |
| `AFFECTS` | `CodeFunction` → `UIComponent` | `confidence`, `evidence` |
| `BELONGS_TO` | `UserFlow` → `Page` | `step_order` |
| `COVERS` | `UserFlow` → `Requirement` | `confidence` |
| `MISSING_FROM` | `AbsentRequirement` → `Page` | `reason` |

#### Confidence levels

```python
CONFIDENCE_HIGH   = 0.85   # Auto-included in report
CONFIDENCE_MEDIUM = 0.60   # Included with warning flag
CONFIDENCE_LOW    = 0.35   # Flagged for manual review
```

All edges store: `confidence` (float), `evidence` (str), `source` (str), `verified_at` (ISO timestamp).

---

## Module 1 — config.py + requirements.txt

**Build this first. Every other module imports from here.**

### Prompt

```
You are building the Blast Radius Analyzer (see Global Context above).

Create two files:

### FILE 1: requirements.txt

Include these packages with pinned major versions:
- anthropic
- neo4j
- playwright
- beautifulsoup4
- httpx
- python-dotenv
- tree-sitter
- tree-sitter-typescript (if available as pip package, else note manual install)
- gitpython
- rich (for CLI progress output)
- pydantic (for data models)

### FILE 2: config.py

Create a Config class (singleton pattern via module-level instance) that:
- Loads all variables from .env using python-dotenv
- Exposes typed attributes for every key in the .env spec above
- Has sensible defaults where applicable
- Raises a clear error at startup if ANTHROPIC_API_KEY or NEO4J_URI is missing
- Has a method `validate()` that checks all required values and prints a status table using rich

The module should print nothing on import — only when validate() is called explicitly.
```

### Smoke test
```bash
python -c "from config import config; config.validate()"
```
Expected: Rich table showing all config values, no errors.

---

## Module 2 — graph/driver.py + graph/schema.py

**Neo4j connection and schema initialization.**

### Prompt

```
You are building the Blast Radius Analyzer (see Global Context above).

Create two files inside graph/:

### FILE 1: graph/driver.py

- Singleton Neo4j driver using neo4j-driver Python SDK
- get_driver() returns the single Driver instance
- get_session() context manager for transactions
- close_driver() for cleanup
- On first connection, log the Neo4j version using a simple query
- Handle connection errors with clear messages

### FILE 2: graph/schema.py

Create a function `initialize_schema(driver)` that runs these Cypher statements
to set up constraints and indexes for the graph schema defined in Global Context:

Constraints (uniqueness):
- Requirement.id
- Feature.id
- Page.id
- UIComponent.id
- UserFlow.id
- CodeFile.id
- CodeFunction.id
- APIEndpoint.id
- AbsentRequirement.id

Indexes (for fast lookup):
- Page.url
- UIComponent.type
- CodeFunction.name
- CodeFile.path

The function should be idempotent — safe to run multiple times.
Log each constraint/index created or skipped.
```

### Smoke test
```bash
python -c "
from graph.driver import get_driver
from graph.schema import initialize_schema
driver = get_driver()
initialize_schema(driver)
print('Schema OK')
"
```

---

## Module 3 — crawler/browser.py + crawler/page_agent.py + crawler/artifacts.py

**The autonomous browser crawler. This is the most complex module.**

### Prompt

```
You are building the Blast Radius Analyzer (see Global Context above).

Create three files inside crawler/:

### FILE 1: crawler/browser.py

Manages the Playwright browser session:
- launch_browser() → returns (playwright, browser, page) tuple
  - Uses Chromium, headless=True
  - Sets viewport 1280x900
  - Sets a realistic user agent
- close_browser(playwright, browser) for cleanup
- navigate(page, url, timeout_ms) → bool — navigates and waits for networkidle
- get_page_dom(page) → str — returns the cleaned HTML (remove script/style tags)
- get_page_screenshot(page, path) → saves PNG screenshot to outputs/crawl/

### FILE 2: crawler/page_agent.py

Uses Claude claude-sonnet-4-6 to semantically understand each page.

Define a dataclass `PageAnalysis` with:
- url: str
- title: str
- purpose: str  (one sentence: what does this page do?)
- ui_components: list[dict]  (each: type, label, selector_hint, purpose, is_interactive)
- outbound_links: list[str]
- user_flows: list[str]  (inferred flows this page participates in)
- screenshot_path: str

Define `analyze_page(page_html: str, url: str, screenshot_path: str) -> PageAnalysis`:
- Calls Claude claude-sonnet-4-6 with the page HTML (truncated to 8000 chars if needed)
- System prompt instructs Claude to respond ONLY with a JSON object matching PageAnalysis fields
- Parse the JSON response into a PageAnalysis instance
- On parse error, return a minimal PageAnalysis with purpose="parse_error"

### FILE 3: crawler/artifacts.py

Manages saving/loading crawl artifacts:
- save_page_analysis(analysis: PageAnalysis) → saves to outputs/crawl/{url_slug}.json
- save_crawl_summary(analyses: list[PageAnalysis]) → saves outputs/crawl/summary.json
- load_crawl_summary() → loads and returns existing summary if present
- url_to_slug(url: str) → str — converts URL to safe filename

### FILE 4: crawler/__init__.py

Define `crawl(start_url: str, max_pages: int) -> list[PageAnalysis]`:

This is the main crawl orchestration function:

1. Launch browser
2. Start with [start_url] in a queue, empty visited set
3. For each URL in queue (up to max_pages):
   a. Skip if already visited or not same domain
   b. Navigate to URL
   c. Take screenshot → outputs/crawl/
   d. Get DOM
   e. Call analyze_page() → PageAnalysis
   f. Save artifact
   g. Add outbound_links to queue
   h. Log progress with rich progress bar
4. Close browser
5. Save crawl summary
6. Return list[PageAnalysis]

Use BFS traversal. Skip URLs with file extensions (.pdf, .zip, etc).
Respect CRAWL_MAX_PAGES from config.
Add 1 second delay between pages to be polite.
```

### Smoke test
```bash
python -c "
from crawler import crawl
results = crawl('https://hoppscotch.io', max_pages=3)
print(f'Crawled {len(results)} pages')
for r in results:
    print(f'  {r.url} — {r.purpose}')
    print(f'  Components: {len(r.ui_components)}')
"
```

---

## Module 4 — ingestor/fetcher.py + ingestor/parser.py

**Downloads Hoppscotch docs and extracts structured requirements.**

### Prompt

```
You are building the Blast Radius Analyzer (see Global Context above).

The ingestion target is Hoppscotch's public documentation.
Sources to fetch:
1. https://raw.githubusercontent.com/hoppscotch/hoppscotch/main/README.md
2. https://docs.hoppscotch.io (crawl first 5 pages via httpx + BeautifulSoup)

### FILE 1: ingestor/fetcher.py

- fetch_github_readme(repo: str) → str  — fetches raw README via GitHub API
- fetch_url_as_text(url: str) → str  — fetches URL, strips HTML to plain text
- fetch_docs_pages(base_url: str, max_pages: int = 5) → list[str]  — fetches multiple doc pages
- All functions return empty string on failure (never raise) and log warnings

### FILE 2: ingestor/parser.py

Define a dataclass `Requirement` with:
- id: str  (stable — e.g. "REQ-001")
- title: str
- description: str
- req_type: str  ("feature" | "user_story" | "constraint" | "acceptance_criterion")
- source: str  (which doc it came from)
- acceptance_criteria: list[str]
- related_ui_keywords: list[str]  (e.g. ["send button", "request builder", "environment"])

Define `parse_requirements(text: str, source_name: str) -> list[Requirement]`:
- Calls Claude claude-sonnet-4-6
- System prompt: "You are a requirements analyst. Extract ALL product requirements, features,
  and user stories from this documentation. Return ONLY a JSON array of requirement objects
  with fields: id, title, description, req_type, acceptance_criteria, related_ui_keywords.
  Be exhaustive. Every distinct feature or capability should be a separate requirement."
- Parse response → list[Requirement]
- Assign stable IDs if not already present (REQ-001, REQ-002, ...)

Define `ingest(sources: list[str]) -> list[Requirement]`:
- Runs parse_requirements on each source text
- Deduplicates by title similarity (simple: if titles share >70% words, skip duplicate)
- Saves to outputs/requirements/requirements.json
- Returns combined list

### FILE 3: ingestor/__init__.py

Define `run_ingestion() -> list[Requirement]`:
- Fetch README + docs pages
- Run ingest() on combined text
- Print summary: "Extracted N requirements from M sources"
- Return requirements list
```

### Smoke test
```bash
python -c "
from ingestor import run_ingestion
reqs = run_ingestion()
print(f'Got {len(reqs)} requirements')
for r in reqs[:3]:
    print(f'  [{r.id}] {r.title}')
    print(f'  Keywords: {r.related_ui_keywords}')
"
```

---

## Module 5 — repo_analyzer/cloner.py + repo_analyzer/extractor.py

**Clones the Hoppscotch repo and extracts code entities.**

> **Scope decision explicitly stated in design doc:**
> Full tree-sitter AST parsing is scoped down. We extract: file list, function names via
> regex on TypeScript/Vue files, and API routes via pattern matching. This is honest and
> sufficient for the blast-radius demo.

### Prompt

```
You are building the Blast Radius Analyzer (see Global Context above).

IMPORTANT SCOPE DECISION: We are NOT doing full AST parsing.
We use targeted regex + pattern matching on TypeScript/Vue files.
This is explicitly documented as a scope decision.

### FILE 1: repo_analyzer/cloner.py

- clone_repo(repo: str, target_dir: str) → str  — sparse clones only src/ directory
  - Uses: git clone --depth 1 --filter=blob:none --sparse {github_url} {target_dir}
  - Then: git sparse-checkout set src packages/hoppscotch-common/src
  - Returns path to cloned directory
  - If already cloned, skip and return existing path
- get_changed_files_from_pr(repo: str, pr_number: int) → list[str]
  - Uses GitHub API: GET /repos/{repo}/pulls/{pr_number}/files
  - Returns list of changed file paths
  - Uses GITHUB_TOKEN from config if available

### FILE 2: repo_analyzer/extractor.py

Define dataclasses:
- CodeFile: id, path, language, module (inferred from path)
- CodeFunction: id, name, file_id, line_start, signature, purpose (LLM-inferred for key files)
- APIEndpoint: id, method, path_pattern, handler_file, handler_function

Define these extraction functions:

`extract_files(repo_dir: str) -> list[CodeFile]`:
- Walk repo_dir recursively
- Include .ts, .vue, .js files only
- Skip node_modules, dist, .git
- Infer module from directory path (e.g. "packages/hoppscotch-common/src/services" → "services")

`extract_functions(file: CodeFile, repo_dir: str) -> list[CodeFunction]`:
- Read file content
- Use regex to find: function declarations, arrow functions assigned to const, Vue component methods
- Pattern: `(export )?(async )?function (\w+)` and `const (\w+)\s*=\s*(async\s*)?\(`
- For files under 200 lines, call Claude to extract a one-line purpose for each function
- For larger files, set purpose = "see file"

`extract_api_endpoints(repo_dir: str) -> list[APIEndpoint]`:
- Search for files in routes/, api/, or containing "router" in name
- Pattern match for: app.get/post/put/delete, router.get/post/put/delete, defineEventHandler
- Extract method + path pattern + surrounding function name

`extract_all(repo_dir: str) -> dict`:
- Returns {"files": [...], "functions": [...], "endpoints": [...]}
- Saves to outputs/repo/repo_model.json

### FILE 3: repo_analyzer/__init__.py

Define `run_repo_analysis(repo: str) -> dict`:
- Clone repo → get repo_dir
- Run extract_all(repo_dir)
- Print summary table using rich
- Return the model dict
```

### Smoke test
```bash
python -c "
from repo_analyzer import run_repo_analysis
model = run_repo_analysis('hoppscotch/hoppscotch')
print(f'Files: {len(model[\"files\"])}')
print(f'Functions: {len(model[\"functions\"])}')
print(f'Endpoints: {len(model[\"endpoints\"])}')
"
```

---

## Module 6 — fusion/mapper.py

**The heart of the system. Maps requirements ↔ UI ↔ Code using LLM + heuristics.**

### Prompt

```
You are building the Blast Radius Analyzer (see Global Context above).

This module generates candidate relationships between the three graph layers.
It does NOT write to the graph — it returns candidates with evidence and confidence.

### FILE: fusion/mapper.py

Define a dataclass `RelationshipCandidate`:
- from_type: str  (node label)
- from_id: str
- to_type: str  (node label)
- to_id: str
- relationship_type: str  (edge label from schema)
- confidence: float  (0.0 to 1.0)
- evidence: str  (human-readable explanation of WHY this relationship exists)
- source: str  ("keyword_match" | "llm_semantic" | "url_pattern" | "filename_pattern")

---

### FUNCTION 1: map_requirements_to_ui

`map_requirements_to_ui(requirements, page_analyses) -> list[RelationshipCandidate]`

Strategy (in order — stop at first match per requirement):

1. **Keyword match** (confidence 0.75):
   For each requirement, check if any of its `related_ui_keywords` appear in
   any UIComponent's label or purpose (case-insensitive).
   If match found → candidate with source="keyword_match"

2. **LLM semantic match** (confidence 0.65):
   For requirements with no keyword match:
   Batch up to 10 requirements + all UIComponent labels/purposes into one Claude call.
   Prompt: "Given these requirements and UI components, identify which components
   implement which requirements. Return JSON array of {req_id, component_id, reason}."
   Parse response → candidates with source="llm_semantic"

3. **Absence detection**:
   Any requirement with zero candidates after both strategies →
   create an `AbsentRequirement` node candidate with:
   - reason = "No matching UI component found"
   - confidence = 1.0 (we are certain it's absent)

---

### FUNCTION 2: map_ui_to_code

`map_ui_to_code(page_analyses, code_model) -> list[RelationshipCandidate]`

Strategy:

1. **URL/filename pattern** (confidence 0.80):
   For each Page, find CodeFiles whose path contains words from the page URL.
   e.g. Page URL contains "graphql" → match files in graphql/ directory.

2. **Component-to-file matching** (confidence 0.70):
   For each UIComponent with type="form" or "button", look for .vue files
   whose filename matches the component's label words.

3. **LLM fallback for key pages** (confidence 0.55):
   For the top 5 most important pages (by component count), call Claude with
   page purpose + top 20 most relevant-sounding filenames.
   Ask: "Which files likely render or handle this page?"

---

### FUNCTION 3: run_fusion

`run_fusion(requirements, page_analyses, code_model) -> dict`:
- Call map_requirements_to_ui()
- Call map_ui_to_code()
- Print candidate summary: "N req→UI mappings, M UI→code mappings, K absent requirements"
- Save to outputs/requirements/fusion_candidates.json
- Return {"req_ui": [...], "ui_code": [...], "absent": [...]}
```

### Smoke test
```bash
python -c "
import json
from ingestor.parser import Requirement
# Load saved artifacts
with open('outputs/requirements/requirements.json') as f:
    reqs_data = json.load(f)
# ... load page analyses and repo model
# from fusion.mapper import run_fusion
# candidates = run_fusion(reqs, pages, code_model)
print('Fusion module imported OK')
from fusion.mapper import RelationshipCandidate
print('RelationshipCandidate OK')
"
```

---

## Module 7 — graph/queries.py + pipeline/offline.py

**Loads all artifacts into Neo4j and wires the graph.**

### Prompt

```
You are building the Blast Radius Analyzer (see Global Context above).

### FILE 1: graph/queries.py

All database writes as named functions. Each takes a neo4j session.

Node creation (MERGE to avoid duplicates):

`upsert_requirement(session, req: dict)` — MERGE on id, SET all properties
`upsert_feature(session, feature: dict)` — MERGE on id
`upsert_page(session, page: dict)` — MERGE on id
`upsert_ui_component(session, component: dict)` — MERGE on id
`upsert_user_flow(session, flow: dict)` — MERGE on id
`upsert_code_file(session, file: dict)` — MERGE on id
`upsert_code_function(session, function: dict)` — MERGE on id
`upsert_api_endpoint(session, endpoint: dict)` — MERGE on id
`upsert_absent_requirement(session, absent: dict)` — MERGE on id

Edge creation (MERGE to avoid duplicates):

`create_implements(session, component_id, req_id, confidence, evidence, source)`
`create_navigates_to(session, from_page_id, to_page_id, via_element)`
`create_contains(session, page_id, component_id)`
`create_renders(session, file_id, page_id, confidence, evidence)`
`create_affects(session, function_id, component_id, confidence, evidence)`
`create_missing_from(session, absent_req_id, page_id, reason)`

Every edge creation includes: verified_at = datetime.utcnow().isoformat()

Query functions (for retrieval):

`get_subgraph_for_files(session, file_paths: list[str]) -> dict`:
- Given a list of changed file paths, traverse:
  CodeFile → CodeFunction → UIComponent → Requirement
  CodeFile → Page → UserFlow
- Return all connected nodes and relationships
- Limit traversal to depth 3

`get_absent_requirements(session) -> list[dict]`:
- Return all AbsentRequirement nodes with their linked Requirement

`get_coverage_stats(session) -> dict`:
- Count nodes per label
- Count edges per type
- Return as dict for reporting

### FILE 2: pipeline/offline.py

`run_offline_pipeline()`:

This runs all 5 stages in order. Each stage is independently retryable.

```python
def run_offline_pipeline():
    console = Console()  # rich

    console.rule("[bold blue]Stage 1: Crawl")
    page_analyses = crawl(config.TARGET_APP_URL, config.CRAWL_MAX_PAGES)

    console.rule("[bold blue]Stage 2: Ingest Requirements")
    requirements = run_ingestion()

    console.rule("[bold blue]Stage 3: Analyze Repository")
    code_model = run_repo_analysis(config.TARGET_REPO)

    console.rule("[bold blue]Stage 4: Knowledge Fusion")
    candidates = run_fusion(requirements, page_analyses, code_model)

    console.rule("[bold blue]Stage 5: Build Graph")
    driver = get_driver()
    initialize_schema(driver)
    with driver.session() as session:
        # Write all nodes
        for req in requirements: upsert_requirement(session, ...)
        for page in page_analyses: upsert_page(session, ...)
        # ... all other node types
        # Write all edges from candidates
        for c in candidates["req_ui"]: create_implements(session, ...)
        for c in candidates["ui_code"]: create_renders(session, ...)
        for c in candidates["absent"]: upsert_absent_requirement(session, ...)
    
    stats = get_coverage_stats(session)
    console.print(f"[green]Graph built: {stats}")
```

Entry point: `if __name__ == "__main__": run_offline_pipeline()`
```

### Smoke test
```bash
python pipeline/offline.py
# Then in Neo4j browser: MATCH (n) RETURN labels(n), count(n)
# Expect: Requirement, Page, UIComponent, CodeFile nodes all present
```

---

## Module 8 — pr_analyzer/ + retrieval/ + reasoning/ + reporter/

**The online pipeline. Given a PR URL → blast radius report.**

### Prompt

```
You are building the Blast Radius Analyzer (see Global Context above).
The offline graph is already built. This module analyzes a new PR.

Target PR for demo: Use a real recent Hoppscotch PR from https://github.com/hoppscotch/hoppscotch/pulls

### FILE 1: pr_analyzer/diff_parser.py

`parse_pr(repo: str, pr_number: int) -> dict`:
- Call GitHub API: GET /repos/{repo}/pulls/{pr_number}  → PR metadata
- Call GitHub API: GET /repos/{repo}/pulls/{pr_number}/files → changed files
- Return:
  {
    "pr_number": int,
    "title": str,
    "description": str,
    "author": str,
    "changed_files": [{"filename": str, "status": str, "additions": int, "deletions": int, "patch": str}],
    "changed_functions": [],  # populated by extracting function names from patch hunks
    "summary": str  # one-line LLM summary of what this PR does
  }
- Extract changed function names from patch: lines starting with "+" that match function patterns
- Call Claude claude-sonnet-4-6 to summarize: "In one sentence, what does this PR change?"

### FILE 2: retrieval/subgraph.py

`retrieve_subgraph(driver, changed_files: list[str]) -> dict`:
- Call get_subgraph_for_files(session, changed_files)
- Filter edges below CONFIDENCE_LOW threshold (0.35) — exclude from reasoning context
- Structure result as:
  {
    "changed_files": [...],
    "affected_code_functions": [...],
    "affected_pages": [...],
    "affected_components": [...],
    "affected_requirements": [...],
    "absent_requirements": [...],
    "user_flows_at_risk": [...],
    "confidence_breakdown": {"high": N, "medium": N, "low": N}
  }
- Log: "Retrieved subgraph: N nodes, M edges"

### FILE 3: reasoning/engine.py

`reason_over_subgraph(pr_data: dict, subgraph: dict) -> dict`:

Build a structured context string (NOT the full graph — just the subgraph summary).
Call Claude claude-sonnet-4-6 with:

System prompt:
"You are a senior QA engineer and product analyst. You have been given:
1. A Pull Request summary and changed files
2. A product knowledge subgraph showing which UI elements, user flows, and requirements
   are connected to those changed files.

Analyze the blast radius of this PR. Be specific, evidence-based, and honest about uncertainty.
Return ONLY a JSON object with this structure:
{
  'risk_level': 'HIGH|MEDIUM|LOW',
  'risk_score': float (0-10),
  'executive_summary': str (2-3 sentences, non-technical),
  'affected_requirements': [{'id': str, 'title': str, 'risk_reason': str, 'confidence': float}],
  'affected_pages': [{'url': str, 'title': str, 'risk_reason': str}],
  'affected_user_flows': [{'name': str, 'impact': str}],
  'regression_recommendations': [str],
  'manual_review_items': [str],
  'missing_coverage': [str]
}"

Parse JSON response → return as dict.
On parse failure, return minimal dict with risk_level="UNKNOWN".

### FILE 4: reporter/generator.py

`generate_report(pr_data: dict, subgraph: dict, reasoning: dict) -> str`:

Generate a Markdown report with this EXACT structure:

```markdown
# Blast Radius Report

**Pull Request:** #{number} — {title}
**Repository:** {repo}
**Author:** {author}
**Analysis Date:** {date}
**Risk Level:** 🔴 HIGH / 🟡 MEDIUM / 🟢 LOW

---

## Executive Summary

{executive_summary}

---

## Changed Components

| File | Status | Changes |
|---|---|---|
| {filename} | Modified | +{additions} -{deletions} |

---

## Affected Requirements ({N} requirements at risk)

### 🔴 High Confidence
- **[REQ-001]** {title}
  - *Why:* {risk_reason}
  - *Evidence:* {evidence}
  - *Confidence:* {confidence}%

### 🟡 Medium Confidence
...

---

## Affected Pages

| Page | URL | Risk Reason |
|---|---|---|

---

## User Flows at Risk

{flow names and impact descriptions}

---

## ⚠️ Absent Requirements (No UI Coverage Found)

These requirements exist in documentation but have no corresponding UI elements in our graph.
They may be unimplemented features or areas needing manual verification:

- **[REQ-XXX]** {title}

---

## Regression Recommendations

1. {recommendation}
2. ...

---

## Items Requiring Manual Review

> The following findings have LOW confidence and should be verified by a human:

- {item}

---

## Coverage Statistics

| Layer | Count |
|---|---|
| Requirements analyzed | N |
| Pages checked | N |
| Code files traced | N |
| Absent requirements | N |

---

*Report generated by Blast Radius Analyzer v1.0*
*Graph evidence available in Neo4j — query: MATCH path=(f:CodeFile)-[*1..3]-(r:Requirement) WHERE f.path IN [{files}] RETURN path*
```

Save report to outputs/reports/pr_{number}_blast_radius.md
Also save JSON to outputs/reports/pr_{number}_blast_radius.json
Return the markdown string.

### FILE 5: pipeline/online.py

`run_online_pipeline(repo: str, pr_number: int)`:
- parse_pr(repo, pr_number)
- retrieve_subgraph(driver, changed_files)
- reason_over_subgraph(pr_data, subgraph)
- generate_report(pr_data, subgraph, reasoning)
- Print: "Report saved to outputs/reports/pr_{number}_blast_radius.md"

Entry point: 
```python
if __name__ == "__main__":
    import sys
    repo = sys.argv[1] if len(sys.argv) > 1 else config.TARGET_REPO
    pr_number = int(sys.argv[2]) if len(sys.argv) > 2 else 4200
    run_online_pipeline(repo, pr_number)
```
```

### Smoke test
```bash
python pipeline/online.py hoppscotch/hoppscotch 4200
# Expect: outputs/reports/pr_4200_blast_radius.md exists and is readable
cat outputs/reports/pr_4200_blast_radius.md
```

---

## Module 9 — README.md

### Prompt

```
Write a README.md for the Blast Radius Analyzer project.

It must include:
1. One-paragraph description of what the system does
2. Architecture diagram in ASCII showing: Crawl → Ingest → Repo → Graph → PR → Report
3. Prerequisites: Python 3.11+, Docker (for Neo4j), Playwright browsers
4. Setup instructions:
   a. Clone repo
   b. pip install -r requirements.txt
   c. playwright install chromium
   d. docker run --name neo4j -p7687:7687 -p7474:7474 -e NEO4J_AUTH=neo4j/password neo4j:5
   e. cp .env.example .env && fill in ANTHROPIC_API_KEY
5. Run offline pipeline: python pipeline/offline.py
6. Run online pipeline: python pipeline/online.py hoppscotch/hoppscotch {PR_NUMBER}
7. View graph: open http://localhost:7474 in browser
8. Scope decisions (honest): what was cut, what was implemented
9. Example output (blast radius report snippet)
```

---

## Build Order Summary

| Order | Module | Time Estimate | Dependency |
|---|---|---|---|
| 1 | config.py + requirements.txt | 15 min | None |
| 2 | graph/driver.py + schema.py | 20 min | Module 1 |
| 3 | crawler/ (all files) | 90 min | Module 1 |
| 4 | ingestor/ (all files) | 60 min | Module 1 |
| 5 | repo_analyzer/ (all files) | 60 min | Module 1 |
| 6 | fusion/mapper.py | 75 min | Modules 3,4,5 |
| 7 | graph/queries.py + pipeline/offline.py | 60 min | Modules 2,6 |
| 8 | pr_analyzer + retrieval + reasoning + reporter | 90 min | Module 7 |
| 9 | README.md | 20 min | All |
| **Total** | | **~8 hours coding** | |

---

## Debugging Tips for Common Failures

**Neo4j connection refused:**
```bash
docker ps  # check container is running
docker logs neo4j  # check for startup errors
```

**Playwright timeout on crawl:**
- Reduce CRAWL_MAX_PAGES to 5 in .env
- Add `page.wait_for_load_state("domcontentloaded")` instead of networkidle

**Claude JSON parse error:**
- Add `response_format` check: strip ```json fences before parsing
- Log raw LLM output before attempting parse

**Neo4j MERGE constraint violation:**
- Run `MATCH (n) DETACH DELETE n` in Neo4j browser to reset
- Re-run offline pipeline

**GitHub rate limit:**
- Set GITHUB_TOKEN in .env
- Add `time.sleep(1)` between API calls in repo_analyzer

---

## Scope Decisions (for Design Document)

These are your honest cuts. Reference these in Section 9 of your design doc.

| Decision | What was cut | Why | Impact |
|---|---|---|---|
| Code parsing | Full AST via tree-sitter → regex patterns | Time constraint | Lower precision on function-level mapping |
| Crawl depth | CRAWL_MAX_PAGES=20 | Hoppscotch is a SPA; 20 pages captures key flows | Acceptable for demo |
| Code layer | Only TypeScript/Vue files | Hoppscotch is TS-first | No coverage loss for this target |
| Auth crawling | No auth — crawl public pages only | Scope | Login-gated features not in graph |
| Historical PRs | Single PR analysis only | Time constraint | No trend analysis |
| Real-time sync | Manual pipeline trigger only | Out of scope for MVP | Documented as Phase 2 |
