"""
Phase 2 entrypoint for blast_radius.ingest.
Run via: python -m blast_radius.ingest  OR  python scripts/run_pipeline.py --phase 2
"""
import sys
from blast_radius.ingest import run_ingest

def main():
    requirements = run_ingest()
    if not requirements:
        print("[ERROR] Phase 2 ingest produced 0 requirements.")
        sys.exit(1)

    explicit_count = sum(1 for r in requirements if r.req_type == "explicit")
    implicit_count = sum(1 for r in requirements if r.req_type == "implicit")
    other_count = len(requirements) - (explicit_count + implicit_count)

    print(f"\n[Phase 2 Complete] Ingested {len(requirements)} structured requirements.")
    print(f"  • Explicit User Stories / Features: {explicit_count}")
    print(f"  • Implicit Feature Capabilities:   {implicit_count} (Prime GapNode candidates)")
    print(f"  • Other (Security/Integration):    {other_count}")
    
    print("\nSample Extracted Requirements:")
    for r in requirements[:5]:
        print(f"  • [{r.requirement_id}] ({r.req_type.upper()}) {r.text[:90]}...")
        print(f"    UI Keywords: {', '.join(r.related_ui_keywords)}")

    sys.exit(0)

if __name__ == "__main__":
    main()
