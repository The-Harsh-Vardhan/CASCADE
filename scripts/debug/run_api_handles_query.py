from blast_radius.graph.writer import get_driver

driver = get_driver()
with driver.session() as session:
    query = """
    MATCH (f:CodeFunction)-[:HANDLES]->(e:APIEndpoint {path: "/api/v1/documents/{id}/send"})
    RETURN f.name AS fn_name LIMIT 20
    """
    results = session.run(query).data()
    print(f"CodeFunction Name (LIMIT 20)")
    print("-" * 50)
    for r in results:
        print(f"  {r['fn_name']}")

driver.close()
