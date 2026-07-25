"""
blast_radius/crawl -- Phase 1 Playwright + Static Docs Crawler.

Fixture mode: if settings.crawl_use_fixture is True, skip live crawling
and load pre-committed PageSnapshot JSON files from data/crawl/fixtures/.
This lets evaluators run Phases 4-6 without a Documenso account.

Public API:
  run_crawl()           -> (CrawlManifest, list[PageSnapshot])   # legacy, used by Phase 4
  run_full_crawl()      -> list[PageAnalysis]                    # new two-phase crawler
"""
import asyncio
import datetime
import json
import logging
from pathlib import Path
from typing import Sequence

from blast_radius.config import settings
from blast_radius.models import CrawlManifest, PageSnapshot
from blast_radius.crawl.artifacts import save_crawl_manifest, save_page_snapshot
from blast_radius.crawl.dynamic import crawl_dynamic_pages
from blast_radius.crawl.static import crawl_static_docs
from blast_radius.crawl.runner import run_full_crawl, run_full_crawl_async  # noqa: F401

logger = logging.getLogger(__name__)


def _load_fixtures() -> list[PageSnapshot]:
    """
    Load pre-committed PageSnapshot fixtures from data/crawl/fixtures/.
    Returns an empty list if the fixtures directory doesn't exist.
    """
    fixtures_dir = settings.data_dir / "crawl" / "fixtures"
    if not fixtures_dir.exists():
        logger.warning(
            "[crawl] CRAWL_USE_FIXTURE=true but fixtures directory not found: %s. "
            "Falling back to empty snapshot list.",
            fixtures_dir,
        )
        return []

    snapshots: list[PageSnapshot] = []
    for p in sorted(fixtures_dir.glob("*.json")):
        try:
            snapshot = PageSnapshot.model_validate_json(p.read_text(encoding="utf-8"))
            snapshots.append(snapshot)
            logger.info("[crawl] Loaded fixture: %s (%s)", snapshot.url, p.name)
        except Exception as e:
            logger.warning("[crawl] Failed to parse fixture %s: %s", p, e)

    logger.info("[crawl] Fixture mode: loaded %d page snapshots.", len(snapshots))
    return snapshots


async def run_crawl_async() -> tuple[CrawlManifest, list[PageSnapshot]]:
    run_id = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()

    if settings.crawl_use_fixture:
        logger.info(
            "[crawl] CRAWL_USE_FIXTURE=true -- loading pre-committed fixtures (run_id=%s)",
            run_id,
        )
        all_snapshots = _load_fixtures()
    else:
        logger.info("Starting Phase 1 crawl pipeline (run_id=%s)", run_id)
        # BUG-03 Fix: Call BOTH dynamic pages and static docs
        dynamic_snapshots = await crawl_dynamic_pages(max_pages=settings.crawl_max_pages)
        static_snapshots = await crawl_static_docs()
        all_snapshots = dynamic_snapshots + static_snapshots

    saved_urls: list[str] = []
    for snapshot in all_snapshots:
        save_page_snapshot(snapshot)
        saved_urls.append(snapshot.url)

    manifest = CrawlManifest(
        run_id=run_id,
        started_at=started_at,
        pages=saved_urls,
        transitions=[]
    )
    save_crawl_manifest(manifest)

    logger.info("Phase 1 completed. Captured %d total page snapshots.", len(all_snapshots))
    return manifest, all_snapshots


def run_crawl() -> tuple[CrawlManifest, list[PageSnapshot]]:
    """Synchronous entry point for Phase 1 crawler."""
    return asyncio.run(run_crawl_async())
