import json, sys
sys.stdout.reconfigure(encoding='utf-8')

r = json.loads(open('data/reports/blast_radius_report.json', encoding='utf-8').read())

print('=== BLAST RADIUS REPORT ===')
print(f"PR #{r['pr_number']}: {r['pr_title']}")
print(f"run_id: {r['run_id']}")

print()
print('--- CHANGED FILES ---')
for f in r['changed_files']:
    print(f"  [{f['status']}] {f['path']} (+{f['additions']}/-{f['deletions']})")

print()
print('--- AFFECTED UI (Pages) ---')
for n in r['affected_ui_elements']:
    path_str = " -> ".join(n['evidence_path'][:5])
    print(f"  [{n['risk_tier']}] {n['label']}")
    print(f"    impact={n['impact_score']:.4f}  conf={n['traceability_confidence']:.4f}")
    print(f"    path: {path_str}")

print()
print('--- AFFECTED REQUIREMENTS ---')
for n in r['affected_requirements']:
    path_str = " -> ".join(n['evidence_path'][:5])
    print(f"  [{n['risk_tier']}] {n['label'][:80]}")
    print(f"    impact={n['impact_score']:.4f}  conf={n['traceability_confidence']:.4f}")
    print(f"    path: {path_str}")

print()
print('--- ABSENT REQUIREMENTS (GapNodes) ---')
for n in r['absent_requirements']:
    print(f"  {n['label'][:80]}")

print()
print('--- DARK CHANGES (no traceable impact) ---')
for d in r['dark_changes']:
    print(f"  {d}")

print()
print('--- MANUAL REVIEW ITEMS ---')
for m in r['manual_review_items']:
    print(f"  - {m}")
