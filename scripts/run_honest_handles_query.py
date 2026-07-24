from blast_radius.graph.writer import get_driver

driver = get_driver()
with driver.session() as session:
    query = """
    MATCH (f:CodeFunction)-[:HANDLES]->(e:APIEndpoint)
    RETURN e.path AS path, count(f) AS handlers
    ORDER BY handlers DESC, path ASC
    """
    results = session.run(query).data()
    print(f"{'APIEndpoint Path':<50} | Handlers Count")
    print("-" * 68)
    for r in results:
        print(f"{r['path']:<50} | {r['handlers']:>5}")

driver.close()
