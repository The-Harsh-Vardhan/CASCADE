from blast_radius.graph.writer import get_driver

driver = get_driver()
with driver.session() as session:
    print("=== QUERY 1 ===")
    q1 = """
    MATCH (a:AbsentRequirement)
    RETURN a.id AS id, a.absence_type AS absence_type, a.reason AS reason
    ORDER BY a.absence_type
    """
    res1 = session.run(q1).data()
    for row in res1:
        print(f"{row['id']} | {row['absence_type']} | {row['reason']}")
    print(f"Total: {len(res1)}")

    print("\n=== QUERY 2 ===")
    q2 = """
    MATCH (a:AbsentRequirement)-[:MISSING_FROM]->(p:Page)
    RETURN a.id AS id, a.absence_type AS absence_type, p.url AS url
    """
    res2 = session.run(q2).data()
    for row in res2:
        print(f"{row['id']} | {row['absence_type']} | {row['url']}")
    print(f"Total: {len(res2)}")
driver.close()
