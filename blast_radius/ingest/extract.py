"""
blast_radius/ingest/extract.py — LLM-driven requirement extraction.
Tuned prompt explicitly hunts for IMPLICIT feature requirements (capabilities/specs
mentioned in docs that aren't structured as explicit user stories) — prime GapNode candidates.
"""
import hashlib
import logging
from typing import Any
from blast_radius.llm import call_llm_json
from blast_radius.models import Provenance, Requirement

logger = logging.getLogger(__name__)

EXTRACTION_PROMPT = """
You are an expert AI Product Engineer analyzing software documentation for Documenso (an open-source e-signature platform).

Analyze the following documentation text from source "{source_name}".

Extract ALL product requirements and capabilities. You MUST explicitly hunt for BOTH:
1. EXPLICIT REQUIREMENTS: Features, user stories, and workflows directly stated (e.g., "Users can upload documents", "Send signature requests").
2. IMPLICIT REQUIREMENTS: Capabilities, integrations, data fields, or architectural features mentioned casually or in feature lists/tables (e.g., "Supports custom branding", "PDF field placement", "tRPC API integration", "Audit log persistence", "Passkey authentication"). These implicit features are critical for tracking missing code/UI coverage (GapNodes).

Respond strictly with a JSON list of objects matching this schema:
[
  {{
    "text": "Full concise statement of the requirement or feature capability",
    "req_type": "explicit" | "implicit" | "non-functional" | "integration",
    "excerpt": "Exact short sentence or phrase from text supporting this finding",
    "related_ui_keywords": ["keyword1", "keyword2", "keyword3"]
  }}
]

Rules:
- Extract at least 8 to 15 distinct requirements if content allows.
- "related_ui_keywords" should contain 2-5 lowercase nouns relevant to UI elements or API routers (e.g., "document", "template", "recipient", "signature", "email", "setting", "auth").
- Do NOT include generic filler words in related_ui_keywords like "page", "app", "view".

SOURCE TEXT ({source_name}):
{content}
"""


async def extract_requirements_from_text(source_name: str, text: str) -> list[Requirement]:
    logger.info("Extracting requirements via Gemini LLM from source: %s (%d chars)", source_name, len(text))
    
    # Truncate text if excessively long to fit within context comfortably
    content_sample = text[:15000]

    prompt = EXTRACTION_PROMPT.format(source_name=source_name, content=content_sample)
    schema_hint = '[{"text": "...", "req_type": "implicit", "excerpt": "...", "related_ui_keywords": ["doc", "sign"]}]'

    raw_items: list[dict[str, Any]] = await call_llm_json(prompt, schema_hint=schema_hint, temperature=0.1)

    requirements: list[Requirement] = []
    for idx, item in enumerate(raw_items):
        text_str = item.get("text", "").strip()
        if not text_str:
            continue

        excerpt_str = item.get("excerpt", text_str[:100])
        req_type = item.get("req_type", "feature")
        ui_keywords = item.get("related_ui_keywords", [])

        # BUG-13 Fix: Use 16-character SHA hex to prevent collisions
        content_sha = hashlib.sha256(f"{source_name}:{text_str}".encode("utf-8")).hexdigest()[:16].upper()
        req_id = f"REQ-{content_sha}"

        prov = Provenance(
            source_file=source_name,
            excerpt=excerpt_str[:250]
        )

        req = Requirement(
            requirement_id=req_id,
            text=text_str,
            req_type=req_type,
            provenance=prov,
            related_ui_keywords=[k.lower() for k in ui_keywords if len(k) >= 3],
            coverage_status="UNKNOWN"
        )
        requirements.append(req)

    logger.info("Extracted %d requirements from %s", len(requirements), source_name)
    return requirements


def deduplicate_requirements(requirements: list[Requirement]) -> list[Requirement]:
    """Deduplicates requirements by text similarity hash."""
    seen_hashes: set[str] = set()
    unique_reqs: list[Requirement] = []

    for req in requirements:
        normalized_text = "".join(c.lower() for c in req.text if c.isalnum())
        text_hash = hashlib.sha256(normalized_text.encode("utf-8")).hexdigest()[:16]
        if text_hash not in seen_hashes:
            seen_hashes.add(text_hash)
            unique_reqs.append(req)

    logger.info("Deduplicated %d requirements down to %d unique requirements.",
                len(requirements), len(unique_reqs))
    return unique_reqs
