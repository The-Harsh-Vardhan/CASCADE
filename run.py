#!/usr/bin/env python3
"""
Blast Radius Analyzer
Usage:   python run.py <github_pr_url>
Example: python run.py https://github.com/documenso/documenso/pull/1234

Assumes the offline pipeline has already been run:
    python pipeline/offline.py

This script ONLY runs the online pipeline:
    parse PR URL → fetch PR diff → retrieve subgraph → reason → generate report

It does NOT crawl, ingest, or rebuild the knowledge graph.
"""

import sys
import re
from pathlib import Path


def parse_pr_url(url: str) -> tuple[str, int]:
    """
    Parse a GitHub PR URL into (repo, pr_number).

    Accepts:
      https://github.com/owner/repo/pull/123
      https://github.com/owner/repo/pull/123/files
      github.com/owner/repo/pull/123
    """
    pattern = r"github\.com/([^/]+/[^/]+)/pull/(\d+)"
    match = re.search(pattern, url)
    if not match:
        print(
            "Error: Could not parse PR URL. "
            "Expected: https://github.com/owner/repo/pull/NUMBER"
        )
        sys.exit(1)
    repo = match.group(1)
    pr_number = int(match.group(2))
    return repo, pr_number


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage:   python run.py <github_pr_url>")
        print("Example: python run.py https://github.com/documenso/documenso/pull/1234")
        sys.exit(1)

    url = sys.argv[1]
    repo, pr_number = parse_pr_url(url)

    print(f"Analyzing PR #{pr_number} in {repo}")
    print("-" * 50)

    # Run the online-only pipeline
    from pipeline.online import run_online_pipeline
    report_path = run_online_pipeline(repo, pr_number)

    # Print result path + full report text
    print("-" * 50)
    print(f"Report saved to: {report_path}")
    print()

    p = Path(report_path)
    if p.exists():
        print(p.read_text(encoding="utf-8"))


if __name__ == "__main__":
    main()
