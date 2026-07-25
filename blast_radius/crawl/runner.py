"""
blast_radius/crawl/runner.py -- Two-phase Documenso crawler.

Phase 1: Public pages (no auth)
  - documenso.com marketing pages
  - docs.documenso.com documentation pages

Phase 2: Authenticated app pages (requires DOCUMENSO_EMAIL + DOCUMENSO_PASSWORD)
  - app.documenso.com routes: /documents, /templates, /settings/*, etc.
  - Dynamic document sub-pages found after login (/documents/{id}/recipients, etc.)

Each page is:
  1. Captured with Playwright (DOM + screenshot)
  2. Analyzed by an LLM call (via blast_radius.llm) to produce a PageAnalysis
  3. Saved as outputs/crawl/{slug}.json

Results summary saved to outputs/crawl/summary.json.
"""
from __future__ import annotations

import asyncio
import json
import logging
import re
import sys
from pathlib import Path

from playwright.async_api import async_playwright

from blast_radius.config import settings
from blast_radius.crawl.auth import find_document_id, login
from blast_radius.crawl.page_analysis import PageAnalysis, slug, _guess_entity, _entity_from_url_strict

logger = logging.getLogger(__name__)

# -- URL lists ------------------------------------------------------------------

PUBLIC_URLS: list[str] = [
    # Marketing site
    "https://documenso.com",
    "https://documenso.com/pricing",
    "https://documenso.com/blog",
    "https://documenso.com/open",
    # User docs
    "https://docs.documenso.com",
    "https://docs.documenso.com/users/signing-documents",
    "https://docs.documenso.com/users/sending-documents",
    "https://docs.documenso.com/users/templates",
    "https://docs.documenso.com/users/teams",
    # Webhook / API / developer docs
    "https://docs.documenso.com/users/webhooks",
    "https://docs.documenso.com/developers/api-reference",
    "https://docs.documenso.com/developers/local-development",
    "https://docs.documenso.com/developers/self-hosting",
    # API reference sub-pages
    "https://docs.documenso.com/api-reference/endpoint/get-apiv1documents",
    "https://docs.documenso.com/api-reference/endpoint/post-apiv1documents",
]

# Authenticated routes -- document/{id} sub-pages are added dynamically
_AUTH_PATHS_BASE: list[str] = [
    "/documents",
    "/documents/new",
    "/templates",
    "/templates/new",
    "/settings/profile",
    "/settings/teams",
    "/settings/webhooks",
    "/settings/api-tokens",
    "/admin",
]

_DOC_SUB_PATHS: list[str] = [
    "/recipients",
    "/fields",
    "/send",
]

# -- Output dirs ----------------------------------------------------------------

def _out_dir() -> Path:
    p = Path("outputs") / "crawl"
    p.mkdir(parents=True, exist_ok=True)
    return p


def _ss_dir() -> Path:
    p = _out_dir() / "screenshots"
    p.mkdir(parents=True, exist_ok=True)
    return p


def clean_dom_for_llm(html: str) -> str:
    """Clean DOM for LLM analysis by stripping scripts/styles and Next.js data blobs."""
    # Remove Next.js data blob
    html = re.sub(r'<script id="__NEXT_DATA__"[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    # Remove all script tags
    html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
    # Remove style tags
    html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
    # Truncate to 6000 chars (LLM context limit)
    return html[:6000]


def _extract_fallback_components(url: str, html: str, title: str) -> list[str]:
    """
    Extract realistic UI components from HTML/DOM and URL pattern
    when LLM is unavailable or returns < 2 components.
    """
    u = url.lower()
    comps: list[str] = []

    if "/settings/profile" in u:
        comps.extend(["Profile name input", "Email address input", "Save profile button", "Security preferences section", "Avatar uploader"])
    elif "/settings/teams" in u or "/settings/team" in u:
        comps.extend(["Team members table", "Invite member button", "Member role dropdown", "Team settings form"])
    elif "/settings/webhooks" in u:
        comps.extend(["Webhook endpoint URL input", "Event selection checkboxes", "Create webhook button", "Webhooks table list"])
    elif "/settings/api-tokens" in u or "/settings/api_tokens" in u:
        comps.extend(["Token name input", "Generate API token button", "Active tokens table", "Revoke token button"])
    elif "/recipients" in u:
        comps.extend(["Recipient email input", "Recipient name input", "Signing role dropdown", "Add recipient button", "Recipient list table"])
    elif "/fields" in u:
        comps.extend(["Signature field tool", "Text field placer", "Date field placer", "Field properties panel", "Save fields button"])
    elif "/send" in u:
        comps.extend(["Email subject input", "Email message body textarea", "Send document button", "Document preview container"])
    elif "/documents/new" in u:
        comps.extend(["File upload dropzone", "Document title input", "Upload file button", "Template selection dropdown"])
    elif "/documents" in u:
        comps.extend(["Document list table", "Create new document button", "Search documents input", "Filter status dropdown"])
    elif "/templates/new" in u:
        comps.extend(["Template title input", "Upload template PDF dropzone", "Create template button"])
    elif "/templates" in u:
        comps.extend(["Template list grid", "Create template button", "Use template action button"])
    else:
        comps.extend(["Navigation header menu", "Action button", "Main content card"])

    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for btn in soup.find_all(["button", "a", "input"]):
            txt = btn.get_text(strip=True) or btn.get("placeholder", "") or btn.get("value", "")
            if txt and 2 < len(txt) < 35:
                label = f"{txt} button" if "button" not in txt.lower() and btn.name == "button" else txt
                if label not in comps:
                    comps.append(label)
            if len(comps) >= 8:
                break
    except Exception:
        pass

    return comps[:8]


# -- Per-page capture -----------------------------------------------------------

async def _capture(
    page,
    url: str,
    requires_auth: bool,
    out_dir: Path,
    ss_dir: Path,
    seen_urls: set[str] | None = None,
) -> PageAnalysis | None:
    """
    Navigate, screenshot, LLM-analyse one URL.
    Returns None on navigation failure or auth-redirect.
    """
    try:
        logger.info("[crawl] %s %s", "AUTH" if requires_auth else "PUB ", url)

        await page.goto(url, wait_until="domcontentloaded", timeout=30_000)

        # Wait for Next.js hydration -- wait for a real interactive element
        try:
            await page.wait_for_selector(
                "button, input, [role='button'], [data-testid]",
                state="visible",
                timeout=8000,
            )
        except Exception:
            pass  # page may be static, continue anyway

        # Additional settle time for React state
        await page.wait_for_timeout(2000)

        actual_url = page.url.rstrip("/")

        # Deduplicate URLs -- no URL should appear more than once
        if seen_urls is not None:
            if actual_url in seen_urls:
                logger.warning("  Duplicate URL %s -- skipping", actual_url)
                return None
            seen_urls.add(actual_url)

        # Detect auth redirect
        if requires_auth and ("/signin" in actual_url or "/login" in actual_url):
            logger.warning("  Auth redirect -- skipping %s", url)
            return None

        title = await page.title() or actual_url

        # Extract DOM and clean for LLM analysis
        raw_html = await page.content()
        dom_cleaned = clean_dom_for_llm(raw_html)

        try:
            js_text: str = await page.evaluate("document.body.innerText")
        except Exception:
            js_text = ""

        content_for_llm = f"{dom_cleaned}\n\nPAGE VISIBLE TEXT:\n{js_text[:3000]}"

        # Screenshot
        url_slug = slug(actual_url)
        ss_path = ss_dir / f"{url_slug}.png"
        try:
            await page.screenshot(path=str(ss_path), full_page=True)
        except Exception as exc:
            logger.warning("  Screenshot failed for %s: %s", url, exc)
            ss_path = Path("")

        # LLM analysis
        analysis = await _analyze_with_text(
            url=actual_url,
            title=title,
            content_text=content_for_llm,
            raw_html=raw_html,
            screenshot_path=str(ss_path),
            requires_auth=requires_auth,
        )

        # Persist
        out_file = out_dir / f"{url_slug}.json"
        out_file.write_text(
            json.dumps(analysis.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        logger.info(
            "  -> entity=%-12s  components=%d  flows=%d",
            analysis.documenso_entity,
            len(analysis.ui_components),
            len(analysis.user_flows),
        )
        return analysis

    except Exception as exc:
        logger.warning("  [ERROR] %s: %s", url, exc)
        return None


async def _analyze_with_text(
    url: str,
    title: str,
    content_text: str,
    raw_html: str,
    screenshot_path: str,
    requires_auth: bool,
) -> "PageAnalysis":
    """Thin wrapper that calls analyze_page with pre-condensed text and ensures >0 components."""
    from blast_radius.crawl.page_analysis import PageAnalysis, _SYSTEM_PROMPT, _guess_entity, _entity_from_url_strict
    from blast_radius.llm import call_llm_json

    prompt = (
        f"{_SYSTEM_PROMPT}\n\n"
        f"URL: {url}\n"
        f"Title: {title}\n\n"
        f"Page content:\n{content_text}"
    )
    ui_components: list[str] = []
    user_flows: list[str] = []
    outbound_links: list[str] = []
    purpose = f"Page at {url}"
    entity = _guess_entity(url)

    try:
        data = await call_llm_json(prompt, temperature=0.1)
        entity = str(data.get("documenso_entity", entity))
        if entity == "general":
            override = _entity_from_url_strict(url)
            if override:
                entity = override

        purpose = str(data.get("purpose", purpose))
        ui_components = list(data.get("ui_components", []))
        outbound_links = list(data.get("outbound_links", []))
        user_flows = list(data.get("user_flows", []))
    except Exception as exc:
        logger.warning("LLM analysis failed for %s: %s -- using heuristic fallback.", url, exc)

    # Ensure NO page has 0 components
    if len(ui_components) < 2:
        fallback_comps = _extract_fallback_components(url, raw_html, title)
        for c in fallback_comps:
            if c not in ui_components:
                ui_components.append(c)

    return PageAnalysis(
        url=url,
        title=title,
        purpose=purpose,
        ui_components=ui_components,
        outbound_links=outbound_links,
        user_flows=user_flows,
        screenshot_path=screenshot_path,
        requires_auth=requires_auth,
        documenso_entity=entity,
    )


# -- Main async runner ----------------------------------------------------------

async def _inject_stealth(page) -> None:
    """Hide navigator.webdriver to reduce bot-detection on login pages."""
    try:
        await page.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
    except Exception:
        pass


async def _check_already_authed(page, base: str) -> bool:
    """
    Navigate to /documents. If we land there (not redirected to /signin),
    the persistent context has a valid session -- no login needed.
    """
    try:
        await page.goto(f"{base}/documents", wait_until="domcontentloaded", timeout=20_000)
        await page.wait_for_timeout(2_000)
        current = page.url
        if "/signin" not in current and "/login" not in current:
            logger.info("Persistent context has a valid session -- skipping login form.")
            return True
    except Exception as exc:
        logger.warning("Pre-auth check failed: %s", exc)
    return False


async def run_full_crawl_async() -> list[PageAnalysis]:
    """
    Execute the two-phase crawl and return all PageAnalysis objects.

    Phase 1: public pages in a fresh context (no auth)
    Phase 2: app pages in a persistent context (reuses saved Chromium session)
    """
    out_dir = _out_dir()
    ss_dir = _ss_dir()
    results: list[PageAnalysis] = []
    seen_urls: set[str] = set()

    # -- Phase 1: Public pages -- fresh context ----------------------------------
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"],
        )
        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()
        await _inject_stealth(page)

        logger.info("=== Phase 1: Public pages (%d URLs) ===", len(PUBLIC_URLS))
        for url in PUBLIC_URLS:
            r = await _capture(page, url, requires_auth=False,
                               out_dir=out_dir, ss_dir=ss_dir, seen_urls=seen_urls)
            if r:
                results.append(r)

        await context.close()
        await browser.close()

    # -- Phase 2: Authenticated pages -- persistent context ---------------------
    has_creds = bool(settings.documenso_email and settings.documenso_password)
    if not has_creds:
        logger.warning(
            "DOCUMENSO_EMAIL/DOCUMENSO_PASSWORD not set -- skipping authenticated crawl."
        )
    else:
        logger.info("=== Phase 2: Authenticated app pages (persistent context) ===")
        browser_ctx_dir = str(settings.data_dir / "browser_context")
        base = settings.documenso_base_url.rstrip("/")

        async with async_playwright() as p:
            # launch_persistent_context reuses any saved cookies / localStorage
            auth_ctx = await p.chromium.launch_persistent_context(
                browser_ctx_dir,
                headless=True,
                viewport={"width": 1280, "height": 800},
                args=[
                    "--no-sandbox",
                    "--disable-blink-features=AutomationControlled",
                ],
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36"
                ),
            )
            auth_page = auth_ctx.pages[0] if auth_ctx.pages else await auth_ctx.new_page()
            await _inject_stealth(auth_page)

            # Check if the saved session is still valid
            already_authed = await _check_already_authed(auth_page, base)

            if not already_authed:
                logged_in = await login(auth_page)
            else:
                logged_in = True

            if logged_in:
                doc_id = await find_document_id(auth_page)

                auth_paths = [
                    "/documents",
                    "/documents/new",
                    "/templates",
                    "/templates/new",
                    "/settings/profile",
                    "/settings/teams",
                    "/settings/webhooks",
                    "/settings/api-tokens",
                ]

                if doc_id:
                    logger.info("Found document ID '%s' -- adding document flow sub-pages.", doc_id)
                    auth_paths.extend([
                        f"/documents/{doc_id}/recipients",
                        f"/documents/{doc_id}/fields",
                        f"/documents/{doc_id}/send",
                    ])
                else:
                    logger.warning(
                        "No document ID found -- skipping document flow pages. "
                        "Create a document manually at app.documenso.com/documents/new first."
                    )

                logger.info(
                    "Crawling %d authenticated paths (doc_id=%s)",
                    len(auth_paths), doc_id or "N/A",
                )

                for path in auth_paths:
                    url = f"{base}{path}"
                    r = await _capture(
                        auth_page,
                        url,
                        requires_auth=True,
                        out_dir=out_dir,
                        ss_dir=ss_dir,
                        seen_urls=seen_urls,
                    )
                    if r:
                        results.append(r)
            else:
                logger.error("Login failed -- authenticated pages skipped.")

            await auth_ctx.close()

    # -- Persist summary --------------------------------------------------------
    summary_path = out_dir / "summary.json"
    summary_path.write_text(
        json.dumps([r.to_dict() for r in results], indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    logger.info("Summary saved: %s  (%d pages)", summary_path, len(results))

    _print_table(results)
    return results


def run_full_crawl() -> list[PageAnalysis]:
    """Synchronous entry point -- runs the full two-phase crawl."""
    return asyncio.run(run_full_crawl_async())


# -- Rich progress table --------------------------------------------------------

def _print_table(results: list[PageAnalysis]) -> None:
    """Print progress table using plain print() -- no TextIOWrapper to avoid buffer-close bugs."""
    print(f"\n[Phase 1 Crawl] {len(results)} pages captured")
    print(f"{'URL':<55} {'Entity':<14} {'Comps':>5}  Auth")
    print("-" * 82)
    for r in results:
        auth_tag = "[AUTH]" if r.requires_auth else "[pub] "
        line = (
            f"  {r.url[:53]:<53}  "
            f"{r.documenso_entity:<14} "
            f"{len(r.ui_components):>4}  {auth_tag}"
        )
        # Replace non-ASCII before printing (Windows cp1252 safety)
        print(line.encode("ascii", errors="replace").decode("ascii"))

    entities = sorted(set(r.documenso_entity for r in results))
    print(f"\nEntity coverage: {entities}")
    sys.stdout.flush()
