# 3D Graph Explorer Architecture & Visual Enhancements Plan

This plan addresses the analysis of graph connectivity/imbalance and provides a complete overhaul for `c:\D Drive\Projects\Summers 2026\Testsigma\data\graph_explorer.html` and `blast_radius/graph/visualizer.py`.

---

## 1. Architectural Analysis & Diagnostic Answers

### Q2: Why are there so few connections between layers?
**Root Cause:**
1. **Siloed Ingestion (Phases 1-3):**
   - **PRD (Phase 2):** Nodes created from Markdown titles/sections (`Requirement` / `GapNode`).
   - **UI (Phase 1):** Nodes created from Playwright DOM crawl (`Page` / `UIElement`).
   - **Code (Phase 3):** Nodes created from AST static analysis (`CodeFunction`).
2. **Strict Entity Resolution Thresholds (Phase 4 - `blast_radius/graph/resolve.py`):**
   - Cross-layer edges (`EXECUTES`, `RENDERS`, `IMPLEMENTS`) depend on string matching or embedding vector similarity between disjoint vocabularies (e.g. PRD heading *"User Invites"* vs UI route `"/settings/members"` vs TypeScript function `inviteMemberHandler()`).
   - High similarity cutoff thresholds (e.g. cosine sim > 0.85) discard potential cross-layer candidate links.

**Remediation Strategy:**
- Implement **hybrid multi-stage entity resolution**:
  - **Rule-based route matching:** Match Next.js API routes / page routes directly to UI page URLs.
  - **Fuzzy text + LLM reranking:** For candidate links between 0.60 and 0.85 vector similarity, use `call_llm_json` in Phase 4 to verify semantic mapping.
  - **Export graph visualization metrics:** Show inter-layer link counts in the UI header to highlight coverage.

---

### Q3: Why is the Code layer overloaded while UI/PRD layers are sparse? How to balance them?
**Root Cause:**
- **AST Granularity Disparity:** Static analysis parses every export, internal helper function, React hook, and utility method in TypeScript files, resulting in hundreds/thousands of `CodeFunction` nodes.
- In contrast, PRD documents contain 10–30 high-level requirements, and Playwright crawls 10–30 top-level pages.

**Remediation Strategy:**
1. **Backend Filtering (Phase 3 & Visualizer):**
   - Exclude private helper functions, internal type definitions (`.d.ts`), and standard utility wrappers from graph ingestion.
   - Retain only **entry point functions** (API endpoints, exported React page components, server action handlers).
2. **PRD & UI Decomposition:**
   - Decompose PRD sections into atomic acceptance criteria / sub-requirements.
   - Ingest granular UI interactive elements (forms, action buttons, modals) rather than just top-level page URLs.
3. **Frontend Visual Layer Balancing:**
   - Scale node physical radiuses inversely proportional to layer density (PRD/UI nodes rendered larger & glowing; Code nodes rendered smaller).
   - Add layer-level visibility toggles (`Code Layer`, `UI Layer`, `Requirement Layer`).

---

## 2. Technical Overhaul Architecture

### Decoupling Data Storage (Fixing the 82,000-line HTML file)
- `blast_radius/graph/visualizer.py` will export graph data to `data/graph_data.json`.
- `data/graph_explorer.html` will be rewritten as a clean, static, lightweight (~400 line) web interface.
- Data fetching workflow:
  ```
  Page Load -> Check IndexedDB/localStorage Cache
    ├─► Cache Valid & Fresh (<24h) ──► Render instantly from cache
    └─► Cache Missing / Expired ─────► Fetch data/graph_data.json or Neo4j API ──► Store in Cache ──► Render
  ```
- A manual **"Refresh Data from Neo4j"** button will clear local cache and re-fetch.

---

## 3. UI Features & Enhancements

### 1. Light / Dark Mode Toggle
- Floating theme switch button (top bar).
- Dynamic CSS variables + Three.js background color change (`#0b0c10` dark vs `#f8f9fa` light).
- Automatic adjustment of link stroke colors, node glow effects, and text contrast.

### 2. Right-Side Search & Explorer Sidebar
- **Search Bar:** Real-time search by node name, ID, file path, or requirement text.
- **Layer Tabs:** Filter nodes by `All`, `Requirements`, `UI Elements`, `Code Functions`, `Gaps`.
- **Node Cards List:** Displays node type badge, degree centrality, layer plane, and status.
- **Click-to-Focus:** Clicking a node in the list smoothly animates the 3D camera to frame the target node and highlights its connected neighbors in 3D space.

### 3. Demo-Ready Polish & Visualization Features
- **Semi-transparent 3D Layer Planes:** Render subtle glassmorphism planes at $Z = +200$ (Requirements), $Z = 0$ (UI), and $Z = -200$ (Code) to visually clarify the multi-layer lattice structure.
- **Blast Radius Simulator Mode:** Select any changed `CodeFunction` node, click *"Simulate Blast Radius"*, and watch visual shockwaves pulse across cross-layer links to highlight affected UI and Requirement nodes.
- **Camera Preset Views:** Quick action buttons for *"Isometric Overview"*, *"Top (Requirements)"*, *"Middle (UI)"*, *"Bottom (Code)"*.

---

## Proposed File Changes

### [blast_radius/graph/visualizer.py](file:///c:/D%20Drive/Projects/Summers%202026/Testsigma/blast_radius/graph/visualizer.py)
- Modify `generate_visualizer_html()` to export `data/graph_data.json` separately.
- Add summary metrics export (node counts per layer, link counts inter-layer).

### [data/graph_explorer.html](file:///c:/D%20Drive/Projects/Summers%202026/Testsigma/data/graph_explorer.html)
- Replace 82,000-line embedded JSON file with a clean static web app structure.
- Include 3D-force-graph library, Three.js, theme switcher, search sidebar, local caching engine, and 3D layer planes.

### [NEW] [data/graph_data.json](file:///c:/D%20Drive/Projects/Summers%202026/Testsigma/data/graph_data.json)
- Standalone exported graph dataset decoupleable from HTML code.

---

## Verification Plan

### Automated Tests
- Run `python -m blast_radius.graph.visualizer` to confirm clean generation of `data/graph_data.json` and verification of `data/graph_explorer.html`.

### Manual Verification
- Open `data/graph_explorer.html` in browser.
- Verify Light/Dark mode toggling.
- Test right sidebar search filtering and camera focusing.
- Verify dynamic local caching and refresh functionality.
