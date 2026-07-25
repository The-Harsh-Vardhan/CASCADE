# scripts/debug/

Internal diagnostic scripts used during development.
These are **not** needed to run the pipeline.

| Script | Purpose |
|---|---|
| `audit_implements.py` | Inspect IMPLEMENTS edge direction in Neo4j |
| `audit_ui_implements.py` | Check UIComponent → Requirement edge coverage |
| `diagnose_graph.py` | Full graph health check (node/edge counts per type) |
| `extract_graph_data.py` | Dump graph data to JSON for inspection |
| `inspect_pr.py` | Print PR delta JSON for a given PR number |
| `inspect_snapshot.py` | Print a single crawl snapshot JSON |
| `print_report.py` | Print a saved blast radius report to terminal |
| `run_cypher_queries.py` | Run ad-hoc Cypher against the live graph |
| `run_flow_query.py` | Query UserFlow and COVERS edges |
| `test_absent_count.py` | Count AbsentRequirement nodes by type |
| `test_auth_crawl.py` | Verify authenticated crawl captures auth pages |
| `test_user_flows.py` | Verify UserFlow COVERS edges are populated |
| `validate_env.py` → moved to `scripts/` | Pre-flight environment check |
| `vocab_gap_audit.py` | Find requirement vocabulary not covered by crawl |
