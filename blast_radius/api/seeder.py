"""
blast_radius/api/seeder.py — Seeds APIEndpoint nodes and relationships into Neo4j.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from blast_radius.api.extract import extract_api_endpoints_from_repo

logger = logging.getLogger(__name__)

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def seed_api_endpoints(driver, repo_dir: str | Path | None = None) -> int:
    """
    Extract API endpoints, upsert APIEndpoint nodes in Neo4j, and build edges:
    - (CodeFunction)-[:HANDLES]->(APIEndpoint)
    - (APIEndpoint)-[:IMPLEMENTS_REQ]->(Requirement)
    - (UIElement)-[:CALLS_API]->(APIEndpoint)

    Returns number of APIEndpoint nodes seeded.
    """
    if driver is None:
        logger.warning("[api] Neo4j driver is None — skipping APIEndpoint seeding.")
        return 0

    if repo_dir is None:
        repo_dir = REPO_ROOT / "data" / "repos" / "documenso"

    endpoints = extract_api_endpoints_from_repo(repo_dir)
    if not endpoints:
        logger.warning("[api] No API endpoints extracted.")
        return 0

    try:
        with driver.session() as session:
            # 1. Upsert APIEndpoint nodes
            for ep in endpoints:
                session.run("""
                    MERGE (e:APIEndpoint {id: $id})
                    SET e.method = $method,
                        e.path = $path,
                        e.description = $description,
                        e.handler_file = $handler_file,
                        e.handler_function = $handler_function,
                        e.feature_area = $feature_area,
                        e.tags = $tags
                """, id=ep["id"], method=ep["method"], path=ep["path"],
                     description=ep.get("description", ""),
                     handler_file=ep.get("handler_file", ""),
                     handler_function=ep.get("handler_function", ""),
                     feature_area=ep.get("feature_area", "api"),
                     tags=ep.get("tags", [])).consume()

            count = session.run("MATCH (e:APIEndpoint) RETURN count(e) as c").single()["c"]
            logger.info("[api] Upserted %d APIEndpoint nodes.", count)

            # 2. Create (CodeFunction)-[:HANDLES]->(APIEndpoint) edges
            handles_query = """
            MATCH (e:APIEndpoint)
            MATCH (f:CodeFunction)
            WHERE (e.handler_function IS NOT NULL AND size(e.handler_function) > 0 AND (toLower(f.name) = toLower(e.handler_function) OR toLower(f.name) ENDS WITH toLower(e.handler_function)))
               OR (f.file CONTAINS 'packages/api' AND f.file CONTAINS 'implementation')
               OR (e.path CONTAINS 'documents' AND f.name CONTAINS 'Document' AND f.file CONTAINS 'packages/lib')
               OR (e.path CONTAINS 'templates' AND f.name CONTAINS 'Template' AND f.file CONTAINS 'packages/lib')
            MERGE (f)-[rel:HANDLES]->(e)
            SET rel.confidence = 0.90,
                rel.evidence = 'Direct route handler',
                rel.source = 'static_analysis'
            """
            session.run(handles_query).consume()

            # 3. Create (APIEndpoint)-[:IMPLEMENTS_REQ]->(Requirement) edges
            impl_query = """
            MATCH (e:APIEndpoint)
            MATCH (r:Requirement)
            WHERE (e.feature_area IS NOT NULL AND r.feature_area IS NOT NULL AND toLower(r.feature_area) = toLower(e.feature_area))
               OR (e.path CONTAINS 'documents' AND (toLower(r.text) CONTAINS 'document' OR toLower(r.title) CONTAINS 'document'))
               OR (e.path CONTAINS 'templates' AND (toLower(r.text) CONTAINS 'template' OR toLower(r.title) CONTAINS 'template'))
               OR (e.path CONTAINS 'recipients' AND (toLower(r.text) CONTAINS 'recipient' OR toLower(r.title) CONTAINS 'recipient'))
            MERGE (e)-[rel:IMPLEMENTS_REQ]->(r)
            SET rel.confidence = 0.85,
                rel.reason = 'API endpoint provides capability for requirement',
                rel.source = 'api_requirement_mapper'
            """
            session.run(impl_query).consume()

            # 4. Create (UIElement)-[:CALLS_API]->(APIEndpoint) edges
            calls_api_query = """
            MATCH (u:UIElement)
            MATCH (e:APIEndpoint)
            WHERE (u.page_url CONTAINS 'documents' AND e.path CONTAINS 'documents')
               OR (u.page_url CONTAINS 'templates' AND e.path CONTAINS 'templates')
               OR (u.page_url CONTAINS 'teams' AND e.path CONTAINS 'teams')
               OR (u.page_url CONTAINS 'webhooks' AND e.path CONTAINS 'webhooks')
            MERGE (u)-[rel:CALLS_API]->(e)
            SET rel.confidence = 0.80,
                rel.source = 'ui_api_mapping'
            """
            session.run(calls_api_query).consume()

            logger.info("[api] Successfully seeded APIEndpoint nodes and relationships.")
            return count

    except Exception as exc:
        logger.error("[api] Failed to seed API endpoints: %s", exc)
        return 0
