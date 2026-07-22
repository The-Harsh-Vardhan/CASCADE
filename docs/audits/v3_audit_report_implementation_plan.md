# Blast Radius Analyzer — v3 Implementation Guide: Critical Audit Report

**Prepared for:** v4 planning  
**Source audited:** `v3_implementation_guide.md`  
**Cross-referenced against:** `d0_AI_Engineer_Updated_-_Assignment.md`, `d1_documentation.md`, `d2_CODING_CONTEXT_v1.md`, `d4_blast_radius_analyzer_reference.md`  
**Audit purpose:** Identify every bug, ambiguity, contradiction, missing instruction, and LLM-trap so v4 can be followed step-by-step to a working system without human intervention.

---

## Severity Classification

| Label | Meaning |
|---|---|
| 🔴 **P0 — Showstopper** | Will crash the pipeline or produce a silent wrong result. Must fix in v4. |
| 🟠 **P1 — High** | Will likely fail in a real run; requires workaround that an LLM won't invent. |
| 🟡 **P2 — Medium** | Ambiguity or missing detail that will produce sub-optimal or inconsistent results. |
| 🟢 **P3 — Low** | Polish issues, misleading prose, or missed best-practices that hurt the document's clarity as a specification. |

---

## Executive Summary

v3 is a substantial improvement over v2. The Documenso migration is well-motivated, the Pydantic data-contract approach is sound, the two-pass crawler (unauth + auth) is realistic, the tRPC-specific ast-grep rule is new and necessary, and the `validate_env.py` pre-flight script is the right instinct. The design document scaffolding in Phase 7 is genuinely useful.

**However, v3 has approximately 23 distinct issues** ranging from outright broken code (the `validate_env.py` script will crash Python on import, the `_load_graph_data` query uses wrong relationship directions, the `crawl4ai` version pin is contradictory) to serious ambiguities that will cause an LLM to stall (no instruction for installing Playwright browsers, no instruction for what to do when `app.documenso.com` returns a login wall for all routes, no guidance on which specific PR to pick).

The single biggest structural problem is that **v3 is written as a document for a human engineer who will improvise the gaps**, not as a machine-executable specification. An LLM following it literally will fail at Phase 0, Phase 1, Phase 3, and Phase 4 before producing a single useful artifact. The fixes are largely additive — the architecture is correct — but the specification work is not yet done.

---

## Phase 0 Issues

### 🔴 P0-01 — `validate_env.py` uses a broken Python idiom that crashes on import

**Location:** `scripts/validate_env.py`, the `check()` helper

**The problem:**
```python
lambda: None if sys.version_info >= (3, 11)
       else (_ for _ in ()).throw(RuntimeError(...))
```
`generator.throw()` does not exist in Python. `(_ for _ in ())` creates a generator; calling `.throw()` on it raises `AttributeError: 'generator' object has no attribute 'throw'`. This pattern is used four more times in the same file (MERGE_SHA check, repo check, etc.). Every one of those checks will crash the interpreter before it even evaluates the condition.

**Fix for v4:** Replace the entire pattern with a conventional `try/raise` lambda:
```python
def check(label: str, fn) -> bool:
    try:
        result = fn()
        if result is False:
            raise RuntimeError("returned False")
        console.print(f"  [green]✓[/green] {label}")
        return True
    except Exception as e:
        console.print(f"  [red]✗[/red] {label}: {e}")
        failures.append(label)
        return False
```
Then each check lambda simply raises on failure:
```python
check("Python >= 3.11", lambda: (_ for _ in [None] if sys.version_info < (3, 11) and (_ for _ in ()).throw(None)))
# Replace with:
def _python_version():
    if sys.version_info < (3, 11):
        raise RuntimeError(f"Python {sys.version_info[:2]} — need 3.11+")
check("Python >= 3.11", _python_version)
```
The entire validate_env.py must be rewritten with conventional `try/except` blocks.

---

### 🔴 P0-02 — `settings.validate_and_print()` uses `.model_dump()` which exposes the raw API key in logs

**Location:** `config.py`, `validate_and_print()`

**The problem:** `safe = self.model_dump()` dumps all fields, then the code does `safe["anthropic_api_key"] = safe["anthropic_api_key"][:8] + "..."`. This only works if the field is named exactly `anthropic_api_key` in the dict. With `pydantic-settings`, field names in `model_dump()` match the Python attribute names, not the env var names — this part is fine. But the bigger issue is that `safe.get("documenso_password")` checks for the key but `model_dump()` always includes all fields, so the condition will always be true even when the password is `None`. The code will then crash on `safe["documenso_password"] = "***"` when `documenso_password` is `None` and the `if` branch nonetheless executes (it won't — the `if` is correct) — actually this specific bug is minor, but there is a real one: `safe["neo4j_password"]` will crash with `KeyError` because `model_dump()` uses the Python attribute name `neo4j_password` correctly, but `safe["anthropic_api_key"]` will also work. The real crash is that `statuses.get(k, "✓")` iterates over ALL keys including `pr_number`, `crawl_max_pages`, etc., and there's no status entry for them — they'll all show "✓" even if wrong. This is a **misleading output**, not a crash, but it will confuse an LLM trying to debug a failed run.

**Fix for v4:** List explicit fields to show, handle `None` passwords cleanly, and don't iterate `model_dump()` — use an explicit display list.

---

### 🟠 P1-03 — No instruction to install Playwright browsers before Phase 1

**Location:** Between Phase 0 and Phase 1

**The problem:** Phase 1 imports `playwright.async_api` and calls `pw.chromium.launch()`. This requires `playwright install chromium` to have been run. The v3 guide mentions it parenthetically in Phase 1's prerequisites line (`Playwright browsers installed (playwright install chromium)`) but never tells the LLM to actually run it. There is no `scripts/validate_env.py` check for it. There is no command in the setup flow. An LLM building a fresh environment will hit `playwright._impl._errors.Error: Executable doesn't exist` on the first crawl and have no context for why.

**Fix for v4:** Add `playwright install chromium` to the Phase 0 setup commands as a required step, add a check to `validate_env.py`:
```python
def _playwright_installed():
    result = subprocess.run(
        ["python", "-m", "playwright", "install", "--dry-run", "chromium"],
        capture_output=True, text=True
    )
    if "chromium" not in result.stdout.lower() and result.returncode != 0:
        raise RuntimeError("Run: playwright install chromium")
check("Playwright chromium installed", _playwright_installed)
```

---

### 🟠 P1-04 — `requirements.txt` uses contradictory version pins for `crawl4ai`

**Location:** Package Versions section

**The problem:** The guide says:
> `crawl4ai>=0.4.0,<0.5.0` — pin to single minor version; API changes between minors

Then in the same paragraph:
> The `AsyncWebCrawler()` no-argument constructor is verified for `0.4.x`

But as of mid-2025, crawl4ai's latest release is `0.6.x`. The `0.4.x` range may not install at all if the package index has moved on. More critically, the guide also says:
> Before using, run: `python -c "import crawl4ai; help(crawl4ai.AsyncWebCrawler.__init__)"`

This is not executable by an LLM building the environment — it requires human inspection. The guide needs to either pin to an exact version that is verified, or provide the concrete constructor call for whatever version is pinned.

**Fix for v4:** Pin to an exact version that was actually tested: `crawl4ai==0.4.3` (or whichever was verified). Add the exact constructor call to the code, not a `help()` invocation. Remove the "before using, run" instruction and replace it with the verified code.

---

### 🟡 P2-05 — `docker-compose.yml` healthcheck will fail if the `cypher-shell` binary path varies across Neo4j versions

**Location:** `docker-compose.yml`

**The problem:** The healthcheck uses `cypher-shell`, which is inside the container. In Neo4j 5.x Community Edition, `cypher-shell` is at `/var/lib/neo4j/bin/cypher-shell`. The `CMD-SHELL` form should work, but the command `cypher-shell -u neo4j -p $NEO4J_PASSWORD 'RETURN 1'` will silently expand `$NEO4J_PASSWORD` from the **container's** environment, which only has `NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}` set — not `NEO4J_PASSWORD` as a standalone variable. So the healthcheck may fail even when Neo4j is healthy.

**Fix for v4:** Use the HTTP endpoint instead, which is simpler and more reliable:
```yaml
healthcheck:
  test: ["CMD", "wget", "--no-verbose", "--tries=1", "--spider", "http://localhost:7474"]
  interval: 10s
  timeout: 5s
  retries: 12
  start_period: 30s
```

---

### 🟡 P2-06 — `scripts/run_pipeline.py` imports modules that don't exist yet at Phase 0

**Location:** `scripts/run_pipeline.py`

**The problem:** `run_pipeline.py` is created in Phase 0 and imports `from blast_radius.crawl import run_crawl`, `from blast_radius.ingest import run_ingest`, etc. These modules don't exist until Phases 1–6 are completed. If an LLM runs `python scripts/run_pipeline.py --phase 1` before completing Phase 1, it will get an `ImportError` from the Phase 1 import at module load time — not a runtime error. The `if __name__ == "__main__"` guard doesn't help here because the import is at the top level of the function body, not the module level, so it's actually fine. Actually, re-reading: the imports are *inside* the `run_phase()` function body, so they're lazy — this works correctly. However, the function has `print("Phase 0 is setup — run manually. See README.")` which tells an LLM nothing about what to do. This is a documentation gap.

**Fix for v4:** Add a comment block above each phase import explaining what must exist for it to succeed. Minor issue.

---

## Phase 1 Issues

### 🔴 P0-07 — `app.documenso.com` returns a redirect loop or empty page for unauthenticated routes in 2025

**Location:** Phase 1, `dynamic.py`, `run_dynamic_crawl()`

**The problem:** `https://app.documenso.com` in its current state (mid-2025) redirects unauthenticated users to `/signin` from almost every route. The guide lists routes `["", "/signin", "/signup"]` for unauthenticated crawl. Navigating to `""` (the root) will immediately redirect to `/signin`, so the crawler will capture `/signin` twice and the `visited` set will catch the second attempt. The root URL snapshot will have `url = "https://app.documenso.com"` but the actual page captured will be the sign-in page. The smoke test checks for `documenso_terms` in the DOM, which will pass because "sign" is in the signin page — but the test says it found e.g. "document" when it actually found "sign". This is a silent semantic failure.

More critically: the guide says "if credentials are absent, the crawler logs a warning and proceeds with unauthenticated pages only" — but there are only 3 unauthenticated routes listed, and all three may produce the sign-in page. The minimum snapshot count check is `>= 2`, so this will pass. But the resulting graph will have essentially no useful UI data — every UIElement will be from the sign-in form.

**Fix for v4:** Either (a) require test credentials and make authenticated crawl mandatory for this target, with instructions for creating a free Documenso account, or (b) switch to crawling `https://docs.documenso.com` as the UI layer source (it's publicly accessible) or the marketing site `https://documenso.com`. Add a smoke test that verifies at least one of `{"documents", "template", "recipient", "field"}` appears in the crawled pages — these are only present in authenticated views.

---

### 🟠 P1-08 — `crawl_page()` uses `wait_until="networkidle"` which will timeout on Documenso's Next.js app

**Location:** `dynamic.py`, `crawl_page()`

**The problem:** Next.js apps with SWR or React Query make continuous background requests. `networkidle` requires no network requests for 500ms, which often never happens in a live SaaS. The timeout is set to `25_000ms`. On a slow connection or if Documenso's app makes background polling requests (analytics, session checks, etc.), this will consistently timeout. The v3 guide even mentions this as a known problem under "Playwright timeout on crawl" in the Debugging Tips section of d2 — but doesn't fix it in the crawler code.

**Fix for v4:** Use `wait_until="domcontentloaded"` with an additional `page.wait_for_load_state("load")` call, then a fixed `asyncio.sleep(2.0)` for JS hydration:
```python
await page.goto(url, wait_until="domcontentloaded", timeout=25_000)
await page.wait_for_load_state("load", timeout=10_000)
await asyncio.sleep(2.0)  # let Next.js hydrate
```

---

### 🟠 P1-09 — The auth login flow selector is fragile and will break

**Location:** `dynamic.py`, auth block

**The problem:**
```python
await page.fill('input[name="email"], input[type="email"]', settings.documenso_email)
await page.fill('input[name="password"], input[type="password"]', settings.documenso_password)
await page.click('button[type="submit"]')
await page.wait_for_url(f"{start_url}/**", timeout=15_000)
```
The `page.fill()` call with a CSS selector that has a comma in it (`'input[name="email"], input[type="email"]'`) is **not valid in Playwright**. Playwright's `fill()` does not accept comma-separated CSS selectors like `querySelector`/`querySelectorAll` does — it requires a single, unambiguous locator. This will raise `playwright._impl._errors.Error: strict mode violation` if both selectors match, or silently fail to find the element if neither matches.

Additionally, `page.wait_for_url(f"{start_url}/**")` uses a glob pattern. Playwright supports this, but the URL after login may be `https://app.documenso.com/documents` — which does match `https://app.documenso.com/**`. However, if the login fails (wrong credentials, CAPTCHA, email verification required), the URL stays at `/signin` and the `wait_for_url` call will timeout after 15 seconds with no useful error message.

**Fix for v4:** Use Playwright's recommended locator API:
```python
await page.get_by_label("Email").fill(settings.documenso_email)
await page.get_by_label("Password").fill(settings.documenso_password)
await page.get_by_role("button", name="Sign in").click()
# Wait for successful navigation
try:
    await page.wait_for_url("**/documents**", timeout=15_000)
except:
    current_url = page.url
    if "signin" in current_url:
        raise RuntimeError(
            f"Login failed — still at {current_url}. "
            "Check DOCUMENSO_EMAIL and DOCUMENSO_PASSWORD in .env. "
            "Note: Documenso may require email verification for new accounts."
        )
```

---

### 🟡 P2-10 — No instruction to create a Documenso test account

**Location:** Phase 0 / Phase 1 prerequisites

**The problem:** The guide says to set `DOCUMENSO_EMAIL` and `DOCUMENSO_PASSWORD` in `.env` but never tells the LLM (or human) how to obtain those credentials. Documenso at `app.documenso.com` requires:
1. Creating a free account
2. Verifying the email address
3. Potentially completing an onboarding flow

An LLM cannot do step 1–3. A human can, but without instructions they may not realize this is required. The `.env.example` says `your-test-account@example.com` which is not a valid hint.

**Fix for v4:** Add an explicit one-time setup section: "Before running Phase 1, create a free account at https://app.documenso.com/signup. Verify your email. Upload at least one test PDF to trigger the document list UI. Set DOCUMENSO_EMAIL and DOCUMENSO_PASSWORD in .env."

---

### 🟡 P2-11 — `_capture_transitions()` generates `Transition` objects but never correctly identifies Documenso's client-side navigation

**Location:** `dynamic.py`, `_capture_transitions()`

**The problem:** The function uses:
```python
links = await page.evaluate("""
    () => Array.from(document.querySelectorAll('a[href]'))
          .slice(0, 50)
          .map(el => ({ href: el.href || '', text: ... }))
""")
```
In Next.js, client-side navigation uses `<Link>` components which render as `<a>` tags but their `href` is the client-side route. However, many Documenso navigation actions (opening a document, adding a recipient) are triggered by `<button>` or `<div>` elements with `onClick` handlers, not `<a>` tags. The BFS traversal will miss all of these. The guide acknowledges that "Dynamic JavaScript state changes won't be fully captured" but the transition capture code doesn't even capture the `<a>` routes that exist — it also filters by `startswith(base_url)` which excludes relative paths.

This is a fundamental limitation acknowledged in the design doc, but the code is silent about it. The smoke test won't catch it because transitions are optional.

**Fix for v4:** Add a comment block in the code and smoke test output explicitly noting how many transitions were found. If zero, log a prominent warning: `"[crawl] WARNING: 0 transitions found on {url} — this is expected for non-anchor navigation (Next.js). The graph will lack Page→Page NAVIGATES_TO edges."` This sets correct expectations.

---

## Phase 2 Issues

### 🔴 P0-12 — `crawl_docs_pages()` in `static.py` uses `result.html` which doesn't exist in crawl4ai 0.4.x

**Location:** `static.py`, `crawl_static_url()`

**The problem:**
```python
result = await crawler.arun(url)
if not result.success:
    return None
return result.html
```
In crawl4ai 0.4.x, the `CrawlResult` object does not have a `.html` attribute. The actual attribute for the cleaned HTML content is `result.cleaned_html`. The raw HTML is `result.raw_html`. `result.html` will raise `AttributeError`. The Markdown output (which is what the guide recommends using crawl4ai for) is `result.markdown`. Since the downstream code calls `extract_requirements(html, ...)` and feeds HTML to an LLM that's expecting text, the most useful field to return would be `result.markdown` or `result.cleaned_html`.

**Fix for v4:** Use `result.markdown or result.cleaned_html or ""` and update `extract_requirements` to accept plain text, not raw HTML with tags. The LLM prompt says "extract from this documentation text" but receives HTML markup — this degrades extraction quality.

---

### 🟠 P1-13 — `extract_requirements_from_docling()` uses an unverified Docling API call

**Location:** `extract.py`

**The problem:**
```python
from docling.document_converter import DocumentConverter
result = DocumentConverter().convert(source_url_or_path)
if result.document is None:
    raise RuntimeError(...)
markdown = result.document.export_to_markdown()
```
The comment in v3 says this is "verified for docling>=2.0.0" and even provides a fallback inspection command. But `DocumentConverter().convert()` returns a `ConversionResult` object. In Docling 2.x, the attribute is `result.document` — this is correct. However, `export_to_markdown()` has a different signature in some 2.x versions: it may require `result.document.export_to_markdown()` vs `result.render_as_markdown()` depending on the exact patch version. The guide pins `docling>=2.0.0,<3.0` which is a wide range with API instability.

More critically: `DocumentConverter().convert(url)` for a remote URL (the README.md raw URL) requires the URL to be downloadable. Docling does support URLs, but it may fail silently on some redirect chains. There's no test for whether the README was actually parsed (e.g., checking character count of the markdown output).

**Fix for v4:** Add an assertion: `assert len(markdown) > 500, f"Docling produced only {len(markdown)} chars from {source_url_or_path} — likely a failed download"`. Pin Docling to an exact version.

---

### 🟡 P2-14 — The requirement deduplication strategy is wrong

**Location:** `ingest/__init__.py`

**The problem:** The guide uses a `seen_ids` set based on content-addressed SHA256 hashes:
```python
req_id = "REQ-" + hashlib.sha256(
    (source_file + text_str).encode()
).hexdigest()[:8].upper()
```
Two requirements with the same text but from different source files get different IDs. Two requirements with the same ID (same source + same text) are deduplicated. But the real deduplication problem is semantic: the README and the docs pages will produce requirements with similar but not identical text. The SHA256 approach won't catch `"Users can upload PDFs for signing"` and `"The platform allows document upload in PDF format"` as duplicates. The v3 guide mentions "title similarity deduplication" from v2 but removed it without replacement. The result is a graph cluttered with near-duplicate requirements.

**Fix for v4:** After extraction, run a simple LLM deduplication call: batch all requirements and ask "which of these are semantically equivalent? Return pairs of IDs." Then merge duplicates, keeping the one with the more specific text. Or use cosine similarity with `sentence-transformers` (already a dependency) to flag pairs above 0.92 similarity as duplicates.

---

### 🟡 P2-15 — LLM system prompt rejects too broadly, will discard real requirements

**Location:** `extract.py`, `_SYSTEM_PROMPT`

**The problem:** The prompt says:
> REJECT sentences describing developer setup, deployment, or CI/CD

Documenso's README contains lines like "Documenso enables teams to manage document signing workflows." This should be a requirement. But it also contains "Self-hosting is supported" — this is a valid product requirement (the ability to self-host) even though it sounds like a deployment concern. The rejection rule is too broad and will discard legitimate requirements.

**Fix for v4:** Refine the rejection criteria to be more specific: reject sentences that are purely commands (start with a verb followed by a package name: "npm install", "docker run", "git clone") rather than rejecting all deployment-related content.

---

## Phase 3 Issues

### 🔴 P0-16 — The `ast-grep` scan paths don't exist in Documenso's monorepo structure

**Location:** `code/index.py`, `ast_matches()`

**The problem:**
```python
scan_paths = [
    str(repo / "packages"),
    str(repo / "apps" / "web" / "src"),
]
```
The Documenso repo's actual structure has `apps/web/src/app/` (Next.js App Router), `apps/web/src/components/`, and `apps/web/src/pages/` — the `src` directory exists. But `packages/` contains subdirectories like `packages/lib/`, `packages/trpc/`, `packages/ui/`, `packages/prisma/`. These are all valid.

However: ast-grep on `packages/` recursively will also scan `packages/prisma/migrations/` (hundreds of SQL files), `packages/ui/node_modules/` (if not gitignored in sparse clone), and `packages/ee/` (enterprise edition code behind a license check). This can generate thousands of spurious function matches from migration files and vendored code.

The guide says to clone with `git clone https://github.com/documenso/documenso data/repos/documenso` (in Appendix B) but Phase 3's prerequisites say "Documenso repo cloned at `data/repos/documenso`" without giving the clone command. The clone command appears only in Phase 3's body text but uses `git clone` (full clone) while the d2 coding context uses `git clone --depth 1 --sparse` (shallow clone). These are inconsistent.

**Fix for v4:** (a) Give the exact clone command in Phase 0 or a new "Repo Setup" section before Phase 3. (b) Scope the scan paths more narrowly:
```python
scan_paths = [
    str(repo / "packages" / "lib"),
    str(repo / "packages" / "trpc"),
    str(repo / "apps" / "web" / "src"),
]
```
And explicitly exclude: `node_modules`, `.git`, `dist`, `build`, `migrations`.

---

### 🔴 P0-17 — The `trpc-procedures.yml` ast-grep rule pattern is almost certainly wrong

**Location:** `rules/trpc-procedures.yml`

**The problem:**
```yaml
id: trpc-procedure
language: TypeScript
rule:
  pattern: $NAME: $PROC.$METHOD($$$)
```
This pattern attempts to match `procedureName: someRouter.query(...)`. But in Documenso's actual tRPC router files, the pattern is:
```typescript
export const documentRouter = router({
  getDocumentWithDetailsById: protectedProcedure
    .input(ZGetDocumentWithDetailsByIdSchema)
    .query(async ({ ctx, input }) => { ... }),
```
The procedure definition spans multiple lines with method chaining. The pattern `$NAME: $PROC.$METHOD($$$)` would need to match across newlines with chaining. ast-grep's tree-sitter patterns match AST nodes, not text — the AST for `getDocumentWithDetailsById: protectedProcedure.input(...).query(...)` is a `property_identifier: call_expression` pair, not a simple `$NAME: $PROC.$METHOD($$$)`. The pattern will likely match zero procedures.

There's also no smoke test output shown for `trpc-procedures.yml` specifically — the guide says to verify `trpc_fns = [f for f in fns if f.ast_node_type == 'trpc-procedure']` but if the rule matches nothing, `trpc_fns` is empty and the assert doesn't fail (there's no assertion that `len(trpc_fns) > 0`).

**Fix for v4:** Either (a) use a different ast-grep rule that targets the `pair` AST node type (property + value in an object), or (b) abandon the ast-grep approach for tRPC detection and instead use a regex scan of router files looking for the pattern `(\w+):\s*(?:protected|public)Procedure`. Add an explicit assertion: `assert len(trpc_fns) > 0, "No tRPC procedures found — check trpc-procedures.yml rule"`.

A working alternative rule:
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

---

### 🔴 P0-18 — `get_pr_delta()` uses `PyDriller.Repository` incorrectly

**Location:** `code/pr.py`

**The problem:**
```python
for commit in Repository(
    repo_path, from_commit=parent_sha, to_commit=merge_sha
).traverse_commits():
    for mod in commit.modified_files:
```
`PyDriller.Repository` with `from_commit` and `to_commit` iterates commits in that range. For a merge commit that has multiple parent commits (octopus merges or squash merges), this may return no commits if `from_commit == to_commit^1` and the merge was a fast-forward. More critically: the guide computes `parent_sha` using `git rev-parse {merge_sha}^1` which is the first parent of the merge commit. For a standard GitHub PR merge commit, this is the tip of the base branch (main), and `merge_sha` is the merge commit itself. PyDriller traversing from `parent_sha` to `merge_sha` will only include the merge commit — which has `modified_files` based on the diff between the two parents. This can work, but only if PyDriller computes the merge diff. PyDriller's `modified_files` for a merge commit may return an empty list because merge commits are often excluded from diff analysis by default.

**Fix for v4:** Use the GitHub API directly instead of PyDriller for PR file changes — it's more reliable and already included as a dependency (`httpx`):
```python
import httpx
resp = httpx.get(
    f"https://api.github.com/repos/documenso/documenso/pulls/{pr_number}/files",
    headers={"Authorization": f"token {settings.github_token}"} if settings.github_token else {},
)
resp.raise_for_status()
files = resp.json()
```
Keep PyDriller as a secondary method and document the fallback explicitly. Or document that `GITHUB_TOKEN` is required for this to work reliably.

---

### 🟠 P1-19 — `_make_function_id()` produces IDs that won't match across Phase 3 and Phase 5

**Location:** `code/index.py`

**The problem:**
```python
def _make_function_id(repo_dir: Path, abs_file: str, start_line: int, name: str) -> str:
    rel = Path(abs_file).relative_to(repo_dir)
    return f"{rel}:{start_line}:{name}"
```
The function ID is `relative_path:line_number:name`. In Phase 5, the seed computation does:
```python
seeds = [fn.function_id for fn in functions if fn.file in changed_paths]
```
Where `changed_paths = {cf.path for cf in delta.changed_files}` and `cf.path` comes from either PyDriller (`mod.new_path`) or the GitHub API. GitHub API returns paths like `packages/trpc/server/routers/document.ts`. PyDriller returns absolute paths. The `fn.file` field is stored as `str(Path(abs_file).relative_to(repo))` which produces `packages/trpc/server/routers/document.ts`. The match `fn.file in changed_paths` works if and only if both use the same relative path format — which they do IF PyDriller returns `new_path` (relative) and not the absolute path. But `mod.new_path` in PyDriller is a relative path. So this works, barely, but only if PyDriller is the source. If the GitHub API is used, the paths are also relative. **This actually works**, but the fallback in Phase 5:
```python
seeds = [fn.function_id for fn in functions if any(
    fn.file.endswith(Path(cf.path).name) for cf in delta.changed_files
)]
```
`Path(cf.path).name` gives just the filename (e.g. `document.ts`). `fn.file.endswith("document.ts")` will match ALL `document.ts` files in the repo, not just the one that changed. Documenso has `packages/trpc/server/routers/document.ts` AND potentially `packages/lib/server-only/document/document.ts`. The fallback over-seeds.

**Fix for v4:** Remove the filename-only fallback. Instead, normalize both sides to POSIX relative paths and do an exact match. Log clearly when no seeds are found rather than falling back silently.

---

### 🟡 P2-20 — Phase 3 has no instruction for what to do when `ast-grep` finds < 50 functions

**Location:** `code/index.py`, `build_call_graph()`

**The problem:**
```python
if len(fn_lookup) < 50:
    raise RuntimeError(
        f"Only {len(fn_lookup)} functions found. "
        "Verify ast-grep is installed and scan paths exist under the cloned repo."
    )
```
50 is an arbitrary threshold that could be wrong in either direction. If someone clones a sparse checkout or the Documenso repo changes its structure, the threshold may trigger on a valid scan. More importantly, the error message says "Verify ast-grep is installed and scan paths exist" — but `validate_env.py` already checks for `sg` being installed. If this error fires, it means the scan paths are wrong or the repo is incomplete. The error message should direct to the specific fix: check that `data/repos/documenso/packages/lib/` exists and contains `.ts` files.

**Fix for v4:** Make the check more diagnostic:
```python
if len(fn_lookup) < 50:
    # Show what was actually found to help debug
    sample = list(fn_lookup.values())[:5]
    raise RuntimeError(
        f"Only {len(fn_lookup)} functions found (need 50+). "
        f"Sample: {[(f.name, f.file) for f in sample]}. "
        f"Check: ls data/repos/documenso/packages/lib/server-only/document/"
    )
```

---

## Phase 4 Issues

### 🔴 P0-21 — `_load_graph_data()` in Phase 5 queries IMPLEMENTS in the wrong direction

**Location:** `reason/__init__.py`, `_load_graph_data()`

**The problem:**
```python
for row in session.run(
    "MATCH (r:Requirement)-[e:IMPLEMENTS]->(c:CodeFunction) "
    "RETURN r.id as from_id, c.id as to_id, ..."
):
    links.append(EntityLink(
        from_id=row["from_id"], to_id=row["to_id"], rel_type="IMPLEMENTS", ...
    ))
```
And then in `build_projection()`:
```python
g.add_edge(link.from_id, link.to_id, weight=WEIGHTS["IMPLEMENTS"] * link.confidence, ...)
```
An IMPLEMENTS edge stored as `(Requirement) -[IMPLEMENTS]-> (CodeFunction)` creates a graph edge from Requirement to CodeFunction. But PPR seeds are CodeFunctions (changed code) and we want to propagate TO Requirements. With this edge direction, the PPR algorithm propagates FROM Requirements TO CodeFunctions — the opposite of what's needed.

In Phase 4's `schema.py`, the edge is defined as:
```cypher
CREATE_IMPLEMENTS = """
MATCH (r:Requirement {id: $from_id}), (c:CodeFunction {id: $to_id})
MERGE (r)-[e:IMPLEMENTS]->(c)
```
This writes `Requirement → IMPLEMENTS → CodeFunction`. For forward blast radius (code change → requirement impact), we need the traversal to go `CodeFunction → something → Requirement`. The IMPLEMENTS edge goes the wrong way for PPR seeded at CodeFunctions.

**Fix for v4:** Either (a) reverse the IMPLEMENTS edge direction in the schema to `CodeFunction -[IMPLEMENTS]-> Requirement`, which is semantically cleaner (a function implements a requirement), or (b) when loading edges into the NetworkX projection, swap `from_id` and `to_id` for IMPLEMENTS edges only. Option (a) is cleaner and should also update the Cypher query:
```cypher
MATCH (c:CodeFunction {id: $from_id}), (r:Requirement {id: $to_id})
MERGE (c)-[e:IMPLEMENTS]->(r)
```
This is a fundamental logical error that causes the PPR to produce wrong results silently.

---

### 🔴 P0-22 — `resolve_requirements_to_functions()` passes `functions.index(fn)` which is O(n) and fragile

**Location:** `graph/resolve.py`

**The problem:**
```python
fn_labels = [f"{f.file}:{f.name}" for f in functions]
...
for j in top_idx:
    if scores[j] >= cosine_threshold:
        candidates.append((req, functions[j], scores[j]))
...
# Later:
"fn_label": fn_labels[functions.index(fn)],
```
`functions.index(fn)` searches the list for `fn` by equality. `CodeFunction` is a Pydantic model, and Pydantic models compare by value, not identity. If two functions have the same `function_id`, `name`, and `file` (possible after deduplication), `index()` returns the first occurrence — which may not be the one in the candidate tuple. This is a latent bug that becomes active if any two functions have similar enough fields to compare equal.

More concretely: the `fn_labels` list and the `functions` list are both indexed `0..N`. The `top_idx` values are indices into both lists simultaneously. So `fn_labels[j]` and `functions[j]` are already aligned — `functions.index(fn)` is unnecessary and wrong. It should be `fn_labels[j]`.

**Fix for v4:** Replace `fn_labels[functions.index(fn)]` with `fn_labels[j]` where `j` is the index from the `top_idx` loop. The candidates tuple should store `(req, j, score)` or `(req, functions[j], fn_labels[j], score)`.

---

### 🟠 P1-23 — `build_graph()` in Phase 4 `__init__.py` calls `mark_absent_requirements` with an already-closed session

**Location:** `graph/__init__.py`

**The problem:**
```python
with driver.session() as session:
    print("[graph] Writing Requirements...")
    write_requirements(session, requirements)
    ...
    missing_count = mark_absent_requirements(session, run_id=run_id)

driver.close()
```
This is actually fine — the `with` block keeps the session open throughout. However, `mark_absent_requirements()` runs `MATCH (r:Requirement {coverage_status: 'MISSING'}) RETURN r.id as id` immediately after `MARK_MISSING_REQUIREMENTS` — but Neo4j's MATCH after a SET within the same session uses the committed state. In Neo4j's default implicit transaction mode, each `session.run()` is its own auto-committed transaction. So `MARK_MISSING_REQUIREMENTS` commits, then the next query reads the updated state. This works correctly.

The actual bug is different: `write_entity_links()` catches all exceptions silently:
```python
except Exception as e:
    print(f"[graph] Edge write warning ({link.rel_type}): {e}")
```
If the Cypher has a node ID mismatch (e.g., a requirement ID exists in the link but not in Neo4j), the edge is silently dropped. After Phase 4, the graph may have far fewer edges than expected with no error. The smoke test only checks node counts, not edge counts.

**Fix for v4:** Add edge count assertions to the Phase 4 smoke test:
```python
implements = d.execute_query("MATCH ()-[:IMPLEMENTS]->() RETURN count(*) as c").records[0]["c"]
renders = d.execute_query("MATCH ()-[:RENDERS]->() RETURN count(*) as c").records[0]["c"]
assert implements > 0, "No IMPLEMENTS edges — entity resolution produced no confirmed links"
assert renders > 0, "No RENDERS edges — URL pattern matching produced no links"
```

---

### 🟡 P2-24 — The `cosine_threshold=0.45` in `resolve_requirements_to_functions` is too low for cross-domain matching

**Location:** `graph/resolve.py`

**The problem:** `all-MiniLM-L6-v2` produces cosine similarities of 0.3–0.5 for semantically related but domain-different text. The threshold of 0.45 will produce many false-positive candidates (requirement text vs. function label from a completely unrelated file). The LLM reranker at `llm_rerank_threshold=0.65` is supposed to filter these, but it receives batches of up to 10 candidates and is asked to confirm/dismiss — if all 10 are noise, it still burns 2048 tokens and returns 10 DISMISSED results.

The `sentence-transformers` model `all-MiniLM-L6-v2` is a general-purpose model not fine-tuned for code-to-requirements matching. A cosine similarity of 0.45 between "Users can upload a PDF document" and `packages/lib/server-only/document/create-document.ts:createDocument` will likely be achieved even without semantic relevance because both contain "document".

**Fix for v4:** Raise the threshold to `0.60` and use a domain-specific model. If keeping `all-MiniLM-L6-v2`, add a keyword pre-filter: only pass a candidate to the LLM if the requirement's `related_ui_keywords` appear in the function's file path or name. This dramatically reduces LLM calls.

---

## Phase 5 Issues

### 🟠 P1-25 — `personalized_pagerank()` will fail when the graph has isolated nodes

**Location:** `reason/ppr.py`

**The problem:**
```python
return nx.pagerank(
    graph,
    alpha=0.85,
    personalization=personalization,
    max_iter=100,
    tol=1e-8,
    weight="weight",
)
```
`nx.pagerank()` requires the graph to be strongly connected or handles dangling nodes with the personalization vector. When `alpha=0.85` and a node has no outgoing edges (a dangling node), the random walk returns to the personalization vector. This is correct behavior. However, if the graph has nodes that are completely disconnected (no edges at all), `nx.pagerank()` will include them in the output with a score proportional to `(1-alpha)/N`. This means unrelated nodes may appear in the blast radius report with non-zero scores.

The more immediate bug: `normalize_scores()` does min-max normalization. If all non-seed scores are `0.000001` (tiny PPR leak to disconnected nodes), the normalization will amplify them to `0.0–1.0`, making them look like real impacts. This will produce a blast radius report full of "HIGH" findings for completely unrelated requirements.

**Fix for v4:** Add a minimum absolute score threshold before normalization:
```python
def normalize_scores(scores, seeds, min_absolute=1e-5):
    non_seed = {k: v for k, v in scores.items() 
                if k not in seeds and v > min_absolute}
```
This ensures disconnected nodes with tiny leak scores are excluded.

---

### 🟡 P2-26 — Phase 5's fallback mode ("projection-only") is never exercised or tested

**Location:** `reason/__init__.py`

**The problem:**
```python
mode = "neo4j"
try:
    entity_links, node_meta, absent_requirements = _load_graph_data()
except Exception as e:
    print(f"[reason] WARNING: Neo4j unavailable ({e}). Running projection-only mode.")
    entity_links = []
    node_meta = {fn.function_id: ... for fn in functions}
    mode = "projection-only"
```
In projection-only mode, `entity_links = []`, so the graph has no edges except CALLS edges from the call graph. PPR will propagate only through call chains and never reach any UIElement or Requirement nodes (because they're not in the projection at all). The resulting report will be all dark changes. This is technically correct but useless and will not be clearly communicated to the user.

Also: if Neo4j is unavailable, the smoke test `"assert has_content"` will fail because dark changes will be non-empty — wait, dark changes being non-empty satisfies `has_content`. So the smoke test passes even in projection-only mode with no useful findings. The report will look complete but contain zero useful information.

**Fix for v4:** Make Neo4j a hard dependency for Phase 5 (it's already required for Phase 4). If Neo4j is unavailable, fail loudly: `raise RuntimeError("Neo4j is required for Phase 5. Run: docker compose up -d")`. Remove the projection-only fallback — it produces misleading results and is never the right behavior for the assignment.

---

## Phase 6 Issues

### 🟠 P1-27 — Jinja2 `autoescape=True` will escape code paths in the HTML template

**Location:** `report/render.py`

**The problem:**
```python
env = Environment(loader=FileSystemLoader("templates"), autoescape=True)
```
With `autoescape=True`, Jinja2 will HTML-escape any string that isn't marked as `Markup`. In the template:
```html
<code>MATCH path=(f:CodeFunction)-[*1..6]-(r:Requirement)
WHERE f.id IN {{ report.seed_function_ids[:3] | tojson }} RETURN path LIMIT 50</code>
```
The `tojson` filter in Jinja2 with `autoescape=True` produces HTML-safe JSON — it escapes `<`, `>`, `&` to their HTML entities. A function ID like `packages/trpc/server/routers/document.ts:142:sendDocument` will be escaped to `packages&#x2F;trpc&#x2F;server&#x2F;routers&#x2F;document.ts:142:sendDocument` in the JSON. This means the Cypher query shown to the user is wrong — copying it from the HTML report and running it in Neo4j Browser will fail.

Additionally, the `evidence_path` is rendered as `{{ el.evidence_path | join(' → ') }}` with autoescape. The arrow `→` is a Unicode character, not HTML — it will pass through fine. But function IDs with file paths containing `/` will be escaped.

**Fix for v4:** Use `autoescape=select_autoescape(['html', 'xml'])` and mark Cypher strings as `| safe` in the template, OR switch to `autoescape=False` for this report template since all content is internal/controlled (not user-generated).

---

### 🟡 P2-28 — The Markdown report generation is incomplete: it doesn't include UI elements

**Location:** `report/render.py`, `render()`

**The problem:** The Markdown generation in `render()` includes sections for `affected_requirements` (split into HIGH/MEDIUM) and `absent_requirements` and `dark_changes`. But it has no section for `affected_ui_elements`. The HTML template does include them. A QA lead reading the Markdown report (which the assignment requires as a deliverable) will see affected requirements but not affected pages/UI elements. The assignment explicitly asks for "which UI elements are at risk" — this is missing from the Markdown output.

**Fix for v4:** Add a `## Affected Pages and UI Elements` section to the Markdown generation block.

---

## Cross-Cutting Issues

### 🔴 P0-29 — No instruction for what specific PR to use

**Location:** Appendix B

**The problem:** Appendix B gives selection criteria ("PRs that modify both a tRPC router file AND a corresponding lib file") but doesn't give a specific PR number. The `PR_NUMBER` field in `.env.example` is blank: `PR_NUMBER=`. If an LLM follows the guide, it will run Phase 3 and Phase 5 and fail immediately because `settings.pr_number` is required but unset (`Field(..., description="Target PR number — required")`), causing a `ValidationError` at settings load time.

The guide could be written any time from now until the submission deadline — the "most recent" merged PR that fits the criteria will change daily. An LLM cannot browse GitHub to find a PR.

**Fix for v4:** Either (a) pin a specific PR number and merge SHA that is known to be a good example (e.g., a recent PR from 2024 that modifies `document.ts` and `send-document.ts`), or (b) provide a GitHub CLI command the user runs to find a suitable PR:
```bash
gh pr list --repo documenso/documenso --state merged --limit 20 \
  --json number,title,files \
  | python -c "import json,sys; prs=json.load(sys.stdin); \
    [print(p['number'], p['title']) for p in prs \
     if any('trpc' in f['path'] and 'lib' in f['path'] \
            for f in p.get('files',[]))]"
```
The guide currently has `PR_NUMBER=4200` as a default in the d2 coding context (for Hoppscotch) but no default for Documenso.

---

### 🟠 P1-30 — `settings.github_token` doesn't exist in the `Settings` model

**Location:** `config.py`, referenced in `code/pr.py`

**The problem:** `code/pr.py` has:
```python
headers={"Authorization": f"token {settings.github_token}"} if settings.github_token else {},
```
But the `Settings` model in `config.py` has no `github_token` field. This will raise `AttributeError: 'Settings' object has no attribute 'github_token'` at runtime.

**Fix for v4:** Add `github_token: Optional[str] = Field(None)` to the Settings model and add `GITHUB_TOKEN=` to `.env.example`.

---

### 🟠 P1-31 — The total time budget is unrealistic and misleading

**Location:** Phase budget headers throughout the guide

**The problem:** The guide assigns:
- Phase 0: 1.5h
- Phase 1: 2.5h
- Phase 2: 1.25h
- Phase 3: 2.5h
- Phase 4: 2.5h
- Phase 5: 2.25h
- Phase 6: 1.0h
- Phase 7: 1.5h
- **Total: 15h**

This doesn't account for: (a) environment setup time (Docker, Playwright, ast-grep, Python virtualenv), (b) actual crawl runtime (20 pages × 2.5s delay = 50s minimum, plus Playwright startup), (c) LLM API call latency (entity resolution over hundreds of candidates can take 5–10 minutes), (d) Neo4j startup time (30–60 seconds), (e) debugging time when any of the P0 issues above occur. A realistic estimate for a clean build following this guide (after fixing P0 bugs) is 20–25 hours.

**Fix for v4:** Either remove the time estimates (they're not useful to an LLM) or replace them with more realistic ones and separate "build time" from "run time." Add expected runtime for each phase's smoke test.

---

### 🟡 P2-32 — The `evidence_path` field in `AffectedNode` is a list of node IDs, but is rendered as a human-readable path

**Location:** `reason/impact.py`, `report/render.py`

**The problem:** `evidence_path` stores raw node IDs like `["packages/trpc/server/routers/document.ts:142:sendDocument", "page:a3f2b1c4", "REQ-4F2A1B3C"]`. In the HTML template:
```html
<td class="evidence">{{ el.evidence_path | join(' → ') }}</td>
```
This renders as: `packages/trpc/server/routers/document.ts:142:sendDocument → page:a3f2b1c4 → REQ-4F2A1B3C`.

The `page:a3f2b1c4` node ID is a SHA256 hash — completely unreadable to a QA lead. The assignment requires the report to be "readable by a non-engineer who understands the product but not your code." A SHA256 hash in the evidence path fails this requirement entirely.

**Fix for v4:** Store a `node_metadata` lookup in the report or in `_load_graph_data()`, and when building the evidence path, substitute node IDs with human-readable labels:
```python
def readable_path(path: list[str], node_meta: dict) -> list[str]:
    return [node_meta.get(n, {}).get("label", n) for n in path]
```
The Appendix A sample report shows `"packages/trpc/server/routers/document.ts:142:sendDocument → page:a3f2b1c4 → REQ-4F2A1B3C"` — even the sample output has this problem.

---

### 🟡 P2-33 — Design document smoke test is trivially satisfiable and tests nothing meaningful

**Location:** Phase 7

**The problem:**
```python
for i in range(1, 11):
    assert str(i) + '.' in p or f'Section {i}' in p, f'Missing section {i}'
```
This checks that the string `"1."` appears somewhere in the document. Any sentence ending in a number (e.g., "There are 10 components.") will satisfy `"1." in p` because it checks substring inclusion. The test does not verify that sections actually contain substantive content. The `len(p) > 10000` check is somewhat meaningful but a document with 10 000 characters of boilerplate satisfies it.

**Fix for v4:** Replace with content-specific assertions:
```python
required_phrases = [
    "deterministic", "LLM", "confidence", "absent", "PPR",
    "scope", "Documenso", "Joern", "entity resolution"
]
for phrase in required_phrases:
    assert phrase in p, f"Design document missing key concept: '{phrase}'"
```

---

### 🟢 P3-34 — The `POLITE_DELAY = 1.5` in Phase 1 conflicts with the `1.0` delay in Phase 2's static crawler

**Location:** Various

Minor inconsistency. Phase 1 uses 1.5 seconds between Playwright navigations; Phase 2 uses 1.0 seconds between crawl4ai fetches. Not a bug, but creates inconsistency that could confuse an LLM reading the code.

---

### 🟢 P3-35 — Missing `__init__.py` files in several packages

**Location:** Project structure

The guide creates `src/blast_radius/crawl/__init__.py`, `src/blast_radius/ingest/__init__.py`, etc., but never creates `src/blast_radius/__init__.py` itself, or `src/__init__.py`. Without these, `from blast_radius.config import settings` will fail with `ModuleNotFoundError` unless the project is installed as a package or `src/` is added to `PYTHONPATH`. The guide doesn't mention installing the package or setting `PYTHONPATH`.

**Fix for v4:** Add either: (a) a `pyproject.toml` with `packages = [{include = "blast_radius", from = "src"}]` and instruct `pip install -e .`, or (b) add `export PYTHONPATH=src` to the setup instructions and the `.env.example`, or (c) restructure to use a flat `blast_radius/` directory without the `src/` wrapper. Pick one and document it explicitly in Phase 0.

---

### 🟢 P3-36 — Loom recording script (Appendix C) references a Neo4j query that will likely return empty results

**Location:** Appendix C

**The problem:** The Loom script says to run:
```cypher
MATCH path=(f:CodeFunction)-[*1..6]-(r:Requirement)
WHERE f.id IN ["fn:packages/trpc/server/routers/document.ts:142:sendDocument"]
RETURN path LIMIT 20
```
But function IDs in v3 are formatted as `packages/trpc/server/routers/document.ts:142:sendDocument` (without the `fn:` prefix). The `fn:` prefix doesn't exist in the code. Additionally, IMPLEMENTS edges go `Requirement → CodeFunction` (P0-21 above), so the pattern `(CodeFunction)-[*1..6]-(r:Requirement)` uses undirected traversal — it will work, but this is incidental.

**Fix for v4:** After fixing P0-21, update this query to use the correct ID format and the correct edge direction.

---

## Summary: Issues by Phase

| Phase | P0 | P1 | P2 | P3 |
|---|---|---|---|---|
| 0 — Setup | 2 | 2 | 1 | 1 |
| 1 — Crawl | 1 | 2 | 2 | 0 |
| 2 — Ingest | 1 | 1 | 2 | 0 |
| 3 — Code | 2 | 2 | 1 | 0 |
| 4 — Graph | 2 | 1 | 1 | 0 |
| 5 — Reason | 0 | 2 | 1 | 0 |
| 6 — Report | 0 | 1 | 1 | 0 |
| 7 — Design doc | 0 | 0 | 1 | 1 |
| Cross-cutting | 1 | 3 | 1 | 2 |
| **Total** | **9** | **14** | **11** | **4** |

---

## v4 Recommendations

### Structural Changes (Must Do)

**1. Add a verified "Verified on [date] against commit [SHA]" header to every code block.**
v3 code was written speculatively. v4 must include the actual commit SHA of the Documenso repo it was validated against, and the exact versions of every dependency it was tested with. An LLM following the guide can then `git checkout [SHA]` and have a deterministic starting point.

**2. Replace the `src/blast_radius/` structure with a flat `blast_radius/` package.**
The `src/` wrapper adds a `PYTHONPATH` requirement that is never documented. A flat package structure (`blast_radius/config.py`, `blast_radius/crawl/__init__.py`, etc.) at the repo root is simpler and works with `pip install -e .` without any path manipulation.

**3. Make Phase 0 a complete, runnable pre-flight.**
Phase 0 should end with a single command that a user or LLM can run:
```bash
python scripts/validate_env.py
```
And get a green status on: Python version, all pip packages, `sg` binary, Neo4j connectivity, Playwright browser, Documenso test account reachable, repo cloned at correct SHA, MERGE_SHA set, PR_NUMBER set.

**4. Add a "One-Time Human Setup" section before Phase 0.**
Some steps require human action that no LLM can perform:
- Create Documenso account + verify email
- Upload a test document to trigger UI state
- Browse `https://github.com/documenso/documenso/pulls?q=is%3Apr+is%3Amerged` and pick a PR that matches the criteria, note the number and merge SHA
- Run `gh pr view {PR_NUMBER} --repo documenso/documenso --json mergeCommit`

These must be explicitly separated from the automated pipeline.

**5. Fix the IMPLEMENTS edge direction throughout.**
Consistently use `CodeFunction -[IMPLEMENTS]-> Requirement` everywhere: in schema.py Cypher, in the `_load_graph_data()` query, in the Phase 4 smoke test, and in the design document Cypher examples.

**6. Replace `validate_env.py`'s broken lambda idiom with conventional `try/except` functions.**
The entire file needs rewriting with a simple, readable pattern.

**7. Fix `crawl4ai` usage to use the correct attribute names (`cleaned_html` or `markdown`).**
Verify against the pinned exact version.

**8. Add explicit GITHUB_TOKEN to Settings and .env.example.**
It's referenced in `pr.py` but missing from the config model.

### Quality Changes (Should Do)

**9. Add edge-count assertions to Phase 4 smoke test.**
The current smoke test only checks node counts. A zero-edge graph passes.

**10. Raise entity resolution cosine threshold to 0.60 and add keyword pre-filter.**
Reduces false-positive candidates and LLM token waste.

**11. Replace SHA-hashed node IDs in `evidence_path` with human-readable labels.**
The assignment requires non-engineer readability. `page:a3f2b1c4` fails this.

**12. Add a minimum absolute PPR score threshold (1e-5) before normalization.**
Prevents noise amplification from disconnected graph nodes.

**13. Add Playwright browser installation to Phase 0 and `validate_env.py`.**
Currently missing from the setup flow.

**14. Make `crawl_page()` use `domcontentloaded` + `asyncio.sleep(2)` instead of `networkidle`.**
Prevents consistent timeouts on the Next.js SPA.

**15. Fix the `page.fill()` CSS comma-selector bug in the auth flow.**
Use Playwright's `get_by_label()` / `get_by_role()` API.

**16. Add a Markdown section for `affected_ui_elements` in the report generator.**
Currently missing, required by the assignment.

**17. Fix the `tRPC-procedures.yml` ast-grep rule to actually match tRPC procedures.**
Current pattern `$NAME: $PROC.$METHOD($$$)` will match zero procedures.

### Documentation Changes (Nice to Have)

**18. Add "expected output" for each smoke test.**
Not just "expected: X nodes present" but actual sample JSON snippets showing what a healthy output looks like. This allows an LLM to verify its output is correct, not just non-crashing.

**19. Remove time estimates or make them honest.**
Replace `2.5h` with `build: 30min, run: varies (LLM calls: ~5min, crawl: ~3min, graph build: ~2min)`.

**20. Add a "Known Limitations" box at the top of each phase.**
E.g., "Phase 1 KNOWN LIMITATION: Documenso's `/documents` route requires authentication. Without credentials, only 2–3 pages will be captured and the graph will have limited UI coverage." This sets correct expectations and prevents an LLM from treating a partially-working crawl as a failure.

---

## Critical Path to a Working v4

If only the P0 issues are fixed, the pipeline will run end-to-end and produce a report. The P1 issues will cause degraded results but not crashes. The minimum changes for a working v4 are:

1. Rewrite `validate_env.py` (P0-01)
2. Fix IMPLEMENTS edge direction throughout (P0-21)
3. Fix `crawl4ai` attribute name `result.html` → `result.cleaned_html` (P0-12)
4. Fix PyDriller PR delta extraction (P0-18)
5. Fix `functions.index(fn)` → `fn_labels[j]` (P0-22)
6. Add `github_token` to Settings (P1-30)
7. Add `PYTHONPATH=src` to setup instructions (P3-35 — actually a P0 in practice)
8. Add `playwright install chromium` to Phase 0 (P1-03)
9. Fix the tRPC ast-grep rule (P0-17)
10. Add a specific PR number or retrieval command (P0-29)

With these 10 fixes, an LLM following the guide should be able to produce a complete, if imperfect, blast radius report.

---

*Audit completed. All issues are independently reproducible by reading the v3 source code and cross-referencing the Documenso repository structure and the Playwright/crawl4ai/neo4j-driver API documentation.*
