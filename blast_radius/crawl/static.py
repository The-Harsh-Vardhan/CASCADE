"""
blast_radius/crawl/static.py — Static docs crawler using httpx + BeautifulSoup4.
Capped at 3 pages per scope decision (overview, features, api).
"""
import hashlib
import logging
from typing import Sequence
import httpx
from bs4 import BeautifulSoup

from blast_radius.config import settings
from blast_radius.models import AccessibilityItem, PageSnapshot

logger = logging.getLogger(__name__)

# Primary doc pages (capped at 3)
DOC_URLS = [
    "https://docs.documenso.com",
    "https://docs.documenso.com/overview",
    "https://docs.documenso.com/features",
]


async def crawl_static_docs(urls: Sequence[str] = DOC_URLS) -> list[PageSnapshot]:
    snapshots: list[PageSnapshot] = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }

    async with httpx.AsyncClient(headers=headers, follow_redirects=True, timeout=15.0) as client:
        for url in urls[:3]:  # Explicit 3-page cap
            try:
                logger.info("Fetching static doc page: %s", url)
                resp = await client.get(url)
                if resp.status_code != 200:
                    logger.warning("HTTP %d fetching %s", resp.status_code, url)
                    continue

                html = resp.text
                soup = BeautifulSoup(html, "html.parser")

                # Remove noise elements
                for s in soup(["script", "style", "nav", "footer"]):
                    s.decompose()

                url_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]

                # Basic accessibility representation from headings and links
                ax_items: list[AccessibilityItem] = []
                idx = 0
                for el in soup.find_all(["h1", "h2", "h3", "a", "button"]):
                    tag_name = el.name.lower()
                    text_str = el.get_text(strip=True)
                    if text_str:
                        ax_items.append(
                            AccessibilityItem(
                                index=idx,
                                tag=tag_name,
                                role="heading" if tag_name.startswith("h") else "link",
                                name=text_str[:100],
                                selector=f"{tag_name}:nth-of-type({idx+1})"
                            )
                        )
                        idx += 1

                snapshot = PageSnapshot(
                    url=url,
                    url_sha256=url_hash,
                    dom_snapshot=str(soup),
                    accessibility_tree=ax_items,
                    screenshot_path="",
                    transitions=[]
                )
                snapshots.append(snapshot)
                logger.info("Captured static doc page %s (%d AX items)", url, len(ax_items))
            except Exception as e:
                logger.warning("Failed to crawl static doc page %s: %s", url, e)

    return snapshots
