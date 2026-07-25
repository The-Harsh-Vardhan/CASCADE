from blast_radius.graph.writer import get_driver

driver = get_driver()
with driver.session() as session:
    print("=== QUERY 1 ===")
    q1 = """
    MATCH (u:UIElement)-[r:IMPLEMENTS]->(req:Requirement)
    RETURN r.source AS source, count(r) AS count, avg(r.confidence) AS avg_conf
    ORDER BY count DESC
    """
    res1 = session.run(q1).data()
    for row in res1:
        avg_c = round(row["avg_conf"], 2) if row["avg_conf"] is not None else 0
        print(f"source={row['source']} | count={row['count']} | avg_conf={avg_c}")
    if not res1:
        print("0 rows returned")

    print("\n=== QUERY 2 (DELETE cosine_only IMPLEMENTS) ===")
    q2 = """
    MATCH ()-[r:IMPLEMENTS]->()
    WHERE r.source = 'cosine_only'
    DELETE r
    """
    res2 = session.run(q2).consume()
    print(f"Deleted {res2.counters.relationships_deleted} 'cosine_only' IMPLEMENTS relationships.")

    print("\n=== QUERY 3 ===")
    q3 = """
    MATCH (f:CodeFunction)-[r:IMPLEMENTS]->(req:Requirement)
    RETURN count(r) AS count
    """
    res3 = session.run(q3).data()
    for row in res3:
        print(f"CodeFunction IMPLEMENTS count: {row['count']}")

driver.close()
