from blast_radius.graph.writer import get_driver
from blast_radius.flows.seeder import seed_user_flows

driver = get_driver()
seed_user_flows(driver)

with driver.session() as session:
    query = """
    MATCH (f:UserFlow)-[:COVERS]->(r:Requirement)
    RETURN f.name AS name, count(r) AS req_count
    ORDER BY req_count DESC
    """
    results = session.run(query).data()
    print(f"{'UserFlow Name':<45} | Covered Requirements")
    print("-" * 68)
    for r in results:
        print(f"{r['name']:<45} | {r['req_count']:>5}")

driver.close()
