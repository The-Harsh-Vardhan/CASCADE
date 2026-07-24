"""
blast_radius/graph/writer.py — Neo4j write operations for Phase 4.

BUG-07 fix applied: build_graph() clears stale GapNodes and resets
coverage_status at the start of each run to prevent accumulation across runs.
"""

from datetime import datetime, timezone

from neo4j import GraphDatabase

from blast_radius.config import settings
from blast_radius.graph.schema import (
    CONSTRAINTS,
    UPSERT_REQUIREMENT,
    UPSERT_UI_ELEMENT,
    UPSERT_CODE_FUNCTION,
    UPSERT_PAGE,
    CREATE_IMPLEMENTS,
    CREATE_RENDERS,
    CREATE_COVERS,
    CREATE_CALLS,
    CREATE_ABSENT_FROM,
    MARK_MISSING_REQUIREMENTS,
    MARK_COVERED_REQUIREMENTS,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_driver():
    """Return a Neo4j driver using settings from .env."""
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


def ensure_schema(driver) -> None:
    """Create uniqueness constraints (idempotent — IF NOT EXISTS)."""
    with driver.session() as session:
        for constraint in CONSTRAINTS:
            try:
                session.run(constraint).consume()
            except Exception as e:
                print(f"[graph] Schema note (may already exist): {e}")


def clear_stale_data(session) -> None:
    """
    BUG-07 fix: clear GapNodes and reset coverage_status before each build.
    Without this, re-runs produce duplicate GapNodes and stale MISSING labels.
    """
    session.run("MATCH (g:GapNode) DETACH DELETE g").consume()
    session.run("MATCH (r:Requirement) SET r.coverage_status = 'UNKNOWN'").consume()
    print("[graph] Cleared stale GapNodes and reset coverage_status")


def write_requirements(session, requirements: list) -> None:
    """Upsert all Requirement nodes."""
    for r in requirements:
        session.run(UPSERT_REQUIREMENT, {
            "id": r.requirement_id,
            "text": r.text,
            "req_type": r.req_type,
            "coverage_status": r.coverage_status,
            "source_file": r.provenance.source_file,
            "excerpt": r.provenance.excerpt,
            "updated_at": _now(),
        }).consume()


def write_ui_elements(session, snapshots: list) -> None:
    """
    Write Page nodes (id='page:{sha}') and UIElement nodes.
    Page ID format matches what resolve_ui_to_functions expects.
    """
    for snap in snapshots:
        session.run(UPSERT_PAGE, {
            "id": f"page:{snap.url_sha256}",
            "url": snap.url,
            "screenshot_path": snap.screenshot_path,
            "updated_at": _now(),
        }).consume()
        for item in snap.accessibility_tree:
            session.run(UPSERT_UI_ELEMENT, {
                "id": f"ui:{snap.url_sha256}:{item.index}",
                "label": item.name or item.tag,
                "role": item.role or item.tag,
                "selector": item.selector,
                "page_url": snap.url,
                "updated_at": _now(),
            }).consume()


def write_code_functions(session, functions: list) -> int:
    """
    Upsert CodeFunction nodes and CALLS edges.
    Returns count of functions written.
    """
    for fn in functions:
        session.run(UPSERT_CODE_FUNCTION, {
            "id": fn.function_id,
            "name": fn.name,
            "file": fn.file,
            "start_line": fn.start_line,
            "ast_node_type": fn.ast_node_type,
            "updated_at": _now(),
        }).consume()

    calls_written = 0
    for fn in functions:
        for callee_id in fn.calls:
            try:
                session.run(CREATE_CALLS, {
                    "from_id": fn.function_id,
                    "to_id": callee_id,
                    "run_id": "v1",
                    "created_at": _now(),
                }).consume()
                calls_written += 1
            except Exception:
                pass  # callee not in graph (cross-file reference) — expected

    print(f"[graph] {len(functions)} CodeFunction nodes, {calls_written} CALLS edges")
    return len(functions)


def write_entity_links(session, links: list, run_id: str = "v1") -> int:
    """
    Write IMPLEMENTS and RENDERS edges to Neo4j.
    Returns count of successfully written edges. Logs but does not raise on failures.
    """
    template_map = {
        "IMPLEMENTS": CREATE_IMPLEMENTS,
        "RENDERS": CREATE_RENDERS,
        "COVERS": CREATE_COVERS,
    }
    written = 0
    failed = 0
    for link in links:
        tmpl = template_map.get(link.rel_type)
        if not tmpl:
            continue
        try:
            session.run(tmpl, {
                "from_id": link.from_id,
                "to_id": link.to_id,
                "confidence": link.confidence,
                "evidence": link.evidence,
                "source": link.source,
                "run_id": run_id,
                "created_at": _now(),
            }).consume()
            written += 1
        except Exception as e:
            failed += 1
            if failed <= 5:
                from_short = link.from_id[:30] if len(link.from_id) > 30 else link.from_id
                to_short = link.to_id[:30] if len(link.to_id) > 30 else link.to_id
                print(f"[graph] Edge warning ({link.rel_type} {from_short}...->{to_short}...): {e}")
    if failed > 5:
        print(f"[graph] ... and {failed - 5} more edge write warnings")
    return written


def mark_absent_requirements(session, run_id: str = "v1") -> int:
    """
    Mark requirements with no IMPLEMENTS edge as MISSING, create GapNodes.
    Returns count of missing requirements.

    v4 fix (P0-21): uses correct IMPLEMENTS direction (CodeFunction → Requirement).
    """
    result = session.run(MARK_MISSING_REQUIREMENTS).single()
    missing_count = result["missing_count"] if result else 0
    session.run(MARK_COVERED_REQUIREMENTS).consume()

    for row in session.run(
        "MATCH (r:Requirement {coverage_status: 'MISSING'}) RETURN r.id as id, r.text as text"
    ).data():
        req_id = row["id"]
        session.run(CREATE_ABSENT_FROM, {
            "req_id": req_id,
            "gap_id": f"gap:{req_id}",
            "reason": (
                "No CodeFunction IMPLEMENTS this requirement at cosine+LLM confidence >= 0.65. "
                "May be unimplemented, behind auth-only UI, or vocabulary mismatch."
            ),
            "threshold": 0.65,
            "run_id": run_id,
            "created_at": _now(),
        }).consume()

    return missing_count
