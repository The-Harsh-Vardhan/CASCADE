"""
blast_radius/crawl/artifacts.py — Manages reading/writing PageSnapshots and CrawlManifest.
"""
import json
import logging
from pathlib import Path
from typing import Sequence

from blast_radius.config import settings
from blast_radius.models import CrawlManifest, PageSnapshot

logger = logging.getLogger(__name__)


def get_crawl_dir() -> Path:
    crawl_dir = settings.data_dir / "crawl"
    crawl_dir.mkdir(parents=True, exist_ok=True)
    return crawl_dir


def get_screenshots_dir() -> Path:
    screenshots_dir = get_crawl_dir() / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)
    return screenshots_dir


def save_page_snapshot(snapshot: PageSnapshot) -> Path:
    crawl_dir = get_crawl_dir()
    filepath = crawl_dir / f"{snapshot.url_sha256}.json"
    filepath.write_text(snapshot.model_dump_json(indent=2), encoding="utf-8")
    logger.info("Saved PageSnapshot for %s to %s", snapshot.url, filepath)
    return filepath


def load_all_page_snapshots() -> list[PageSnapshot]:
    crawl_dir = get_crawl_dir()
    snapshots: list[PageSnapshot] = []
    for p in crawl_dir.glob("*.json"):
        if p.name == "manifest.json":
            continue
        try:
            snapshot = PageSnapshot.model_validate_json(p.read_text(encoding="utf-8"))
            snapshots.append(snapshot)
        except Exception as e:
            logger.warning("Failed to parse PageSnapshot from %s: %s", p, e)
    return snapshots


def save_crawl_manifest(manifest: CrawlManifest) -> Path:
    crawl_dir = get_crawl_dir()
    filepath = crawl_dir / "manifest.json"
    filepath.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    logger.info("Saved CrawlManifest to %s", filepath)
    return filepath
