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

### blast_radius/crawl/__init__.py

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

### blast_radius/ingest/__init__.py

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

### blast_radius/code/__init__.py

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
