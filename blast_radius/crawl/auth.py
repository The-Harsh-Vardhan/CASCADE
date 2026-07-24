"""
blast_radius/crawl/auth.py — Playwright login flow for app.documenso.com.

Provides two helpers:
  login(page)              — fills email/password and waits for /documents redirect
  find_document_id(page)   — scrapes the documents list to find a real doc ID
                             (needed to build sub-page URLs for the auth crawl)
"""
from __future__ import annotations

import logging
import re

from playwright.async_api import Page

from blast_radius.config import settings

logger = logging.getLogger(__name__)


async def login(page: Page) -> bool:
    """
    Sign in to app.documenso.com using DOCUMENSO_EMAIL + DOCUMENSO_PASSWORD.
    Returns True on success, False if credentials missing or login fails.
    """
    email = settings.documenso_email
    password = settings.documenso_password
    base = settings.documenso_base_url.rstrip("/")

    if not email or not password:
        logger.warning(
            "DOCUMENSO_EMAIL / DOCUMENSO_PASSWORD not configured — "
            "skipping authenticated crawl."
        )
        return False

    signin_url = f"{base}/signin"
    logger.info("Navigating to sign-in: %s", signin_url)

    try:
        await page.goto(signin_url, wait_until="domcontentloaded", timeout=30_000)

        # Wait for React hydration — the form inputs aren't interactive immediately
        try:
            await page.wait_for_load_state("networkidle", timeout=10_000)
        except Exception:
            pass
        await page.wait_for_timeout(2_500)

        # ── Locate email input (broad selector set) ────────────────────────────
        email_sel = (
            'input[type="email"], '
            'input[name="email"], '
            'input[autocomplete="email"], '
            'input[placeholder*="email" i]'
        )
        try:
            email_loc = page.locator(email_sel).first
            await email_loc.wait_for(state="visible", timeout=10_000)
            await email_loc.click()
            await email_loc.fill(email)
            logger.info("Filled email field.")
        except Exception as exc:
            logger.error("Could not fill email field: %s", exc)
            return False

        # ── Locate password input ──────────────────────────────────────────────
        pwd_sel = (
            'input[type="password"], '
            'input[name="password"], '
            'input[autocomplete="current-password"]'
        )
        try:
            pwd_loc = page.locator(pwd_sel).first
            await pwd_loc.wait_for(state="visible", timeout=8_000)
            await pwd_loc.click()
            await pwd_loc.fill(password)
            logger.info("Filled password field.")
        except Exception as exc:
            logger.error("Could not fill password field: %s", exc)
            return False

        # ── Save debug screenshot before submit ────────────────────────────────
        try:
            debug_dir = Path("outputs") / "crawl"
            debug_dir.mkdir(parents=True, exist_ok=True)
            await page.screenshot(path=str(debug_dir / "debug_signin.png"))
            logger.info("Debug screenshot saved to outputs/crawl/debug_signin.png")
        except Exception:
            pass

        # ── Submit — try button click first, then Enter ────────────────────────
        submitted = False
        try:
            btn = page.locator("button[type='submit']").first
            if await btn.count():
                await btn.click()
                submitted = True
                logger.info("Clicked submit button.")
        except Exception as exc:
            logger.warning("Button click failed: %s", exc)

        if not submitted:
            await pwd_loc.press("Enter")
            logger.info("Pressed Enter in password field.")

        # ── Poll URL for redirect (Next.js client-side) ────────────────────────
        await page.wait_for_timeout(3_000)
        for _ in range(30):  # up to 30 s
            current = page.url
            if "/signin" not in current and "/login" not in current:
                break
            await page.wait_for_timeout(1_000)
        else:
            # Save failure screenshot for debugging
            try:
                await page.screenshot(path=str(debug_dir / "debug_signin_fail.png"))
            except Exception:
                pass
            logger.error(
                "Login timed out after 30 s — still on %s. "
                "Check outputs/crawl/debug_signin.png for the form state.",
                page.url,
            )
            return False

        await page.wait_for_timeout(1_500)
        final_url = page.url
        if "/signin" in final_url or "/login" in final_url:
            logger.error("Login did not redirect — credentials may be wrong.")
            return False

        logger.info("Login successful — landed at: %s", final_url)
        return True

    except Exception as exc:
        logger.error("Login raised exception: %s", exc)
        return False


async def find_document_id(page: Page) -> tuple[str, str] | None:
    """
    Navigate to /documents and extract a real document ID from href links.

    Documenso v2 redirects /documents to /t/{team_slug}/documents.
    Returns (url_base_prefix, doc_id) so the caller can build correct sub-page
    URLs like {url_base_prefix}/documents/{doc_id}/recipients.
    Returns None if no document IDs are found.
    """
    base = settings.documenso_base_url.rstrip("/")
    docs_url = f"{base}/documents"

    try:
        await page.goto(docs_url, wait_until="domcontentloaded", timeout=20_000)
        try:
            await page.wait_for_load_state("networkidle", timeout=8_000)
        except Exception:
            pass
        await page.wait_for_timeout(2_000)

        # Record the actual URL after redirect (may be /t/{slug}/documents)
        actual_url = page.url
        # Derive team prefix: everything up to /documents
        if "/documents" in actual_url:
            team_prefix = actual_url.split("/documents")[0]
        else:
            team_prefix = base

        # Collect all hrefs containing /documents/<id>
        hrefs: list[str] = await page.evaluate(
            """
            () => Array.from(document.querySelectorAll('a[href]'))
                  .map(a => a.getAttribute('href'))
                  .filter(h => h && /\\/documents\\/[^/?#]+/.test(h))
            """
        )

        _skip = {"new", "inbox", "", "pending", "completed", "draft", "all", "move"}

        for href in hrefs:
            m = re.search(r"/documents/([^/?#]+)", href)
            if not m:
                continue
            doc_id = m.group(1)
            if doc_id.lower() in _skip:
                continue
            logger.info("Found document ID: %s (team prefix: %s)", doc_id, team_prefix)
            return (team_prefix, doc_id)

        logger.warning(
            "No usable document IDs found on %s "
            "(account may have no documents).",
            actual_url,
        )
        return None

    except Exception as exc:
        logger.warning("find_document_id raised exception: %s", exc)
        return None
