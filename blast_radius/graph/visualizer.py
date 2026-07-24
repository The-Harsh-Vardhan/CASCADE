"""
blast_radius/graph/visualizer.py — Standalone 3D Crystal Lattice Graph Exporter & Generator.

Queries Neo4j database for all nodes and edges across Code, UI, and Requirement layers,
formats them with 3D spatial layer coordinates, and injects data into data/graph_explorer.html.

Usage:
    python -m blast_radius.graph.visualizer
"""

import json
from pathlib import Path
from typing import Any

from neo4j import GraphDatabase
from blast_radius.config import settings

OUTPUT_HTML = Path(settings.data_dir) / "graph_explorer.html"


def fetch_neo4j_graph() -> dict[str, Any]:
    """
    Fetch all nodes and relationships from Neo4j database.
    Assigns layer spatial Z-planes:
      - CodeFunction: Z = -200
      - Page / UIElement: Z = 0
      - Requirement / GapNode: Z = +200
    """
    uri = settings.neo4j_uri
    user = settings.neo4j_user
    password = settings.neo4j_password

    nodes_dict: dict[str, dict[str, Any]] = {}
    links_list: list[dict[str, Any]] = []

    try:
        driver = GraphDatabase.driver(uri, auth=(user, password))
        with driver.session() as session:
            # Query all nodes
            node_result = session.run("""
                MATCH (n)
                RETURN elementId(n) AS internal_id, labels(n) AS labels, properties(n) AS props
            """)
            for record in node_result:
                labels = record["labels"]
                props = record["props"]
                node_id = props.get("id") or str(record["internal_id"])
                node_type = labels[0] if labels else "Unknown"

                # Assign layer Z-coordinates
                if node_type == "CodeFunction":
                    z_plane = -200
                    color = "#ba7517"
                    layer = "code"
                elif node_type in ("Page", "UIElement"):
                    z_plane = 0
                    color = "#1d9e75"
                    layer = "ui"
                elif node_type == "GapNode":
                    z_plane = 200
                    color = "#a32d2d"
                    layer = "gap"
                else:  # Requirement
                    z_plane = 200
                    color = "#7f77dd"
                    layer = "req"

                # Derive readable label
                name = props.get("name") or props.get("label") or props.get("url") or (props.get("text", "")[:40]) or node_id

                nodes_dict[node_id] = {
                    "id": node_id,
                    "name": name,
                    "node_type": node_type,
                    "layer": layer,
                    "fz": z_plane,  # Fixed Z coordinate for crystal lattice layout
                    "color": color,
                    "properties": props,
                }

            # Query all relationships
            rel_result = session.run("""
                MATCH (a)-[r]->(b)
                RETURN a.id AS source_id, elementId(a) AS source_int,
                       b.id AS target_id, elementId(b) AS target_int,
                       type(r) AS rel_type, properties(r) AS props
            """)
            for record in rel_result:
                src = record["source_id"] or str(record["source_int"])
                tgt = record["target_id"] or str(record["target_int"])
                rel_type = record["rel_type"]

                if src in nodes_dict and tgt in nodes_dict:
                    links_list.append({
                        "source": src,
                        "target": tgt,
                        "name": rel_type,
                        "rel_type": rel_type,
                        "properties": record["props"] or {},
                    })

        driver.close()
        print(f"[visualizer] Extracted {len(nodes_dict)} nodes and {len(links_list)} relationships from Neo4j.")
    except Exception as e:
        print(f"[visualizer] WARNING: Failed to fetch from Neo4j ({e}). Generating fallback template schema.")

    return {
        "nodes": list(nodes_dict.values()),
        "links": links_list,
    }


def generate_visualizer_html() -> Path:
    """
    Generate or update data/graph_explorer.html with embedded Neo4j graph data and 3D features.
    """
    graph_data = fetch_neo4j_graph()
    json_str = json.dumps(graph_data, indent=2)

    if OUTPUT_HTML.exists():
        html_content = OUTPUT_HTML.read_text(encoding="utf-8")
        target_token = "let fullGraphData = { nodes: [], links: [] };"
        replacement_token = f"let fullGraphData = {json_str};"

        if target_token in html_content:
            html_content = html_content.replace(target_token, replacement_token)
            OUTPUT_HTML.write_text(html_content, encoding="utf-8")
            print(f"[visualizer] Successfully embedded {len(graph_data['nodes'])} nodes into {OUTPUT_HTML}")
        else:
            print(f"[visualizer] 3D Graph explorer ready at: {OUTPUT_HTML}")

    return OUTPUT_HTML


if __name__ == "__main__":
    generate_visualizer_html()
