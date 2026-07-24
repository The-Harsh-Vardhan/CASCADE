"""
scripts/test_api_endpoints.py — Smoke test script for APIEndpoint extraction, seeding, and Neo4j graph relationships.
"""

import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from blast_radius.graph.writer import get_driver
from blast_radius.api.seeder import seed_api_endpoints

try:
    driver = get_driver()
    driver.verify_connectivity()
    print("[OK] Neo4j connected successfully!")

    n_endpoints = seed_api_endpoints(driver)
    print(f"[OK] Seeded {n_endpoints} APIEndpoint nodes in Neo4j!")

    with driver.session() as session:
        # 1. Query 1: MATCH (e:APIEndpoint) RETURN e.method, e.path ORDER BY e.path
        res_ep = session.run("MATCH (e:APIEndpoint) RETURN e.method as method, e.path as path ORDER BY e.path").data()
        print(f"\n1. APIEndpoint nodes in Neo4j ({len(res_ep)}):")
        for ep in res_ep:
            print(f"   {ep['method']:<6} {ep['path']}")
        assert len(res_ep) >= 15, f"Expected >= 15 APIEndpoints, got {len(res_ep)}"

        # 2. Query 2: MATCH (f:CodeFunction)-[:HANDLES]->(e:APIEndpoint) RETURN f.name, e.method, e.path
        res_handles = session.run("""
            MATCH (f:CodeFunction)-[:HANDLES]->(e:APIEndpoint)
            RETURN f.name as fn_name, e.method as method, e.path as path
            LIMIT 10
        """).data()
        count_handles = session.run("MATCH (f:CodeFunction)-[:HANDLES]->(e:APIEndpoint) RETURN count(*) as c").single()["c"]
        print(f"\n2. HANDLES edges ({count_handles}):")
        for h in res_handles:
            print(f"   {h['fn_name']:<30} -> {h['method']:<6} {h['path']}")
        assert count_handles >= 5, f"Expected >= 5 HANDLES links, got {count_handles}"

        # 3. Query 3: MATCH (e:APIEndpoint)-[:IMPLEMENTS_REQ]->(r:Requirement) RETURN e.path, r.title
        res_impl = session.run("""
            MATCH (e:APIEndpoint)-[:IMPLEMENTS_REQ]->(r:Requirement)
            RETURN e.method as method, e.path as path, r.id as req_id, r.title as title
            LIMIT 10
        """).data()
        count_impl = session.run("MATCH (e:APIEndpoint)-[:IMPLEMENTS_REQ]->(r:Requirement) RETURN count(*) as c").single()["c"]
        print(f"\n3. IMPLEMENTS_REQ edges ({count_impl}):")
        for i in res_impl:
            t = (i['title'] or '')[:45]
            print(f"   {i['method']:<6} {i['path']:<40} -> [{i['req_id']}] {t}")
        assert count_impl > 0, f"Expected > 0 IMPLEMENTS_REQ links, got {count_impl}"

        # 4. Query 4: MATCH (u:UIElement)-[:CALLS_API]->(e:APIEndpoint)
        count_calls = session.run("MATCH (u:UIElement)-[:CALLS_API]->(e:APIEndpoint) RETURN count(*) as c").single()["c"]
        print(f"\n4. CALLS_API edges ({count_calls})")

    driver.close()
    print("\n[SUCCESS] All APIEndpoint smoke tests passed!")

except Exception as exc:
    print(f"\n[ERROR] APIEndpoint test failed: {exc}")
    import traceback
    traceback.print_exc()
