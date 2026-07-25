"""
blast_radius/reason/impact.py -- Compute affected nodes and evidence paths from PPR scores.

v4 fixes applied:
  - evidence_path stores human-readable labels (fn.name, URL, req text excerpt)
  - weight="weight" passed as string to nx.shortest_path (not a callable)
  - paths > MAX_HOPS dropped to avoid noise
  - deduplication: keep highest impact_score per node_id
"""

import networkx as nx

from blast_radius.models import AffectedNode, EntityLink

MAX_HOPS = 6


def evidence_path_labels(
    graph: nx.DiGraph,
    seed: str,
    target: str,
    node_metadata: dict[str, dict],
) -> list[str]:
    """
    Find shortest path from seed to target and return human-readable labels.

    v4 fix: weight="weight" is the string attribute name on edges, NOT a callable.
    v4 fix: paths longer than MAX_HOPS return [] to avoid spurious evidence.
    """
    try:
        path = nx.shortest_path(
            graph,
            seed,
            target,
            method="dijkstra",
            weight="weight",   # string attribute name -- not a callable
        )
    except (nx.NetworkXNoPath, nx.NodeNotFound):
        return []

    if len(path) > MAX_HOPS + 1:
        return []

    # Convert node IDs to human-readable labels
    readable = []
    for node_id in path:
        meta = node_metadata.get(node_id, {})
        label = meta.get("label", node_id)
        readable.append(label)
    return readable


def classify_risk(impact_score: float, traceability_confidence: float) -> str:
    """Classify node risk tier from PPR impact score and path confidence."""
    if impact_score >= 0.70 and traceability_confidence >= 0.70:
        return "HIGH"
    if impact_score >= 0.40 and traceability_confidence >= 0.40:
        return "MEDIUM"
    return "LOW"


def compute_affected_nodes(
    graph: nx.DiGraph,
    seeds: list[str],
    normalized_scores: dict[str, float],
    entity_links: list[EntityLink],
    node_metadata: dict[str, dict],
) -> tuple[list[AffectedNode], list[AffectedNode], list[str]]:
    """
    Compute blast radius: affected UI/Pages and Requirements from changed functions.

    Returns:
      affected_ui     -- Page/UIElement nodes reachable from seeds
      affected_req    -- Requirement nodes reachable from seeds
      dark_changes    -- seed functions with no reachable downstream nodes
                        (changed code with no graph-traced impact)
    """
    affected_ui:  list[AffectedNode] = []
    affected_req: list[AffectedNode] = []
    dark_changes: list[str] = []

    for seed in seeds:
        if seed not in graph:
            seed_label = node_metadata.get(seed, {}).get("label", seed)
            dark_changes.append(seed_label)
            continue

        reachable = nx.descendants(graph, seed)
        if not reachable:
            seed_label = node_metadata.get(seed, {}).get("label", seed)
            dark_changes.append(seed_label)
            continue

        for node_id in reachable:
            meta = node_metadata.get(node_id, {})
            node_type = meta.get("node_type", "Unknown")
            if node_type not in ("UIElement", "Requirement", "Page"):
                continue

            impact_score = normalized_scores.get(node_id, 0.0)
            path_labels  = evidence_path_labels(graph, seed, node_id, node_metadata)
            if not path_labels:
                continue

            # Traceability confidence = min edge weight along the evidence path
            try:
                raw_path = nx.shortest_path(
                    graph, seed, node_id,
                    method="dijkstra", weight="weight"
                )
                edge_weights = [
                    (graph.get_edge_data(raw_path[i], raw_path[i + 1]) or {}).get("weight", 0.5)
                    for i in range(len(raw_path) - 1)
                ]
                tc = min(edge_weights) if edge_weights else 0.5
            except Exception:
                tc = 0.5

            risk = classify_risk(impact_score, tc)
            node_label = meta.get("label", node_id)

            node = AffectedNode(
                node_id=node_id,
                node_type=node_type,
                label=node_label,
                impact_score=round(impact_score, 4),
                traceability_confidence=round(tc, 4),
                evidence_path=path_labels,
                risk_tier=risk,
            )
            if node_type in ("UIElement", "Page"):
                affected_ui.append(node)
            else:
                affected_req.append(node)

    def dedup(nodes: list[AffectedNode]) -> list[AffectedNode]:
        seen: dict[str, AffectedNode] = {}
        for n in nodes:
            if n.node_id not in seen or n.impact_score > seen[n.node_id].impact_score:
                seen[n.node_id] = n
        return sorted(seen.values(), key=lambda x: x.impact_score, reverse=True)

    return dedup(affected_ui), dedup(affected_req), list(set(dark_changes))
