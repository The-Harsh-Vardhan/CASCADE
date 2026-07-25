"""
blast_radius/reason/ppr.py -- Personalized PageRank for blast radius computation.

v4 fixes:
  P1-25: min_absolute floor (1e-5) prevents noise amplification from disconnected nodes.
  P0-21: Graph is forward (CodeFunction -> Requirement), NOT reversed.
         PPR seeded at changed CodeFunctions propagates TO Pages and Requirements.
"""

import networkx as nx


def build_projection(functions: list, entity_links: list) -> nx.DiGraph:
    """
    Build a typed weighted directed graph for PPR.

    Nodes:
      - CodeFunction nodes (one per indexed function)
    Edges (all directed CodeFunction -> Target):
      - CALLS:      CodeFunction -> CodeFunction  (weight=1.0)
      - RENDERS:    CodeFunction -> Page           (weight=0.95)
      - IMPLEMENTS: CodeFunction -> Requirement   (weight=0.85)

    PPR seeded at changed CodeFunctions propagates FORWARD to reach
    Pages and Requirements -- these are the blast radius targets.
    """
    WEIGHTS = {
        "CALLS":      1.0,
        "RENDERS":    0.95,
        "IMPLEMENTS": 0.85,
        "COVERS":     0.75,   # Page/UIElement -> Requirement (FIX-1 new edge type)
    }

    g = nx.DiGraph()

    # Add all CodeFunction nodes first
    for fn in functions:
        g.add_node(fn.function_id, node_type="CodeFunction", label=fn.name)
        # Add same-file CALLS edges from the call graph
        for callee_id in fn.calls:
            g.add_edge(
                fn.function_id, callee_id,
                weight=WEIGHTS["CALLS"],
                rel_type="CALLS",
            )

    # Add IMPLEMENTS, RENDERS, and COVERS edges from Phase 4 entity links
    for link in entity_links:
        w = WEIGHTS.get(link.rel_type, 0.5) * link.confidence
        g.add_edge(link.from_id, link.to_id, weight=w, rel_type=link.rel_type)
        # Annotate target nodes with their type (for impact.py classification)
        if link.rel_type in ("IMPLEMENTS",):
            if link.to_id not in g.nodes:
                g.add_node(link.to_id, node_type="Requirement", label=link.to_id)
            elif "node_type" not in g.nodes[link.to_id]:
                g.nodes[link.to_id]["node_type"] = "Requirement"
        elif link.rel_type in ("RENDERS",):
            if link.to_id not in g.nodes:
                g.add_node(link.to_id, node_type="Page", label=link.to_id)
            elif "node_type" not in g.nodes[link.to_id]:
                g.nodes[link.to_id]["node_type"] = "Page"
        elif link.rel_type == "COVERS":
            # Source is a Page; target is a Requirement
            if link.from_id not in g.nodes:
                g.add_node(link.from_id, node_type="Page", label=link.from_id)
            elif "node_type" not in g.nodes[link.from_id]:
                g.nodes[link.from_id]["node_type"] = "Page"
            if link.to_id not in g.nodes:
                g.add_node(link.to_id, node_type="Requirement", label=link.to_id)
            elif "node_type" not in g.nodes[link.to_id]:
                g.nodes[link.to_id]["node_type"] = "Requirement"

    return g


def personalized_pagerank(graph: nx.DiGraph, seeds: list[str]) -> dict[str, float]:
    """
    Forward PPR -- seeds are changed CodeFunction nodes.
    Activation flows toward Pages and Requirements (the blast radius targets).

    v4 fix: graph is NOT reversed -- forward propagation finds downstream impact.
    """
    if not seeds:
        raise RuntimeError(
            "No seed nodes provided. Changed files are not indexed in the call graph. "
            "Check that Phase 3 paths match the PR delta paths."
        )

    missing = [s for s in seeds if s not in graph]
    if missing:
        raise RuntimeError(
            f"Seed nodes not found in graph: {missing[:3]}\n"
            "Check that Phase 3 and Phase 4 ran with matching path formats."
        )

    personalization = {n: 0.0 for n in graph.nodes()}
    weight_per_seed = 1.0 / len(seeds)
    for s in seeds:
        personalization[s] = weight_per_seed

    return nx.pagerank(
        graph,           # forward -- NOT reversed
        alpha=0.85,
        personalization=personalization,
        max_iter=100,
        tol=1e-8,
        weight="weight",
    )


def normalize_scores(
    scores: dict[str, float],
    seeds: set[str],
    min_absolute: float = 1e-5,   # v4 fix P1-25: floor prevents noise amplification
) -> dict[str, float]:
    """
    Min-max normalize PPR scores for non-seed nodes.
    Nodes below min_absolute are excluded (disconnected graph noise).
    """
    non_seed = {
        k: v for k, v in scores.items()
        if k not in seeds and v > min_absolute
    }
    if not non_seed:
        return {}
    min_v = min(non_seed.values())
    max_v = max(non_seed.values())
    if max_v == min_v:
        return {k: 0.5 for k in non_seed}
    return {k: (v - min_v) / (max_v - min_v) for k, v in non_seed.items()}
