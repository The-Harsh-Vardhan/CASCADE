"""
blast_radius/flows/seeder.py — UserFlow seeder for Documenso domain.

Defines 10 canonical Documenso user flows and seeds them into Neo4j with:
  (UserFlow)-[:BELONGS_TO {step_order: idx}]->(Page)
  (UserFlow)-[:COVERS {confidence: 0.85, ...}]->(Requirement)
  (UIElement)-[:PART_OF_FLOW]->(UserFlow)
"""

from __future__ import annotations

import logging
from blast_radius.graph.queries import (
    upsert_user_flow,
    create_flow_belongs_to_page,
    create_flow_covers_requirement,
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
        "entity": "document",
    },
    {
        "id": "FLOW-002",
        "name": "Document Signing (Recipient Flow)",
        "description": "Recipient receives email, opens signing link, reviews document, fills fields, signs and completes",
        "steps": ["Open email link", "Review document", "Fill required fields", "Sign", "Complete"],
        "pages_involved": ["/sign/{token}"],
        "requirements_covered": ["REQ-signing-001", "REQ-signing-002"],
        "entity": "signing",
    },
    {
        "id": "FLOW-003",
        "name": "Template Creation",
        "description": "User creates a reusable document template with pre-placed fields",
        "steps": ["Navigate to /templates", "Create new template", "Upload base document", "Place fields", "Save template"],
        "pages_involved": ["/templates", "/templates/new"],
        "requirements_covered": ["REQ-template-001", "REQ-template-002"],
        "entity": "template",
    },
    {
        "id": "FLOW-004",
        "name": "Template to Document",
        "description": "User instantiates a document from an existing template",
        "steps": ["Select template", "Configure recipients", "Send"],
        "pages_involved": ["/templates", "/documents/new"],
        "requirements_covered": ["REQ-template-003"],
        "entity": "template",
    },
    {
        "id": "FLOW-005",
        "name": "Team Member Invitation",
        "description": "Team owner invites a new member, sets role, member accepts",
        "steps": ["Navigate to /settings/teams", "Invite member", "Set role", "Member accepts email"],
        "pages_involved": ["/settings/teams"],
        "requirements_covered": ["REQ-team-001", "REQ-team-002"],
        "entity": "team",
    },
    {
        "id": "FLOW-006",
        "name": "Webhook Configuration",
        "description": "User creates a webhook, selects events, verifies delivery",
        "steps": ["Navigate to /settings/webhooks", "Add endpoint URL", "Select events", "Save", "Test"],
        "pages_involved": ["/settings/webhooks"],
        "requirements_covered": ["REQ-webhook-001"],
        "entity": "webhook",
    },
    {
        "id": "FLOW-007",
        "name": "API Token Management",
        "description": "User creates and manages API tokens for programmatic access",
        "steps": ["Navigate to /settings/api-tokens", "Create token", "Copy token", "Set expiry"],
        "pages_involved": ["/settings/api-tokens"],
        "requirements_covered": ["REQ-api-001"],
        "entity": "api_token",
    },
    {
        "id": "FLOW-008",
        "name": "Document Audit Trail Review",
        "description": "User reviews the audit trail of a completed document",
        "steps": ["Open completed document", "View history/audit tab"],
        "pages_involved": ["/documents/{id}"],
        "requirements_covered": ["REQ-audit-001"],
        "entity": "document",
    },
    {
        "id": "FLOW-009",
        "name": "Signing Order Configuration",
        "description": "Sender configures sequential signing order for multiple recipients",
        "steps": ["Add multiple recipients", "Enable signing order", "Set order numbers", "Send"],
        "pages_involved": ["/documents/{id}/recipients"],
        "requirements_covered": ["REQ-recipient-002"],
        "entity": "recipient",
    },
    {
        "id": "FLOW-010",
        "name": "Document Download After Completion",
        "description": "User downloads the signed PDF after all recipients have signed",
        "steps": ["Navigate to completed document", "Click Download"],
        "pages_involved": ["/documents/{id}"],
        "requirements_covered": ["REQ-signing-003"],
        "entity": "document",
    },
]


def seed_user_flows(driver, requirements=None, page_analyses=None) -> int:
    """
    Seed 10 canonical UserFlow nodes and create edges to Page, Requirement, and UIElement nodes.
    Returns number of flows seeded.
    """
    if driver is None:
        logger.warning("[flows] Neo4j driver is None — skipping flow seeding.")
        return 0

    try:
        with driver.session() as session:
            # 1. Upsert all UserFlow nodes
            for flow in DOCUMENSO_USER_FLOWS:
                upsert_user_flow(session, flow)

                # 2. Link Requirement nodes (COVERS edge)
                for req_id in flow.get("requirements_covered", []):
                    create_flow_covers_requirement(
                        session,
                        flow_id=flow["id"],
                        req_id=req_id,
                        confidence=0.85,
                        evidence="Defined in flow specification",
                    )

                # 3. Link Page nodes (BELONGS_TO edge)
                for idx, pattern in enumerate(flow.get("pages_involved", [])):
                    query = """
                    MATCH (f:UserFlow {id: $flow_id})
                    MATCH (p:Page)
                    WHERE p.url = $pattern
                       OR p.url ENDS WITH $pattern
                       OR p.url CONTAINS $pattern
                       OR ($pattern CONTAINS '{id}' AND p.url CONTAINS split($pattern, '{id}')[0] AND p.url CONTAINS split($pattern, '{id}')[1])
                       OR ($pattern = '/documents/{id}' AND p.url CONTAINS '/documents/' AND NOT p.url CONTAINS '/recipients' AND NOT p.url CONTAINS '/fields' AND NOT p.url CONTAINS '/send' AND NOT p.url CONTAINS '/new')
                       OR ($pattern CONTAINS '{token}' AND (p.url CONTAINS '/sign' OR p.url CONTAINS 'signing-documents'))
                    MERGE (f)-[r:BELONGS_TO]->(p)
                    SET r.step_order = $step_order
                    """
                    session.run(query, flow_id=flow["id"], pattern=pattern, step_order=idx).consume()

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
