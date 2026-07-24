"""
Analyse the keyword/vocabulary gap between requirements and code functions
to understand exactly WHY cross-layer links are sparse.
"""
import json, re
from pathlib import Path
from collections import Counter

BASE = Path(".")
STOPWORDS = {
    "page", "component", "module", "function", "service", "handler",
    "route", "type", "interface", "model", "schema", "data", "item",
    "list", "user", "get", "set", "create", "update", "delete",
}

reqs = json.loads((BASE / "data/requirements/requirements.json").read_text(encoding="utf-8"))
cg = json.loads((BASE / "data/code/call_graph.json").read_text(encoding="utf-8"))

print("=" * 60)
print("REQUIREMENT KEYWORDS vs CODE VOCABULARY OVERLAP AUDIT")
print("=" * 60)

for r in reqs[:10]:
    req_words = set(re.findall(r"\b[a-z]{4,}\b", r.get("text","").lower())) - STOPWORDS
    ui_kws = set(" ".join(r.get("related_ui_keywords", [])).lower().split())
    all_req_kws = req_words | ui_kws

    # find best matches in function names
    matches = []
    for fn in cg:
        fn_words = set(re.findall(r"\b[a-z]{4,}\b", fn.get("name","").lower())) - STOPWORDS
        fn_file_words = set(re.findall(r"\b[a-z]{4,}\b", fn.get("file","").lower())) - STOPWORDS
        overlap = all_req_kws & (fn_words | fn_file_words)
        if overlap:
            matches.append((len(overlap), fn.get("name",""), fn.get("file",""), overlap))

    matches.sort(reverse=True)
    print(f"\nREQ [{r.get('requirement_id','?')[:12]}]: {r.get('text','')[:70]}")
    print(f"  Keywords: {sorted(all_req_kws)[:10]}")
    print(f"  Top keyword-matching functions: {len(matches)}")
    for cnt, name, file, ov in matches[:3]:
        print(f"    [{cnt}] {name} ({file[:50]}) overlap={sorted(ov)}")
    if not matches:
        print(f"    ** NO KEYWORD OVERLAP WITH ANY FUNCTION **")

print()
print("=" * 60)
print("RENDERS COVERAGE: UI page urls vs code file paths")
print("=" * 60)
crawl_dir = BASE / "data/crawl"
snapshots_found = list(crawl_dir.glob("**/*.json")) if crawl_dir.exists() else []
print(f"Crawl snapshot files found: {len(snapshots_found)}")
for sf in snapshots_found[:5]:
    print(f"  {sf}")
