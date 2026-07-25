from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from blast_radius.graph.queries import (
    upsert_user_flow,
    create_flow_belongs_to_page,
)

logger = logging.getLogger(__name__)

DOCUMENSO_USER_FLOWS: list[dict] = [
    {
        "id": "FLOW-001",
        "name": "Document Upload and Send",
        "description": "User uploads a PDF, configures recipients, places signature fields, and sends for signing",
        "steps": ["Navigate to /documents", "Click Upload", "Add recipients", "Place fields", "Send document"],
        "pages_involved": ["/documents", "/documents/new", "/documents/{id}/recipients", "/documents/{id}/fields", "/documents/{id}/send"],
        "requirements_covered": ["REQ-sending-001", "REQ-recipient-001", "REQ-field-001"],
        "requirement_keywords": ["upload", "send", "recipient", "field", "configure", "pdf", "envelope", "draft", "prepare"],
        "entity": "document",
    },
    {
        "id": "FLOW-002",
        "name": "Document Signing (Recipient Flow)",
        "description": "Recipient receives email, opens signing link, reviews document, fills fields, signs and completes",
        "steps": ["Open email link", "Review document", "Fill required fields", "Sign", "Complete"],
        "pages_involved": ["/sign/{token}"],
        "requirements_covered": ["REQ-signing-001", "REQ-signing-002"],
        "requirement_keywords": ["sign", "signature", "complete", "review", "consent", "decline", "adopt"],
        "entity": "signing",
    },
    {
        "id": "FLOW-003",
        "name": "Template Creation",
        "description": "User creates a reusable document template with pre-placed fields",
        "steps": ["Navigate to /templates", "Create new template", "Upload base document", "Place fields", "Save template"],
        "pages_involved": ["/templates", "/templates/new"],
        "requirements_covered": ["REQ-template-001", "REQ-template-002"],
        "requirement_keywords": ["template", "create template", "reusable", "base document", "template field"],
        "entity": "template",
    },
    {
        "id": "FLOW-004",
        "name": "Template to Document",
        "description": "User instantiates a document from an existing template",
        "steps": ["Select template", "Configure recipients", "Send"],
        "pages_involved": ["/templates", "/documents/new"],
        "requirements_covered": ["REQ-template-003"],
        "requirement_keywords": ["use template", "from template", "instantiate"],
        "entity": "template",
    },
    {
        "id": "FLOW-005",
        "name": "Team Member Invitation",
        "description": "Team owner invites a new member, sets role, member accepts",
        "steps": ["Navigate to /settings/teams", "Invite member", "Set role", "Member accepts email"],
        "pages_involved": ["/settings/teams"],
        "requirements_covered": ["REQ-team-001", "REQ-team-002"],
        "requirement_keywords": ["invite", "team member", "role", "admin", "manager", "accept invitation", "team settings"],
        "entity": "team",
    },
    {
        "id": "FLOW-006",
        "name": "Webhook Configuration",
        "description": "User creates a webhook, selects events, verifies delivery",
        "steps": ["Navigate to /settings/webhooks", "Add endpoint URL", "Select events", "Save", "Test"],
        "pages_involved": ["/settings/webhooks"],
        "requirements_covered": ["REQ-webhook-001"],
        "requirement_keywords": ["webhook", "endpoint", "event", "payload", "secret", "delivery", "trigger"],
        "entity": "webhook",
    },
    {
        "id": "FLOW-007",
        "name": "API Token Management",
        "description": "User creates and manages API tokens for programmatic access",
        "steps": ["Navigate to /settings/api-tokens", "Create token", "Copy token", "Set expiry"],
        "pages_involved": ["/settings/api-tokens"],
        "requirements_covered": ["REQ-api-001"],
        "requirement_keywords": ["api token", "token", "programmatic", "api key", "generate token", "expiry"],
        "entity": "api_token",
    },
    {
        "id": "FLOW-008",
        "name": "Document Audit Trail Review",
        "description": "User reviews the audit trail of a completed document",
        "steps": ["Open completed document", "View history/audit tab"],
        "pages_involved": ["/documents/{id}"],
        "requirements_covered": ["REQ-audit-001"],
        "requirement_keywords": ["audit", "history", "log", "trail", "activity", "timestamp", "event log"],
        "entity": "document",
    },
    {
        "id": "FLOW-009",
        "name": "Signing Order Configuration",
        "description": "Sender configures sequential signing order for multiple recipients",
        "steps": ["Add multiple recipients", "Enable signing order", "Set order numbers", "Send"],
        "pages_involved": ["/documents/{id}/recipients"],
        "requirements_covered": ["REQ-recipient-002"],
        "requirement_keywords": ["signing order", "sequential", "order", "recipient order", "parallel"],
        "entity": "recipient",
    },
    {
        "id": "FLOW-010",
        "name": "Document Download After Completion",
        "description": "User downloads the signed PDF after all recipients have signed",
        "steps": ["Navigate to completed document", "Click Download"],
        "pages_involved": ["/documents/{id}"],
        "requirements_covered": ["REQ-signing-003"],
        "requirement_keywords": ["download", "completed", "export", "final pdf", "signed document", "certificate"],
        "entity": "document",
    },
]


def create_covers_edges_for_flow(session, flow: dict, requirements: list) -> int:
    """
    Match requirements to flows using keyword matching against
    requirement title + description text.
    Only create COVERS edge if >= 1 keyword matches.
    Capped at 40 requirements per flow.
    """
    flow_keywords = [kw.lower() for kw in flow.get("requirement_keywords", [])]

    matched = []
    for req in requirements:
        req_id = req.get("id") or req.get("requirement_id")
        if not req_id:
            continue
        title = req.get("title", "") or ""
        desc = req.get("description", "") or req.get("text", "") or ""
        req_text = (title + " " + desc).lower()

        matching_kws = [kw for kw in flow_keywords if kw in req_text]

        if len(matching_kws) >= 1:
            confidence = min(0.95, 0.65 + (len(matching_kws) * 0.10))
            evidence = f"Keyword match: {matching_kws[:3]} found in requirement text"
            matched.append((req_id, confidence, evidence))

    # Cap at 40 requirements per flow to prevent over-matching
    matched = sorted(matched, key=lambda x: -x[1])[:40]

    ts_now = datetime.now(timezone.utc).isoformat()
    for req_id, confidence, evidence in matched:
        session.run("""
            MATCH (f:UserFlow {id: $flow_id})
            MATCH (r:Requirement {id: $req_id})
            MERGE (f)-[rel:COVERS]->(r)
            SET rel.confidence = $confidence,
                rel.evidence = $evidence,
                rel.source = 'keyword_match',
                rel.verified_at = $ts
        """, flow_id=flow["id"], req_id=req_id,
             confidence=confidence, evidence=evidence,
             ts=ts_now)

    return len(matched)


def seed_user_flows(driver, requirements=None, page_analyses=None) -> int:
    """
    Seed 10 canonical UserFlow nodes and create edges to Page, Requirement, and UIElement nodes.
    Returns number of flows seeded.
    """
    if driver is None:
        logger.warning("[flows] Neo4j driver is None -- skipping flow seeding.")
        return 0

    try:
        from blast_radius.graph.writer import write_requirements, write_ui_elements, clear_stale_data, REPO_ROOT
        base_url = "https://app.documenso.com"

        # Load requirements if not provided
        if not requirements:
            for p in [
                REPO_ROOT / "outputs" / "requirements" / "requirements.json",
                REPO_ROOT / "data" / "requirements" / "requirements.json",
            ]:
                if p.exists():
                    try:
                        requirements = json.loads(p.read_text(encoding="utf-8"))
                        if requirements:
                            break
                    except Exception:
                        pass
        requirements = requirements or []

        with driver.session() as session:
            # 0. Clear stale hex Requirements & GapNodes, then ensure clean Requirement and Page nodes exist
            clear_stale_data(session)
            write_requirements(session, requirements)
            write_ui_elements(session, page_analyses or [])

            # 1. Upsert all UserFlow nodes
            for flow in DOCUMENSO_USER_FLOWS:
                upsert_user_flow(session, flow)

                # 2. Link Requirement nodes (Keyword-based COVERS edge)
                create_covers_edges_for_flow(session, flow, requirements)

                # 3. Link Page nodes (BELONGS_TO edge)
                for i, page_path in enumerate(flow.get("pages_involved", [])):
                    full_url = base_url + page_path if page_path.startswith("/") else page_path
                    create_flow_belongs_to_page(session, flow["id"], full_url, i)
                    create_flow_belongs_to_page(session, flow["id"], page_path, i)

                # 4. Link UIElement / UIComponent nodes (PART_OF_FLOW edge)
                ui_query = """
                MATCH (f:UserFlow {id: $flow_id})-[:BELONGS_TO]->(p:Page)
                MATCH (u:UIElement) WHERE u.page_url = p.url
                MERGE (u)-[:PART_OF_FLOW]->(f)
                """
                session.run(ui_query, flow_id=flow["id"]).consume()

            count = session.run("MATCH (f:UserFlow) RETURN count(f) as c").single()["c"]
            logger.info("[flows] Successfully seeded %d UserFlow nodes in Neo4j.", count)
            return count

    except Exception as exc:
        logger.error("[flows] Failed to seed user flows: %s", exc)
        return 0
