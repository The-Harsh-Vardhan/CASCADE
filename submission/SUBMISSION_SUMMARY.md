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

## 🎥 Loom Recording Overview & Timestamp Breakdown

**Recording:** [Watch Video on Loom](https://www.loom.com/share/cdab254822bd4cbfbc5ebf0c9c79874e) *(Duration: 9:53)*

1. **0:00 – 1:35 | Introduction & Problem Statement:**
   - Candidate introduction (Harsh Vardhan) and Cascade overview: AI-powered blast radius analyzer for PRs.
   - The core problem: software complexity makes manual dependency tracing across docs, code, and live apps slow and error-prone.
   - The solution: an evidence-backed product knowledge graph linking documentation, live app crawl, and source code.

2. **1:35 – 2:37 | System Workflow & Architecture:**
   - Multi-source ingestion (Docling specification parsing, Playwright app crawling, ast-grep static analysis).
   - Unified graph assembly and per-PR execution workflow: changed entity mapping → multi-hop graph traversal → explainable report generation.

3. **2:37 – 4:55 | Interactive 3D Knowledge Graph Explorer Demo:**
   - Demonstrating the live 3D Crystal Lattice visualization ([cascade-graph-explorer.vercel.app](https://cascade-graph-explorer.vercel.app)).
   - Explaining the 3 tiers: Code (Amber), UI & UserFlows (Green), and Business Requirements (Purple).
   - Live **Path Trace Demo**: Selecting `signing token` code node → tracing cross-layer path through UI page → to the satisfied Requirement node.

4. **4:55 – 6:53 | Live Prototype Execution (PR #3046):**
   - Starting Neo4j container (`docker compose up -d`).
   - Running `python run.py https://github.com/documenso/documenso/pull/3046` live in terminal.
   - Explaining online reasoning pipeline: GitHub API diff fetching, entity seeding, multi-hop graph traversal, and confidence scoring.

5. **6:53 – 9:53 | Blast Radius Report Walkthrough (QA Lead Edition):**
   - Opening generated HTML report (`pr_3046_blast_radius.html`) in browser.
   - Reviewing executive summary, risk breakdown pie chart, and impact traversal flowchart.
   - Actionable QA test scenarios (Team Public Profile Page, Attachment URL HTTP/HTTPS validation, Popovers).
   - Dark changes table (security utilities mapping), absent specs (uncovered requirements), and final summary metrics.

```
