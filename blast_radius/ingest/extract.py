"""
blast_radius/ingest/extract.py — LLM-driven requirement extraction.

One LLM call per source using an exhaustive extraction prompt that targets
every button action, user flow, API endpoint, config option, webhook event,
and permission distinction in Documenso.

Deduplication rules (applied after all sources are combined):
  1. Exact title match → keep first occurrence, merge acceptance_criteria
  2. Jaccard word overlap > 70 % → keep the richer (longer) version
Target: 50–80 unique requirements.
"""
import logging
from typing import Any

from blast_radius.llm import call_llm_json
from blast_radius.models import Provenance, Requirement

logger = logging.getLogger(__name__)

# ── Controlled vocabularies ────────────────────────────────────────────────────

VALID_AREAS: frozenset[str] = frozenset(
    {"signing", "sending", "templates", "teams", "webhooks", "api", "auth", "admin", "notifications"}
)
VALID_TYPES: frozenset[str] = frozenset(
    {"feature", "user_story", "constraint", "api_capability"}
)
VALID_PRIORITIES: frozenset[str] = frozenset({"core", "secondary", "nice-to-have"})

# ── Extraction prompt ──────────────────────────────────────────────────────────

_SYSTEM = """\
You are a requirements analyst specializing in document signing platforms.
Extract EVERY distinct product requirement, feature, user story, and API capability
from this documentation about Documenso.

Be EXHAUSTIVE. Each of these must be a separate requirement:
- Every button action (upload document, add recipient, place field, send for signing)
- Every user flow (signing flow, template creation, team invitation)
- Every API endpoint capability described
- Every setting or configuration option
- Every notification or webhook event type
- Every permission or role distinction

Return ONLY a JSON array. Each object must have all fields from the schema below.
No preamble. No markdown. Valid JSON only.

Focus especially on:
- Document lifecycle: upload -> configure -> send -> sign -> complete -> download
- Recipient management: add, configure signing order, set field permissions
- Field types: signature, initials, date, text, checkbox, dropdown
- Template operations: create, use, duplicate, manage
- Team features: invite, roles, shared templates
- Webhook events: document.sent, document.signed, document.completed, etc.
- API token management
- Audit trail and history

IMPORTANT: Return at most 20 requirements per call. Keep acceptance_criteria to
2-3 items max per requirement. This ensures JSON fits within output limits.

JSON schema for every object in the array:
{
  "title":                "<short name, max 8 words>",
  "description":          "<full description of the requirement>",
  "req_type":             "feature" | "user_story" | "constraint" | "api_capability",
  "feature_area":         "signing" | "sending" | "templates" | "teams" | "webhooks"
                          | "api" | "auth" | "admin" | "notifications",
  "acceptance_criteria":  ["<AC 1>", "<AC 2>"],
  "related_ui_keywords":  ["<word likely to appear in UI labels/buttons>"],
  "related_api_endpoints":["<e.g. POST /api/v1/documents>"],
  "priority":             "core" | "secondary" | "nice-to-have"
}"""

_SCHEMA_HINT = (
    '[{"title": "Upload Document", "description": "...", '
    '"req_type": "feature", "feature_area": "sending", '
    '"acceptance_criteria": ["User can upload PDF"], '
    '"related_ui_keywords": ["upload", "document"], '
    '"related_api_endpoints": ["POST /api/v1/documents"], '
    '"priority": "core"}]'
)


def _build_prompt(source_name: str, content: str) -> str:
    return f"{_SYSTEM}\n\nSOURCE: {source_name}\n\nDOCUMENTATION TEXT:\n{content}"


# ── Extraction ─────────────────────────────────────────────────────────────────

async def extract_requirements_from_text(
    source_name: str, text: str
) -> list[dict[str, Any]]:
    """
    Send one LLM call for `source_name` and return raw requirement dicts.
    IDs are NOT assigned here — that happens after deduplication.
    """
    logger.info(
        "Extracting requirements from %-20s (%d chars)", source_name, len(text)
    )
    prompt = _build_prompt(source_name, text)

    try:
        raw: list[dict[str, Any]] = await call_llm_json(
            prompt, schema_hint=_SCHEMA_HINT, temperature=0.1
        )
    except Exception as exc:
        logger.error("LLM call failed for %s: %s", source_name, exc)
        return []

    if not isinstance(raw, list):
        logger.warning("LLM returned non-list for %s — skipping.", source_name)
        return []

    items: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        title = str(item.get("title", "")).strip()
        if not title:
            continue

        # Normalize controlled-vocab fields; fall back to safe defaults
        area = str(item.get("feature_area", "")).lower().strip()
        if area not in VALID_AREAS:
            area = "admin"

        rtype = str(item.get("req_type", "")).lower().strip()
        if rtype not in VALID_TYPES:
            rtype = "feature"

        priority = str(item.get("priority", "")).lower().strip()
        if priority not in VALID_PRIORITIES:
            priority = "secondary"

        items.append(
            {
                "title": title,
                "description": str(item.get("description", title)).strip() or title,
                "req_type": rtype,
                "feature_area": area,
                "acceptance_criteria": [
                    str(ac) for ac in item.get("acceptance_criteria", []) if ac
                ],
                "related_ui_keywords": [
                    str(k).lower()
                    for k in item.get("related_ui_keywords", [])
                    if len(str(k)) >= 3
                ],
                "related_api_endpoints": [
                    str(ep) for ep in item.get("related_api_endpoints", []) if ep
                ],
                "priority": priority,
                "source": source_name,
            }
        )

    logger.info(
        "  → %d valid requirements extracted from %s", len(items), source_name
    )
    return items


# ── Deduplication ──────────────────────────────────────────────────────────────

def _title_words(title: str) -> frozenset[str]:
    """Lowercase word tokens longer than 2 chars (stop-word filtered)."""
    _STOP = {"the", "and", "for", "via", "with", "that", "this", "from"}
    return frozenset(
        w.lower() for w in title.split() if len(w) > 2 and w.lower() not in _STOP
    )


def _jaccard(t1: str, t2: str) -> float:
    """Jaccard similarity of two title word-sets."""
    w1, w2 = _title_words(t1), _title_words(t2)
    if not w1 or not w2:
        return 0.0
    return len(w1 & w2) / len(w1 | w2)


def _detail_score(item: dict[str, Any]) -> int:
    """Higher is better: longer description + more acceptance criteria."""
    return len(item.get("description", "")) + 10 * len(item.get("acceptance_criteria", []))


def deduplicate_raw(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Deduplicate raw requirement dicts:
      1. Exact title match (case-insensitive) → keep first, merge ACs.
      2. Jaccard overlap > 0.70 → keep the richer version.
    """
    unique: list[dict[str, Any]] = []

    for item in items:
        title = item["title"]
        merged = False

        for existing in unique:
            # Rule 1: exact title match
            if existing["title"].lower() == title.lower():
                # Merge acceptance criteria (union, deduped)
                merged_acs = list(
                    dict.fromkeys(
                        existing.get("acceptance_criteria", [])
                        + item.get("acceptance_criteria", [])
                    )
                )
                existing["acceptance_criteria"] = merged_acs
                merged = True
                break

            # Rule 2: high word overlap → keep richer
            if _jaccard(existing["title"], title) > 0.70:
                if _detail_score(item) > _detail_score(existing):
                    # Replace existing with the richer variant but merge ACs
                    merged_acs = list(
                        dict.fromkeys(
                            existing.get("acceptance_criteria", [])
                            + item.get("acceptance_criteria", [])
                        )
                    )
                    existing.update(item)
                    existing["acceptance_criteria"] = merged_acs
                merged = True
                break

        if not merged:
            unique.append(dict(item))  # defensive copy

    logger.info("Dedup: %d raw → %d unique", len(items), len(unique))
    return unique


# ── ID assignment & model conversion ──────────────────────────────────────────

def assign_ids_and_build_requirements(
    items: list[dict[str, Any]],
) -> list[Requirement]:
    """
    Assign stable REQ-NNN IDs (1-indexed) and convert raw dicts to
    `blast_radius.models.Requirement` Pydantic objects.
    """
    requirements: list[Requirement] = []
    for idx, item in enumerate(items, start=1):
        req_id = f"REQ-{idx:03d}"
        source = item.get("source", "unknown")
        title = item["title"]
        description = item.get("description", title)

        prov = Provenance(
            source_file=source,
            excerpt=description[:250],
        )
        req = Requirement(
            requirement_id=req_id,
            text=description,
            req_type=item.get("req_type", "feature"),
            provenance=prov,
            related_ui_keywords=item.get("related_ui_keywords", []),
            coverage_status="UNKNOWN",
            # Extended fields
            title=title,
            description=description,
            feature_area=item.get("feature_area", "admin"),
            acceptance_criteria=item.get("acceptance_criteria", []),
            related_api_endpoints=item.get("related_api_endpoints", []),
            priority=item.get("priority", "secondary"),
            source=source,
        )
        requirements.append(req)

    return requirements


# ── Legacy shim (kept for any code that still calls the old signature) ─────────

def deduplicate_requirements(requirements: list[Requirement]) -> list[Requirement]:
    """Convert Requirement objects → raw dicts → dedup → back to objects."""
    raw = [
        {
            "title": r.title or r.text[:60],
            "description": r.text,
            "req_type": r.req_type,
            "feature_area": r.feature_area,
            "acceptance_criteria": r.acceptance_criteria,
            "related_ui_keywords": r.related_ui_keywords,
            "related_api_endpoints": r.related_api_endpoints,
            "priority": r.priority,
            "source": r.provenance.source_file,
        }
        for r in requirements
    ]
    unique_raw = deduplicate_raw(raw)
    return assign_ids_and_build_requirements(unique_raw)
