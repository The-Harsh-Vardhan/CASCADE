"""
blast_radius/graph/schema.py — Neo4j Cypher templates for graph construction.

v4 fix (P0-21): IMPLEMENTS direction is CodeFunction → Requirement.
v5 fix (FIX-1): Added COVERS edge (Page/UIElement → Requirement) from UI resolver.
v5 fix (FIX-3): MARK_MISSING excludes infra-pattern IMPLEMENTS (source='infra_pattern').
PPR seeded at changed CodeFunctions propagates FORWARD to Requirements via CALLS → IMPLEMENTS.
"""

# ── Constraints (idempotent — IF NOT EXISTS) ──────────────────────────────────
CONSTRAINTS = [
    "CREATE CONSTRAINT req_id IF NOT EXISTS FOR (n:Requirement) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT ui_id  IF NOT EXISTS FOR (n:UIElement)   REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT fn_id  IF NOT EXISTS FOR (n:CodeFunction) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT gap_id IF NOT EXISTS FOR (n:GapNode)      REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT page_id IF NOT EXISTS FOR (n:Page)        REQUIRE n.id IS UNIQUE",
]

# ── Node upserts ──────────────────────────────────────────────────────────────
UPSERT_REQUIREMENT = """
MERGE (n:Requirement {id: $id})
SET n.text = $text, n.req_type = $req_type, n.coverage_status = $coverage_status,
    n.source_file = $source_file, n.excerpt = $excerpt, n.updated_at = $updated_at
"""

UPSERT_UI_ELEMENT = """
MERGE (n:UIElement {id: $id})
SET n.label = $label, n.role = $role, n.selector = $selector,
    n.page_url = $page_url, n.updated_at = $updated_at
"""

UPSERT_CODE_FUNCTION = """
MERGE (n:CodeFunction {id: $id})
SET n.name = $name, n.file = $file, n.start_line = $start_line,
    n.ast_node_type = $ast_node_type, n.updated_at = $updated_at
"""

UPSERT_PAGE = """
MERGE (n:Page {id: $id})
SET n.url = $url, n.screenshot_path = $screenshot_path, n.updated_at = $updated_at
"""

# ── Edges ─────────────────────────────────────────────────────────────────────

# v4 fix (P0-21): IMPLEMENTS = CodeFunction → Requirement
CREATE_IMPLEMENTS = """
MATCH (c:CodeFunction {id: $from_id}), (r:Requirement {id: $to_id})
MERGE (c)-[e:IMPLEMENTS]->(r)
SET e.confidence = $confidence, e.evidence = $evidence,
    e.source = $source, e.run_id = $run_id, e.created_at = $created_at
"""

# RENDERS: CodeFunction → Page (file path segment matches URL)
CREATE_RENDERS = """
MATCH (c:CodeFunction {id: $from_id}), (p:Page {id: $to_id})
MERGE (c)-[e:RENDERS]->(p)
SET e.confidence = $confidence, e.evidence = $evidence,
    e.source = $source, e.run_id = $run_id, e.created_at = $created_at
"""

# FIX-1: COVERS: Page/UIElement → Requirement (UI vocabulary keyword match)
CREATE_COVERS = """
MATCH (p:Page {id: $from_id}), (r:Requirement {id: $to_id})
MERGE (p)-[e:COVERS]->(r)
SET e.confidence = $confidence, e.evidence = $evidence,
    e.source = $source, e.run_id = $run_id, e.created_at = $created_at
"""

CREATE_CALLS = """
MATCH (a:CodeFunction {id: $from_id}), (b:CodeFunction {id: $to_id})
MERGE (a)-[e:CALLS]->(b)
SET e.weight = 1.0, e.run_id = $run_id, e.created_at = $created_at
"""

# Absence modeling: GapNodes for requirements with no IMPLEMENTS edge
CREATE_ABSENT_FROM = """
MATCH (r:Requirement {id: $req_id})
MERGE (g:GapNode {id: $gap_id})
SET g.requirement_id = $req_id, g.reason = $reason,
    g.threshold = $threshold, g.run_id = $run_id
MERGE (r)-[e:ABSENT_FROM]->(g)
SET e.run_id = $run_id, e.created_at = $created_at
"""

# v4 fix (P0-21): check IMPLEMENTS in correct direction
# v5 fix (FIX-3): exclude infra-pattern IMPLEMENTS from gap classification
MARK_MISSING_REQUIREMENTS = """
MATCH (r:Requirement)
WHERE NOT (:CodeFunction)-[:IMPLEMENTS]->(r)
  AND NOT ()-[:IMPLEMENTS {source: 'infra_pattern'}]->(r)
  AND NOT ()-[:COVERS]->(r)
SET r.coverage_status = 'MISSING'
RETURN count(r) as missing_count
"""

MARK_COVERED_REQUIREMENTS = """
MATCH (r:Requirement)
WHERE (:CodeFunction)-[:IMPLEMENTS]->(r)
SET r.coverage_status = 'PARTIAL'
RETURN count(r) as partial_count
"""
