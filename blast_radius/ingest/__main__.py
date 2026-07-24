"""
Phase 2 entrypoint for blast_radius.ingest.

Run via:
  python -m blast_radius.ingest
  python scripts/run_pipeline.py --phase 2
"""
import sys
import io
import logging
from collections import Counter

# Force UTF-8 stdout on Windows to avoid cp1252 UnicodeEncodeError
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s -- %(message)s",
    datefmt="%H:%M:%S",
)

from blast_radius.ingest import run_ingest  # noqa: E402  (after logging setup)


def main() -> None:
    requirements = run_ingest()

    if not requirements:
        print("[ERROR] Phase 2 ingest produced 0 requirements.", file=sys.stderr)
        sys.exit(1)

    # -- Summary ---------------------------------------------------------------
    area_counts: Counter[str] = Counter(r.feature_area for r in requirements)
    type_counts: Counter[str] = Counter(r.req_type for r in requirements)

    print(f"\n{'='*60}")
    print(f"  Phase 2 Complete -- {len(requirements)} structured requirements")
    print(f"{'='*60}")
    print("\n  By req_type:")
    for rtype, count in sorted(type_counts.items()):
        print(f"    {rtype:<20} {count:>3}")

    print("\n  Sample requirements:")
    for r in requirements[:5]:
        print(f"    [{r.requirement_id}] ({r.feature_area}) {r.title}")
        if r.acceptance_criteria:
            print(f"      AC: {r.acceptance_criteria[0]}")

    sys.exit(0)


if __name__ == "__main__":
    main()
