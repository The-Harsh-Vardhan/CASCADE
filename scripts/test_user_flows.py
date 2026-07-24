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
        # 1. MATCH (f:UserFlow) RETURN f.id, f.name, f.entity
        res_flows = session.run("MATCH (f:UserFlow) RETURN f.id as id, f.name as name, f.entity as entity").data()
        print(f"\nUserFlow nodes in Neo4j ({len(res_flows)}):")
        for f in res_flows:
            print(f"  {f['id']} | {f['name']} ({f['entity']})")

        # 2. MATCH (f:UserFlow)-[:BELONGS_TO]->(p:Page)
        res_belongs = session.run("MATCH (f:UserFlow)-[:BELONGS_TO]->(p:Page) RETURN f.name as flow, p.url as page").data()
        print(f"\nBELONGS_TO edges ({len(res_belongs)}):")
        for b in res_belongs[:5]:
            print(f"  {b['flow']} -> {b['page']}")

        # 3. MATCH (f:UserFlow)-[:COVERS]->(r:Requirement)
        res_covers = session.run("MATCH (f:UserFlow)-[:COVERS]->(r:Requirement) RETURN f.name as flow, r.id as req").data()
        print(f"\nCOVERS edges ({len(res_covers)}):")
        for c in res_covers[:5]:
            print(f"  {c['flow']} -> {c['req']}")

        # 4. Test get_flows_affected_by_pages query
        affected = get_flows_affected_by_pages(session, ["/documents/new", "/settings/webhooks"])
        print(f"\nAffected flows for ['/documents/new', '/settings/webhooks'] ({len(affected)}):")
        for a in affected:
            print(f"  {a['id']} | {a['name']}")

    driver.close()

except Exception as exc:
    print(f"[WARN] Neo4j test skipped: {exc}")
