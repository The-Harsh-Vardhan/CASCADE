"""
Phase 6 entrypoint -- run via: python -m blast_radius.report
"""
from blast_radius.report import render_report

if __name__ == "__main__":
    html_path, md_path = render_report()
    print(f"\nPhase 6 complete:")
    print(f"  HTML:     {html_path}")
    print(f"  Markdown: {md_path}")
