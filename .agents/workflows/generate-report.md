# Workflow: /generate-report

Run this workflow to generate the final blast radius report.
Prerequisites: Phases 0–5 must be complete and smoke tests passed.

---

## Steps

1. Load the blast-radius-domain skill (for report format requirements)

2. Verify prerequisites:
   ```bash
   python -c "
   import json
   from pathlib import Path
   report = json.loads(Path('data/reports/blast_radius_report.json').read_text())
   print(f'PR: #{report[\"pr_number\"]} — {report[\"pr_title\"]}')
   print(f'Changed files: {len(report[\"changed_files\"])}')
   print(f'Affected UI: {len(report[\"affected_ui_elements\"])}')
   print(f'Affected requirements: {len(report[\"affected_requirements\"])}')
   print(f'Absent requirements: {len(report[\"absent_requirements\"])}')
   print(f'Dark changes: {len(report[\"dark_changes\"])}')
   "
   ```

3. Run Phase 6 to render the report:
   ```bash
   python scripts/run_pipeline.py --phase 6
   ```

4. Verify report quality against the checklist:
   - [ ] Executive summary is 2–3 sentences, no technical jargon
   - [ ] Every HIGH finding shows evidence path with readable labels (not SHA hashes)
   - [ ] Absent requirements section present
   - [ ] Dark changes section present
   - [ ] Coverage statistics table at bottom
   - [ ] HTML renders without visible escape sequences

5. If any checklist item fails, fix the render.py or Jinja2 template and re-run.

6. Open the HTML report and read the executive summary aloud. If it requires
   knowing what tRPC is to understand, rewrite it.

---

## Report format reminder

Required sections in order:
1. Executive Summary (plain English, 2–3 sentences)
2. Changed Files (table)
3. Affected UI / Pages (HIGH → MEDIUM → LOW with evidence)
4. Affected Requirements (HIGH → MEDIUM → LOW with evidence)
5. Absent Requirements (purple section)
6. Dark Changes (black section)
7. Manual Review Required (if any)
8. Coverage Statistics (table)
