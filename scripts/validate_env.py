#!/usr/bin/env python3
"""
Phase 0 pre-flight validation.
Run this before any other phase. All checks must pass.
"""
import sys
import os
from pathlib import Path

# Add repo root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from rich.console import Console
from rich.table import Table

console = Console()
PASS = "[green]✓[/green]"
FAIL = "[red]✗[/red]"
errors = []


def check(label: str, ok: bool, fix: str = "") -> None:
    status = PASS if ok else FAIL
    console.print(f"  {status} {label}")
    if not ok:
        errors.append(f"{label} — {fix}")


console.print("\n[bold]Blast Radius Analyzer — Pre-flight Validation[/bold]\n")

# 1. Python version
import sys
py_ok = sys.version_info >= (3, 11)
check(f"Python >= 3.11 (found {sys.version.split()[0]})", py_ok,
      "Install Python 3.11+ from python.org")

# 2. .env file
env_path = Path(".env")
check(".env file exists", env_path.exists(), "cp .env.example .env and fill in values")

# 3. Required env vars
if env_path.exists():
    from dotenv import load_dotenv
    load_dotenv()

required_vars = [
    ("ANTHROPIC_API_KEY", "Get from console.anthropic.com"),
    ("GITHUB_TOKEN", "Create at GitHub → Settings → Developer settings → Tokens"),
    ("DOCUMENSO_EMAIL", "Register at app.documenso.com/signup"),
    ("DOCUMENSO_PASSWORD", "Register at app.documenso.com/signup"),
    ("NEO4J_URI", "Start Neo4j: docker compose up -d"),
    ("NEO4J_PASSWORD", "Set in docker-compose.yml and .env"),
]
for var, fix in required_vars:
    val = os.getenv(var, "")
    check(f"${var} is set", bool(val) and val != "...", fix)

pr_num = os.getenv("PR_NUMBER", "0")
check("PR_NUMBER is set (non-zero)", pr_num not in ("0", "", "..."),
      "Run: gh pr list --repo documenso/documenso --state merged --limit 20")

# 4. Neo4j reachable
console.print("\n  Checking Neo4j...")
try:
    from neo4j import GraphDatabase
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USER", "neo4j")
    password = os.getenv("NEO4J_PASSWORD", "password")
    driver = GraphDatabase.driver(uri, auth=(user, password))
    driver.verify_connectivity()
    driver.close()
    check("Neo4j reachable", True)
except Exception as e:
    check("Neo4j reachable", False, f"docker compose up -d (error: {e})")

# 5. Playwright / Chromium
console.print("\n  Checking Playwright...")
try:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        browser.close()
    check("Playwright Chromium launchable", True)
except Exception as e:
    check("Playwright Chromium launchable", False,
          f"Run: playwright install chromium (error: {e})")

# 6. ast-grep binary
import shutil
check("ast-grep binary in PATH", shutil.which("sg") is not None,
      "brew install ast-grep  OR  download from github.com/ast-grep/ast-grep/releases")

# 7. Documenso repo cloned
repo_path = Path(os.getenv("REPO_CLONE_DIR", "data/repos/documenso"))
check(f"Documenso repo cloned at {repo_path}",
      (repo_path / "package.json").exists(),
      f"git clone https://github.com/documenso/documenso {repo_path}")

# 8. Data directories
for d in ["data/crawl", "data/code", "data/requirements", "data/reports"]:
    check(f"data dir {d} exists", Path(d).exists(), f"mkdir -p {d}")

# 9. Rules files exist (warn only)
rules = list(Path("rules").glob("*.yml"))
console.print(f"\n  ast-grep rules found: {len(rules)}")

# Summary
console.print()
if errors:
    console.print(f"[red][bold]{len(errors)} check(s) failed:[/bold][/red]")
    for e in errors:
        console.print(f"  • {e}")
    console.print("\nFix all errors before running the pipeline.\n")
    sys.exit(1)
else:
    console.print("[green][bold]All checks passed. Ready to run the pipeline.[/bold][/green]\n")
    sys.exit(0)
