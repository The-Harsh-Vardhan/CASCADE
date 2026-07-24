"""
blast_radius/ingest/fetch.py — Fetches all Documenso documentation sources.

Primary sources: GitHub raw MDX files from apps/docs/content/docs/ — these are
static, fully readable, and cover every feature area. The original docs.documenso.com
URLs are JS-rendered and return <2 KB of useful text; MDX files are the canonical
source of truth.

Sources:
  Group A — GitHub raw Markdown (always works)
  1.  README.md
  2.  CONTRIBUTING.md

  Group B — User docs (GitHub MDX)
  3.  mdx_documents_fields   — add-fields.mdx     (signing)
  4.  mdx_documents_send     — send.mdx            (sending)
  5.  mdx_documents_upload   — upload.mdx          (sending)
  6.  mdx_documents_recipients — add-recipients.mdx (sending)
  7.  mdx_templates_create   — create.mdx          (templates)
  8.  mdx_templates_use      — use.mdx             (templates)
  9.  mdx_orgs_overview      — overview.mdx        (teams)
  10. mdx_orgs_members       — members.mdx         (teams)
  11. mdx_orgs_groups        — groups.mdx          (teams)
  12. mdx_settings_security  — security.mdx        (auth)
  13. mdx_settings_api_tokens— api-tokens.mdx      (auth/api)
  14. mdx_settings_profile   — profile.mdx         (admin)

  Group C — Developer docs (GitHub MDX)
  15. mdx_webhooks_events    — events.mdx          (webhooks)
  16. mdx_webhooks_setup     — setup.mdx           (webhooks)
  17. mdx_api_documents      — documents.mdx       (api)
  18. mdx_api_recipients     — recipients.mdx      (api)
  19. mdx_api_templates      — templates.mdx       (api)
  20. mdx_api_auth           — authentication.mdx  (auth)
  21. mdx_docs_index         — index.mdx           (overview)

All sources truncated to MAX_CHARS before passing to the LLM.
"""
import logging
from pathlib import Path

import httpx
from bs4 import BeautifulSoup

from blast_radius.config import settings

logger = logging.getLogger(__name__)

# ── Source registry ────────────────────────────────────────────────────────────

_GH_RAW = "https://raw.githubusercontent.com/documenso/documenso/main"
_MDX    = f"{_GH_RAW}/apps/docs/content/docs"

SOURCES: list[tuple[str, str]] = [
    # Group A — plain Markdown (reliable, large)
    ("README.md",               f"{_GH_RAW}/README.md"),
    ("CONTRIBUTING.md",         f"{_GH_RAW}/CONTRIBUTING.md"),

    # Group B — User docs MDX
    ("mdx_documents_fields",    f"{_MDX}/users/documents/add-fields.mdx"),
    ("mdx_documents_send",      f"{_MDX}/users/documents/send.mdx"),
    ("mdx_documents_upload",    f"{_MDX}/users/documents/upload.mdx"),
    ("mdx_documents_recipients",f"{_MDX}/users/documents/add-recipients.mdx"),
    ("mdx_documents_direct",    f"{_MDX}/users/documents/direct-links.mdx"),
    ("mdx_templates_create",    f"{_MDX}/users/templates/create.mdx"),
    ("mdx_templates_use",       f"{_MDX}/users/templates/use.mdx"),
    ("mdx_orgs_overview",       f"{_MDX}/users/organisations/overview.mdx"),
    ("mdx_orgs_members",        f"{_MDX}/users/organisations/members.mdx"),
    ("mdx_orgs_groups",         f"{_MDX}/users/organisations/groups.mdx"),
    ("mdx_orgs_create_team",    f"{_MDX}/users/organisations/create-team.mdx"),
    ("mdx_settings_security",   f"{_MDX}/users/settings/security.mdx"),
    ("mdx_settings_api_tokens", f"{_MDX}/users/settings/api-tokens.mdx"),
    ("mdx_settings_profile",    f"{_MDX}/users/settings/profile.mdx"),
    ("mdx_gs_send_first",       f"{_MDX}/users/getting-started/send-first-document.mdx"),

    # Group C — Developer docs MDX
    ("mdx_webhooks_events",     f"{_MDX}/developers/webhooks/events.mdx"),
    ("mdx_webhooks_setup",      f"{_MDX}/developers/webhooks/setup.mdx"),
    ("mdx_webhooks_verify",     f"{_MDX}/developers/webhooks/verification.mdx"),
    ("mdx_api_documents",       f"{_MDX}/developers/api/documents.mdx"),
    ("mdx_api_recipients",      f"{_MDX}/developers/api/recipients.mdx"),
    ("mdx_api_templates",       f"{_MDX}/developers/api/templates.mdx"),
    ("mdx_api_auth",            f"{_MDX}/developers/getting-started/authentication.mdx"),
    ("mdx_api_first_call",      f"{_MDX}/developers/getting-started/first-api-call.mdx"),
    ("mdx_docs_index",          f"{_MDX}/index.mdx"),
]

MAX_CHARS = 20_000      # per-source LLM context budget
MIN_CHARS = 200         # skip sources shorter than this

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/json,*/*;q=0.9",
}


# ── Internal helpers ───────────────────────────────────────────────────────────

def _html_to_text(html: str) -> str:
    """Strip HTML tags, scripts, nav, and footer; return clean plain text."""
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "head", "meta", "link"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def _fetch_one(url: str, client: httpx.Client) -> str:
    """
    Fetch a single URL.  HTML responses are stripped to plain text.
    Returns empty string on any error or non-200 status.
    """
    try:
        resp = client.get(url, follow_redirects=True)
    except Exception as exc:
        logger.warning("Network error fetching %s: %s", url, exc)
        return ""

    if resp.status_code != 200:
        logger.warning("HTTP %d for %s -- skipping.", resp.status_code, url)
        return ""

    content_type = resp.headers.get("content-type", "")
    if "html" in content_type:
        return _html_to_text(resp.text)
    # Raw text (markdown, MDX, JSON, plain)
    return resp.text


# ── Public API ─────────────────────────────────────────────────────────────────

def fetch_all_sources() -> list[tuple[str, str]]:
    """
    Fetch all configured documentation sources.

    Returns:
        List of (source_name, text_content) tuples.
        Sources with < MIN_CHARS content are silently dropped.
        Each source is truncated to MAX_CHARS characters.
    """
    results: list[tuple[str, str]] = []

    with httpx.Client(headers=_HEADERS, timeout=20.0) as client:
        for name, url in SOURCES:
            logger.info("Fetching %-30s <- %s", name, url)
            text = _fetch_one(url, client)

            if len(text) < MIN_CHARS:
                logger.warning("  -> Too short (%d chars), skipping '%s'.", len(text), name)
                continue

            truncated = text[:MAX_CHARS]
            results.append((name, truncated))
            logger.info(
                "  -> Captured %d chars%s",
                len(truncated),
                " (truncated)" if len(text) > MAX_CHARS else "",
            )

    # README fallback if the network fetch failed
    names_fetched = {n for n, _ in results}
    if "README.md" not in names_fetched:
        local_readme: Path = settings.repo_clone_dir / "README.md"
        if local_readme.exists():
            logger.info("README.md not fetched online -- using local fallback at %s", local_readme)
            text = local_readme.read_text(encoding="utf-8")
            results.append(("README.md", text[:MAX_CHARS]))
        else:
            logger.warning(
                "README.md unavailable online and no local clone found at %s.", local_readme
            )

    logger.info("Fetch complete: %d/%d sources captured.", len(results), len(SOURCES))
    return results


# Backward-compat shims ──────────────────────────────────────────────────────

def fetch_readme_text() -> tuple[str, str]:
    """Return (source_name, text) for README.md only."""
    for name, text in fetch_all_sources():
        if name == "README.md":
            return name, text
    raise RuntimeError("Could not fetch README.md from network or local clone.")


def fetch_docs_texts() -> list[tuple[str, str]]:
    """Return all sources except README.md."""
    return [(n, t) for n, t in fetch_all_sources() if n != "README.md"]
