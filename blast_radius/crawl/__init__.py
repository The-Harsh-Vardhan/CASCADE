"""
blast_radius/crawl — Phase 1 Playwright + Static Docs Crawler.
"""
import asyncio
import datetime
import logging
from typing import Sequence

from blast_radius.config import settings
from blast_radius.models import CrawlManifest, PageSnapshot
from blast_radius.crawl.artifacts import save_crawl_manifest, save_page_snapshot
from blast_radius.crawl.dynamic import crawl_dynamic_pages
from blast_radius.crawl.static import crawl_static_docs

logger = logging.getLogger(__name__)


async def run_crawl_async() -> tuple[CrawlManifest, list[PageSnapshot]]:
    run_id = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%d_%H%M%S")
    started_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
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

    logger.info("Phase 1 crawl completed. Captured %d total page snapshots.", len(all_snapshots))
    return manifest, all_snapshots


def run_crawl() -> tuple[CrawlManifest, list[PageSnapshot]]:
    """Synchronous entry point for Phase 1 crawler."""
    return asyncio.run(run_crawl_async())
