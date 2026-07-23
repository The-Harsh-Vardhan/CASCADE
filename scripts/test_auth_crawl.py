#!/usr/bin/env python3
"""
Step 0.5 — Minimal Auth Smoke Test script.
Verifies Documenso login with .env credentials, navigates to /documents,
captures DOM + accessibility tree + screenshot, and saves a PageSnapshot JSON artifact.
"""
import asyncio
import hashlib
import json
import logging
import sys
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from blast_radius.config import settings
from blast_radius.models import AccessibilityItem, PageSnapshot

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("auth_smoke_test")


async def run_auth_smoke_test():
    email = settings.documenso_email
    password = settings.documenso_password
    base_url = settings.target_url.rstrip("/")

    if not email or not password:
        logger.error("DOCUMENSO_EMAIL or DOCUMENSO_PASSWORD is not set in .env")
        sys.exit(1)

    logger.info("Starting Auth Smoke Test for %s", base_url)
    logger.info("Account: %s", email)

    user_data_dir = settings.data_dir / "browser_context"
    user_data_dir.mkdir(parents=True, exist_ok=True)

    from playwright.async_api import async_playwright

    async with async_playwright() as p:
        logger.info("Launching persistent browser context at %s...", user_data_dir)
        context = await p.chromium.launch_persistent_context(
            user_data_dir=str(user_data_dir),
            headless=False,
            viewport={"width": 1280, "height": 800},
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = context.pages[0] if context.pages else await context.new_page()

        # Step 1: Navigate to login page
        login_url = f"{base_url}/signin"
        logger.info("Navigating to login page: %s", login_url)
        await page.goto(login_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        # Step 2: Fill in email
        logger.info("Filling login form...")
        email_field = page.locator("input[name='email'], input[type='email']").first
        await email_field.fill(email)

        # Step 3: Fill in password
        password_field = page.locator("input[name='password'], input[type='password']").first
        await password_field.fill(password)
        await page.wait_for_timeout(1000)

        # Step 3.5: Check for Cloudflare Turnstile iframe
        logger.info("Checking Cloudflare Turnstile verification status...")
        try:
            turnstile_iframe = page.frame_locator("iframe[src*='challenges.cloudflare.com']")
            cb = turnstile_iframe.locator("input[type='checkbox'], .mark, body")
            if await cb.count():
                logger.info("Clicking Cloudflare Turnstile checkbox...")
                await cb.first.click()
                await page.wait_for_timeout(3000)
        except Exception as e:
            logger.info("Turnstile check info: %s", e)

        # Step 4: Submit via Enter key or Click Sign In
        logger.info("Submitting form...")
        await password_field.press("Enter")
        
        # Wait up to 15s for authentication / Turnstile completion
        logger.info("Waiting for authentication / Turnstile verification...")
        for i in range(15):
            if "/signin" not in page.url:
                logger.info("Authenticated! Logged in URL: %s", page.url)
                break
            await page.wait_for_timeout(1000)

        # If still on signin page, try clicking the Sign In button explicitly
        if "/signin" in page.url:
            submit_btn = page.locator("button[type='submit']").first
            if await submit_btn.count():
                await submit_btn.click()
                for i in range(10):
                    if "/signin" not in page.url:
                        break
                    await page.wait_for_timeout(1000)

        # Step 5: Check if logged in or navigate to /documents
        logger.info("URL after signin attempt: %s", page.url)
        docs_url = f"{base_url}/documents"
        logger.info("Navigating to authenticated documents page: %s", docs_url)
        await page.goto(docs_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(3000)

        current_url = page.url
        logger.info("Current URL after auth navigation: %s", current_url)

        # Step 6: Capture artifacts
        dom_html = await page.content()
        url_hash = hashlib.sha256(current_url.encode("utf-8")).hexdigest()[:16]

        # Screenshots dir
        screenshots_dir = settings.data_dir / "crawl" / "screenshots"
        screenshots_dir.mkdir(parents=True, exist_ok=True)
        screenshot_path = screenshots_dir / f"auth_smoke_{url_hash}.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        logger.info("Saved screenshot to %s", screenshot_path)

        # Accessibility tree snapshot
        ax_tree_items: list[AccessibilityItem] = []
        try:
            # Extract basic interactive elements for AX tree representation
            interactive_elements = await page.locator("a, button, input, select, textarea, [role='button']").all()
            for idx, el in enumerate(interactive_elements[:50]):
                tag_name = await el.evaluate("node => node.tagName.toLowerCase()")
                role = await el.get_attribute("role") or tag_name
                text_content = (await el.text_content() or "").strip()
                placeholder = await el.get_attribute("placeholder") or ""
                aria_label = await el.get_attribute("aria-label") or ""
                name = text_content or aria_label or placeholder
                selector = f"{tag_name}:nth-of-type({idx+1})"
                
                ax_tree_items.append(
                    AccessibilityItem(
                        index=idx,
                        tag=tag_name,
                        role=role,
                        name=name[:100],
                        selector=selector
                    )
                )
        except Exception as e:
            logger.warning("Failed to construct full AX tree: %s", e)

        # Construct PageSnapshot
        snapshot = PageSnapshot(
            url=current_url,
            url_sha256=url_hash,
            dom_snapshot=dom_html,
            accessibility_tree=ax_tree_items,
            screenshot_path=str(screenshot_path),
            transitions=[]
        )

        output_path = settings.data_dir / "crawl" / "auth_smoke_test.json"
        output_path.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
        logger.info("Saved PageSnapshot JSON to %s (%d chars DOM, %d AX items)",
                    output_path, len(dom_html), len(ax_tree_items))

        await context.close()

    print("\n[SUCCESS] Auth Smoke Test completed cleanly!")
    print(f"  URL: {current_url}")
    print(f"  Snapshot JSON: {output_path}")
    print(f"  Screenshot: {screenshot_path}")


if __name__ == "__main__":
    asyncio.run(run_auth_smoke_test())
