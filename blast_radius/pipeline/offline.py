"""
blast_radius/pipeline/offline.py — Offline indexing and graph construction pipeline.
"""

from __future__ import annotations

import logging
from blast_radius.graph import build_graph
from blast_radius.graph.writer import get_driver
from flows.seeder import seed_user_flows

logger = logging.getLogger(__name__)


def run_offline_pipeline() -> dict:
    """
    Execute offline graph build pipeline:
      1. Build knowledge graph (Requirements, CodeFunctions, Pages/UIElements)
      2. Seed 10 canonical UserFlow nodes with BELONGS_TO, COVERS, and PART_OF_FLOW edges
    """
    logger.info("=== Running Offline Graph Pipeline ===")
    stats = build_graph()

    try:
        driver = get_driver()
        driver.verify_connectivity()
        n_flows = seed_user_flows(driver)
        stats["n_user_flows"] = n_flows
        driver.close()
    except Exception as exc:
        logger.warning("Neo4j driver unreachable during offline pipeline seeding: %s", exc)

    return stats


if __name__ == "__main__":
    run_offline_pipeline()
