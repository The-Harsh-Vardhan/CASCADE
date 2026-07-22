# Blast Radius Analyzer — v2 Implementation Guide: Critical Audit Report

> **Scope of this audit:** `v2_implementation_guide.md` evaluated against the original assignment brief (`d0`), the reference document (`d4`), the v1 audit (`v1_audit`), and the new Documenso target application. Written so an LLM building v3 understands every failure mode before writing a single line of code.

---

## Verdict Summary

| Dimension | v1 Score | v2 Score | Verdict |
|---|:---:|:---:|---|
| Structural completeness | 6/10 | 7/10 | Improved but still missing glue code |
| Code correctness | 4/10 | 7/10 | Most v1 bugs fixed; new bugs introduced |
| LLM-followability | 4/10 | 6/10 | Better, but target-mismatch is fatal |
| Scope honesty | 8/10 | 8/10 | Equally honest — good |
| Assignment alignment | 7/10 | 5/10 | **Documenso switch breaks everything** |
| Dependency hygiene | 3/10 | 7/10 | Verified bounds; ast-grep correctly separated |

**The core problem in v2:** The entire guide is written for the Cypress Real World App. You have asked to switch the target to Documenso (`https://app.documenso.com`). This is not a small config change — it invalidates crawl strategies, crawl credentials, code analysis patterns, PR selection, requirement sources, entity resolution prompts, domain spot-check assertions, and the sample report. v2 is otherwise meaningfully better than v1 on correctness, but it is unusable as-is for Documenso.

**The second-largest problem:** Several v1 bugs were fixed correctly, but two new bugs were introduced in the process, and three `# VERIFY` comments still survived from v1 in disguised form.

---

## Section 1: The Documenso Migration Gap (CRITICAL — Blocks Everything)

This is the most important section. Every item below must be resolved in v3 before any other work.

### 1.1 Target Application Mismatch

v2 opens with:
```
Target app: Cypress Real World App (RWA) — http://localhost:3000
```

Every subsequent decision cascades from this. Switching to Documenso means:

| Component | v2 (RWA) | v3 (Documenso) required |
|---|---|---|
| Target URL | `http://localhost:3000` | `https://app.documenso.com` |
| Repo | `cypress-io/cypress-realworld-app` | `documenso/documenso` |
| Language | TypeScript/React | **TypeScript/Next.js/Prisma/tRPC** |
| Auth for crawl | `data-test="signin-username"` (known) | Unknown — needs investigation |
| Domain keywords | `transaction`, `transfer`, `payment` | `document`, `recipient`, `signer`, `template`, `signing` |
| PR for demo | `#1421` (user settings) | Unknown — must be selected fresh |
| Requirement source | RWA README | `https://docs.documenso.com` + `https://github.com/documenso/documenso/blob/main/README.md` |
| ast-grep paths | `data/repos/rwa/src` | `data/repos/documenso/packages/` and `apps/` |

**Every hardcoded string in v2 is wrong for Documenso.** v3 must perform a systematic search-and-replace plus a deep rethink of several modules.

### 1.2 Crawl Strategy Must Change for Documenso

Documenso at `https://app.documenso.com` is a **live public SaaS with authentication**. This creates three new problems v2 doesn't address:

**Problem A — Auth wall.** Unlike RWA (which has known demo credentials in its public README), Documenso's live app requires a real account. The crawler must either: (a) use a created test account with credentials stored in `.env`, or (b) crawl only the unauthenticated marketing/login/signup pages. v3 must decide this explicitly. The v1 audit warned about auth-gated features not being in the graph — this is now the primary crawl surface.

**Problem B — No `data-test` attributes.** RWA has `data-test="signin-username"` attributes throughout. Documenso's production app almost certainly does not. The login flow in `dynamic.py` hardcodes these selectors and will fail silently. v3 must inspect the actual Documenso login page HTML and use correct selectors.

**Problem C — Public SaaS rate limits.** Crawling `https://app.documenso.com` aggressively may trigger rate limits or IP blocks. v2 has no rate limiting in the crawler. v3 must add polite delays and check the site's `robots.txt`.

**Recommendation for v3:** Define two crawl modes explicitly:
1. **Unauthenticated crawl**: marketing pages, signup flow, login page, docs — no credentials needed.
2. **Authenticated crawl**: full document lifecycle, template management, recipient flows — requires test account credentials in `.env`.

State which mode is used in the demo. The design document must acknowledge auth-gated features as absent from the graph.

### 1.3 Repository Structure for Documenso

Documenso is a **monorepo** with this structure:
```
packages/
  lib/              # core business logic
  prisma/           # Prisma schema and migrations
  trpc/             # tRPC router definitions
  ui/               # shared React components
apps/
  web/              # Next.js web app
  marketing/        # marketing site
```

This means:
- ast-grep must scan `packages/` AND `apps/web/` — not `src/` (which doesn't exist at the root level)
- The `ts-functions.yml` rule covers TypeScript, which is correct
- But **tRPC routers** are the API layer — not Express `router.get/post` patterns. v3 must add a tRPC-specific ast-grep rule
- **Prisma schema** (`schema.prisma`) is the data model layer — v3 should extract model names as `DataEntity` nodes in the graph to add a fourth graph layer or enrich the Code layer

**New ast-grep rule needed for v3:**
```yaml
id: trpc-procedures
language: TypeScript
rule:
  any:
    - pattern: $ROUTER.procedure.$METHOD($$$)
    - pattern: publicProcedure.$METHOD($$$)
    - pattern: protectedProcedure.$METHOD($$$)
```

### 1.4 PR Selection for Documenso

PR `#1421` from RWA is hardcoded throughout v2. For Documenso:
- Browse `https://github.com/documenso/documenso/pulls?q=is%3Apr+is%3Amerged`
- Filter for PRs that modify files in `packages/lib/` or `packages/trpc/` (business logic layer)
- Avoid PRs that only change `packages/ui/` (pure styling) — same reasoning as rejecting RWA's logo-swap PR
- Good candidates: PRs touching document signing flow, recipient notification, template management
- v3 must pin the merge SHA: `gh pr view {PR_NUMBER} --repo documenso/documenso --json mergeCommit`

### 1.5 Domain Spot-Check Assertions Are Wrong

The Phase 2 smoke test contains:
```python
banking_terms = {'transaction', 'transfer', 'payment', 'account', 'balance', 'contact'}
```

This will fail for Documenso. Replace with:
```python
documenso_terms = {'document', 'sign', 'recipient', 'template', 'field', 'certificate', 'sender', 'signer'}
```

The LLM extraction prompt in Phase 2 also says:
```
You are a requirements analyst for a banking web application (Cypress Real World App).
```
This must be replaced with a Documenso-specific prompt.

---

## Section 2: Code Bugs Introduced in v2

v2 fixed most v1 bugs. But it introduced some new ones, and left some v1 bugs in disguised form.

### 2.1 NEW BUG — `ast_node_type` extraction is broken

In `code/index.py`:
```python
ast_node_type=match.get("rule", {}).get("kind", "unknown"),
```

ast-grep's JSON output does not have a `rule.kind` field. The top-level keys are `text`, `range`, `file`, `lines`, `metaVariables`, and (in some versions) `ruleId`. There is no nested `rule` dict. This will silently set `ast_node_type="unknown"` for every function.

**Fix for v3:** Extract node type from the matched text using the existing regex logic, or drop `ast_node_type` from the smoke test assertion since it's not load-bearing. Alternatively use:
```python
ast_node_type=match.get("ruleId", "ts-functions"),
```

### 2.2 NEW BUG — `resolve_ui_to_functions` receives wrong type

In `graph/resolve.py`, the function signature is:
```python
def resolve_ui_to_functions(
    snapshots: list,        # list[PageSnapshot]
    functions: list[CodeFunction],
    ...
```
But `snapshots` has no type annotation, and the function accesses `snap.url_sha256` and `snap.url` — both `PageSnapshot` attributes. However, it also has:
```python
for item in snap.accessibility_tree:
```
...which is never actually used. The comment says "Match UIElement accessibility labels to CodeFunction file names" but the logic only uses `snap.url`. This is misleading and will confuse anyone debugging why the UI→code links are sparse.

More critically, the `ui_id` constructed inside the function:
```python
ui_id = f"ui:{snap.url_sha256}:page"
```
...is a single ID per page. But in `graph/writer.py`, UIElements are written with IDs like `f"ui:{snap.url_sha256}:{item.index}"`. The page-level `ui_id` will not match any node in the graph, so `CREATE_RENDERS` edges will silently fail (the MATCH clause will find nothing and MERGE will not create an edge, but won't raise an error).

**Fix for v3:** Either use the page node ID (`f"page:{snap.url_sha256}"`) in `RENDERS` links and update the schema to have `CodeFunction -[:RENDERS]-> Page` relationships, or iterate over `snap.accessibility_tree` and create one RENDERS link per UIElement with its correct ID. The latter is more granular and correct.

### 2.3 SURVIVING v1 BUG — `evidence_path` weight lambda is still broken

From v2's `reason/impact.py`:
```python
path = nx.shortest_path(
    graph,
    seed,
    target,
    method="dijkstra",
    weight=lambda u, v, d: 1.0 / max(d.get("weight", 1.0), 1e-6),
)
```

v2 correctly adds `method="dijkstra"`. But `nx.shortest_path` with `method="dijkstra"` does not accept a callable `weight` parameter — it accepts only a string (the name of the edge attribute). The callable form is for `nx.dijkstra_path`. This will raise `TypeError: 'function' object is not subscriptable` at runtime.

**Fix for v3:** Either use `nx.dijkstra_path(graph, seed, target, weight="weight")` (uses the pre-stored numeric weight) or use:
```python
nx.shortest_path(graph, seed, target, method="dijkstra", weight="weight")
```
...and ensure all edge weights are stored as numeric values (which they are in `build_projection`).

### 2.4 SURVIVING v1 BUG — `crawl4ai` import guard is wrong

From v2's `crawl/static.py`:
```python
try:
    from crawl4ai import AsyncWebCrawler
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False
```

The function then does:
```python
async def crawl_static_url(url: str) -> Optional[str]:
    if not CRAWL4AI_AVAILABLE:
        raise RuntimeError("crawl4ai is not installed...")
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url)
```

`crawl4ai` is in `requirements.txt` with `crawl4ai>=0.4.0,<1.0`. If it's installed (and it should be, per requirements.txt), the guard is useless. If it's NOT installed, the RuntimeError message says to install it — but the requirements.txt says it should already be there. This creates confusing error messages.

More importantly: `AsyncWebCrawler()` with no arguments uses whatever the current API default is. In `crawl4ai>=0.4.0`, the constructor may require different initialization. This is still a `# VERIFY` in disguise.

**Fix for v3:** Since `crawl4ai` is a declared dependency, remove the try/except guard. Pin a specific crawl4ai version and document the exact constructor call verified against that version. For Documenso's public docs pages, `crawl4ai` is actually appropriate (static content) — document this use case clearly.

### 2.5 NEW BUG — `run_crawl` is called incorrectly

In `crawl/__init__.py`:
```python
def run_crawl() -> list:
    ...
    snapshots = asyncio.run(
        run_dynamic_crawl(settings.target_url, settings.crawl_max_pages)
    )
```

But `scripts/run_pipeline.py` calls:
```python
from blast_radius.crawl import run_crawl
run_crawl()
```

The module declares `run_crawl() -> list` but `scripts/run_pipeline.py`'s `run_phase(1)` ignores the return value. This is fine. But the module docstring at the top of `crawl/__init__.py` says:
```python
from blast_radius.crawl import run_crawl
run_crawl()
```
...as the invocation. However, `if __name__ == "__main__"` is never set up in `crawl/__init__.py`. The smoke test says `python -m blast_radius.crawl` — but `__init__.py` has no `if __name__ == "__main__"` guard, so it will execute nothing when run as a module. The `run_crawl()` function must be explicitly called.

**Fix for v3:** Add to `crawl/__init__.py`:
```python
if __name__ == "__main__":
    run_crawl()
```

### 2.6 NEW BUG — `report/render.py` mutates a frozen Pydantic model

```python
report = report.model_copy(update={"summary": summary})
```

`BlastRadiusReport` does not have `frozen=True` set in its Pydantic config, so `model_copy` should work. However, this pattern creates a new object and shadows the old one, but the variable name `report` is reused inside the function. If `_generate_summary` raises an exception, the `except` block assigns nothing and `report.summary` is still `""`. The report is then rendered with an empty summary, which is acceptable per the design — but the `except` block prints a warning and continues, so this behavior is correct and not a bug. Marking this as a **style issue** rather than a bug: the mutation-via-copy pattern is fragile. Use a local variable name `report_with_summary` to avoid confusion.

---

## Section 3: Structural Gaps Still Present from v1

### 3.1 The Docling `# VERIFY` comment survived

In `ingest/extract.py`:
```python
# VERIFY before use: check current DoclingDocument item traversal API with:
#     python -c "from docling.document_converter import DocumentConverter; help(DocumentConverter)"
```

The v1 audit said the problem with `# VERIFY` comments is that an LLM cannot run `help()` at plan-time. v2 improves the v1 Docling code (the heuristic is removed) but leaves this comment without resolving it. The function `extract_requirements_from_docling` then calls `result.document.export_to_markdown()` — which is the correct Docling 2.x API. The `# VERIFY` comment is therefore unnecessary and should be removed in v3.

**Fix for v3:** Remove the comment. The API call is verified by the guide's own code. If the Docling API changes in a future version, the import will fail with an `AttributeError` that is self-explanatory.

### 3.2 `models.py` `GapNode` model is defined but never used in Phase 5

`BlastRadiusReport` does not include `GapNode` nodes in its output. Phase 5 (`reason/__init__.py`) reads IMPLEMENTS and RENDERS edges from Neo4j but never reads ABSENT_FROM edges or GapNodes. The design document section says to create GapNodes in Phase 4 and query them in Phase 5, but the Phase 5 code never does this.

This means the "absent requirements" section — one of the most explicitly asked-for features in the assignment brief — is missing from the blast radius output.

**Fix for v3:** In `_load_entity_links_from_neo4j()`, add:
```python
# Load absent requirements
for row in session.run(
    "MATCH (r:Requirement)-[:ABSENT_FROM]->(g:GapNode) "
    "RETURN r.id as req_id, r.text as req_text, g.reason as reason"
):
    # Add to manual_review_items or a dedicated absent_requirements field
```
Add `absent_requirements: list[AffectedNode]` to `BlastRadiusReport`, and populate it in `analyze_pr()`. Include it in the HTML/MD report template.

### 3.3 PR `changed_function_ids` is set to `[]` and never populated

In `code/pr.py`:
```python
return PRDelta(
    ...
    changed_function_ids=[],  # populated in Phase 5
)
```

In Phase 5's `analyze_pr()`:
```python
changed_paths = {cf.path for cf in delta.changed_files}
seeds = [fn.function_id for fn in functions if fn.file in changed_paths]
```

This does NOT populate `delta.changed_function_ids`. The delta's JSON file on disk always has an empty list. Anyone reading `pr_{number}.json` sees empty `changed_function_ids` even after Phase 5 runs. This is a data integrity issue: the PR artifact does not reflect what the system discovered.

**Fix for v3:** After computing seeds in Phase 5, write back the updated delta:
```python
delta.changed_function_ids = seeds
delta_path.write_text(delta.model_dump_json(indent=2), encoding="utf-8")
```

### 3.4 `resolve_requirements_to_functions` has an O(n²) performance problem

```python
fn_labels = [f"{f.file}:{f.name}" for f in functions]
...
for i, req in enumerate(requirements):
    sims = [cosine_similarity(req_embeddings[i], fn_embeddings[j]) for j in range(len(functions))]\
```

For Documenso (a large monorepo with potentially 1000+ TypeScript functions), this is O(requirements × functions) cosine similarity computations in pure Python. Sentence-transformers supports batch similarity with `util.cos_sim(req_embeddings, fn_embeddings)` which uses vectorized numpy/torch operations and is 50–100× faster.

**Fix for v3:**
```python
from sentence_transformers import util
import torch

sim_matrix = util.cos_sim(req_embeddings, fn_embeddings)  # returns torch.Tensor
for i, req in enumerate(requirements):
    scores = sim_matrix[i].tolist()
    top_idx = sorted(range(len(scores)), key=lambda x: scores[x], reverse=True)[:5]
    ...
```

### 3.5 Jinja template missing `filter` for list rendering

In `templates/report.html.j2`:
```html
<code>MATCH path=(f:CodeFunction)-[*1..6]-(r:Requirement)
WHERE f.id IN {{ report.seed_function_ids[:3] }} RETURN path LIMIT 50</code>
```

Jinja2's `autoescape=True` will HTML-escape the list representation. `['fn:src/x.ts:42:handleSubmit', 'fn:src/y.ts:99:processForm']` becomes `[&#39;fn:src/...&#39;, ...]` — the single quotes are escaped, making the Cypher query syntactically invalid in the rendered HTML. This is cosmetic but embarrassing in a demo.

**Fix for v3:** Use Jinja's `tojson` filter or explicitly format the list:
```html
WHERE f.id IN [{{ report.seed_function_ids[:3] | map('tojson') | join(', ') }}]
```

---

## Section 4: Assignment Alignment Gaps Not Fixed from v1

### 4.1 The Design Document Is Still a Scaffold Without Content

Phase 7 says "Populate each section with artifact-backed evidence." But it provides only section headings and pointers to which artifact to cite — no actual prose. An LLM executing Phase 7 will write placeholder text because the section guide gives structure but not substance.

The design document is worth roughly 50% of the assignment score. Spending 1.25 hours on it and providing only section headers is the most dangerous scope decision in v2.

**Fix for v3:** For each of the 10 required sections, provide:
- 2–3 sentences of scaffolded prose the LLM can expand (not just a pointer to an artifact path)
- A specific example from the Documenso domain that grounds the section
- One concrete Cypher query or code snippet cited verbatim

### 4.2 Sample Blast Radius Report Uses RWA Domain

The Appendix A sample report references:
- `src/models/user.ts`, `src/routes/userRoutes.ts` — RWA file paths
- `handleSubmit`, `user profile update` — RWA business logic
- Banking language: "display name", "email address", "profile changes persist"

For a Documenso demo, the evaluator will see a sample report about a banking app and a real report about a document-signing platform. These need to be consistent. The sample report must use Documenso entities: `packages/lib/server-only/document/`, `recipient`, `signing`, `template`.

### 4.3 Absent Requirements Remain Underspecified in the Report

The assignment brief explicitly asks: "how do you model absence — the requirements that should be testable but aren't reflected anywhere in the captured UI?"

v2's graph builds `GapNode`s and sets `coverage_status = "MISSING"` on Requirements. But the blast radius report template has no "Absent Requirements" section. The HTML template has no absent requirements block. The Markdown renderer has no absent requirements section. Phase 5's `BlastRadiusReport` model has no `absent_requirements` field.

This means the most explicitly-asked-for assignment feature is implemented in the graph (Phase 4) but never surfaced in the output (Phase 5/6). An evaluator reading the report would not see it.

**This is a critical gap from the assignment brief.** Fix in v3 as described in Section 3.2 above.

### 4.4 The Loom Recording Has No Guidance

The assignment requires a 5–10 minute Loom. v2 has zero guidance on what to show in the Loom. Evaluators watch the Loom first — it's the first impression.

**Fix for v3:** Add a Phase 8 (or Appendix C) titled "Loom Recording Script" with:
1. Show Neo4j Browser: `MATCH (n) RETURN labels(n), count(n)` — graph is populated
2. Show the ABSENT_FROM query — first-class absence modeling
3. Open a real Documenso PR on GitHub — walk through changed files
4. Run `python scripts/run_pipeline.py --phase 5,6` live
5. Open the generated HTML report — walk through Executive Summary, High Risk sections, Dark Changes
6. Return to Neo4j Browser: show the evidence path for one high-risk finding

### 4.5 Eval Section Missing a Concrete Failure Definition

Phase 7 / `evaluation_protocol.md` says "target: Precision > 0.70, Recall > 0.60." But there's no gold label collection procedure for Documenso PRs. The protocol says "a QA engineer reviews the report" — but who is this QA engineer in the context of a take-home assignment? The evaluator?

**Fix for v3:** Explicitly state that for the purpose of the assignment demo, the "gold labels" are the LLM's own judgment: after generating the report, run a second LLM call asking "Given this PR's changed files and the reported affected requirements, are these plausible impacts? Rate each as CONFIRMED/DISMISSED with rationale." This is a self-evaluation that is honest about its limitations.

---

## Section 5: Dependency and Infrastructure Issues

### 5.1 `crawl4ai>=0.4.0,<1.0` Upper Bound Is Too Wide

crawl4ai has had breaking API changes between minor versions. `>=0.4.0,<1.0` allows installation of `0.5.x`, `0.6.x`, `0.7.x` — all of which have different `AsyncWebCrawler` constructor signatures. The `<1.0` upper bound does not protect against this.

**Fix for v3:** After verifying the crawl4ai version that works with `AsyncWebCrawler()` (no-arg construction), pin to `>=0.4.x,<0.5.0` — a single minor version. Document which minor version was verified.

### 5.2 `sentence-transformers>=2.7.0` Has No Upper Bound

`sentence-transformers>=2.7.0` without an upper bound allows installation of 3.x if it exists, which may have breaking changes. Add `<4.0` at minimum.

### 5.3 `ast-grep` Binary Verification Is Delegated to the User Without a Check Script

v2 correctly says "ast-grep is a system binary, not a pip package." But there's no script to verify the installation and print the version before Phase 3 runs. If `sg` is not on the PATH, Phase 3 fails with:
```
FileNotFoundError: [Errno 2] No such file or directory: 'sg'
```
...which is not a helpful error message for debugging.

**Fix for v3:** Add to the Phase 0 smoke test:
```python
import subprocess
result = subprocess.run(["sg", "--version"], capture_output=True, text=True)
if result.returncode != 0:
    raise RuntimeError("ast-grep (sg) is not installed or not on PATH. Install it before Phase 3.")
print(f"ast-grep version: {result.stdout.strip()}")
```

And add this to `scripts/validate_env.py` (which should exist — see Section 5.4).

### 5.4 No `validate_env.py` Script

v1 audit recommended a `validate_env.py` script that checks all dependencies before Phase 1. v2 did not implement this. For Documenso, which has more external dependencies (live SaaS, GitHub API, Anthropic API, Neo4j, ast-grep binary), a validation script is more important than ever.

**Fix for v3:** Create `scripts/validate_env.py` that checks:
- Python version >= 3.11
- All `requirements.txt` packages importable
- `sg --version` succeeds (ast-grep binary present)
- Neo4j reachable at configured URI
- Anthropic API key set and valid format
- GitHub token set (optional but recommended)
- `data/repos/documenso` directory exists (or warn user to clone)
- `MERGE_SHA` is set and non-empty

### 5.5 `docker-compose.yml` Healthcheck Uses Wrong Auth Pattern

```yaml
healthcheck:
  test: ["CMD", "cypher-shell", "-u", "neo4j", "-p", "${NEO4J_PASSWORD}"]
```

Docker Compose does not expand `.env` variables inside `test:` arrays in all versions. The healthcheck may silently use the literal string `${NEO4J_PASSWORD}` as the password, causing it to always fail. Use:
```yaml
test: ["CMD-SHELL", "cypher-shell -u neo4j -p $NEO4J_PASSWORD 'RETURN 1' || exit 1"]
```

---

## Section 6: Documenso-Specific Technical Considerations for v3

### 6.1 tRPC Is the Primary API Layer — Not REST

Documenso uses tRPC for all client-server communication. The existing code analysis extracts TypeScript function declarations and arrow functions — this will capture tRPC procedure definitions. However:

- tRPC procedures follow the pattern: `publicProcedure.query(async ({ ctx, input }) => {...})`
- The outer procedure name comes from the router key: `{ getDocument: publicProcedure.query(...) }`
- The ast-grep rule extracts the inner arrow function, which is anonymous — `_extract_name_from_text` will return `"anonymous"` for most tRPC handlers

**Fix for v3:** Add a tRPC-specific rule that captures the router key name:
```yaml
id: trpc-procedure
language: TypeScript
rule:
  pattern: $NAME: $PROC.$METHOD($$$)
```

### 6.2 Prisma Schema Is a Fourth Analysis Layer

Documenso's `packages/prisma/schema.prisma` defines the data model. Requirements like "A Document has Recipients" are directly verifiable against the schema. v3 should:

1. Add a `parse_prisma_schema(path)` function that extracts model names and fields using regex (not AST — Prisma's schema language is not TypeScript)
2. Add `DataModel` as a new node type in the graph: `(:DataModel {id, name, fields[]})`
3. Add `MODELS` as a new edge: `(:CodeFunction)-[:MODELS]->(:DataModel)` for functions that reference a Prisma model

This is a genuine differentiator. Most implementations will only do three layers. Documenso's schema makes a fourth layer trivially extractable.

### 6.3 The AGPL-3.0 License Complicates Local Crawling

Documenso is AGPL-3.0. Running it locally (for a demo) without network access requires only complying with the license for distribution/modification — self-hosting for testing is fine. However, the guide should explicitly state: "We crawl `https://app.documenso.com` (the public SaaS) for UI artifacts. We analyze the public GitHub repository for code artifacts. No proprietary code is included in this analysis tool."

### 6.4 Document Lifecycle as a Built-in User Flow

Documenso has a clear, documented user flow: Create Document → Add Fields → Add Recipients → Send → Recipient Signs → Completion Certificate. This is a superior demo surface vs. RWA because:

- The flow is linear and inspectable
- Requirements map directly to UI steps
- Each step has a corresponding API call
- The "signing" step involves a different UI actor (recipient vs. sender) — this is a good test of the graph's ability to model multiple user roles

v3 should hardcode this flow as a `UserFlow` node in the graph and use it as a seeded known-good cross-layer connection.

---

## Section 7: What v2 Gets Right (Keep These)

1. **pydantic-settings for config** — correct fix from v1. Keep.
2. **Forward PPR direction** — the `graph.reverse()` bug is fixed. Keep.
3. **NetworkXNoPath handling** — exception is caught. Keep (but fix the weight lambda).
4. **LLM-based requirement extraction** — replaces the catastrophic line-prefix heuristic. Keep, but update the system prompt for Documenso.
5. **Typed inter-phase artifacts via Pydantic** — all phases use shared models. Keep; this is the most important structural improvement in v2.
6. **`scripts/run_pipeline.py` orchestrator** — phase-by-phase execution with skip flags. Keep.
7. **Neo4j MERGE with typed labels** — no more `%s` string formatting. Keep.
8. **Complete Jinja template** — the full template is provided, unlike v1. Keep (fix the list rendering issue).
9. **Complete code for all declared files** — no file is listed without code. Keep.
10. **Cosine + LLM reranker replacing Splink** — simpler, correct, adequate for v1. Keep.
11. **`DARK_CHANGE` handling as a first-class case** — not a silent empty success. Keep.
12. **Domain spot-checks in smoke tests** — domain-aware assertions, not just schema checks. Keep (update for Documenso).
13. **`run_id` on every edge** — audit trail for graph updates. Keep.
14. **Absence modeling via `coverage_status`** — first-class property vs. runtime threshold. Keep (but surface it in the report).

---

## Section 8: Prioritized Fixes for v3

### P0 — Documenso Migration (BLOCKS EVERYTHING)

1. **Replace all RWA references** with Documenso equivalents: URLs, repo paths, PR number, credential selectors, domain keywords, LLM prompts, sample report.
2. **Select a real Documenso PR** that modifies `packages/lib/` or `packages/trpc/`. Pin its merge SHA. Document the selection rationale.
3. **Decide on crawl auth strategy**: test account credentials in `.env` (more complete graph) vs. unauthenticated-only (simpler, safer). Document the choice explicitly.
4. **Update ast-grep scan paths**: `packages/` and `apps/web/src/` instead of `src/`.
5. **Add tRPC-specific ast-grep rule** for procedure extraction.
6. **Update all domain spot-check assertions** with Documenso terms.

### P1 — Code Bugs (WRONG RESULTS WITHOUT THESE)

7. **Fix `evidence_path` weight lambda**: use `weight="weight"` string, not a callable.
8. **Fix `ui_id` mismatch in `resolve_ui_to_functions`**: align with the IDs written in `write_ui_elements`.
9. **Fix `ast_node_type` extraction**: use `match.get("ruleId", "ts-functions")`.
10. **Add `if __name__ == "__main__"` to `crawl/__init__.py`**.
11. **Populate `delta.changed_function_ids`** after Phase 5 computes seeds.
12. **Add absent requirements to `BlastRadiusReport`** and surface in report template.

### P2 — Assignment Score (QUALITY AND SCORING)

13. **Surface GapNodes in the HTML/MD report** — add "Absent Requirements" section. This is explicitly required by the assignment.
14. **Update sample blast radius report** with Documenso domain (documents, recipients, signing).
15. **Add Loom recording script** as Appendix C.
16. **Flesh out design document sections** with scaffolded prose, not just section headers.
17. **Fix Jinja `seed_function_ids` list rendering** with `tojson` filter.
18. **Add `scripts/validate_env.py`** with pre-flight checks.

### P3 — Polish and Reliability

19. **Fix `crawl4ai` minor version pin** to a single verified minor version.
20. **Fix docker-compose healthcheck** to use `CMD-SHELL` form.
21. **Add Documenso-specific Prisma schema extraction** as a bonus fourth graph layer.
22. **Fix `O(n²)` cosine similarity** with `sentence_transformers.util.cos_sim`.
23. **Remove the surviving `# VERIFY` comment** from Docling (the code is already correct).
24. **Add upper bound to `sentence-transformers`**: `<4.0`.

---

## Appendix A: v3 Suggested Document Structure

```
# Blast Radius Analyzer — v3 Implementation Guide

## Quick Reference
  Target: Documenso (https://app.documenso.com)
  Repo: documenso/documenso
  PR: #{CHOSEN_PR} — {RATIONALE}
  Merge SHA: {PIN BEFORE PHASE 3}
  Crawl mode: authenticated | unauthenticated (choose one explicitly)

## Package Versions (Verified)
  [same structure as v2, with crawl4ai pinned to a single minor version]

## Documenso-Specific Context  ← NEW SECTION
  - Monorepo structure: packages/ + apps/
  - tRPC as API layer (not REST)
  - Prisma schema as optional fourth graph layer
  - AGPL-3.0: crawl public SaaS, analyze public repo
  - Auth strategy for crawl: [explicit decision]
  - Key business entities: Document, Template, Recipient, Signer, Field, Certificate

## Architecture Overview
  [identical to v2 architecture, updated URLs]

## Inter-Phase Data Contracts
  [add absent_requirements: list[AffectedNode] to BlastRadiusReport]
  [add DataModel node type for Prisma extraction]

## Phase 0: Project Skeleton
  [same as v2, with validate_env.py added, docker-compose healthcheck fixed]

## Phase 1: Crawler MVP
  [Documenso login selectors, rate limiting, robots.txt check]
  [two crawl modes: unauth (marketing pages) + auth (document flows)]

## Phase 2: PRD Ingest
  [Documenso-specific LLM prompt]
  [Sources: docs.documenso.com + README.md]
  [Domain spot-check: documenso terms]

## Phase 3: Code Analysis
  [Scan paths: packages/ and apps/web/src/]
  [ts-functions.yml + trpc-procedures.yml rules]
  [Optional: prisma schema extraction]
  [ast-grep JSON format verified against installed version]

## Phase 4: Knowledge Graph Construction
  [Fix ui_id mismatch in resolve_ui_to_functions]
  [Surface GapNodes from ABSENT_FROM query]

## Phase 5: Blast Radius Reasoning
  [Fix evidence_path weight lambda]
  [Populate delta.changed_function_ids]
  [Load and include absent_requirements in report]

## Phase 6: Human-Readable Report
  [Add Absent Requirements section to HTML and MD templates]
  [Fix Jinja seed_function_ids list rendering]

## Phase 7: Design Document
  [Scaffolded prose for all 10 sections, not just section headers]
  [Documenso-specific examples throughout]

## Appendix A: Sample Blast Radius Report (Documenso)
  [Replace RWA banking report with Documenso signing flow report]

## Appendix B: Week 2 Roadmap
  [same as v2]

## Appendix C: Loom Recording Script  ← NEW
  [6-step walkthrough script with timing]

## Common Failures and Fixes
  [update all RWA-specific entries with Documenso equivalents]
  [add Documenso auth-related failures]
```

---

## Appendix B: Documenso PR Selection Guide

Browse `https://github.com/documenso/documenso/pulls?q=is%3Apr+is%3Amerged+sort%3Aupdated-desc` and filter for PRs that:

**Good candidates (deep impact):**
- Modify files in `packages/lib/server-only/document/` — core document logic
- Modify files in `packages/trpc/server/routers/` — API procedure changes
- Touch `packages/lib/server-only/recipient/` — recipient/signing flow
- Change `packages/prisma/schema.prisma` — data model changes

**Avoid (shallow impact, same reason as RWA logo swap):**
- Only modify `packages/ui/components/` — styling changes
- Only modify `.md` files — documentation
- Only modify `apps/marketing/` — marketing site

**Ideal PR for demo:** One that modifies a tRPC router file AND a corresponding `lib/` business logic file — this exercises the full `Requirement → UIElement → CodeFunction (tRPC procedure) → CodeFunction (lib)` propagation chain.

---

*Audit completed against: `v2_implementation_guide.md`, `d0_AI_Engineer_Updated_-_Assignment.md`, `d2_CODING_CONTEXT_v1.md`, `d4_blast_radius_analyzer_reference.md`, `d1_documentation.md`, `v1_audit_blast_radius_implementation_guide.md`, and Documenso project specifications provided by user.*

*Target application switched from Cypress Real World App to Documenso by user request. All migration impacts documented above.*
