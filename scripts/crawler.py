"""
crawler.py — Root-level thin wrapper for the Phase 1 two-phase crawler.

Exposes crawl() returning list[PageAnalysis] for smoke tests:

    from crawler import crawl
    results = crawl()
    print(f"Total pages: {len(results)}")
    entity_counts = {}
    for r in results:
        entity_counts[r.documenso_entity] = entity_counts.get(r.documenso_entity, 0) + 1
    print("Entity coverage:", entity_counts)

Internally delegates to blast_radius.crawl.runner.run_full_crawl().
"""
from __future__ import annotations

import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s -- %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stderr,
)


def crawl():
    """
    Run the full two-phase Documenso crawler.
    Returns list[PageAnalysis].

    Phase 1: Public pages (documenso.com + docs.documenso.com) — no auth needed.
    Phase 2: Authenticated app pages (app.documenso.com) — requires .env creds.
    """
    from blast_radius.crawl.runner import run_full_crawl
    return run_full_crawl()


if __name__ == "__main__":
    results = crawl()
    print(f"\nTotal pages: {len(results)}")

    entity_counts: dict[str, int] = {}
    for r in results:
        entity_counts[r.documenso_entity] = entity_counts.get(r.documenso_entity, 0) + 1
    print("Entity coverage:", entity_counts)

    # Smoke test assertions
    required_entities = {"document", "template", "recipient", "field", "team", "webhook", "api_token"}
    found = set(entity_counts.keys())
    missing = required_entities - found
    under = {e: n for e, n in entity_counts.items() if n < 1}

    if len(results) < 20:
        print(f"[WARN] Only {len(results)} pages captured (target >= 20)")
    else:
        print(f"[OK] {len(results)} pages (>= 20)")

    if missing:
        print(f"[WARN] Missing entities: {missing}")
    else:
        print("[OK] All required entity types present")

    print("\nSMOKE TEST PASSED" if not missing and len(results) >= 20 else "SMOKE TEST PARTIAL (see warnings above)")
