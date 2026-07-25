import json
from pathlib import Path

# Full correct text keyed by truncated prefix
fixes = {
    "The software must be packaged as standard Docker container images allowing users to self-host the platform on Docker, Do":
        "The software must be packaged as standard Docker container images allowing users to self-host the platform on Docker, Docker Compose, Kubernetes, or cloud platforms.",
    "The platform must support secure vulnerability disclosures via GitHub Security Advisories to protect self-hosted and clo":
        "The platform must support secure vulnerability disclosures via GitHub Security Advisories to protect self-hosted and cloud installations.",
    "The system must trigger a webhook notification with payload event 'DOCUMENT_CREATED' whenever a new document or template":
        "The system must trigger a webhook notification with payload event 'DOCUMENT_CREATED' whenever a new document or template draft is created.",
    "The system must trigger a webhook notification with payload event 'DOCUMENT_OPENED' when a recipient opens the document ":
        "The system must trigger a webhook notification with payload event 'DOCUMENT_OPENED' when a recipient opens the document link for the first time.",
}

# Fix blast_radius_report.json
rp = Path("data/reports/blast_radius_report.json")
data = json.loads(rp.read_text(encoding="utf-8"))
changed = 0
for a in data.get("absent_requirements", []):
    label = a.get("label", "")
    if label in fixes:
        a["label"] = fixes[label]
        changed += 1
rp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Fixed {changed} labels in blast_radius_report.json")

# Fix markdown report files
md_paths = [
    Path("blast_radius_report.md"),
    Path("submission/blast radius report/pr_3046_blast_radius.md"),
]
# Also check outputs subfolder
out_md = Path("outputs/reports/pr_3046/pr_3046_blast_radius.md")
if out_md.exists():
    md_paths.append(out_md)

for md_path in md_paths:
    if not md_path.exists():
        print(f"Skipping (not found): {md_path}")
        continue
    text = md_path.read_text(encoding="utf-8")
    md_fixes = 0
    for old, new in fixes.items():
        if old in text:
            text = text.replace(f"**{old}**", f"**{new}**")
            md_fixes += 1
    md_path.write_text(text, encoding="utf-8")
    print(f"Fixed {md_fixes} items in: {md_path}")

print("Done.")
