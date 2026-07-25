"""
Phase 5 entrypoint -- run via: python -m blast_radius.reason
"""
from blast_radius.reason import analyze_pr

if __name__ == "__main__":
    report = analyze_pr()
    print()
    print(f"PR:          #{report.pr_number} -- {report.pr_title}")
    print(f"Seeds:       {len(report.seed_function_ids)} changed functions")
    print(f"Affected UI: {len(report.affected_ui_elements)} pages/elements")
    print(f"Affected req:{len(report.affected_requirements)} requirements")
    print(f"Absent req:  {len(report.absent_requirements)} requirements")
    print(f"Dark changes:{len(report.dark_changes)} untraceable functions")
    print(f"Manual rev:  {len(report.manual_review_items)} items")
