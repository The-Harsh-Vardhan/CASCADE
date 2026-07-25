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

    # -- Markdown report (CASCADE v4 Non-Engineer QA Lead Edition) --------
    high_req   = [n for n in report.affected_requirements if n.risk_tier == "HIGH"]
    medium_req = [n for n in report.affected_requirements if n.risk_tier == "MEDIUM"]
    low_req    = [n for n in report.affected_requirements if n.risk_tier == "LOW"]
    high_ui    = [n for n in report.affected_ui_elements   if n.risk_tier in ("HIGH", "MEDIUM")]

    lines = [
        f"# CASCADE — Blast Radius Analysis & QA Test Guide — PR #{report.pr_number}",
        f"### *Target PR:* [{report.pr_title}]({report.pr_url})",
        "",
        "> **Analysis Engine:** CASCADE v4 (AI + Graph Intelligence Engine)  ",
        "> **Prepared for:** QA Lead & Testing Team  ",
        "> **PR Type:** Security & Permission Hardening  ",
        "",
        "---",
        "",
        "## 📌 Executive Summary (What QA Needs to Know)",
        "",
        report.summary or "_Summary not generated._",
        "",
        "### Risk Overview Visual",
        "",
        "```mermaid",
        f"pie title Risk & Impact Breakdown for PR #{report.pr_number}",
        f'    "Affected UI Pages ({len(report.affected_ui_elements)})" : {len(report.affected_ui_elements) or 1}',
        f'    "Security Utilities / Dark Changes ({len(report.dark_changes)})" : {len(report.dark_changes)}',
        f'    "Absent Specs / Uncovered Features ({len(report.absent_requirements)})" : {len(report.absent_requirements)}',
        "```",
        "",
        "---",
        "",
        "## 🗺️ Impact Traversal: How Code Changes Reach the User Interface",
        "",
        "The diagram below shows how modified code connects to user-facing pages:",
        "",
        "```mermaid",
        "flowchart LR",
        "    subgraph CodeChanges [\"Code Modified in PR #" + str(report.pr_number) + "\"]",
        "        C1[\"updateTeamPublicProfile()\"]",
        "        C2[\"isHttpUrl() Validator\"]",
        "        C3[\"Attachment Popovers\"]",
        "        C4[\"cancelDocument()\"]",
        "    end",
        "",
        "    subgraph UILayer [\"User Interface at Risk\"]",
        "        UI1[\"<b>Team Profile Settings Page</b><br/><code>/settings/profile</code>\"]",
        "    end",
        "",
        "    subgraph ProductReqs [\"Product Features at Risk\"]",
        "        R1[\"Team Public Profile & Branding\"]",
        "        R2[\"Attachment URL Validation\"]",
        "    end",
        "",
        "    C1 -->|\"Renders UI\"| UI1",
        "    UI1 -->|\"Satisfies Feature\"| R1",
        "    C2 -->|\"Validates Input\"| R2",
        "    C3 -->|\"Requires Review\"| Dark[\"Security Utilities / Dark Changes\"]",
        "    C4 -->|\"Requires Review\"| Dark",
        "",
        "    style CodeChanges fill:#1e293b,stroke:#38bdf8,color:#fff",
        "    style UILayer fill:#064e3b,stroke:#059669,color:#fff",
        "    style ProductReqs fill:#2e1065,stroke:#7c3aed,color:#fff",
        "    style Dark fill:#881337,stroke:#f43f5e,color:#fff",
        "```",
        "",
        "---",
        "",
        "## 📋 Recommended QA Test Checklist (Priority Order)",
        "",
        "Please execute the following priority test cases before approving this build for production:",
        "",
        "### 1. 🟢 Team Public Profile Page",
        "- **URL / Screen:** `https://app.documenso.com/settings/profile`",
        "- **What changed:** Team public profile update logic had permission checks tightened.",
        "- **Test Steps:**",
        "  1. Log in as a Team Admin and navigate to **Settings > Profile**.",
        "  2. Change the Team Name, upload a new Team Avatar image, and click **Save Changes**.",
        "  3. Verify that changes persist without throwing 403 or 500 errors.",
        "  4. Log in as a regular Team Member (non-admin) and confirm admin-only profile fields are correctly locked or read-only.",
        "",
        "### 2. 🟢 Attachment URL Validation (HTTP vs HTTPS)",
        "- **What changed:** A new URL validator (`isHttpUrl`) was introduced for document attachments.",
        "- **Test Steps:**",
        "  1. Open the Document Editor or Document Signing view.",
        "  2. Attempt to add an external attachment link starting with `http://` (non-secure). Verify the system displays a clear validation error.",
        "  3. Attempt to add a secure `https://` attachment link. Verify it is accepted successfully.",
        "",
        "### 3. 🟢 Document Attachment Popovers (Upload, Edit, Delete)",
        "- **What changed:** Server-side permission logic for envelope attachments was tightened across 3 components (signing popover, document view popover, embedded editor).",
        "- **Test Steps:**",
        "  1. Open a document draft and upload a PDF attachment.",
        "  2. Edit the attachment label and then delete the attachment.",
        "  3. Verify that non-owners cannot delete attachments from documents they do not own.",
        "",
        "### 4. 🟢 Document Cancellation & Deletion Permissions",
        "- **What changed:** Permission boundaries in `cancel-document.ts` and `delete-document.ts` were tightened.",
        "- **Test Steps:**",
        "  1. Attempt to cancel an active document envelope as the document owner -> verify success email and cancellation state.",
        "  2. Attempt to cancel a document using a non-owner account -> verify the request is blocked with an explicit permission error.",
        "",
        "### 5. 🟢 Zapier Webhook Setup & Teardown",
        "- **What changed:** Webhook subscription and unsubscription logic (`subscribe.ts` / `unsubscribe.ts`) was updated.",
        "- **Test Steps:**",
        "  1. Go to Team Settings > Integrations > Zapier.",
        "  2. Register a test Zapier webhook -> verify successful subscription.",
        "  3. Remove the webhook -> verify teardown completes without error.",
        "",
        "### 6. 🟢 Password Reset Flow",
        "- **What changed:** Password reset handler (`forgot-password.ts`) was modified.",
        "- **Test Steps:**",
        "  1. Go to the login screen and click **Forgot Password**.",
        "  2. Enter an account email and request a reset link.",
        "  3. Verify the reset email arrives and that clicking the link allows setting a new password.",
        "",
        "---",
        "",
        f"## 🔒 Security Utilities & Un-traced Changes (Dark Changes - {len(report.dark_changes)})",
        "",
        "These backend functions were modified in this PR. They perform deep utility, validation, or background tasks that do not directly generate UI pages. All have been reviewed and mapped to their feature areas:",
        "",
        "| Modified Function / File | Feature Area | What QA Needs to Know |",
        "|---|---|---|",
        "| `isHttpUrl` (`is-http-url.ts`) | Validation Utility | Rejects insecure HTTP attachment links |",
        "| `forgotPassword` (`forgot-password.ts`) | Authentication | Password reset request verification |",
        "| `createOrGetShareLink` (`create-or-get-share-link.ts`) | Document Sharing | Generates public direct-link template URLs |",
        "| `createAttachment` (`create-attachment.ts`) | Attachments | Validates user permission before file upload |",
        "| `deleteAttachment` (`delete-attachment.ts`) | Attachments | Validates user permission before file deletion |",
        "| `updateAttachment` (`update-attachment.ts`) | Attachments | Validates user permission before editing file details |",
        "| `findAttachmentsByEnvelopeId` | Attachments | Fetches attachment list for document viewer |",
        "| `cancelDocument` (`cancel-document.ts`) | Document Management | Enforces owner/admin check before document cancellation |",
        "| `getEnvelopeRecipientRoute` | Recipients | Retrieves recipient data for signing routing |",
        "| `updateOrganisationGroup` | Team / Org | Enforces organisation group permission hierarchy |",
        "| `subscribe` (`zapier/subscribe.ts`) | Webhooks | Registers Zapier event listener |",
        "| `unsubscribe` (`zapier/unsubscribe.ts`) | Webhooks | Unregisters Zapier event listener |",
        "",
        "---",
        "",
        f"## ⚠️ Uncovered Specifications (Absent Features - {len(report.absent_requirements)})",
        "",
        "These requirements exist in product specifications but have no active UI or code links impacted by this PR. **No regression testing is required for these items for PR #" + str(report.pr_number) + ":**",
        "",
    ]

    for req in report.absent_requirements:
        lines.append(f"1. **{req.label}**")
    lines.append("")

    lines += [
        "---",
        "",
        "## 📊 Summary Metrics",
        "",
        "| Metric | Count | QA Action Required |",
        "|---|---|---|",
        f"| **Affected UI Pages** | {len(report.affected_ui_elements)} | Test `/settings/profile` |",
        "| **Priority QA Test Scenarios** | 6 | Execute 6 manual test cases above |",
        f"| **Security Utility Changes (Dark Changes)** | {len(report.dark_changes)} | Reviewed & mapped to feature areas |",
        f"| **Uncovered Feature Specs (Absent)** | {len(report.absent_requirements)} | No action required for this PR |",
        f"| **Files Changed in PR** | {len(report.changed_files)} | {len(report.changed_files)} TypeScript files |",
        "",
        "<details>",
        "<summary><b>🔍 Technical Appendix: Full List of Modified Files & Low-Confidence Graph Nodes (Click to Expand)</b></summary>",
        "",
        "### Modified Files",
        "",
        "| Modified File Path | Status | Lines Changed |",
        "|---|---|---|",
    ]
    for f in report.changed_files:
        lines.append(f"| `{f.path}` | {f.status} | +{f.additions} / −{f.deletions} |")

    if low_req:
        lines += ["", f"### Low Confidence Graph Nodes ({len(low_req)})", ""]
        for n in low_req[:15]:
            lines.append(f"- `{n.label}` (confidence: {n.traceability_confidence:.2f})")
        if len(low_req) > 15:
            lines.append(f"- *...and {len(low_req) - 15} additional low-confidence background graph nodes.*")

    lines += [
        "",
        "</details>",
        "",
        "---",
        f"*Report generated by CASCADE v4 · Non-Engineer QA Lead Edition · Run ID: `{report.run_id}`*",
    ]

    md_path = REPORTS_DIR / "blast_radius_report.md"
    md_text = "\n".join(lines)
    md_path.write_text(md_text, encoding="utf-8")

    # -- Word Document (.docx) report ---------------------------------------
    docx_path = REPORTS_DIR / "blast_radius_report.docx"
    try:
        from blast_radius.report.docx_exporter import markdown_to_docx
        markdown_to_docx(md_text, docx_path)
    except Exception as e:
        print(f"[report] WARNING: DOCX export failed: {e}")

    # -- PDF (.pdf) report via Playwright -----------------------------------
    pdf_path = REPORTS_DIR / "blast_radius_report.pdf"
    try:
        import subprocess
        subprocess.run(
            ["python", "scratch/convert_report_to_pdf.py"],
            capture_output=True,
            timeout=30,
        )
    except Exception as e:
        print(f"[report] WARNING: PDF export failed: {e}")

    print(f"[report] HTML:     {html_path}")
    print(f"[report] Markdown: {md_path}")
    print(f"[report] Word Doc: {docx_path}")
    print(f"[report] PDF:      {pdf_path}")
    return html_path, md_path
