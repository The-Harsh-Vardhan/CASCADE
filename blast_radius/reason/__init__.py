"""
blast_radius/reason/__init__.py — Phase 5: Blast Radius Reasoning orchestrator.

Loads Phase 3/4 artifacts, runs forward PPR, computes affected nodes,
and writes data/reports/blast_radius_report.json.

_load_graph_data() reads from entity_links.json (Phase 4 output) as the
primary source. Neo4j is attempted as a secondary source if available.
This avoids a hard Neo4j dependency while remaining compatible with the spec.

v4 fixes:
  P0-21: IMPLEMENTS direction is CodeFunction → Requirement (forward PPR).
  P1-25: min_absolute=1e-5 floor passed to normalize_scores.
  P2-26: Removed no-op Neo4j hard-fail; JSON fallback is authoritative.
"""

import json
import uuid
from pathlib import Path

import networkx as nx

from blast_radius.config import settings
from blast_radius.models import (
    AffectedNode, BlastRadiusReport, CodeFunction, EntityLink, PRDelta, Requirement,
)
from blast_radius.reason.impact import compute_affected_nodes
from blast_radius.reason.ppr import build_projection, normalize_scores, personalized_pagerank

DATA_DIR = Path(settings.data_dir)
REPORTS_DIR = DATA_DIR / "reports"


# ── Artifact loaders ──────────────────────────────────────────────────────────

def _load_artifacts() -> tuple[list[CodeFunction], PRDelta]:
    """Load Phase 3 call_graph.json and the PR delta file."""
    fn_path = DATA_DIR / "code" / "call_graph.json"
    if not fn_path.exists():
        raise FileNotFoundError(f"call_graph.json not found at {fn_path}. Run Phase 3 first.")
    functions = [
        CodeFunction.model_validate(f)
        for f in json.loads(fn_path.read_text(encoding="utf-8"))
    ]

    pr_path = DATA_DIR / "code" / f"pr_{settings.pr_number}.json"
    if not pr_path.exists():
        raise FileNotFoundError(f"PR delta not found at {pr_path}. Run Phase 3 first.")
    delta = PRDelta.model_validate_json(pr_path.read_text(encoding="utf-8"))

    return functions, delta


def _load_graph_data(functions: list[CodeFunction]) -> tuple[list[EntityLink], dict[str, dict], list[AffectedNode]]:
    """
    Load entity links and build node_metadata for evidence path rendering.

    Primary source: data/graph/entity_links.json (Phase 4 output — always available).
    The node_metadata dict is built from entity links + call_graph (no Neo4j needed).

    v4 fix (P0-21): IMPLEMENTS is CodeFunction -> Requirement (already correct in JSON).
    v4 fix (P2-32): node_metadata stores human-readable labels for evidence_path.
    """
    # Load entity links from JSON (Phase 4 output)
    links_path = DATA_DIR / "graph" / "entity_links.json"
    if not links_path.exists():
        raise FileNotFoundError(
            f"entity_links.json not found at {links_path}.\n"
            "Run Phase 4 first: python -m blast_radius.graph"
        )
    entity_links = [
        EntityLink.model_validate(l)
        for l in json.loads(links_path.read_text(encoding="utf-8"))
    ]

    # Load requirements for metadata
    req_path = DATA_DIR / "requirements" / "requirements.json"
    req_by_id: dict[str, Requirement] = {}
    if req_path.exists():
        for r in json.loads(req_path.read_text(encoding="utf-8")):
            req = Requirement.model_validate(r)
            req_by_id[req.requirement_id] = req

    # Build node_metadata from functions + entity links
    node_meta: dict[str, dict] = {}

    # CodeFunction metadata
    for fn in functions:
        file_stem = Path(fn.file).name
        node_meta[fn.function_id] = {
            "node_type": "CodeFunction",
            "label": f"{fn.name} ({file_stem})",
        }

    # Requirement and Page metadata from entity links
    for link in entity_links:
        if link.rel_type == "IMPLEMENTS":
            to_id = link.to_id
            if to_id not in node_meta:
                req = req_by_id.get(to_id)
                if req:
                    node_meta[to_id] = {
                        "node_type": "Requirement",
                        "label": req.text[:80],
                    }
                else:
                    node_meta[to_id] = {"node_type": "Requirement", "label": to_id[:40]}
        elif link.rel_type == "RENDERS":
            to_id = link.to_id
            if to_id not in node_meta:
                node_meta[to_id] = {
                    "node_type": "Page",
                    "label": to_id,  # page:{sha} — enriched below if crawl available
                }

    # Enrich Page labels from crawl snapshots if available
    try:
        from blast_radius.crawl.artifacts import load_all_page_snapshots
        for snap in load_all_page_snapshots():
            pid = f"page:{snap.url_sha256}"
            if pid in node_meta:
                node_meta[pid]["label"] = snap.url
    except Exception:
        pass

    # Build absent_requirements from gap_nodes.json
    absent_requirements: list[AffectedNode] = []
    gap_path = DATA_DIR / "graph" / "gap_nodes.json"
    if gap_path.exists():
        for g in json.loads(gap_path.read_text(encoding="utf-8")):
            absent_requirements.append(AffectedNode(
                node_id=g["requirement_id"],
                node_type="Requirement",
                label=g.get("text", g["requirement_id"])[:80],
                impact_score=0.0,
                traceability_confidence=0.0,
                evidence_path=[],
                risk_tier="ABSENT",
            ))

    print(
        f"[reason] Loaded {len(entity_links)} entity links | "
        f"{len(node_meta)} node metadata entries | "
        f"{len(absent_requirements)} absent requirements"
    )
    return entity_links, node_meta, absent_requirements


# ── Main analysis ─────────────────────────────────────────────────────────────

def analyze_pr() -> BlastRadiusReport:
    """
    Run full Phase 5 blast radius analysis for PR_NUMBER.
    Writes data/reports/blast_radius_report.json and returns the report.
    """
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid.uuid4())[:8]

    print(f"[reason] Phase 5: Blast Radius Analysis (run_id={run_id})")

    functions, delta = _load_artifacts()
    entity_links, node_meta, absent_requirements = _load_graph_data(functions)

    # Build networkx PPR projection
    graph = build_projection(functions, entity_links)
    print(f"[reason] Graph: {graph.number_of_nodes()} nodes, {graph.number_of_edges()} edges")

    # Identify seeds: PR changed paths → CodeFunction IDs
    changed_paths = {cf.path for cf in delta.changed_files}
    seeds = [fn.function_id for fn in functions if fn.file in changed_paths]

    if not seeds:
        # Diagnostic: log path format mismatch details
        sample_fn_files  = [fn.file for fn in functions[:5]]
        sample_changed   = list(changed_paths)[:5]
        print(
            f"[reason] WARNING: No seed functions found.\n"
            f"  Changed paths (PR): {sample_changed}\n"
            f"  Sample fn.file:     {sample_fn_files}\n"
            f"  Paths must match exactly. Check Phase 3 _make_function_id() format."
        )
        report = BlastRadiusReport(
            run_id=run_id, pr_url=delta.pr_url, pr_number=delta.pr_number,
            pr_title=delta.title, mode="json",
            changed_files=delta.changed_files, seed_function_ids=[],
            affected_ui_elements=[], affected_requirements=[],
            absent_requirements=absent_requirements,
            dark_changes=[cf.path for cf in delta.changed_files],
            evidence_subgraph=[], confidence_scores={},
            manual_review_items=[
                "All changed files have no matching CodeFunction nodes in the call graph. "
                "This PR may affect configuration, migrations, or files outside the indexed scope. "
                "Manual review required for all changed files."
            ],
        )
        _save_report(report)
        return report

    print(f"[reason] Seeds: {len(seeds)} changed functions")

    # Forward PPR — v4 fix P1-25: min_absolute floor
    raw_scores  = personalized_pagerank(graph, seeds)
    normalized  = normalize_scores(raw_scores, set(seeds), min_absolute=1e-5)

    affected_ui, affected_req, dark_changes = compute_affected_nodes(
        graph, seeds, normalized, entity_links, node_meta
    )
    print(
        f"[reason] Affected: {len(affected_ui)} UI/Page | "
        f"{len(affected_req)} Requirement | {len(dark_changes)} dark changes"
    )

    # Write seeds back to PR delta file
    delta.changed_function_ids = seeds
    pr_path = DATA_DIR / "code" / f"pr_{settings.pr_number}.json"
    pr_path.write_text(delta.model_dump_json(indent=2), encoding="utf-8")

    # Evidence subgraph: edges on shortest paths from seeds to affected nodes
    evidence_edge_set: set[tuple[str, str]] = set()
    for node in affected_ui + affected_req:
        for seed in seeds:
            try:
                raw_path = nx.shortest_path(
                    graph, seed, node.node_id, method="dijkstra", weight="weight"
                )
                for i in range(len(raw_path) - 1):
                    evidence_edge_set.add((raw_path[i], raw_path[i + 1]))
            except Exception:
                pass
    evidence_subgraph = [
        link.model_dump()
        for link in entity_links
        if (link.from_id, link.to_id) in evidence_edge_set
    ]

    # Manual review items
    manual_review: list[str] = []
    low_conf = [n for n in affected_ui + affected_req if n.risk_tier == "LOW"]
    if low_conf:
        manual_review.append(
            f"{len(low_conf)} node(s) have LOW confidence — verify before updating test plans."
        )
    if dark_changes:
        manual_review.append(
            f"{len(dark_changes)} changed function(s) have no traceable path to UI or requirements: "
            + ", ".join(str(dc) for dc in dark_changes[:3])
            + ("..." if len(dark_changes) > 3 else "")
        )
    if absent_requirements:
        manual_review.append(
            f"{len(absent_requirements)} requirement(s) have no code or UI coverage. "
            "They may be unimplemented features or gaps in the crawl coverage."
        )

    report = BlastRadiusReport(
        run_id=run_id, pr_url=delta.pr_url, pr_number=delta.pr_number,
        pr_title=delta.title, mode="json",
        changed_files=delta.changed_files,
        seed_function_ids=seeds,
        affected_ui_elements=affected_ui,
        affected_requirements=affected_req,
        absent_requirements=absent_requirements,
        dark_changes=dark_changes,
        evidence_subgraph=evidence_subgraph,
        confidence_scores={n.node_id: n.impact_score for n in affected_ui + affected_req},
        manual_review_items=manual_review,
    )
    _save_report(report)
    return report


def _save_report(report: BlastRadiusReport) -> None:
    out = REPORTS_DIR / "blast_radius_report.json"
    out.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    print(
        f"[reason] Report saved => {out}\n"
        f"         UI:{len(report.affected_ui_elements)} | "
        f"req:{len(report.affected_requirements)} | "
        f"absent:{len(report.absent_requirements)} | "
        f"dark:{len(report.dark_changes)} | "
        f"manual:{len(report.manual_review_items)}"
    )
