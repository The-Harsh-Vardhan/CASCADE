"""
blast_radius/ingest/fetch.py — Fetches requirement source texts from README.md and static doc pages.
Uses httpx with local repo fallback for README.md.
"""
import logging
from pathlib import Path
import httpx
from bs4 import BeautifulSoup

from blast_radius.config import settings

logger = logging.getLogger(__name__)

RAW_README_URL = "https://raw.githubusercontent.com/documenso/documenso/main/README.md"
DOC_PAGES = [
    ("https://docs.documenso.com", "docs_home.html"),
    ("https://docs.documenso.com/overview", "docs_overview.html"),
    ("https://docs.documenso.com/features", "docs_features.html"),
]


def fetch_readme_text() -> tuple[str, str]:
    """Fetches raw README.md content. Returns (source_name, text)."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        logger.info("Fetching README.md from GitHub raw URL: %s", RAW_README_URL)
        resp = httpx.get(RAW_README_URL, headers=headers, follow_redirects=True, timeout=15.0)
        if resp.status_code == 200 and len(resp.text) > 500:
            return ("README.md", resp.text)
    except Exception as e:
        logger.warning("Failed to fetch online README.md: %s", e)

    # Fallback to cloned repo README.md
    local_readme = settings.repo_clone_dir / "README.md"
    if local_readme.exists():
        logger.info("Reading local fallback README.md at %s", local_readme)
        return ("README.md", local_readme.read_text(encoding="utf-8"))

    raise RuntimeError("Could not fetch README.md online or from local repo clone.")


def fetch_docs_texts() -> list[tuple[str, str]]:
    """Fetches static doc page texts (capped at 3 pages). Returns list of (source_name, text)."""
    results: list[tuple[str, str]] = []
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

    with httpx.Client(headers=headers, follow_redirects=True, timeout=15.0) as client:
        for url, name in DOC_PAGES[:3]:  # Capped at 3 pages per scope decision
            try:
                logger.info("Fetching doc page text from %s", url)
                resp = client.get(url)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for s in soup(["script", "style", "nav", "footer"]):
                        s.decompose()
                    clean_text = soup.get_text(separator="\n", strip=True)
                    if len(clean_text) > 200:
                        results.append((name, clean_text))
            except Exception as e:
                logger.warning("Failed to fetch doc page %s: %s", url, e)

    return results
