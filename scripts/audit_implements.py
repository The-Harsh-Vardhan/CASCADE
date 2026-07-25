from blast_radius.graph.writer import get_driver

driver = get_driver()
with driver.session() as session:
    print("=== AUDIT: IMPLEMENTS edges (UIComponent -> Requirement) ===")
    q1 = """
    MATCH (ui:UIComponent)-[r:IMPLEMENTS]->(req:Requirement)
    RETURN ui.label, req.title, r.confidence, r.evidence, r.source
    ORDER BY r.confidence DESC
    LIMIT 20
    """
    res1 = session.run(q1).data()
    for row in res1:
        print(f"UI: {row.get('ui.label', 'N/A')}")
        print(f"REQ: {row.get('req.title', 'N/A')}")
        print(f"Conf: {row.get('r.confidence', 'N/A')} | Src: {row.get('r.source', 'N/A')}")
        print(f"Evid: {row.get('r.evidence', 'N/A')[:120]}")
        print("---")
    print(f"Total: {len(res1)}")

    print("\n=== What IMPLEMENTS edges actually look like by direction ===")
    q2 = """
    MATCH (a)-[r:IMPLEMENTS]->(b)
    RETURN labels(a) AS from_labels, labels(b) AS to_labels,
           r.source AS source, r.confidence AS confidence,
           count(r) AS n
    ORDER BY n DESC
    LIMIT 15
    """
    res2 = session.run(q2).data()
    for row in res2:
        print(f"({row['from_labels']}) -[IMPLEMENTS]-> ({row['to_labels']}) | src={row['source']} conf={row['confidence']} n={row['n']}")

    print("\n=== UIComponent nodes in graph ===")
    q3 = "MATCH (n:UIComponent) RETURN n.id, n.label, n.role, n.page_url LIMIT 10"
    res3 = session.run(q3).data()
    print(f"UIComponent count sample: {len(res3)}")
    for row in res3:
        print(f"  {row.get('n.id', '')} | {row.get('n.label', '')} | {row.get('n.role', '')} | {row.get('n.page_url', '')}")

    print("\n=== UIElement nodes (actual label used) ===")
    q4 = "MATCH (n:UIElement) RETURN n.id, n.label, n.role, n.page_url LIMIT 10"
    res4 = session.run(q4).data()
    print(f"UIElement count sample: {len(res4)}")
    for row in res4:
        print(f"  {row.get('n.id', '')} | {row.get('n.label', '')} | {row.get('n.role', '')} | {row.get('n.page_url', '')}")

    print("\n=== CodeFunction IMPLEMENTS summary ===")
    q5 = """
    MATCH (f:CodeFunction)-[r:IMPLEMENTS]->(req:Requirement)
    RETURN r.source AS source, count(r) AS n, avg(r.confidence) AS avg_conf
    ORDER BY n DESC
    """
    res5 = session.run(q5).data()
    for row in res5:
        print(f"src={row['source']} | n={row['n']} | avg_conf={round(row['avg_conf'],3)}")

driver.close()
