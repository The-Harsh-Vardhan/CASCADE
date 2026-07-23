#!/usr/bin/env python3
"""
Pipeline runner. Run phases individually or all at once.

Usage:
    python scripts/run_pipeline.py --phase 1
    python scripts/run_pipeline.py --all
"""
import argparse
import sys
import subprocess
from pathlib import Path

# Ensure UTF-8 stdout on Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from rich.console import Console

console = Console()

PHASES = {
    0: ("Pre-flight validation",     "scripts/validate_env.py"),
    1: ("Crawl Documenso",           "blast_radius/crawl/__main__.py"),
    2: ("Ingest requirements",       "blast_radius/ingest/__main__.py"),
    3: ("Analyze code + PR diff",    "blast_radius/code/__main__.py"),
    4: ("Build Neo4j graph",         "blast_radius/graph/__main__.py"),
    5: ("Compute blast radius",      "blast_radius/reason/__main__.py"),
    6: ("Render report",             "blast_radius/report/__main__.py"),
}


def run_phase(n: int) -> bool:
    name, module = PHASES[n]
    console.print(f"\n[bold cyan]=== Phase {n}: {name} ===[/bold cyan]")
    result = subprocess.run(
        [sys.executable, module],
        cwd=Path(__file__).parent.parent,
    )
    if result.returncode != 0:
        console.print(f"[red]✗ Phase {n} FAILED (exit {result.returncode})[/red]")
        console.print(f"  Fix the error above before proceeding to Phase {n+1}.\n")
        return False
    console.print(f"[green]✓ Phase {n} complete[/green]")
    return True


def main():
    parser = argparse.ArgumentParser(description="Blast Radius Analyzer pipeline runner")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--phase", type=int, choices=list(PHASES.keys()),
                       help="Run a single phase (0–6)")
    group.add_argument("--all", action="store_true",
                       help="Run all phases in sequence, stop on first failure")
    args = parser.parse_args()

    if args.all:
        console.print("[bold]Running all phases sequentially...[/bold]")
        for n in sorted(PHASES.keys()):
            if not run_phase(n):
                console.print(f"[red]Pipeline stopped at Phase {n}.[/red]")
                sys.exit(1)
        console.print("\n[green][bold]Pipeline complete! Reports in data/reports/[/bold][/green]")
    else:
        ok = run_phase(args.phase)
        sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
