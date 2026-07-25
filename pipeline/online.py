"""
pipeline/online.py — Online pipeline: fetch PR diff → reason → report.

Reads from the pre-built Neo4j graph (populated by pipeline/offline.py).
Does NOT crawl, ingest, build the graph, or run any offline steps.

Entry point called by run.py:
    from pipeline.online import run_online_pipeline
    report_path = run_online_pipeline(repo, pr_number)
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Graph readiness guard
# ---------------------------------------------------------------------------

def check_graph_ready(driver) -> bool:
    """
    Assert the Neo4j graph has been populated by the offline pipeline.

    Returns True if the graph has >= 100 nodes.
    Prints guidance and calls sys.exit(1) if the graph is empty/incomplete.
    """
    with driver.session() as session:
        count = session.run("MATCH (n) RETURN count(n) as c").single()["c"]
        if count < 100:
            print("Error: Knowledge graph is empty or incomplete.")
            print("Run the offline pipeline once before using this script:")
            print("  python pipeline/offline.py")
            print("Then re-run:")
            print("  python run.py <github_pr_url>")
            sys.exit(1)
        print(f"Graph ready - {count} nodes loaded.")
        return True


# ---------------------------------------------------------------------------
# PR delta fetch (online step — GitHub API only, no local repo needed)
# ---------------------------------------------------------------------------

def _fetch_and_save_pr_delta(repo: str, pr_number: int) -> Path:
    """
    Fetch the PR diff from the GitHub REST API and write it to
    data/code/pr_{pr_number}.json so that analyze_pr() can read it.

    Returns the path to the written delta file.
    Raises SystemExit on 404 / auth errors.
    """
    import httpx
    from blast_radius.config import settings
    from blast_radius.models import ChangedFile, PRDelta

    headers = {"Accept": "application/vnd.github.v3+json"}
    auth_headers = dict(headers)
    if settings.github_token and not settings.github_token.startswith("ghp_your"):
        auth_headers["Authorization"] = f"token {settings.github_token}"
    else:
        print(
            "Note: GITHUB_TOKEN is missing or placeholder — using unauthenticated API request."
        )

    base = f"https://api.github.com/repos/{repo}"

    # -- Fetch PR metadata -------------------------------------------------
    try:
        meta_resp = httpx.get(f"{base}/pulls/{pr_number}", headers=auth_headers, timeout=30)
        if meta_resp.status_code == 401 and "Authorization" in auth_headers:
            print("Notice: GITHUB_TOKEN unauthorized (401). Retrying unauthenticated...")
            auth_headers.pop("Authorization", None)
            meta_resp = httpx.get(f"{base}/pulls/{pr_number}", headers=auth_headers, timeout=30)

        if meta_resp.status_code == 404:
            print(
                f"Error: PR #{pr_number} not found in {repo}. "
                "Check the URL and your GITHUB_TOKEN."
            )
            sys.exit(1)
        meta_resp.raise_for_status()
        pr_meta = meta_resp.json()
    except SystemExit:
        raise
    except Exception as exc:
        print(f"Error: Failed to fetch PR metadata from GitHub API: {exc}")
        sys.exit(1)

    # -- Fetch changed files (paginated) -----------------------------------
    all_files: list[ChangedFile] = []
    page = 1
    try:
        while True:
            resp = httpx.get(
                f"{base}/pulls/{pr_number}/files",
                headers=auth_headers,
                params={"per_page": 100, "page": page},
                timeout=30,
            )
            resp.raise_for_status()
            batch = resp.json()
            if not batch:
                break
            all_files.extend(
                ChangedFile(
                    path=f["filename"],
                    status=f["status"],
                    additions=f.get("additions", 0),
                    deletions=f.get("deletions", 0),
                )
                for f in batch
            )
            if len(batch) < 100:
                break
            page += 1
    except Exception as exc:
        print(f"Error: Failed to fetch PR file list from GitHub API: {exc}")
        sys.exit(1)

    if not all_files:
        print(
            f"Error: PR #{pr_number} in {repo} returned no changed files. "
            "Verify the PR is open/merged and GITHUB_TOKEN has repo read access."
        )
        sys.exit(1)

    ts_files = [f for f in all_files if f.path.endswith((".ts", ".tsx"))]
    print(
        f"  {len(all_files)} files changed, {len(ts_files)} TypeScript"
    )

    # -- Build PRDelta and persist -----------------------------------------
    delta = PRDelta(
        pr_number=pr_number,
        title=pr_meta.get("title", f"PR #{pr_number}"),
        body=pr_meta.get("body") or "",
        author=pr_meta.get("user", {}).get("login", ""),
        merge_sha=pr_meta.get("merge_commit_sha") or "",
        parent_sha="",
        html_url=pr_meta.get("html_url", f"https://github.com/{repo}/pull/{pr_number}"),
        pr_url=f"https://github.com/{repo}/pull/{pr_number}",
        changed_files=all_files,
        changed_function_ids=[],  # populated by analyze_pr()
    )

    code_dir = Path(settings.data_dir) / "code"
    code_dir.mkdir(parents=True, exist_ok=True)
    delta_path = code_dir / f"pr_{pr_number}.json"
    delta_path.write_text(delta.model_dump_json(indent=2), encoding="utf-8")
    print(f"  PR delta saved -> {delta_path}")
    return delta_path


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run_online_pipeline(repo: str, pr_number: int) -> str:
    """
    Run the online (read-only) blast radius pipeline:

        1. Connect to Neo4j and verify graph is ready
        2. Fetch PR diff from GitHub API -> save data/code/pr_{pr_number}.json
        3. Patch settings.pr_number so analyze_pr() reads the correct delta
        4. Run Phase 5 reasoning (analyze_pr)
        5. Run Phase 6 rendering (render_report -> Markdown + HTML)
        6. Copy Markdown to outputs/reports/pr_{pr_number}_blast_radius.md

    Returns the path to the generated Markdown report as a string.
    Does NOT write to Neo4j. Does NOT trigger any offline phase.
    """
    # -- 1. Neo4j connectivity + graph guard --------------------------------
    try:
        from blast_radius.graph.writer import get_driver
        driver = get_driver()
        driver.verify_connectivity()
    except Exception as exc:
        err = str(exc)
        if "connection" in err.lower() or "refused" in err.lower() or "unavailable" in err.lower():
            print("Error: Cannot connect to Neo4j.")
            print("Start it with:  docker compose up -d")
            print(f"(Details: {exc})")
        else:
            print(f"Error: Neo4j error - {exc}")
        sys.exit(1)

    check_graph_ready(driver)
    driver.close()

    # -- 2. Fetch PR diff ---------------------------------------------------
    print(f"\nFetching PR #{pr_number} from {repo} ...")
    _fetch_and_save_pr_delta(repo, pr_number)

    # -- 3. Patch settings so reason/__init__.py reads the right delta ------
    from blast_radius.config import settings
    # pydantic-settings fields are normally frozen; bypass via object.__setattr__
    object.__setattr__(settings, "pr_number", pr_number)
    object.__setattr__(settings, "github_repo", repo)

    # -- 4. Phase 5: Reasoning ----------------------------------------------
    print("\nRunning Phase 5: Blast Radius Reasoning ...")
    from blast_radius.reason import analyze_pr
    analyze_pr()

    # -- 5. Phase 6: Render Markdown + HTML report --------------------------
    print("\nRunning Phase 6: Report Rendering ...")
    from blast_radius.report import render_report
    _html_path, md_path = render_report()

    # -- 6. Copy all 4 report formats (MD, HTML, PDF, DOCX) to PR subfolder ---
    pr_folder_name = f"pr_{pr_number}"
    out_dir = Path("outputs") / "reports" / pr_folder_name
    out_dir.mkdir(parents=True, exist_ok=True)

    sub_dir = Path("submission") / "blast radius report" / pr_folder_name
    sub_dir.mkdir(parents=True, exist_ok=True)

    md_text = md_path.read_text(encoding="utf-8")

    # Markdown (.md)
    canonical = out_dir / f"pr_{pr_number}_blast_radius.md"
    canonical.write_text(md_text, encoding="utf-8")
    Path("blast_radius_report.md").write_text(md_text, encoding="utf-8")
    (sub_dir / f"blast_radius_report_pr{pr_number}.md").write_text(md_text, encoding="utf-8")
    (Path("submission") / "blast radius report" / f"blast_radius_report_pr{pr_number}.md").write_text(md_text, encoding="utf-8")

    # HTML (.html)
    if _html_path.exists():
        html_text = _html_path.read_text(encoding="utf-8")
        (out_dir / f"pr_{pr_number}_blast_radius.html").write_text(html_text, encoding="utf-8")
        (sub_dir / f"blast_radius_report_pr{pr_number}.html").write_text(html_text, encoding="utf-8")
        (Path("submission") / "blast radius report" / f"blast_radius_report_pr{pr_number}.html").write_text(html_text, encoding="utf-8")

    # Word Doc (.docx)
    src_docx = Path("data/reports/blast_radius_report.docx")
    if src_docx.exists():
        import shutil
        shutil.copy(src_docx, out_dir / f"pr_{pr_number}_blast_radius.docx")
        shutil.copy(src_docx, sub_dir / f"blast_radius_report_pr{pr_number}.docx")

    # PDF (.pdf)
    src_pdf = Path("data/reports/blast_radius_report.pdf")
    if src_pdf.exists():
        import shutil
        shutil.copy(src_pdf, out_dir / f"pr_{pr_number}_blast_radius.pdf")
        shutil.copy(src_pdf, sub_dir / f"blast_radius_report_pr{pr_number}.pdf")

    print(f"\n[CASCADE] 4 Report Formats (MD, HTML, PDF, DOCX) saved to PR folder -> {out_dir}")
    return str(canonical)
