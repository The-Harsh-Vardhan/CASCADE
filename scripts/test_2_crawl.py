import json
from pathlib import Path

root = Path(__file__).resolve().parent.parent
summary_path = root / "outputs" / "crawl" / "summary.json"

with open(summary_path, encoding="utf-8") as f:
    summary = json.load(f)

auth_pages = [p for p in summary if p.get("requires_auth")]
print(f"Auth pages crawled: {len(auth_pages)}")
for p in auth_pages:
    print(f"  {p['url']} — {len(p.get('ui_components', []))} components")