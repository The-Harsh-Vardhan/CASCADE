<p align="center">
  <img src="../docs/images/cascade_logo.png" alt="CASCADE Logo" width="220" />
</p>

# CASCADE — Change Analysis for Software Cascade using Dependency Evidence

### *Testsigma AI Engineer Assignment — Submission Package*

> *"Understand every consequence before every merge."*

**Candidate:** Harsh Vardhan (*B.Tech CSE - Data Science & Analytics, IIIT Nagpur*)  
**Role:** AI Engineer — Testsigma  
**Target Application:** [app.documenso.com](https://app.documenso.com) / [github.com/documenso/documenso](https://github.com/documenso/documenso)  
**Evaluated PR:** [Documenso PR #3046](https://github.com/documenso/documenso/pull/3046) (*fix: tighten permission and validation checks*)  

---

## 📦 Submission Deliverables Index

All four core assignment deliverables specified in Part 3 of the brief (`docs/assignment/d0_AI Engineer Updated - Assignment.md`) are package-ready in this repository:

| Deliverable | Package Location | Status | Summary |
|---|---|---|---|
| **1. Code Repository & README** | Root repo / [`README.md`](../README.md) | ✅ Complete | Fully runnable 6-phase pipeline, entry point `python run.py <url>`, 34 passing unit tests. |
| **2. Design Document (Expanded & Streamlined)** | **Expanded (21 pages):**<br>[`design_document_expanded.pdf`](design%20document/design_document_expanded.pdf)<br>[`design_document_expanded.md`](design%20document/design_document_expanded.md)<br>**Streamlined (~10 pages):**<br>[`design_document.pdf`](design%20document/design_document.pdf)<br>[`design_document.md`](design%20document/design_document.md) | ✅ Complete | Both 21-page Expanded Edition (with complete sequence diagrams, full schema descriptions, formulas, and Cypher queries) and Streamlined edition available in PDF, MD, and HTML. |
| **3. Sample Blast Radius Report (All 4 Formats)** | [`pr_3046_blast_radius.pdf`](blast%20radius%20report/pr_3046_blast_radius.pdf)<br>[`pr_3046_blast_radius.docx`](blast%20radius%20report/pr_3046_blast_radius.docx)<br>[`pr_3046_blast_radius.html`](blast%20radius%20report/pr_3046_blast_radius.html)<br>[`pr_3046_blast_radius.md`](blast%20radius%20report/pr_3046_blast_radius.md) | ✅ Complete | Real report for Documenso PR #3046 formatted for a non-engineer QA lead in 4 formats (PDF, DOCX, HTML, MD). |
| **4. Loom Walkthrough Video** | [Watch on Loom](https://www.loom.com/share/cdab254822bd4cbfbc5ebf0c9c79874e) | ✅ Complete | 5–10 min video walking through prototype execution, Neo4j 3D graph visualizer, and Design Document. |

---

## 🛠️ System Architecture & Quick Start

### Quick Execution Command

```bash
# 1. Start Neo4j container (one-time setup)
docker compose up -d

# 2. Run blast radius analysis on any Documenso PR URL
python run.py https://github.com/documenso/documenso/pull/3046
```

### Architecture Summary

```
OFFLINE PIPELINE (Graph Construction):
  Phase 1: Autonomous Browser Crawl (Playwright + Fixture Fallback) -> UIElement & UserFlow Nodes
  Phase 2: Product Spec Ingestion (Docling MDX + Gemini) -> Requirement & Gap Nodes
  Phase 3: Static Code Analysis (ast-grep AST Parser) -> CodeFunction Nodes
  Phase 4: Hybrid Entity Resolution (Vector Cosine + Gemini Reranker) -> Neo4j 3-Layer Graph

ONLINE PIPELINE (Per-PR Reasoning):
  GitHub PR URL -> Fetch Diff (REST API) -> Phase 5: Reason Engine (Personalized PageRank) -> Phase 6: Jinja2 + Gemini Prose Summary -> Final Blast Radius Report
```

---

## 🎥 Loom Walkthrough

**Recording:** [https://www.loom.com/share/cdab254822bd4cbfbc5ebf0c9c79874e](https://www.loom.com/share/cdab254822bd4cbfbc5ebf0c9c79874e)

**What the recording covers:**

1. **0:00 – 1:00 | Intro & Executive Overview:**
   - Candidate introduction and assignment objective (Blast Radius Analyzer for Documenso PRs).
   - Overview of the 3-layer Knowledge Graph (Requirements, UI/UserFlows, Code).

2. **1:00 – 2:30 | Live Prototype Demo:**
   - Neo4j running (`docker compose up -d`).
   - `python run.py https://github.com/documenso/documenso/pull/3046` executed live.
   - Report findings: 1 affected page (`/settings/profile`), 12 dark changes (security utilities), non-engineer QA test checklist.

3. **2:30 – 3:45 | Interactive 3D Graph Explorer:**
   - Live demo via [https://cascade-graph-explorer.vercel.app](https://cascade-graph-explorer.vercel.app) (or `data/graph_explorer.html`).
   - 2,300+ nodes and 7,400+ cross-layer edges explored.
   - Color-coded nodes (Purple = Requirements, Green = UIElements, Amber = CodeFunctions, Red = GapNodes/AbsentRequirements).

4. **3:45 – 5:00 | Design Document & Scope Defense:**
   - `submission/design document/design_document_expanded.md` walkthrough.
   - Agent decomposition (why graph reasoning is deterministic linear algebra, not prompt chaining).
   - Scope cuts defended (tRPC abstraction boundary, depth-1 AST parsing) and 1-week roadmap.

---

## ✉️ Email Submission Template

```text
To: [Hiring Manager / Recruiter Email]
Subject: Harsh Vardhan — AI Engineer Assignment Submission

Dear Testsigma Engineering Team,

Please find my submission for the AI Engineer Take-Home Assignment below.

- GitHub Repository: https://github.com/The-Harsh-Vardhan/Testsigma
- Loom Walkthrough Video: https://www.loom.com/share/cdab254822bd4cbfbc5ebf0c9c79874e
- Submission Package Directory: /submission

Key Deliverables:
1. Runnable Code & README: Complete 6-phase pipeline, single entry point `python run.py <pr_url>`, 34 passing unit tests.
2. Design Document (Expanded 21-page): /submission/design document/design_document_expanded.pdf
3. Sample Blast Radius Report: /submission/blast radius report/pr_3046_blast_radius.pdf (4 formats: PDF, DOCX, HTML, MD)
4. Loom Walkthrough: https://www.loom.com/share/cdab254822bd4cbfbc5ebf0c9c79874e
5. Interactive 3D Graph Explorer (Live Web App): https://cascade-graph-explorer.vercel.app

Thank you for the opportunity to work on this assignment. I look forward to discussing the design and code with the team!

Best regards,
Harsh Vardhan
```
