import sys
from pathlib import Path

root = Path(__file__).resolve().parent.parent
if str(root) not in sys.path:
    sys.path.insert(0, str(root))

from blast_radius.graph.writer import get_driver
from blast_radius.graph.queries import (
    upsert_user_flow,
    create_flow_belongs_to_page,
    create_flow_covers_requirement,
    get_flows_affected_by_pages,
)
from flows.seeder import DOCUMENSO_USER_FLOWS, seed_user_flows

print(f"Total defined flows: {len(DOCUMENSO_USER_FLOWS)}")

try:
    driver = get_driver()
    driver.verify_connectivity()
    print("[OK] Neo4j is connected!")

    n_flows = seed_user_flows(driver)
    print(f"[OK] Seeded {n_flows} UserFlow nodes!")

    with driver.session() as session:
        # 1. UserFlow Nodes
        res_flows = session.run("MATCH (f:UserFlow) RETURN f.id as id, f.name as name, f.entity as entity").data()
        print(f"\nUserFlow nodes in Neo4j ({len(res_flows)}):")
        for f in res_flows:
            print(f"  {f['id']} | {f['name']} ({f['entity']})")

        # 2. BELONGS_TO edges count & list
        res_belongs = session.run("MATCH (f:UserFlow)-[r:BELONGS_TO]->(p:Page) RETURN f.id as flow_id, f.name as flow, p.url as page, r.step_order as step ORDER BY f.id, r.step_order").data()
        print(f"\nBELONGS_TO edges ({len(res_belongs)}):")
        for b in res_belongs:
            print(f"  [{b['flow_id']}] {b['flow']} (step {b['step']}) -> {b['page']}")

        # 3. COVERS edges count & list
        res_covers = session.run("MATCH (f:UserFlow)-[:COVERS]->(r:Requirement) RETURN f.name as flow, r.id as req, r.text as text LIMIT 10").data()
        count_covers = session.run("MATCH (f:UserFlow)-[:COVERS]->(r:Requirement) RETURN count(*) as c").single()["c"]
        print(f"\nCOVERS edges ({count_covers}):")
        for c in res_covers:
            txt = (c['text'] or '')[:60]
            print(f"  {c['flow']} -> {c['req']} ({txt}...)")

        # 4. Hex ID verification
        hex_count = session.run("MATCH (r:Requirement) WHERE size(r.id) > 10 RETURN count(r) as c").single()["c"]
        print(f"\nHex Requirement IDs in graph: {hex_count} (Must be 0)")

        # 5. FLOW-001 verification
        flow_001_pages = [b['page'] for b in res_belongs if b['flow_id'] == 'FLOW-001']
        print(f"\nFLOW-001 connected pages ({len(flow_001_pages)}):")
        for p in flow_001_pages:
            print(f"  - {p}")

        # 6. FLOW-002 verification (MUST NOT contain /signup)
        flow_002_pages = [b['page'] for b in res_belongs if b['flow_id'] == 'FLOW-002']
        signup_linked = any('/signup' in p for p in flow_002_pages)
        print(f"\nFLOW-002 connected pages ({len(flow_002_pages)}):")
        for p in flow_002_pages:
            print(f"  - {p}")
        print(f"FLOW-002 links to /signup? {signup_linked} (Expected: False)")

        # 7. Test get_flows_affected_by_pages query
        affected = get_flows_affected_by_pages(session, ["documents", "webhooks", "teams"])
        print(f"\nAffected flows for ['documents', 'webhooks', 'teams'] ({len(affected)}):")
        for a in affected:
            print(f"  {a['id']} | {a['name']}")

    driver.close()

except Exception as exc:
    print(f"[WARN] Neo4j test error: {exc}")
    import traceback
    traceback.print_exc()
