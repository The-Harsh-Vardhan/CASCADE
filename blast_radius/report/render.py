"""
blast_radius/report/render.py -- Generate HTML + Markdown blast radius reports.

v4 fixes:
  P1-27: autoescape=False -- content is internal/controlled (not user-generated).
  P2-28: Affected UI elements section included in both HTML and Markdown.
  LLM:   _generate_summary() uses call_llm_sync (never anthropic directly).
         Graceful fallback to structured summary if LLM quota is exhausted.
"""

from pathlib import Path

from blast_radius.config import settings
from blast_radius.models import BlastRadiusReport

REPORTS_DIR = Path(settings.data_dir) / "reports"


def _generate_summary(report: BlastRadiusReport) -> str:
    """
    Generate plain-English executive summary using Gemini via call_llm_sync.
    Falls back to a structured summary string if LLM quota is exhausted.

    LLM rule: NEVER call google.generativeai directly -- always use blast_radius.llm.
    """
    high = [n for n in report.affected_requirements if n.risk_tier == "HIGH"]
    prompt = (
        "Write a 2-3 sentence plain-English executive summary of this PR's impact "
        "for a non-technical QA lead at a document signing company (Documenso).\n"
        f"PR URL: {report.pr_url}\n"
        f"Changed files: {[cf.path for cf in report.changed_files[:5]]}\n"
        f"High-risk requirements affected: {[n.label for n in high[:3]]}\n"
        f"Absent requirements (no code coverage): {len(report.absent_requirements)}\n"
        f"Dark changes (untraceable to features): {len(report.dark_changes)}\n"
        "Write ONLY what the structured data supports. Do not invent risks not present. "
        "Do not use jargon like 'blast radius' or 'PPR'. Write for a QA lead who knows the product."
    )

    try:
        from blast_radius.llm import call_llm_sync
        return call_llm_sync(prompt)
    except Exception as e:
        err = str(e)
        if "429" in err or "quota" in err.lower() or "RESOURCE_EXHAUSTED" in err:
            print(f"[report] LLM quota exhausted -- using structured summary fallback.")
        else:
            print(f"[report] WARNING: LLM summary failed: {e}. Using structured fallback.")

        # Structured fallback summary
        parts = [
            f"PR #{report.pr_number} ({report.pr_title}) changed {len(report.changed_files)} files, "
            f"touching {len(report.seed_function_ids)} indexed functions."
        ]
        if report.affected_ui_elements:
            parts.append(
                f"{len(report.affected_ui_elements)} UI element(s)/page(s) are reachable from the changed code."
            )
        if report.dark_changes:
            parts.append(
                f"{len(report.dark_changes)} changed function(s) have no traceable path to product features "
                f"and require manual QA review."
            )
        if report.absent_requirements:
            parts.append(
                f"{len(report.absent_requirements)} requirement(s) have no code coverage and may be unimplemented."
            )
        return " ".join(parts)


def render(report: BlastRadiusReport) -> tuple[Path, Path]:
    """
    Render the blast radius report as HTML and Markdown.
    Returns (html_path, md_path).
    Raises RuntimeError if the report is completely empty (pipeline failure indicator).
    """
    if (
        not report.evidence_subgraph
        and not report.dark_changes
        and not report.manual_review_items
        and not report.absent_requirements
        and not report.affected_requirements
        and not report.affected_ui_elements
    ):
        raise RuntimeError(
            "Refusing to render a completely empty report. "
            "This indicates a pipeline failure in Phase 3, 4, or 5. "
            "Check logs from each phase."
        )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    # Generate executive summary (LLM or structured fallback)
    try:
        summary = _generate_summary(report)
        report = report.model_copy(update={"summary": summary})
    except Exception as e:
        print(f"[report] WARNING: Summary generation failed unexpectedly: {e}. Proceeding without.")

    # -- HTML report -------------------------------------------------------
    # v4 fix P1-27: autoescape=False -- all content is internal/controlled
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader("templates"), autoescape=False)
    template = env.get_template("report.html.j2")
    html = template.render(report=report)
    html_path = REPORTS_DIR / "blast_radius_report.html"
    html_path.write_text(html, encoding="utf-8")

    # -- Markdown report ---------------------------------------------------
    high_req   = [n for n in report.affected_requirements if n.risk_tier == "HIGH"]
    medium_req = [n for n in report.affected_requirements if n.risk_tier == "MEDIUM"]
    high_ui    = [n for n in report.affected_ui_elements   if n.risk_tier == "HIGH"]
    medium_ui  = [n for n in report.affected_ui_elements   if n.risk_tier == "MEDIUM"]

    lines = [
        f"# Blast Radius Report -- PR #{report.pr_number}",
        "",
        f"**PR:** [{report.pr_title}]({report.pr_url})  ",
        f"**Mode:** {report.mode}  **Run ID:** `{report.run_id}`",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        report.summary or "_Summary not generated._",
        "",
        "---",
        "",
        "## Changed Files",
        "",
        "| File | Status | +/− |",
        "|---|---|---|",
    ]
    for f in report.changed_files:
        lines.append(f"| `{f.path}` | {f.status} | +{f.additions}/−{f.deletions} |")

    # v4 fix P2-28: Affected UI section in Markdown
    lines += ["", f"## Affected UI / Pages ({len(report.affected_ui_elements)})", ""]
    if high_ui:
        lines += ["### 🔴 High Confidence", ""]
        for n in high_ui:
            lines += [
                f"- **{n.label}**",
                f"  - Impact: {n.impact_score:.2f} | Confidence: {n.traceability_confidence:.2f}",
                f"  - Evidence: {' -> '.join(n.evidence_path)}",
                "",
            ]
    if medium_ui:
        lines += ["### 🟡 Medium Confidence", ""]
        for n in medium_ui:
            lines.append(f"- **{n.label}** (impact: {n.impact_score:.2f})")
        lines.append("")
    if not report.affected_ui_elements:
        lines.append("_No UI elements directly traced to changed code._\n")

    lines += [f"## Affected Requirements ({len(report.affected_requirements)})", ""]
    if high_req:
        lines += ["### High Risk", ""]
        for n in high_req:
            lines += [
                f"- **{n.label}**",
                f"  - Impact: {n.impact_score:.2f} | Confidence: {n.traceability_confidence:.2f}",
                f"  - Evidence path: {' -> '.join(n.evidence_path)}",
                "",
            ]
    if medium_req:
        lines += ["### Medium Risk", ""]
        for n in medium_req:
            lines += [
                f"- **{n.label}**",
                f"  - Impact: {n.impact_score:.2f} | Confidence: {n.traceability_confidence:.2f}",
                f"  - Evidence path: {' -> '.join(n.evidence_path)}",
                "",
            ]
    low_req = [n for n in report.affected_requirements if n.risk_tier == "LOW"]
    if low_req:
        lines += ["### Low Risk (verify before updating test plans)", ""]
        for n in low_req:
            lines += [
                f"- **{n.label}**",
                f"  - Confidence: {n.traceability_confidence:.2f}",
                f"  - Evidence path: {' -> '.join(n.evidence_path)}",
                "",
            ]
    if not report.affected_requirements:
        lines.append("_No requirements directly traced to changed code._\n")

    if report.absent_requirements:
        lines += [
            f"## Absent Requirements - No Coverage Found ({len(report.absent_requirements)})",
            "",
            "These requirements exist in documentation but have no CodeFunction or UIElement "
            "linked in the graph. Each is a candidate for manual verification.",
            "",
        ]
        for req in report.absent_requirements:
            # Use full label without truncation
            lines.append(f"- **{req.label}**")
        lines.append("")

    if report.dark_changes:
        lines += [
            f"## ⚫ Dark Changes ({len(report.dark_changes)})",
            "",
            "These changed functions have no traceable path to any UI or requirement:",
            "",
        ]
        for dc in report.dark_changes:
            lines.append(f"- `{dc}`")
        lines.append("")

    if report.manual_review_items:
        lines += ["## ⚠️ Manual Review Required", ""]
        for item in report.manual_review_items:
            lines.append(f"- {item}")
        lines.append("")

    lines += [
        "## Coverage Statistics",
        "",
        "| Metric | Count |",
        "|---|---|",
        f"| Affected UI elements / pages | {len(report.affected_ui_elements)} |",
        f"| Affected requirements | {len(report.affected_requirements)} |",
        f"| Absent requirements | {len(report.absent_requirements)} |",
        f"| Dark changes | {len(report.dark_changes)} |",
        f"| Manual review items | {len(report.manual_review_items)} |",
        "",
        "---",
        f"*Report generated by Blast Radius Analyzer v4 · Run ID: `{report.run_id}`*",
    ]

    md_path = REPORTS_DIR / "blast_radius_report.md"
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"[report] HTML:     {html_path}")
    print(f"[report] Markdown: {md_path}")
    return html_path, md_path
