"""
Phase 4 entrypoint — run via: python -m blast_radius.graph
"""

from blast_radius.graph import build_graph

if __name__ == "__main__":
    stats = build_graph()
    print()
    print("Phase 4 complete:")
    for k, v in stats.items():
        print(f"  {k:20s}: {v}")
