"""
ingestor.py — Root-level entry point for the requirements ingestion smoke test.

Exposes run_ingestion() so tests can do:
    from ingestor import run_ingestion
    reqs = run_ingestion()

Delegates entirely to blast_radius.ingest.run_ingest().
"""
from blast_radius.ingest import run_ingest
from blast_radius.models import Requirement


def run_ingestion() -> list[Requirement]:
    """
    Run the full Phase 2 requirements ingestion pipeline.

    Returns:
        List of Requirement objects with stable REQ-NNN IDs.
        Also saves to outputs/requirements/requirements.json.

    Smoke-test usage:
        reqs = run_ingestion()
        assert len(reqs) >= 50
        areas = {r.feature_area for r in reqs}
        assert areas >= {"signing", "sending", "templates", "teams",
                          "webhooks", "api", "auth", "admin"}
    """
    return run_ingest()
