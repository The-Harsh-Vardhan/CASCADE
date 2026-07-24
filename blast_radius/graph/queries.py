"""
blast_radius/graph/queries.py — Neo4j Cypher helper queries for UserFlow nodes and graph operations.
"""

from __future__ import annotations

import json
import logging

logger = logging.getLogger(__name__)

UPSERT_USER_FLOW = """
MERGE (f:UserFlow {id: $id})
SET f.name = $name,
    f.description = $description,
    f.steps = $steps,
    f.entity = $entity,
    f.pages_involved = $pages_involved
"""


def upsert_user_flow(session, flow: dict) -> None:
    """MERGE UserFlow node with all properties."""
    steps_val = json.dumps(flow.get("steps", [])) if isinstance(flow.get("steps"), list) else str(flow.get("steps", "[]"))
    pages_val = json.dumps(flow.get("pages_involved", [])) if isinstance(flow.get("pages_involved"), list) else str(flow.get("pages_involved", "[]"))

    session.run(
        UPSERT_USER_FLOW,
        {
            "id": flow["id"],
            "name": flow["name"],
            "description": flow["description"],
            "steps": steps_val,
            "entity": flow["entity"],
            "pages_involved": pages_val,
        },
    ).consume()


def create_flow_belongs_to_page(session, flow_id: str, page_id: str, step_order: int) -> None:
    """Create BELONGS_TO edge between UserFlow and Page."""
    query = """
    MATCH (f:UserFlow {id: $flow_id})
    MATCH (p:Page) WHERE p.id = $page_id OR p.url = $page_id
    MERGE (f)-[r:BELONGS_TO]->(p)
    SET r.step_order = $step_order
    """
    session.run(query, flow_id=flow_id, page_id=page_id, step_order=step_order).consume()


def create_flow_covers_requirement(
    session,
    flow_id: str,
    req_id: str,
    confidence: float = 0.85,
    evidence: str = "Defined in flow specification",
) -> None:
    """Create COVERS edge between UserFlow and Requirement."""
    query = """
    MATCH (f:UserFlow {id: $flow_id})
    MATCH (r:Requirement)
    WHERE r.id = $req_id 
       OR r.id STARTS WITH $req_id
       OR ($req_id CONTAINS '-' AND toLower(r.feature_area) = toLower(split($req_id, '-')[1]))
       OR ($req_id CONTAINS '-' AND toLower(r.feature_area) CONTAINS toLower(split($req_id, '-')[1]))
       OR toLower(r.title) CONTAINS toLower(f.entity)
    MERGE (f)-[c:COVERS]->(r)
    SET c.confidence = $confidence,
        c.evidence = $evidence,
        c.source = "manual_flow_definition",
        c.verified_at = datetime()
    """
    session.run(query, flow_id=flow_id, req_id=req_id, confidence=confidence, evidence=evidence).consume()


def get_flows_affected_by_pages(session, page_urls: list[str]) -> list[dict]:
    """Given a list of affected page URLs, return all UserFlows that BELONG_TO those pages."""
    query = """
    MATCH (f:UserFlow)-[b:BELONGS_TO]->(p:Page)
    WHERE any(u IN $page_urls WHERE p.url CONTAINS u OR u CONTAINS p.url OR p.url ENDS WITH u)
    RETURN DISTINCT f.id as id, f.name as name, f.description as description, 
                    f.entity as entity, f.steps as steps, f.pages_involved as pages_involved
    """
    result = session.run(query, page_urls=page_urls)
    return [record.data() for record in result]
