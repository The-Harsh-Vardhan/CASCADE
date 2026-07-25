"""
blast_radius/code/__init__.py -- Phase 3: Code Analysis orchestrator.

Runs:
  1. ast-grep two-pass scan -> call_graph.json
  2. GitHub API PR delta fetch -> pr_<number>.json
  3. Path alignment verification (BUG-04 fix)

Output artifacts:
  data/code/call_graph.json
  data/code/pr_<pr_number>.json
"""

import json
from pathlib import Path

from blast_radius.config import settings
from blast_radius.code.index import build_call_graph, verify_path_alignment
from blast_radius.code.pr import get_pr_delta

CODE_DIR = Path(settings.data_dir) / "code"
REPO_PATH = str(Path(settings.data_dir) / "repos" / "documenso")


def run_code_analysis() -> dict:
    """
    Orchestrate Phase 3.

    Returns dict with 'functions' (list[CodeFunction]) and 'delta' (PRDelta).
    Raises RuntimeError on hard failures (missing repo, zero functions, path mismatch).
    """
    CODE_DIR.mkdir(parents=True, exist_ok=True)

    repo = Path(REPO_PATH)
    if not repo.exists():
        raise FileNotFoundError(
            f"Documenso repo not found at {repo}.\n"
            f"  Run: git clone --depth 1 https://github.com/documenso/documenso {repo}"
        )

    # -- Pass 1: ast-grep scan ---------------------------------------------
    print("[code] Running ast-grep scan (ts-functions + trpc-procedures)...")
    functions = build_call_graph(repo)
    trpc_fns = [f for f in functions if f.ast_node_type == "trpc-procedure"]
    print(
        f"[code] Found {len(functions)} functions total, "
        f"{len(trpc_fns)} tRPC procedures, "
        f"{sum(1 for f in functions if f.calls)} with call edges"
    )

    call_graph_path = CODE_DIR / "call_graph.json"
    call_graph_path.write_text(
        json.dumps([f.model_dump() for f in functions], indent=2),
        encoding="utf-8",
    )
    print(f"[code] Saved call graph => {call_graph_path}")

    # -- Pass 2: GitHub API PR delta --------------------------------------
    print(f"[code] Fetching PR #{settings.pr_number} delta from GitHub API...")
    delta = get_pr_delta(REPO_PATH, settings.pr_number, settings.merge_sha)
    delta_path = CODE_DIR / f"pr_{settings.pr_number}.json"
    delta_path.write_text(delta.model_dump_json(indent=2), encoding="utf-8")
    print(f"[code] Saved PR delta => {delta_path}")

    # -- BUG-04 fix: path alignment guard --------------------------------
    print("[code] Verifying path alignment (BUG-04 fix)...")
    verify_path_alignment(functions, delta)

    return {"functions": functions, "delta": delta}
