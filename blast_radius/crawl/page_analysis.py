"""
blast_radius/crawl/page_analysis.py — PageAnalysis dataclass + LLM-powered page analyzer.

Called once per crawled page. Passes condensed page text to call_llm_json()
and returns a structured PageAnalysis object covering all interactive components,
inferred user flows, and the primary Documenso entity the page manages.

LLM invocation follows AGENTS.md rule: always via blast_radius.llm.
"""
from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, field

from blast_radius.llm import call_llm_json

logger = logging.getLogger(__name__)

# ── Prompt ─────────────────────────────────────────────────────────────────────

_SYSTEM_PROMPT = """\
You are analyzing a page from Documenso, an open-source document signing platform.
Extract ALL interactive UI components visible on this page.
For each component identify:
  - type: one of button|input|form|table|modal|nav|card|link|select|textarea|badge|dropdown
  - label: the visible text, placeholder, or aria-label (keep it short)
  - selector_hint: best CSS selector to target this element uniquely
  - purpose: one sentence describing what this element does
  - is_interactive: true if the user can click, type, or activate it

Return ONLY a JSON object with these exact fields (no preamble, no fences):
{
  "purpose": "<one sentence: what does this PAGE do?>",
  "documenso_entity": "<one of: document|template|recipient|field|team|webhook|api_token|user|general>",
  "ui_components": [
    {"type": "...", "label": "...", "selector_hint": "...", "purpose": "...", "is_interactive": true}
  ],
  "user_flows": ["<flow this page participates in, e.g. Document Signing>"],
  "outbound_links": ["<href value>"]
}"""


# ── Dataclass ──────────────────────────────────────────────────────────────────

@dataclass
class PageAnalysis:
    url: str
    title: str
    purpose: str
    ui_components: list[dict]
    outbound_links: list[str]
    user_flows: list[str]
    screenshot_path: str
    requires_auth: bool
    documenso_entity: str

    def to_dict(self) -> dict:
        return asdict(self)


# ── Helpers ────────────────────────────────────────────────────────────────────

def slug(url: str) -> str:
    """Convert a URL to a safe filesystem slug (max 80 chars)."""
    clean = re.sub(r"https?://", "", url)
    clean = re.sub(r"[^a-zA-Z0-9_-]", "_", clean)
    return clean[:80].strip("_") or "page"


def _condense_html(html: str, max_chars: int = 10_000) -> str:
    """Strip scripts/styles/SVG and return plain text for LLM context."""
    try:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")
        for tag in soup(["script", "style", "head", "meta", "link", "svg", "img", "noscript"]):
            tag.decompose()
        return soup.get_text(separator="\n", strip=True)[:max_chars]
    except Exception:
        # Fallback: strip tags with regex
        stripped = re.sub(r"<[^>]+>", " ", html)
        return re.sub(r"\s+", " ", stripped)[:max_chars]


def _guess_entity(url: str) -> str:
    """
    Heuristic entity classification from URL.
    Ordered from most-specific to least-specific so settings routes
    win over bare /documents or /templates matches.
    """
    u = url.lower()
    # Settings sub-pages (most specific first)
    if "/settings/api-token" in u or "/settings/api_token" in u:
        return "api_token"
    if "/settings/team" in u:
        return "team"
    if "/settings/webhook" in u:
        return "webhook"
    if "/settings/profile" in u or "/settings/security" in u:
        return "user"
    # Document sub-pages & doc pages for recipient/field flows
    if "/recipients" in u or "signing-documents" in u or "/recipient" in u:
        return "recipient"
    if "/fields" in u or "sending-documents" in u or "/field" in u:
        return "field"
    # Top-level entity pages
    if "/template" in u:
        return "template"
    if "/document" in u:
        return "document"
    if "/team" in u or "/organisation" in u:
        return "team"
    if "/webhook" in u:
        return "webhook"
    if "/api-token" in u or "/api_token" in u:
        return "api_token"
    if "/profile" in u or "/security" in u:
        return "user"
    return "general"


def _entity_from_url_strict(url: str) -> str | None:
    """
    Return entity ONLY for URL patterns that are unambiguously specific.
    Used to override LLM 'general' classification on known-entity settings pages.
    Returns None if the URL is not a strong indicator.
    """
    u = url.lower()
    # Settings pages are the most common false-general case
    if "/settings/api-token" in u or "/settings/api_token" in u:
        return "api_token"
    if "/settings/team" in u:
        return "team"
    if "/settings/webhook" in u:
        return "webhook"
    if "/settings/profile" in u:
        return "user"
    # Document workflow sub-pages & docs
    if "/recipients" in u or "signing-documents" in u:
        return "recipient"
    if "/fields" in u or "sending-documents" in u:
        return "field"
    # Upload/creation pages clearly belong to their parent entity
    if "/documents/new" in u:
        return "document"
    if "/templates/new" in u:
        return "template"
    return None



# ── Main analyzer ──────────────────────────────────────────────────────────────

async def analyze_page(
    url: str,
    title: str,
    html_content: str,
    screenshot_path: str,
    requires_auth: bool,
) -> PageAnalysis:
    """
    Run LLM page analysis and return a populated PageAnalysis.
    Falls back to a URL-heuristic stub if LLM fails.
    """
    condensed = _condense_html(html_content)
    prompt = (
        f"{_SYSTEM_PROMPT}\n\n"
        f"URL: {url}\n"
        f"Title: {title}\n\n"
        f"Page content (condensed):\n{condensed}"
    )

    try:
        data = await call_llm_json(prompt, temperature=0.1)
        return PageAnalysis(
            url=url,
            title=title,
            purpose=str(data.get("purpose", "")),
            ui_components=list(data.get("ui_components", [])),
            outbound_links=list(data.get("outbound_links", [])),
            user_flows=list(data.get("user_flows", [])),
            screenshot_path=screenshot_path,
            requires_auth=requires_auth,
            documenso_entity=str(data.get("documenso_entity", _guess_entity(url))),
        )
    except Exception as exc:
        logger.warning("LLM analysis failed for %s: %s — using heuristic stub.", url, exc)
        return PageAnalysis(
            url=url,
            title=title,
            purpose=f"Page at {url}",
            ui_components=[],
            outbound_links=[],
            user_flows=[],
            screenshot_path=screenshot_path,
            requires_auth=requires_auth,
            documenso_entity=_guess_entity(url),
        )
