"""
blast_radius/crawl/dynamic.py — Playwright-based crawler for Documenso app.
Crawls both authenticated app pages (/documents, /templates, /settings)
and unauthenticated entry points (/, /signin, /signup).
"""
import asyncio
import hashlib
import logging
from typing import Sequence
from pathlib import Path

from blast_radius.config import settings
from blast_radius.models import AccessibilityItem, PageSnapshot, Transition
from blast_radius.crawl.artifacts import save_page_snapshot, get_screenshots_dir

logger = logging.getLogger(__name__)

# Target paths for dynamic crawl
AUTH_TARGET_PATHS = ["/documents", "/templates", "/settings"]
UNAUTH_TARGET_PATHS = ["/signin", "/signup"]


async def crawl_dynamic_pages(max_pages: int = settings.crawl_max_pages) -> list[PageSnapshot]:
    base_url = settings.target_url.rstrip("/")
    user_data_dir = settings.data_dir / "browser_context"
    user_data_dir.mkdir(parents=True, exist_ok=True)
    screenshots_dir = get_screenshots_dir()

    snapshots: list[PageSnapshot] = []
    visited_urls: set[str] = set()

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        logger.info("Starting dynamic Playwright crawl with persistent context at %s", user_data_dir)
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=True,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = context.pages[0] if context.pages else await context.new_page()

        # Target list of path suffixes
        target_paths = AUTH_TARGET_PATHS + UNAUTH_TARGET_PATHS
        count = 0

        for rel_path in target_paths:
            if count >= max_pages:
                break

            target_url = f"{base_url}{rel_path}"
            if target_url in visited_urls:
                continue

            try:
                logger.info("[%d/%d] Crawling dynamic page: %s", count + 1, max_pages, target_url)
                resp = await page.goto(target_url, wait_until="domcontentloaded", timeout=25000)
                await page.wait_for_timeout(2500)

                actual_url = page.url
                visited_urls.add(target_url)
                visited_urls.add(actual_url)

                dom_html = await page.content()
                url_hash = hashlib.sha256(actual_url.encode("utf-8")).hexdigest()[:16]

                # Save screenshot
                screenshot_filename = f"{url_hash}.png"
                screenshot_path = screenshots_dir / screenshot_filename
                await page.screenshot(path=str(screenshot_path), full_page=True)

                # Extract accessibility items
                ax_items: list[AccessibilityItem] = []
                try:
                    elements = await page.locator("a, button, input, select, textarea, [role='button'], h1, h2, h3").all()
                    for idx, el in enumerate(elements[:60]):
                        tag_name = await el.evaluate("node => node.tagName.toLowerCase()")
                        role = await el.get_attribute("role") or tag_name
                        text_val = (await el.text_content() or "").strip()
                        aria_label = await el.get_attribute("aria-label") or ""
                        placeholder = await el.get_attribute("placeholder") or ""
                        name = text_val or aria_label or placeholder

                        ax_items.append(
                            AccessibilityItem(
                                index=idx,
                                tag=tag_name,
                                role=role,
                                name=name[:100],
                                selector=f"{tag_name}:nth-of-type({idx+1})"
                            )
                        )
                except Exception as e:
                    logger.warning("Error constructing AX tree for %s: %s", actual_url, e)

                snapshot = PageSnapshot(
                    url=actual_url,
                    url_sha256=url_hash,
                    dom_snapshot=dom_html,
                    accessibility_tree=ax_items,
                    screenshot_path=str(screenshot_path),
                    transitions=[]
                )

                snapshots.append(snapshot)
                count += 1
                logger.info("Captured %s (URL: %s, %d AX items)", rel_path, actual_url, len(ax_items))

            except Exception as e:
                logger.warning("Failed to crawl dynamic page %s: %s", target_url, e)

        await context.close()

    return snapshots
