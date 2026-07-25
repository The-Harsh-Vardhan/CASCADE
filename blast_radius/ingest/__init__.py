"""
blast_radius/ingest -- Phase 2 Requirements Ingestion Package.

Pipeline:
  1. Fetch all 11 Documenso documentation sources via httpx.
  2. One LLM call per source (call_llm_json) using the exhaustive extraction prompt.
  3. Deduplicate across all sources (exact title + Jaccard > 70 %).
  4. Assign stable REQ-NNN IDs.
  5. Save to outputs/requirements/requirements.json   <- primary output
            + data/requirements/requirements.json     <- legacy path for Phase 4
  6. Print breakdown by feature_area; flag any area with < 3 requirements.

Target: ≥ 50 unique requirements covering all 8 required feature areas.
"""
from __future__ import annotations

import asyncio
import json
import logging
from collections import Counter
from pathlib import Path

from blast_radius.config import settings
from blast_radius.models import Requirement
from blast_radius.ingest.fetch import fetch_all_sources
from blast_radius.ingest.extract import (
    extract_requirements_from_text,
    deduplicate_raw,
    assign_ids_and_build_requirements,
)

logger = logging.getLogger(__name__)

# -- Validation thresholds ------------------------------------------------------
MIN_TOTAL: int = 50
MIN_PER_AREA: int = 3
REQUIRED_AREAS: frozenset[str] = frozenset(
    {"signing", "sending", "templates", "teams", "webhooks", "api", "auth", "admin"}
)


# -- Serialisation helpers ------------------------------------------------------

def _req_to_output_dict(req: Requirement) -> dict:
    """Serialize a Requirement to the canonical outputs/requirements schema."""
    return {
        "id": req.requirement_id,
        "title": req.title,
        "description": req.description,
        "req_type": req.req_type,
        "source": req.source,
        "feature_area": req.feature_area,
        "acceptance_criteria": req.acceptance_criteria,
        "related_ui_keywords": req.related_ui_keywords,
        "related_api_endpoints": req.related_api_endpoints,
        "priority": req.priority,
    }


def _print_breakdown(requirements: list[Requirement]) -> None:
    """Print a feature_area breakdown table; flag under-ingested areas."""
    import sys
    # Force UTF-8 on Windows to avoid cp1252 UnicodeEncodeError
    out = open(sys.stdout.fileno(), mode="w", encoding="utf-8", buffering=1, closefd=False)

    area_counts: Counter[str] = Counter(r.feature_area for r in requirements)

    out.write("\n[Phase 2] Requirements by feature_area:\n")
    out.write(f"  {'Area':<16}  {'Count':>5}  Status\n")
    out.write(f"  {'-'*16}  {'-'*5}  ------\n")
    for area in sorted(REQUIRED_AREAS | set(area_counts.keys())):
        count = area_counts.get(area, 0)
        flag = "[!] UNDER-INGESTED" if count < MIN_PER_AREA else "[OK]"
        out.write(f"  {area:<16}  {count:>5}  {flag}\n")

    missing = REQUIRED_AREAS - set(area_counts.keys())
    if missing:
        logger.warning("Feature areas with ZERO requirements: %s", sorted(missing))

    status = f"  [!] BELOW TARGET ({MIN_TOTAL})" if len(requirements) < MIN_TOTAL else f"  [OK] (target >= {MIN_TOTAL})"
    out.write(f"\n  Total: {len(requirements)}{status}\n")
    out.flush()


# -- Core pipeline --------------------------------------------------------------

async def run_ingest_async() -> list[Requirement]:
    """Async implementation of the Phase 2 ingestion pipeline."""
    logger.info("Phase 2 Requirements Ingestion -- START")

    # 1. Fetch all sources
    sources: list[tuple[str, str]] = fetch_all_sources()
    logger.info("Fetched %d sources.", len(sources))

    # 2. Extract raw dicts from each source (sequential -- one LLM call each)
    all_raw: list[dict] = []
    for source_name, text in sources:
        raw_items = await extract_requirements_from_text(source_name, text)
        all_raw.extend(raw_items)
        logger.info(
            "Running total after %s: %d raw items", source_name, len(all_raw)
        )

    logger.info("Total raw requirements before dedup: %d", len(all_raw))

    # 3. Deduplicate across all sources
    unique_raw = deduplicate_raw(all_raw)

    # 4. Assign stable IDs and convert to Requirement objects
    requirements = assign_ids_and_build_requirements(unique_raw)
    logger.info("Final requirement count: %d", len(requirements))

    # 5a. Save to outputs/requirements/requirements.json (primary) -- BEFORE print
    primary_dir = Path("outputs") / "requirements"
    primary_dir.mkdir(parents=True, exist_ok=True)
    primary_path = primary_dir / "requirements.json"
    primary_path.write_text(
        json.dumps([_req_to_output_dict(r) for r in requirements], indent=2),
        encoding="utf-8",
    )
    logger.info("Saved %d requirements -> %s", len(requirements), primary_path)

    # 5b. Save Pydantic model_dump to legacy data/ path (consumed by Phase 4)
    legacy_dir = settings.data_dir / "requirements"
    legacy_dir.mkdir(parents=True, exist_ok=True)
    legacy_path = legacy_dir / "requirements.json"
    legacy_path.write_text(
        json.dumps([r.model_dump() for r in requirements], indent=2),
        encoding="utf-8",
    )
    logger.info("Also saved -> %s  (legacy Phase 4 path)", legacy_path)

    # 6. Print breakdown (after save so files are written even if print fails)
    _print_breakdown(requirements)

    logger.info("Phase 2 Requirements Ingestion -- DONE")
    return requirements


def run_ingest() -> list[Requirement]:
    """Synchronous entry point -- wraps the async pipeline with asyncio.run()."""
    return asyncio.run(run_ingest_async())
