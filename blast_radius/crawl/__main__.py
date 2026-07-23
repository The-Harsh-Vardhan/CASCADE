"""
Phase 1 entrypoint for blast_radius.crawl.
Run via: python -m blast_radius.crawl  OR  python scripts/run_pipeline.py --phase 1
"""
import sys
from blast_radius.crawl import run_crawl

def main():
    manifest, snapshots = run_crawl()
    if not snapshots:
        print("[ERROR] Phase 1 crawl produced 0 page snapshots.")
        sys.exit(1)
    
    print(f"\n[Phase 1 Complete] Captured {len(snapshots)} snapshots across dynamic app & docs.")
    for s in snapshots:
        print(f"  • {s.url} ({len(s.accessibility_tree)} AX items)")
    sys.exit(0)

if __name__ == "__main__":
    main()
