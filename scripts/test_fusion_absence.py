"""
scripts/test_fusion_absence.py — Smoke test for fusion/mapper.py absence detection.

Run AFTER the full offline pipeline (Phase 1-4):
    python scripts/test_fusion_absence.py

Without Neo4j (in-memory only):
    python scripts/test_fusion_absence.py --no-neo4j

Expected (with 50+ requirements and 20+ pages):
  - absent_requirements >= 8
  - orphaned_ui >= 10
  - dark_code >= 0 (requires Neo4j + PR changed functions)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Ensure repo root on path
repo_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(repo_root))


def test_in_memory(requirements_path: Path, crawl_dir: Path) -> None:
    """Run fusion detection without Neo4j (offline mode)."""
    from blast_radius.models import Requirement
    from blast_radius.fusion.mapper import (
        detect_ui_absent_requirements,
        detect_orphaned_ui_components,
        _load_page_analyses_from_outputs,
    )

    print(f"\n=== In-Memory Fusion Smoke Test ===")

    # Load requirements — on-disk schema uses 'id'/'description', model uses 'requirement_id'/'text'
    reqs_raw = json.loads(requirements_path.read_text(encoding="utf-8"))

    def _remap(r: dict) -> dict:
        """Normalize on-disk requirement dict to match the Pydantic Requirement model."""
        out = dict(r)
        if "requirement_id" not in out and "id" in out:
            out["requirement_id"] = out["id"]
        if "text" not in out:
            out["text"] = out.get("description") or out.get("title") or ""
        if "provenance" not in out:
            out["provenance"] = {
                "source_file": out.get("source", "requirements.json"),
                "excerpt": out.get("text", "")[:200],
            }
        return out

    requirements = [Requirement.model_validate(_remap(r)) for r in reqs_raw]
    print(f"Loaded {len(requirements)} requirements from {requirements_path}")

    # Load page analyses
    page_analyses = _load_page_analyses_from_outputs()
    print(f"Loaded {len(page_analyses)} page analyses")

    # Type 1: UI-Absent Requirements (skip LLM classification for smoke test speed)
    # Patch _classify_absence_with_llm to avoid LLM calls during unit smoke test
    import blast_radius.fusion.mapper as mapper_module
    _orig_classify = mapper_module._classify_absence_with_llm

    def _stub_classify(req, pages):
        return "UNKNOWN", "Smoke-test stub — LLM skipped"

    mapper_module._classify_absence_with_llm = _stub_classify
    try:
        absent = detect_ui_absent_requirements(requirements, page_analyses, [])
    finally:
        mapper_module._classify_absence_with_llm = _orig_classify

    print(f"\n--- Type 1: UI-Absent Requirements ---")
    print(f"  Found: {len(absent)}")
    for a in absent[:10]:
        print(f"  {a.id:<30} type={a.absence_type}  evidence={a.evidence[:60]}")

    # Type 3: Orphaned UI
    orphaned = detect_orphaned_ui_components(page_analyses, requirements, [])
    print(f"\n--- Type 3: Orphaned UI Components ---")
    print(f"  Found: {len(orphaned)}")
    for o in orphaned[:10]:
        print(f"  [{o['type']:10}] {o['component_label'][:50]}")

    # Assertions
    errors = []
    if len(absent) < 8:
        errors.append(f"FAIL: only {len(absent)} absent requirements (expected >= 8)")
    else:
        print(f"\nPASS: {len(absent)} absent requirements >= 8 threshold")

    if len(orphaned) < 10:
        errors.append(f"FAIL: only {len(orphaned)} orphaned UI components (expected >= 10)")
    else:
        print(f"PASS: {len(orphaned)} orphaned UI components >= 10 threshold")

    if errors:
        for e in errors:
            print(f"\n{e}")
        sys.exit(1)
    else:
        print("\n=== All in-memory assertions PASSED ===")


def test_neo4j() -> None:
    """Verify AbsentRequirement nodes were written to Neo4j."""
    from blast_radius.graph.writer import get_driver
    from blast_radius.graph.queries import get_absent_requirements

    print(f"\n=== Neo4j Smoke Test ===")

    try:
        driver = get_driver()
        driver.verify_connectivity()
    except Exception as e:
        print(f"SKIP: Neo4j not reachable — {e}")
        return

    with driver.session() as session:
        absent = get_absent_requirements(session)

    print(f"AbsentRequirements in graph: {len(absent)}")
    for a in absent:
        req_id = a.get("requirement_id", "")
        atype = a.get("absence_type", "")
        reason = (a.get("reason") or "")[:60]
        print(f"  {a['id']:<30} {atype:<16} {reason}")

    if len(absent) >= 8:
        print(f"\nPASS: {len(absent)} AbsentRequirements in graph >= 8 threshold")
    else:
        print(f"\nFAIL: only {len(absent)} AbsentRequirements in graph (expected >= 8)")
        print("      Run `python -m blast_radius.graph` to rebuild the graph first.")
        sys.exit(1)

    driver.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Fusion absence detection smoke test")
    parser.add_argument("--no-neo4j", action="store_true", help="Skip Neo4j assertions")
    args = parser.parse_args()

    # Locate requirements
    for req_path in [
        repo_root / "outputs" / "requirements" / "requirements.json",
        repo_root / "data" / "requirements" / "requirements.json",
    ]:
        if req_path.exists():
            requirements_path = req_path
            break
    else:
        print("ERROR: requirements.json not found. Run Phase 2 first.")
        sys.exit(1)

    # Locate crawl dir
    for crawl_path in [
        repo_root / "outputs" / "crawl",
        repo_root / "data" / "crawl",
    ]:
        if crawl_path.is_dir():
            crawl_dir = crawl_path
            break
    else:
        print("ERROR: crawl directory not found. Run Phase 1 first.")
        sys.exit(1)

    test_in_memory(requirements_path, crawl_dir)

    if not args.no_neo4j:
        test_neo4j()


if __name__ == "__main__":
    main()
