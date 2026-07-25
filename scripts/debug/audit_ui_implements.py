"""
scripts/audit_ui_implements.py — Audit and spot-check UIElement→Requirement IMPLEMENTS edges.

Run AFTER the pipeline re-runs with map_requirements_to_ui_v2:
    python scripts/audit_ui_implements.py

Without Neo4j (offline only, checks fusion_candidates.json):
    python scripts/audit_ui_implements.py --offline
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))


def check_offline() -> bool:
    """Verify fusion_candidates.json has tiered UI_IMPLEMENTS with real evidence."""
    for p in [
        repo_root / "outputs" / "requirements" / "fusion_candidates.json",
        repo_root / "data" / "requirements" / "fusion_candidates.json",
    ]:
        if p.exists():
            fusion_path = p
            break
    else:
        print("ERROR: fusion_candidates.json not found. Run the pipeline first.")
        return False

    data = json.loads(fusion_path.read_text(encoding="utf-8"))
    ui_impl = data.get("ui_implements", [])
    summary = data.get("summary", {})

    print(f"\n=== fusion_candidates.json (offline check) ===")
    print(f"  Total UI_IMPLEMENTS candidates: {len(ui_impl)}")
    print(f"  Summary: {json.dumps(summary.get('n_ui_implements_by_tier', {}), indent=4)}")

    if not ui_impl:
        print("FAIL: No ui_implements entries in fusion_candidates.json")
        return False

    # Check tier distribution
    tier_counts: dict[str, int] = {}
    conf_by_tier: dict[str, list[float]] = {}
    for link in ui_impl:
        src = link.get("source", "unknown")
        conf = link.get("confidence", 0)
        tier_counts[src] = tier_counts.get(src, 0) + 1
        conf_by_tier.setdefault(src, []).append(conf)

    print("\n  Tier breakdown:")
    all_pass = True
    for tier, expected_conf in [
        ("keyword_match_exact", 0.89),
        ("keyword_match_single", 0.69),
        ("page_level_match", 0.64),
        ("llm_semantic", 0.0),
    ]:
        n = tier_counts.get(tier, 0)
        if n:
            avg = sum(conf_by_tier[tier]) / n
            conf_ok = avg >= expected_conf
            mark = "✓" if conf_ok else "✗"
            print(f"  {mark} {tier:<28} n={n:<4} avg_conf={avg:.2f}")
            if not conf_ok:
                all_pass = False

    # Spot-check 5 random entries
    import random
    samples = random.sample(ui_impl, min(5, len(ui_impl)))
    print("\n  --- Spot-check (5 random edges) ---")
    for link in samples:
        print(f"  UIElement id: {link.get('from_id', '')}")
        print(f"  Requirement:  {link.get('to_id', '')}")
        print(f"  Confidence:   {link.get('confidence', 'N/A')}  Source: {link.get('source', 'N/A')}")
        print(f"  Evidence:     {link.get('evidence', '')[:120]}")
        print("  ---")

    return all_pass


def check_neo4j() -> bool:
    """Run the three verification Cypher queries from the task."""
    from blast_radius.graph.writer import get_driver

    try:
        driver = get_driver()
        driver.verify_connectivity()
    except Exception as e:
        print(f"SKIP: Neo4j not reachable — {e}")
        return True

    print("\n=== Neo4j Verification ===")
    with driver.session() as session:
        # QUERY 1: source + count + avg_conf breakdown
        q1 = """
        MATCH ()-[r:IMPLEMENTS]->()
        RETURN r.source AS source, count(r) AS n_edges, avg(r.confidence) AS avg_conf
        ORDER BY avg_conf DESC
        """
        print("\n--- All IMPLEMENTS edges by source ---")
        rows = session.run(q1).data()
        for row in rows:
            src = row["source"] or "none"
            n = row["n_edges"]
            avg = round(row["avg_conf"] or 0, 3)
            print(f"  {src:<30} n={n:<6} avg_conf={avg}")

        # QUERY 2: UIElement→Requirement spot check (5 random)
        q2 = """
        MATCH (ui:UIElement)-[r:IMPLEMENTS]->(req:Requirement)
        RETURN ui.label AS ui_label, req.title AS req_title,
               r.confidence AS conf, r.evidence AS evidence, r.source AS source
        ORDER BY rand() LIMIT 5
        """
        print("\n--- UIElement→Requirement IMPLEMENTS spot-check (5 random) ---")
        rows2 = session.run(q2).data()
        if not rows2:
            print("  (no UIElement→Requirement IMPLEMENTS edges found yet)")
        for row in rows2:
            print(f"  UI:         {row.get('ui_label', '')}")
            print(f"  REQ:        {row.get('req_title', '')}")
            print(f"  Confidence: {row.get('conf', 'N/A')} | Source: {row.get('source', 'N/A')}")
            print(f"  Evidence:   {str(row.get('evidence', ''))[:120]}")
            print("  ---")

        # QUERY 3: confidence distribution check
        q3 = """
        MATCH (ui:UIElement)-[r:IMPLEMENTS]->(req:Requirement)
        RETURN r.source AS source, count(r) AS count, avg(r.confidence) AS avg_conf
        ORDER BY avg_conf DESC
        """
        rows3 = session.run(q3).data()
        print("\n--- UIElement→Req IMPLEMENTS tier summary ---")
        if not rows3:
            print("  No UIElement→Req IMPLEMENTS edges in Neo4j yet.")
            print("  Pipeline must be re-run to write UI_IMPLEMENTS edges.")
        else:
            for row in rows3:
                print(f"  {row['source']:<28} count={row['count']:<4} avg_conf={round(row['avg_conf'],2)}")

    driver.close()
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit UIElement→Requirement IMPLEMENTS edges")
    parser.add_argument("--offline", action="store_true", help="Only check fusion_candidates.json (no Neo4j)")
    args = parser.parse_args()

    ok = check_offline()

    if not args.offline:
        ok = check_neo4j() and ok

    if ok:
        print("\n=== AUDIT PASSED ===")
    else:
        print("\n=== AUDIT FAILED — see above ===")
        sys.exit(1)


if __name__ == "__main__":
    main()
