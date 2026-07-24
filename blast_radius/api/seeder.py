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

            # 2. Delete all existing HANDLES edges first
            session.run("MATCH ()-[r:HANDLES]->() DELETE r").consume()

            # 3. Create HANDLES edges per endpoint (Strict file-path matching + exact ts-rest handler fallback)
            KNOWN_CONTRACT_HANDLERS = [
                "sendDocument", "createDocument", "getDocument", "deleteDocument",
                "createTemplate", "getTemplate", "deleteTemplate", "useTemplate",
                "getProfile", "inviteTeamMember", "createWebhook", "getAuditLogs",
                "resendDocument", "createRecipient", "updateRecipient", "deleteRecipient",
                "createField", "updateField", "deleteField", "getTemplates",
                "getDocuments", "getRecipients", "generateDocumentFromTemplate"
            ]

            for ep in endpoints:
                ep_id = ep["id"]
                raw_path = ep["path"]
                # Derive expected route file path: e.g. /api/v1/documents/{id}/send -> api/v1/documents/[id]/send/route
                subpath = (
                    raw_path.replace("{id}", "[id]")
                    .replace("{fieldId}", "[fieldId]")
                    .replace("{recipientId}", "[recipientId]")
                    .replace("{templateId}", "[templateId]")
                )
                if subpath.startswith("/"):
                    subpath = subpath[1:]

                route_file_pattern = f"{subpath}/route"

                # Step 2: Try file-path based matching first
                res_path = session.run("""
                    MATCH (e:APIEndpoint {id: $ep_id})
                    MATCH (f:CodeFunction)
                    WHERE (f.file CONTAINS $route_pattern OR (f.file_path IS NOT NULL AND f.file_path CONTAINS $route_pattern))
                      AND (f.name IN ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'handler', 'default']
                           OR toUpper(f.name) = e.method)
                    MERGE (f)-[rel:HANDLES]->(e)
                    SET rel.confidence = 0.95,
                        rel.source = 'file_path_match'
                    RETURN count(rel) AS c
                """, ep_id=ep_id, route_pattern=route_file_pattern).single()["c"]

                # Step 3: Fallback — ts-rest contract handlers only (exact name match)
                if res_path == 0 and ep.get("handler_function"):
                    h_fn = ep["handler_function"]
                    session.run("""
                        MATCH (e:APIEndpoint {id: $ep_id})
                        MATCH (f:CodeFunction)
                        WHERE f.name = $h_fn AND f.name IN $known_handlers
                        MERGE (f)-[rel:HANDLES]->(e)
                        SET rel.confidence = 0.90,
                            rel.source = 'contract_exact_match'
                    """, ep_id=ep_id, h_fn=h_fn, known_handlers=KNOWN_CONTRACT_HANDLERS).consume()

                # Step 4: If still no match, leave endpoint without HANDLES edges (honest matching)

            # 4. Create (APIEndpoint)-[:IMPLEMENTS_REQ]->(Requirement) edges
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

            # 5. Create (UIElement)-[:CALLS_API]->(APIEndpoint) edges
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
