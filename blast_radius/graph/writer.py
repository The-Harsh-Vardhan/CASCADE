"""
blast_radius/graph/writer.py — Neo4j write operations for Phase 4.

BUG-07 fix applied: build_graph() clears stale GapNodes and resets
coverage_status at the start of each run to prevent accumulation across runs.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

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
    BUG-07 fix: clear GapNodes, stale hex-ID requirements, UserFlow nodes, and reset coverage_status.
    """
    session.run("MATCH (g:GapNode) DETACH DELETE g").consume()
    session.run("MATCH (r:Requirement) WHERE size(r.id) > 10 DETACH DELETE r").consume()
    session.run("MATCH (f:UserFlow) DETACH DELETE f").consume()
    session.run("MATCH (r:Requirement) SET r.coverage_status = 'UNKNOWN'").consume()
    print("[graph] Cleared stale GapNodes, hex Requirements, and UserFlow nodes; reset coverage_status")


ROOT_DIR = Path(__file__).resolve().parent.parent


def write_requirements(session, requirements: list = None) -> None:
    """Upsert all Requirement nodes."""
    if not requirements:
        for p in [
            ROOT_DIR / "outputs" / "requirements" / "requirements.json",
            ROOT_DIR / "data" / "requirements" / "requirements.json",
            Path("outputs/requirements/requirements.json"),
            Path("data/requirements/requirements.json"),
        ]:
            if p.exists():
                try:
                    requirements = json.loads(p.read_text(encoding="utf-8"))
                    if requirements:
                        break
                except Exception as err:
                    print(f"[graph] Failed loading requirements from {p}: {err}")

    if not requirements:
        print("[graph] WARNING: No requirements found to write!")
        return

    for r in requirements:
        req_id = getattr(r, "requirement_id", None) or (r.get("requirement_id") or r.get("id") if isinstance(r, dict) else str(r))
        text_val = getattr(r, "text", None) or (r.get("text") or r.get("description", "") if isinstance(r, dict) else "")
        title_val = getattr(r, "title", None) or (r.get("title", "") if isinstance(r, dict) else "")
        req_type_val = getattr(r, "req_type", None) or (r.get("req_type", "feature") if isinstance(r, dict) else "feature")
        area_val = getattr(r, "feature_area", None) or (r.get("feature_area", "") if isinstance(r, dict) else "")
        coverage_val = getattr(r, "coverage_status", None) or (r.get("coverage_status", "UNKNOWN") if isinstance(r, dict) else "UNKNOWN")

        source_file = ""
        excerpt_val = ""
        prov = getattr(r, "provenance", None)
        if prov:
            source_file = getattr(prov, "source_file", "") or ""
            excerpt_val = getattr(prov, "excerpt", "") or ""
        elif isinstance(r, dict):
            source_file = r.get("source", "")
            excerpt_val = r.get("description", "")

        session.run(UPSERT_REQUIREMENT, {
            "id": req_id,
            "text": text_val,
            "title": title_val,
            "req_type": req_type_val,
            "feature_area": area_val,
            "coverage_status": coverage_val,
            "source_file": source_file,
            "excerpt": excerpt_val,
            "updated_at": _now(),
        }).consume()


def write_ui_elements(session, snapshots: list = None) -> None:
    """
    Write Page nodes and UIElement nodes from outputs/crawl/*.json, summary.json, or PageSnapshot list.
    """
    import hashlib

    pages_by_url: dict[str, dict] = {}

    # 1. Load from outputs/crawl/*.json or data/crawl/*.json
    for crawl_out_dir in [
        ROOT_DIR / "outputs" / "crawl",
        ROOT_DIR / "data" / "crawl",
        Path("outputs/crawl"),
        Path("data/crawl"),
    ]:
        if crawl_out_dir.exists():
            for json_file in crawl_out_dir.glob("*.json"):
                if json_file.name in ("summary.json", "manifest.json"):
                    continue
                try:
                    data = json.loads(json_file.read_text(encoding="utf-8"))
                    if isinstance(data, dict) and "url" in data:
                        pages_by_url[data["url"]] = data
                except Exception:
                    pass

    # 2. Fallback to summary.json if directory scan found nothing
    if not pages_by_url:
        for summary_path in [
            ROOT_DIR / "outputs" / "crawl" / "summary.json",
            Path("outputs/crawl/summary.json"),
        ]:
            if summary_path.exists():
                try:
                    summary = json.loads(summary_path.read_text(encoding="utf-8"))
                    for data in summary:
                        if isinstance(data, dict) and "url" in data:
                            pages_by_url[data["url"]] = data
                except Exception:
                    pass

    # 3. Include any explicit snapshots passed in
    if snapshots:
        for snap in snapshots:
            url_val = getattr(snap, "url", None) or (snap.get("url") if isinstance(snap, dict) else str(snap))
            if url_val and url_val not in pages_by_url:
                pages_by_url[url_val] = snap

    for url_val, snap in pages_by_url.items():
        sha = getattr(snap, "url_sha256", None) or (snap.get("url_sha256") if isinstance(snap, dict) else None)
        if not sha:
            sha = hashlib.sha256(url_val.encode("utf-8")).hexdigest()[:16]

        ss_path = getattr(snap, "screenshot_path", None) or (snap.get("screenshot_path", "") if isinstance(snap, dict) else "")

        session.run(UPSERT_PAGE, {
            "id": f"page:{sha}",
            "url": url_val,
            "screenshot_path": ss_path,
            "updated_at": _now(),
        }).consume()

        items = getattr(snap, "accessibility_tree", None) or getattr(snap, "ui_components", None)
        if items is None and isinstance(snap, dict):
            items = snap.get("ui_components", []) or snap.get("accessibility_tree", [])

        if isinstance(items, list):
            for idx, item in enumerate(items):
                if isinstance(item, str):
                    label_val = item
                    role_val = "component"
                    selector_val = f"text={item}"
                else:
                    label_val = getattr(item, "name", None) or getattr(item, "label", None) or (item.get("name") or item.get("label", "") if isinstance(item, dict) else str(item))
                    role_val = getattr(item, "role", None) or getattr(item, "tag", None) or (item.get("role") or item.get("tag", "element") if isinstance(item, dict) else "element")
                    selector_val = getattr(item, "selector", None) or (item.get("selector", f"el:{idx}") if isinstance(item, dict) else f"el:{idx}")

                session.run(UPSERT_UI_ELEMENT, {
                    "id": f"ui:{sha}:{idx}",
                    "label": label_val,
                    "role": role_val,
                    "selector": selector_val,
                    "page_url": url_val,
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
