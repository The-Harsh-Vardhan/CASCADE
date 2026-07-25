"""
blast_radius/graph/queries.py -- Neo4j Cypher helper queries for UserFlow nodes and graph operations.

Includes:
  - UserFlow upsert + edge creation
  - AbsentRequirement node upsert + smoke-test query
  - Dark-code path check via Cypher
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


# -- AbsentRequirement schema -------------------------------------------------

UPSERT_ABSENT_REQUIREMENT = """
MERGE (a:AbsentRequirement {id: $id})
SET a.requirement_id   = $requirement_id,
    a.absence_type     = $absence_type,
    a.reason           = $reason,
    a.confidence       = $confidence,
    a.evidence         = $evidence,
    a.closest_page_url = $closest_page_url
WITH a
OPTIONAL MATCH (r:Requirement {id: $requirement_id})
FOREACH (_ IN CASE WHEN r IS NOT NULL THEN [1] ELSE [] END |
    MERGE (r)-[:ABSENT_FROM]->(a)
)
WITH a
OPTIONAL MATCH (p1:Page)
WHERE $closest_page_url <> "" AND (p1.url = $closest_page_url OR p1.url CONTAINS $closest_page_url OR $closest_page_url CONTAINS p1.url)
WITH a, p1
OPTIONAL MATCH (p2:Page)
WITH a, coalesce(p1, p2) AS p
WHERE p IS NOT NULL
WITH a, p LIMIT 1
MERGE (a)-[:MISSING_FROM]->(p)
"""


def write_absent_requirements(session, absent_list: list[Any]) -> int:
    """
    Upsert AbsentRequirement nodes from fusion/mapper output and create MISSING_FROM edges to Pages.

    Args:
        session:      open Neo4j session
        absent_list:  list of AbsentRequirement dataclasses or dicts

    Returns:
        count of nodes written
    """
    written = 0
    for a in absent_list:
        # Accept dataclasses or plain dicts (from JSON reload)
        if hasattr(a, "__dataclass_fields__"):
            from dataclasses import asdict
            d = asdict(a)
        elif isinstance(a, dict):
            d = a
        else:
            logger.warning("[queries] Skipping unknown absent type: %s", type(a))
            continue

        try:
            session.run(UPSERT_ABSENT_REQUIREMENT, {
                "id":               d["id"],
                "requirement_id":   d["requirement_id"],
                "absence_type":     d["absence_type"],
                "reason":           d["reason"],
                "confidence":       float(d.get("confidence", 0.90)),
                "evidence":         d.get("evidence", ""),
                "closest_page_url": d.get("closest_page_url", ""),
            }).consume()
            written += 1
        except Exception as exc:
            logger.warning("[queries] Failed to write AbsentRequirement %s: %s", d.get("id"), exc)

            written += 1
        except Exception as exc:
            logger.warning("[queries] Failed to write AbsentRequirement %s: %s", d.get("id"), exc)

    logger.info("[queries] Wrote %d AbsentRequirement nodes", written)
    return written


def get_absent_requirements(session) -> list[dict]:
    """
    Return all AbsentRequirement nodes from Neo4j.

    Used in the smoke test:
        absent = get_absent_requirements(session)
        assert len(absent) >= 8

    Returns list of dicts with keys:
        id, requirement_id, absence_type, reason, confidence, evidence
    """
    query = """
    MATCH (a:AbsentRequirement)
    RETURN a.id             AS id,
           a.requirement_id AS requirement_id,
           a.absence_type   AS absence_type,
           a.reason         AS reason,
           a.confidence     AS confidence,
           a.evidence       AS evidence
    ORDER BY a.absence_type, a.id
    """
    result = session.run(query)
    return [record.data() for record in result]

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


def create_flow_belongs_to_page(session, flow_id: str, page_url: str, step_order: int) -> None:
    """Create BELONGS_TO edge between UserFlow and Page."""
    query = """
    MATCH (f:UserFlow {id: $flow_id})
    MATCH (p:Page)
    WHERE (NOT p.url CONTAINS '/signup' OR $page_url CONTAINS '/signup')
      AND (
           p.url = $page_url  
        OR p.url CONTAINS $page_url
        OR $page_url CONTAINS p.url
        OR p.url ENDS WITH $page_url
        OR ($page_url CONTAINS '{id}' AND p.url CONTAINS split($page_url, '{id}')[0] AND p.url CONTAINS split($page_url, '{id}')[1])
        OR ($page_url = '/documents/{id}' AND p.url CONTAINS '/documents/' AND NOT p.url CONTAINS '/recipients' AND NOT p.url CONTAINS '/fields' AND NOT p.url CONTAINS '/send' AND NOT p.url CONTAINS '/new')
        OR ($page_url CONTAINS '{token}' AND (p.url CONTAINS '/sign' OR p.url CONTAINS 'signing-documents') AND NOT p.url CONTAINS '/signup')
      )
    MERGE (f)-[r:BELONGS_TO]->(p)
    SET r.step_order = $step_order
    """
    session.run(query, flow_id=flow_id, page_url=page_url, step_order=step_order).consume()


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
       OR (f.entity IS NOT NULL AND r.req_type IS NOT NULL AND toLower(r.req_type) = toLower(f.entity))
       OR (f.entity IS NOT NULL AND r.text IS NOT NULL AND toLower(r.text) CONTAINS toLower(f.entity))
    MERGE (f)-[c:COVERS]->(r)
    SET c.confidence = $confidence,
        c.evidence = $evidence,
        c.source = "manual_flow_definition"
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
