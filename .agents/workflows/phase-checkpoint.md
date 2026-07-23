# Workflow: /phase-checkpoint

Run this workflow after completing each pipeline phase.
Do not proceed to the next phase until all checks pass.

---

## Steps

1. Run the smoke test block from the v4 plan for the phase just completed

2. Verify the output data file exists and is valid:
   - Phase 0: `python scripts/validate_env.py` exits 0
   - Phase 1: `data/crawl/manifest.json` exists, contains ≥ 5 PageSnapshots
   - Phase 2: `data/requirements/requirements.json` contains ≥ 5 Requirement objects
   - Phase 3: `data/code/call_graph.json` contains ≥ 10 CodeFunction objects
             AND `data/code/pr_{number}.json` contains ≥ 1 changed file
   - Phase 4: Neo4j contains ≥ 1 IMPLEMENTS edge AND ≥ 1 RENDERS edge
   - Phase 5: `data/reports/blast_radius_report.json` is valid BlastRadiusReport
             AND at least 1 affected_requirement OR 1 dark_change is present
   - Phase 6: Both .html and .md reports exist, contain "Blast Radius Report"
             title, and contain "Affected UI" section

3. Run the path alignment check if completing Phase 3 or 4:
   ```python
   from blast_radius.code.index import load_functions
   from blast_radius.code.pr import load_delta
   verify_path_alignment(load_functions(), load_delta())
   ```

4. Commit to git with message: `phase N complete: <one-line description>`

5. Report the smoke test results and confirm which phase to proceed to next.

---

## Hard stops (do not proceed if these are true)

- Phase 1 produced < 3 PageSnapshots → crawler is broken, fix before Phase 2
- Phase 2 produced < 5 Requirements → ingest is broken or README URL failed
- Phase 3 path alignment check shows 0 matches → stop, normalize paths
- Phase 4 RENDERS count = 0 → auth crawl failed, check credentials
- Phase 5 all risk tiers are LOW → PPR sink boost may not be applied
