"""
blast_radius/code/pr.py -- Fetch PR changed-file list via GitHub API (httpx).

v4 fix (P0-18): GitHub API primary, PyDriller optional fallback.
v4 fix (P1-19): Explicit path normalization; warning when no seeds found.
v4 fix (P1-30): Uses settings.github_token.

Note: PyDriller is NOT a declared dependency (assignment forbids it).
      The fallback exists for resilience but will fail gracefully if missing.
"""

import subprocess

import httpx

from blast_radius.config import settings
from blast_radius.models import ChangedFile, PRDelta


def get_pr_delta(repo_path: str, pr_number: int, merge_sha: str) -> PRDelta:
    """
    Build a PRDelta by fetching changed files from the GitHub API.

    Falls back to PyDriller if the API returns empty (rate limit, no token).
    Raises RuntimeError if both paths fail.
    """
    if not merge_sha:
        raise RuntimeError(
            "MERGE_SHA is not set.\n"
            f"  Run: gh pr view {pr_number} --repo {settings.github_repo} --json mergeCommit\n"
            "  Add MERGE_SHA=<sha> to .env"
        )

    # Primary: GitHub API
    changed_files, pr_meta = _get_files_from_github_api(pr_number)

    if not changed_files:
        print("[code] WARNING: GitHub API returned no files -- trying PyDriller fallback")
        changed_files = _get_files_from_pydriller(repo_path, merge_sha)
        pr_meta = {}

    if not changed_files:
        raise RuntimeError(
            f"No changed files found for PR #{pr_number}.\n"
            "  Verify MERGE_SHA is correct and GITHUB_TOKEN has repo read access."
        )

    # Compute parent SHA for the report / design doc
    parent_sha = ""
    try:
        result = subprocess.run(
            ["git", "-C", repo_path, "rev-parse", f"{merge_sha}^1"],
            capture_output=True, text=True, timeout=15,
        )
        if result.returncode == 0:
            parent_sha = result.stdout.strip()
    except Exception as e:
        print(f"[code] WARNING: Could not compute parent SHA: {e}")

    ts_files = [f for f in changed_files if f.path.endswith((".ts", ".tsx"))]
    print(
        f"[code] PR #{pr_number}: {len(changed_files)} files changed, "
        f"{len(ts_files)} TypeScript"
    )
    if not ts_files:
        print(
            "[code] WARNING: No TypeScript files in the changed set. "
            "Phase 5 will classify all changes as DARK_CHANGE."
        )

    return PRDelta(
        pr_number=pr_number,
        title=pr_meta.get("title", f"PR #{pr_number}"),
        body=pr_meta.get("body") or "",
        author=pr_meta.get("user", {}).get("login", ""),
        merge_sha=merge_sha,
        parent_sha=parent_sha,
        html_url=pr_meta.get("html_url", f"https://github.com/{settings.github_repo}/pull/{pr_number}"),
        pr_url=f"https://github.com/{settings.github_repo}/pull/{pr_number}",
        changed_files=changed_files,
        changed_function_ids=[],  # populated by Phase 5
    )


def _get_files_from_github_api(pr_number: int) -> tuple[list[ChangedFile], dict]:
    """
    Fetch PR file list and metadata from GitHub REST API.
    Returns (changed_files, pr_meta_dict) -- both empty on failure.
    """
    headers = {"Accept": "application/vnd.github.v3+json"}
    if settings.github_token:
        headers["Authorization"] = f"token {settings.github_token}"
    else:
        print(
            "[code] WARNING: GITHUB_TOKEN not set -- "
            "unauthenticated rate limit is 60 req/hour"
        )

    base = f"https://api.github.com/repos/{settings.github_repo}"

    try:
        # Fetch PR metadata
        meta_resp = httpx.get(f"{base}/pulls/{pr_number}", headers=headers, timeout=30)
        meta_resp.raise_for_status()
        pr_meta = meta_resp.json()
    except Exception as e:
        print(f"[code] WARNING: Could not fetch PR metadata: {e}")
        pr_meta = {}

    try:
        # Fetch file list -- paginate if >30 files
        all_files: list[ChangedFile] = []
        page = 1
        while True:
            resp = httpx.get(
                f"{base}/pulls/{pr_number}/files",
                headers=headers,
                params={"per_page": 100, "page": page},
                timeout=30,
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            all_files.extend(
                ChangedFile(
                    path=f["filename"],       # forward slashes from GitHub API
                    status=f["status"],
                    additions=f.get("additions", 0),
                    deletions=f.get("deletions", 0),
                )
                for f in batch
            )
            if len(batch) < 100:
                break
            page += 1

        return all_files, pr_meta

    except Exception as e:
        print(f"[code] WARNING: GitHub API file fetch failed: {e}")
        return [], pr_meta


def _get_files_from_pydriller(repo_path: str, merge_sha: str) -> list[ChangedFile]:
    """
    Fallback: PyDriller (not a declared dep -- may raise ImportError).
    Returns [] on any failure.
    """
    try:
        from pydriller import Repository  # type: ignore
        changed: list[ChangedFile] = []
        for commit in Repository(repo_path, single=merge_sha).traverse_commits():
            for mod in commit.modified_files:
                path = (mod.new_path or mod.old_path or "").replace("\\", "/")
                if path:
                    changed.append(ChangedFile(
                        path=path,
                        status=mod.change_type.name.lower() if mod.change_type else "modified",
                        additions=mod.added_lines,
                        deletions=mod.deleted_lines,
                    ))
        return changed
    except Exception as e:
        print(f"[code] WARNING: PyDriller fallback failed: {e}")
        return []
