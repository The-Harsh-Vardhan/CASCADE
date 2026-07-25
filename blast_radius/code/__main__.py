"""
Phase 3 entrypoint -- run via: python -m blast_radius.code
"""

from blast_radius.code import run_code_analysis

if __name__ == "__main__":
    result = run_code_analysis()
    fns = result["functions"]
    delta = result["delta"]
    trpc = [f for f in fns if f.ast_node_type == "trpc-procedure"]
    print(f"\n✅ Phase 3 complete:")
    print(f"   {len(fns)} functions  |  {len(trpc)} tRPC procedures")
    print(f"   {len(delta.changed_files)} PR files  |  merge SHA: {delta.merge_sha[:12]}...")
