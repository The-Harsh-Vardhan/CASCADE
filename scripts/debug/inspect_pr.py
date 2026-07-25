"""Quick PR inspection script — reads from a JSON file or stdin."""
import json, sys
from pathlib import Path

pr_num = sys.argv[1] if len(sys.argv) > 1 else "pr"
data_file = Path(f"tmp_pr{pr_num}.json")
pr = json.loads(data_file.read_text(encoding="utf-8-sig"))

print(f"PR #{pr['number']}: {pr['title']}")
print(f"Merged: {pr['mergedAt']}")
commit = pr.get("mergeCommit") or {}
print(f"Merge SHA: {commit.get('oid', 'N/A')}")
print(f"Changed files: {pr['changedFiles']}  (+{pr['additions']} / -{pr['deletions']})")

files = [f["path"] for f in pr.get("files", [])]
trpc_files = [f for f in files if "trpc/server" in f]
lib_files   = [f for f in files if "server-only" in f]
other       = [f for f in files if f not in trpc_files and f not in lib_files
               and ".spec." not in f and "e2e/" not in f and not f.endswith(".md")]

print(f"\n=== trpc/server files ({len(trpc_files)}) ===")
for f in trpc_files: print(f"  {f}")
print(f"\n=== lib/server-only files ({len(lib_files)}) ===")
for f in lib_files: print(f"  {f}")
print(f"\n=== Other substantive ({len(other)}) ===")
for f in other: print(f"  {f}")
