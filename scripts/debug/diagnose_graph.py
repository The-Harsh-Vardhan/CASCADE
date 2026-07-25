"""
Diagnostic script to verify the actual state of cross-layer connections
in the pipeline artifacts and graph_data.json.
"""
import json
from pathlib import Path
from collections import Counter

BASE = Path(".")

# ─── 1. graph_data.json ──────────────────────────────────────────────────────
print("=" * 60)
print("1. GRAPH DATA (graph_data.json)")
print("=" * 60)
gd = json.loads((BASE / "data/graph_data.json").read_text(encoding="utf-8"))
nodes = gd["nodes"]
links = gd["links"]
layer_counts = Counter(n["layer"] for n in nodes)
rel_counts = Counter(lk["rel_type"] for lk in links)

print(f"Total nodes : {len(nodes)}")
for layer, cnt in sorted(layer_counts.items()):
    print(f"  {layer:8s}: {cnt}")

print(f"\nTotal links : {len(links)}")
for rel, cnt in sorted(rel_counts.items()):
    print(f"  {rel:20s}: {cnt}")

# Count cross-layer vs same-layer links
node_layer = {n["id"]: n["layer"] for n in nodes}
cross, same = 0, 0
cross_type_counts: Counter = Counter()
for lk in links:
    src_layer = node_layer.get(lk["source"], "?")
    tgt_layer = node_layer.get(lk["target"], "?")
    if src_layer != tgt_layer:
        cross += 1
        cross_type_counts[f"{src_layer}->{tgt_layer} ({lk['rel_type']})"] += 1
    else:
        same += 1

print(f"\nCross-layer links: {cross}")
for k, v in sorted(cross_type_counts.items(), key=lambda x: -x[1]):
    print(f"  {k}: {v}")
print(f"Same-layer links: {same}")

# ─── 2. entity_links.json ────────────────────────────────────────────────────
print()
print("=" * 60)
print("2. ENTITY LINKS (data/graph/entity_links.json)")
print("=" * 60)
el = json.loads((BASE / "data/graph/entity_links.json").read_text(encoding="utf-8"))
el_rels = Counter(l["rel_type"] for l in el)
el_src = Counter(l["source"] for l in el)
print(f"Total entity links: {len(el)}")
for k, v in el_rels.items():
    print(f"  {k}: {v}")
print("  By source:")
for k, v in el_src.items():
    print(f"    {k}: {v}")

# Show a few sample IMPLEMENTS links
print("\n  Sample IMPLEMENTS links:")
for l in el:
    if l["rel_type"] == "IMPLEMENTS":
        print(f"    fn={l['from_id'][:50]} -> req={l['to_id'][:40]}  conf={l.get('confidence','?')}")
        break

# ─── 3. requirements.json ────────────────────────────────────────────────────
print()
print("=" * 60)
print("3. REQUIREMENTS (data/requirements/requirements.json)")
print("=" * 60)
reqs = json.loads((BASE / "data/requirements/requirements.json").read_text(encoding="utf-8"))
print(f"Total requirements: {len(reqs)}")
for r in reqs[:5]:
    print(f"  [{r.get('requirement_id','?')}] {r.get('text','')[:80]}")

# Check keywords presence
print("\n  Sample related_ui_keywords:")
for r in reqs[:3]:
    print(f"  {r.get('requirement_id','?')}: {r.get('related_ui_keywords', [])[:5]}")

# ─── 4. call_graph.json ──────────────────────────────────────────────────────
print()
print("=" * 60)
print("4. CODE FUNCTIONS (data/code/call_graph.json, first 2000 bytes)")
print("=" * 60)
cg_raw = (BASE / "data/code/call_graph.json").read_text(encoding="utf-8")
cg = json.loads(cg_raw)
print(f"Total functions: {len(cg)}")
# Sample names
for fn in cg[:5]:
    print(f"  name={fn.get('name','?')[:50]}  file={fn.get('file','?')[:60]}")

# ─── 5. gap_nodes.json ───────────────────────────────────────────────────────
print()
print("=" * 60)
print("5. GAP NODES (data/graph/gap_nodes.json)")
print("=" * 60)
gaps = json.loads((BASE / "data/graph/gap_nodes.json").read_text(encoding="utf-8"))
print(f"Total gap nodes (uncovered requirements): {len(gaps)}")
for g in gaps[:5]:
    print(f"  {g.get('requirement_id','?')}: {g.get('text','')[:80]}")
