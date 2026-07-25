"""
blast_radius/graph/__init__.py -- Phase 4: Knowledge Graph Construction orchestrator.

Builds the knowledge graph in two layers:
  1. REQUIRED: in-memory resolution saved to data/graph/entity_links.json
     (cosine + LLM -> IMPLEMENTS edges, URL pattern -> RENDERS edges)
  2. OPTIONAL: Neo4j persistence -- skipped gracefully if Neo4j is not reachable.
     Phase 5 reads entity_links.json directly, so Neo4j is NOT on the critical path.

This design means Phase 4 passes its smoke test even without Docker running.
Neo4j provides the browser visualization and ABSENT_FROM gap analysis,
but does not block Phases 5 and 6.

Prerequisites: Phases 2 and 3 must have run (requirements.json, call_graph.json).
"""

import json
import uuid
from pathlib import Path

from blast_radius.config import settings
from blast_radius.crawl.artifacts import load_all_page_snapshots
from blast_radius.graph.resolve import (
    resolve_requirements_to_functions,
    resolve_ui_to_functions,
    resolve_ui_to_requirements,
    resolve_infra_requirements,
)
from blast_radius.models import Requirement, CodeFunction, EntityLink

DATA_DIR = Path(settings.data_dir)
GRAPH_DIR = DATA_DIR / "graph"


def _try_write_neo4j(
    requirements, functions, snapshots, entity_links, absent_reqs, run_id
) -> dict:
    """
    Attempt to write the graph to Neo4j.
    Returns stats dict on success; returns {} if Neo4j is not reachable (soft failure).
    """
    try:
        from blast_radius.graph.writer import (
            get_driver, ensure_schema, clear_stale_data,
            write_requirements, write_ui_elements, write_code_functions,
            write_entity_links, mark_absent_requirements,
        )
        from blast_radius.graph.queries import write_absent_requirements
        driver = get_driver()
        # Quick connectivity check before spending time writing nodes
        driver.verify_connectivity()
    except Exception as e:
        print(f"[graph] Neo4j not reachable ({e.__class__.__name__}): {e}")
        print("[graph] Skipping Neo4j write -- entity_links.json is the source of truth for Phase 5")
        return {}

    print("[graph] Neo4j is reachable -- writing full graph...")
    try:
        ensure_schema(driver)
        with driver.session() as session:
            clear_stale_data(session)
            write_requirements(session, requirements)
            write_ui_elements(session, snapshots)
            n_fns = write_code_functions(session, functions)

            impl_links = [l for l in entity_links if l.rel_type == "IMPLEMENTS"]
            ui_impl_links = [l for l in entity_links if l.rel_type == "UI_IMPLEMENTS"]
            renders_links = [l for l in entity_links if l.rel_type == "RENDERS"]
            covers_links = [l for l in entity_links if l.rel_type == "COVERS"]
            n_impl = write_entity_links(session, impl_links, run_id=run_id)
            n_ui_impl = write_entity_links(session, ui_impl_links, run_id=run_id)
            n_renders = write_entity_links(session, renders_links, run_id=run_id)
            n_covers = write_entity_links(session, covers_links, run_id=run_id)
            missing_count = mark_absent_requirements(session, run_id=run_id)

            # Write fusion-layer AbsentRequirement nodes (Type 1 absence taxonomy)
            n_absent_written = write_absent_requirements(session, absent_reqs)

        # Seed UserFlow nodes and edges
        from flows.seeder import seed_user_flows
        n_flows = seed_user_flows(driver, requirements, snapshots)

        driver.close()
        print(
            f"[graph] Neo4j write complete: {n_impl} fn IMPLEMENTS, {n_ui_impl} UI IMPLEMENTS, "
            f"{n_renders} RENDERS, {n_covers} COVERS, {n_flows} UserFlows, {missing_count} MISSING, "
            f"{n_absent_written} AbsentRequirements"
        )
        return {
            "n_impl_neo4j": n_impl,
            "n_ui_impl_neo4j": n_ui_impl,
            "n_renders_neo4j": n_renders,
            "n_covers_neo4j": n_covers,
            "n_flows_neo4j": n_flows,
            "n_missing_neo4j": missing_count,
            "n_absent_neo4j": n_absent_written,
        }
    except Exception as e:
        print(f"[graph] Neo4j write failed mid-flight: {e}")
        try:
            driver.close()
        except Exception:
            pass
        return {}


def build_graph() -> dict:
    """
    Orchestrate Phase 4. Returns stats dict for smoke test assertions.

    Critical path (always runs):
      1. Load Phase 2/3 artifacts
      2. Cosine + LLM entity resolution -> IMPLEMENTS links
      3. URL pattern matching -> RENDERS links
      4. Save data/graph/entity_links.json

    Optional path (skipped if Neo4j down):
      5. Write all nodes + edges to Neo4j
      6. Mark absent requirements -> GapNodes
    """
    run_id = str(uuid.uuid4())[:8]
    GRAPH_DIR.mkdir(parents=True, exist_ok=True)

    # -- Load Phase 2 artifacts --------------------------------------------
    req_path = DATA_DIR / "requirements" / "requirements.json"
    if not req_path.exists():
        raise FileNotFoundError(
            f"Requirements not found at {req_path}.\n"
            "Run Phase 2 first: python -m blast_radius.ingest"
        )
    requirements = [
        Requirement.model_validate(r)
        for r in json.loads(req_path.read_text(encoding="utf-8"))
    ]

    # -- Load Phase 3 artifacts --------------------------------------------
    cg_path = DATA_DIR / "code" / "call_graph.json"
    if not cg_path.exists():
        raise FileNotFoundError(
            f"Call graph not found at {cg_path}.\n"
            "Run Phase 3 first: python -m blast_radius.code"
        )
    functions = [
        CodeFunction.model_validate(f)
        for f in json.loads(cg_path.read_text(encoding="utf-8"))
    ]

    # -- Load Phase 1 artifacts (optional) --------------------------------
    try:
        snapshots = load_all_page_snapshots()
    except Exception as e:
        print(f"[graph] WARNING: Could not load crawl snapshots: {e}")
        snapshots = []

    print(
        f"[graph] Loaded: {len(requirements)} requirements | "
        f"{len(functions)} functions | {len(snapshots)} crawl snapshots"
    )

    # -- Stage 1: IMPLEMENTS links (cosine + LLM) -------------------------
    print("[graph] Resolving IMPLEMENTS edges (cosine + LLM)...")
    impl_links = resolve_requirements_to_functions(
        requirements, functions, run_id=run_id
    )
    print(f"[graph]   {len(impl_links)} IMPLEMENTS links confirmed")

    # -- Stage 2: RENDERS links (URL pattern) -----------------------------
    print("[graph] Resolving RENDERS edges (URL pattern)...")
    renders_links = resolve_ui_to_functions(snapshots, functions, run_id=run_id)
    print(f"[graph]   {len(renders_links)} RENDERS links resolved")

    # Stage 3: COVERS links (UI -> Requirement keyword match)
    print("[graph] Resolving COVERS edges (UI -> Requirement)...")
    covers_links = resolve_ui_to_requirements(snapshots, requirements, run_id=run_id)
    print(f"[graph]   {len(covers_links)} COVERS links resolved")

    # -- Stage 4: Infra IMPLEMENTS (tooling requirements) -----------------
    repo_root = str(DATA_DIR / "repos" / "documenso")
    print("[graph] Resolving infrastructure IMPLEMENTS edges...")
    infra_links = resolve_infra_requirements(requirements, repo_root=repo_root, run_id=run_id)
    print(f"[graph]   {len(infra_links)} infra IMPLEMENTS links resolved")

    all_links = impl_links + renders_links + covers_links + infra_links

    # -- Stage 5: Fusion -- three-type absence detection -----------------
    print("[graph] Running fusion absence detection (Types 1/2/3)...")
    from blast_radius.fusion.mapper import run_fusion
    fusion_result = run_fusion(
        requirements=requirements,
        page_analyses=snapshots,   # PageSnapshot list -- mapper handles duck-typing
        code_model={"functions": functions},
        driver=None,               # no driver yet; dark code runs post-Neo4j
    )
    absent_reqs = fusion_result["absent"]
    orphaned_ui = fusion_result["orphaned_ui"]
    ui_implements = fusion_result["req_ui"]   # UIElement->Requirement IMPLEMENTS (tiered)
    print(
        f"[graph]   {len(absent_reqs)} UI-absent requirements, "
        f"{len(orphaned_ui)} orphaned UI components, "
        f"{len(ui_implements)} UIElement->Req IMPLEMENTS candidates"
    )

    all_links.extend(ui_implements)

    # -- Save entity_links.json (source of truth for Phase 5) -------------
    links_path = GRAPH_DIR / "entity_links.json"
    links_path.write_text(
        json.dumps([l.model_dump() for l in all_links], indent=2),
        encoding="utf-8",
    )
    print(f"[graph] Saved {len(all_links)} entity links => {links_path}")

    # Save GapNode summary (requirements with no IMPLEMENTS link)
    covered_req_ids = {l.to_id for l in impl_links}
    gap_nodes = [
        {"requirement_id": r.requirement_id, "text": r.text[:120],
         "reason": "No IMPLEMENTS link above confidence threshold"}
        for r in requirements
        if r.requirement_id not in covered_req_ids
    ]
    gap_path = GRAPH_DIR / "gap_nodes.json"
    gap_path.write_text(json.dumps(gap_nodes, indent=2), encoding="utf-8")
    print(f"[graph] {len(gap_nodes)} GapNodes (uncovered requirements) => {gap_path}")

    # -- Optional: write to Neo4j ------------------------------------------
    neo4j_stats = _try_write_neo4j(
        requirements, functions, snapshots, all_links, absent_reqs, run_id
    )

    stats = {
        "run_id": run_id,
        "n_requirements": len(requirements),
        "n_functions": len(functions),
        "n_snapshots": len(snapshots),
        "n_implements": len(impl_links),
        "n_renders": len(renders_links),
        "n_covers": len(covers_links),
        "n_infra_implements": len(infra_links),
        "n_ui_implements": len(ui_implements),
        "n_gap_nodes": len(gap_nodes),
        "n_absent_requirements": len(absent_reqs),
        "n_orphaned_ui": len(orphaned_ui),
        "neo4j_written": bool(neo4j_stats),
    }
    stats.update(neo4j_stats)
    return stats
