"""
blast_radius/ingest — Phase 2 Requirements Ingestion Package.
"""
import asyncio
import json
import logging
from pathlib import Path

from blast_radius.config import settings
from blast_radius.models import Requirement
from blast_radius.ingest.fetch import fetch_readme_text, fetch_docs_texts
from blast_radius.ingest.extract import extract_requirements_from_text, deduplicate_requirements

logger = logging.getLogger(__name__)


async def run_ingest_async() -> list[Requirement]:
    logger.info("Starting Phase 2 Requirements Ingestion pipeline...")

    all_raw_reqs: list[Requirement] = []

    # 1. Fetch & extract README.md
    readme_name, readme_text = fetch_readme_text()
    readme_reqs = await extract_requirements_from_text(readme_name, readme_text)
    all_raw_reqs.extend(readme_reqs)

    # 2. Fetch & extract static doc pages (capped at 3)
    docs_texts = fetch_docs_texts()
    for doc_name, doc_text in docs_texts:
        doc_reqs = await extract_requirements_from_text(doc_name, doc_text)
        all_raw_reqs.extend(doc_reqs)

    # 3. Deduplicate
    unique_reqs = deduplicate_requirements(all_raw_reqs)

    if len(unique_reqs) < 5:
        logger.warning("Fewer than 5 requirements extracted (total %d). Check prompts.", len(unique_reqs))

    # 4. Save to data/requirements/requirements.json
    out_dir = settings.data_dir / "requirements"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "requirements.json"

    data = [req.model_dump() for req in unique_reqs]
    out_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    logger.info("Saved %d structured requirements to %s", len(unique_reqs), out_path)

    return unique_reqs


def run_ingest() -> list[Requirement]:
    """Synchronous entry point for Phase 2 ingest pipeline."""
    return asyncio.run(run_ingest_async())
