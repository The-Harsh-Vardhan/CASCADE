# Blast Radius Analyzer — Unified Reference Document

> **Purpose:** This document is a single source of truth for building the AI-Powered Blast Radius Analyzer described in the Testsigma take-home assignment. It synthesizes the assignment brief, two deep-research literature reviews (ChatGPT + Gemini), and two repository surveys (ChatGPT + Gemini) into one reference an engineer or LLM coding assistant can use throughout the project.

---

## Table of Contents

1. [Assignment Brief](#1-assignment-brief)
2. [System Architecture Overview](#2-system-architecture-overview)
3. [Component Breakdown](#3-component-breakdown)
4. [Recommended Technology Stack](#4-recommended-technology-stack)
5. [Top Repositories by Subsystem](#5-top-repositories-by-subsystem)
6. [Full Repository Reference (Top 50)](#6-full-repository-reference-top-50)
7. [Literature Review — Key Papers by Component](#7-literature-review--key-papers-by-component)
8. [Graph Schema Design](#8-graph-schema-design)
9. [Blast Radius Algorithm Design](#9-blast-radius-algorithm-design)
10. [Confidence Handling & Human-in-the-Loop](#10-confidence-handling--human-in-the-loop)
11. [Evaluation Strategy](#11-evaluation-strategy)
12. [Scope Decisions & What to Cut](#12-scope-decisions--what-to-cut)
13. [What to Build Next (Extension Roadmap)](#13-what-to-build-next-extension-roadmap)
14. [Phased Implementation Blueprint](#14-phased-implementation-blueprint)
15. [Design Document Checklist](#15-design-document-checklist)

---

## 1. Assignment Brief

### Core Task
Build an agent that does all four of the following on a **public web application** of your choice:

| # | Stage | What It Means |
|---|-------|---------------|
| 1 | **Crawl** | Browser agent explores the live app; captures DOM, screenshots, interaction transitions, screen relationships |
| 2 | **Ingest** | Parse a public PRD / README / wiki into structured form the graph can use |
| 3 | **Graph** | Neo4j knowledge graph with three layers: Requirements → DOM/UI → Code |
| 4 | **Reason** | Given a real PR, output a blast radius report: which UI elements, flows, and requirements are at risk |

### Hard Constraints
- **16 hours total** — deliberately insufficient for all four layers at equal depth
- A working narrow slice beats three half-done layers
- Explicitly document scope decisions in the design document

### Deliverables
- GitHub repo (runnable, with README)
- Design document (PDF or Markdown, 8–12 pages)
- Sample output — blast radius report for a real PR, readable by a non-engineer QA lead
- 5–10 minute Loom walkthrough

### Design Document Must Address
1. Agent decomposition — stages, boundaries, deterministic vs. LLM-driven
2. Graph schema with justification — node/edge types, cross-layer connections, modeling **absence**
3. Confidence handling under ambiguity
4. Eval approach — how to know if output is correct
5. Scope decisions — what was cut and why
6. What you'd build next (three highest-value things, in order)

---

## 2. System Architecture Overview

The system is a **neuro-symbolic pipeline** that bridges three heterogeneous artifact layers:

```
PRD / Requirements  ──────────────────────────────────────────┐
       │                                                        │
       ▼                                                        │
DOM / UI / User Flows  ─────────────────────────────────┐      │
       │                                                 │      │
       ▼                                                 │      │
Source Code / APIs / CPG  ──────────────────────────────┘      │
       │                                                        │
       ▼                                                        │
Product Knowledge Graph (Neo4j / PostgreSQL+AGE)  ◄────────────┘
       │
       ▼
Pull Request Delta  ──►  Blast Radius Agent  ──►  Explainable Report
```

### The Five Reasoning Stages (Agent Decomposition)

```
Stage 1: CRAWL          Stage 2: INGEST         Stage 3: GRAPH
──────────────          ───────────────         ──────────────
Browser agent           PRD / Docs parser       Neo4j KG with
maps live UI            (Docling)               3-layer schema
(browser-use,                                   + embeddings
 Crawl4AI)
                                                       │
Stage 5: REPORT         Stage 4: REASON                │
───────────────         ───────────────                ▼
GNNExplainer /          PR ingested via         Blast radius
ExplainVulD edge        PyDriller → HippoRAG   computed via PPR
attribution             PPR traversal           seed-node routing
→ non-engineer          → OpenHands ACI
  readable output         investigates
                          ambiguities
```

### Deterministic vs. LLM-Driven

| Component | Mode | Rationale |
|-----------|------|-----------|
| AST parsing (ast-grep, Joern) | **Deterministic** | Structural code facts must be exact |
| Git diff extraction (PyDriller) | **Deterministic** | Source of truth is the VCS |
| Graph traversal (PPR, DFS) | **Deterministic** | Math-based impact routing |
| PRD → entity extraction | **LLM-driven** | Natural language needs semantic understanding |
| UI → DOM semantic labeling | **LLM-driven** | Visual + textual meaning exceeds rule-based parsing |
| Entity resolution (PRD ↔ Code) | **LLM-driven + statistical** | Cross-vocabulary mapping; Splink for scoring |
| Blast radius explanation | **LLM-driven** | Human-readable synthesis |
| Ambiguity investigation | **LLM-driven (ACI)** | OpenHands agent investigates low-confidence edges |

---

## 3. Component Breakdown

### 3.1 Autonomous Web Crawler (UI Layer)

**Goal:** Explore the live application and capture structured artifacts — DOM trees, screenshots, interaction transitions, inter-page relationships.

**Strategy:**
- Use **Crawl4AI** for fast, static-page crawling → outputs noise-free Markdown + semantic clusters
- Use **browser-use** for dynamic SPAs and authenticated flows → accessibility tree extraction, stateful multi-step flows
- Translate DOM → Accessibility Tree (AXTree) following the **WebArena** methodology, making DOM token-efficient for LLMs
- Capture: page URL, AXTree, screenshot, outbound links, form fields, button labels, semantic role labels

**Output nodes for graph:**
- `Page` nodes (URL, title, screenshot path)
- `UIComponent` nodes (type, label, selector, bounding box)
- `UserFlow` edges between Pages (action → transition)

**Key limitation to acknowledge in design doc:** Dynamic JavaScript state changes won't be fully captured by static crawling; browser-use handles this but adds latency.

---

### 3.2 Documentation / PRD Ingestion

**Goal:** Parse a public PRD, README, GitHub Wiki, or feature spec into structured entities the graph can link.

**Strategy:**
- Use **Docling** as the universal parser — handles PDF, Word, Markdown, HTML, tables, images (via VLM OCR)
- Docling's `ProvenanceItem` schema records exact page/bbox/character-span origin of every extracted fact — critical for citing evidence in the blast radius report
- Use **UserTrace** (zero-shot LLM pipeline) to extract user stories and map them to downstream artifacts
- Use **T-SimCSE** contrastive learning with specificity reward to distinguish overlapping requirement descriptions

**Output nodes for graph:**
- `Requirement` nodes (ID, text, source document, provenance bbox)
- `Feature` nodes (higher-level groupings)
- `UserStory` nodes (actor, action, outcome)

**Modeling Absence:** A `Requirement` node that has no outbound `COVERED_BY` edge to any `UIComponent` or `CodeFunction` is flagged as `coverage_status: MISSING`. This is a first-class schema concern, not an afterthought.

---

### 3.3 Code Repository Analysis

**Goal:** Index the public repository linked to the application; build a structural map the graph can traverse.

**Strategy:**
- **PyDriller** — ingests the PR diff, extracts changed files, added/removed lines, commit metadata (lazy-loading, topological sort)
- **ast-grep** — multi-threaded Tree-sitter-based structural AST search; YAML rules identify function declarations, API endpoints, DB queries; MCP server allows the LLM agent to query the AST dynamically
- **Joern** (reference/optional) — full Code Property Graph (CPG = AST + CFG + PDG) for deep data-flow tracking; high overhead, use for reference schema design only
- **GraphCodeBERT / DeepSeek-Coder** — converts CPG nodes to dense embeddings that encode data-flow structure (not just token text)
- **CodeTIDAL5** — type inference for dynamically typed JS/TS frontend code via CPG slicing, maintaining chain of evidence from backend to DOM

**Output nodes for graph:**
- `CodeFile` nodes
- `Function` / `Method` nodes (name, signature, file, line range)
- `APIEndpoint` nodes (HTTP method, route, handler function)
- `DBQuery` nodes
- `CPGEdge` edges (CALLS, DATA_FLOWS_TO, CONTROLS)

---

### 3.4 Knowledge Graph Construction

**Goal:** Fuse the three artifact layers into a unified, queryable Neo4j knowledge graph.

**Technology choice: LightRAG (primary) + Microsoft GraphRAG (baseline)**

| Concern | LightRAG | GraphRAG (Microsoft) |
|---------|----------|----------------------|
| Indexing speed | Fast (incremental) | Slow (full rebuild) |
| CI/CD suitability | ✅ Real-time PR updates | ❌ Too slow for PR hooks |
| Global summarization | Good | Excellent (Leiden communities) |
| Backend | PostgreSQL (pgvector + Apache AGE), Neo4j | Python/NetworkX |
| Cost | Low | High (many LLM calls) |

**Entity Resolution (cross-layer linking):**
- **Splink** — probabilistic Fellegi-Sunter linkage between PRD feature names and code entity names; works without labeled training data; DuckDB backend for fast local runs
- **DeepMatcher / cross-encoder LLMs** — sequence-pair classification for fuzzy name matching across vocabulary boundaries ("User Authentication" ↔ `auth_controller.ts`)
- **T-SimCSE specificity reward** — ranks candidate matches by uniqueness, reducing false positives from overlapping terminology

**Incremental updates:** When a PR is merged, LightRAG's set-merging deduplication updates only affected subgraph nodes — no full rebuild.

---

### 3.5 Blast Radius Reasoning

**Goal:** Given a PR diff, compute which UI elements, user flows, and requirements are at risk.

**Algorithm:**

1. **Seed node identification:** PyDriller extracts changed functions/files → these become seed nodes in the KG
2. **Impact propagation:** HippoRAG's **Personalized PageRank (PPR)** routes activation energy from seed nodes outward through:
   - `CALLS` edges (code → code)
   - `RENDERS` edges (code → UIComponent)
   - `COVERS` edges (UIComponent → Requirement)
3. **PPR score → Confidence score:** Higher activation = higher confidence of impact
4. **DFS transitive closure** (Ekstazi-inspired): For any seed node, compute all transitively reachable nodes via DFS across CPG edges
5. **Ambiguity handling:** Nodes below confidence threshold → escalate to OpenHands ACI agent for dynamic investigation

**Agent-Computer Interface (ACI) for ambiguity:**
- Inspired by **SWE-agent's** constrained terminal toolset
- Agent has tools: `query_graph(cypher)`, `search_ast(yaml_rule)`, `read_file(path, lines)`, `fetch_ui_element(selector)`
- Agent iterates: investigate → update confidence → decide (report or escalate to human)

---

### 3.6 Explainable Report Generation

**Goal:** Produce a blast radius report readable by a non-engineer QA lead.

**Structure of output report:**

```
## Blast Radius Report — PR #<number>: <title>

### Summary
<2–3 sentence plain-English impact summary>

### High-Confidence Impacts (score > 0.7)
- UIComponent: [Checkout Button] → UserFlow: [Add to Cart → Checkout]
  - Evidence: cart_controller.py:handleSubmit() → calls payment_api.charge()
  - Requirement covered: REQ-42 "Users can complete purchase in under 3 clicks"
  - PRD Source: Page 7, §3.2 of product_spec.pdf

### Medium-Confidence Impacts (0.4–0.7)
...

### Requirements Losing Coverage
- REQ-17 "Cart state persists across sessions" — no UI test currently covers this

### Missing Coverage (Absence)
- REQ-23 "Guest checkout flow" — no UIComponent or CodeFunction linked in graph

### Recommended Test Areas
1. ...
2. ...
```

**Explainability mechanism:**
- **GNNExplainer** mutual information masking → isolates the minimal subgraph causing the prediction
- **ExplainVulD** edge-aware attention + gradient attribution → highlights exact CPG path (Function → API → DOM element)
- Provenance from Docling's `ProvenanceItem` → every requirement citation links back to exact page/line in the PRD

---

## 4. Recommended Technology Stack

### Primary Stack (Build With These)

| Layer | Technology | Why |
|-------|-----------|-----|
| Web crawling (static) | **Crawl4AI** | Fast, async, LLM-friendly Markdown output |
| Web crawling (dynamic) | **browser-use** | Playwright-based, accessibility tree, auth flows |
| Doc parsing | **Docling** | Universal format support, provenance tracking |
| Git/PR ingestion | **PyDriller** | Industry standard, lazy-load, topological sort |
| AST/code search | **ast-grep** | Rust-fast, Tree-sitter, MCP server for agent use |
| Knowledge graph | **Neo4j** or **PostgreSQL + pgvector + Apache AGE** | Graph storage + vector search in one backend |
| Graph RAG | **LightRAG** | Incremental updates, dual-layer retrieval |
| Entity resolution | **Splink** | Probabilistic, no labeled data needed |
| PR analysis | **qodo-ai/pr-agent** | Diff compression, GitHub webhook integration |
| Agentic reasoning | **OpenHands** (ACI) | Sandboxed, multi-agent, 100+ LLM support |
| LLM gateway | **LiteLLM** | Switch between Claude/GPT/Ollama without code changes |
| Code embeddings | **GraphCodeBERT** or **DeepSeek-Coder** | Data-flow aware, not just token-based |
| Report UI | **lobehub/lobe-chat** or custom Markdown | Readable by non-engineers |

### Secondary / Reference (Study But Don't Depend On)

| Technology | Role |
|-----------|------|
| **Joern** | Reference CPG schema design; too heavy for primary use |
| **Microsoft GraphRAG** | Initial baseline KG construction; too slow for real-time |
| **Skyvern** | Vision-based UI analysis inspiration; AGPL license risk |
| **SWE-agent** | Reference for ACI terminal formatting and context management |
| **Semgrep** | Pattern-based code scanning as supplement to ast-grep |
| **GNNExplainer** | Explainability mechanism for report evidence |
| **HippoRAG** | PPR algorithm for confidence scoring |

---

## 5. Top Repositories by Subsystem

### Crawler & UI Engine
| Repository | Stars | Role |
|-----------|-------|------|
| [unclecode/crawl4ai](https://github.com/unclecode/crawl4ai) | ~74k | Primary static crawler |
| [browser-use/browser-use](https://github.com/browser-use/browser-use) | ~105k | Dynamic/authenticated UI crawling |
| [skyvern-ai/skyvern](https://github.com/skyvern-ai/skyvern) | ~22k | Vision-based reference; AGPL |
| [lavague-ai/LaVague](https://github.com/lavague-ai/LaVague) | ~5k | BDD→DOM compilation pattern |
| [steel-dev/steel-browser](https://github.com/steel-dev/steel-browser) | ~7k | Headless browser API alternative |
| [browserbase/stagehand](https://github.com/browserbase/stagehand) | ~24k | TypeScript browser agent SDK |

### Documentation Parsing
| Repository | Stars | Role |
|-----------|-------|------|
| [docling-project/docling](https://github.com/docling-project/docling) | ~64k | Primary doc parser (PDF/Word/MD) |
| [neo4j-labs/llm-graph-builder](https://github.com/neo4j-labs/llm-graph-builder) | ~5k | LLM → Neo4j extraction pipeline |
| [Rahulnyk/knowledge_graph](https://github.com/Rahulnyk/knowledge_graph) | ~3k | Text → KG pattern reference |

### Code Analysis
| Repository | Stars | Role |
|-----------|-------|------|
| [ast-grep/ast-grep](https://github.com/ast-grep/ast-grep) | ~15k | Primary AST search (Rust, Tree-sitter) |
| [joernio/joern](https://github.com/joernio/joern) | ~3k | CPG reference implementation (Scala, JVM) |
| [semgrep/semgrep](https://github.com/semgrep/semgrep) | ~16k | Pattern-based static analysis |
| [ishepard/pydriller](https://github.com/ishepard/pydriller) | ~1k | Git/PR diff extraction |
| [crytic/slither](https://github.com/crytic/slither) | ~6k | Reference for AST intermediate representation design |

### Knowledge Graph & Retrieval
| Repository | Stars | Role |
|-----------|-------|------|
| [HKUDS/LightRAG](https://github.com/HKUDS/LightRAG) | ~5k | Primary graph RAG (incremental, fast) |
| [microsoft/graphrag](https://github.com/microsoft/graphrag) | ~35k | Leiden community detection; baseline KG |
| [OSU-NLP-Group/HippoRAG](https://github.com/OSU-NLP-Group/HippoRAG) | ~2k | PPR-based confidence scoring |
| [moj-analytical-services/splink](https://github.com/moj-analytical-services/splink) | ~5k | Probabilistic entity resolution |

### PR Analysis & Agentic Reasoning
| Repository | Stars | Role |
|-----------|-------|------|
| [All-Hands-AI/OpenHands](https://github.com/All-Hands-AI/OpenHands) | ~75k | Primary ACI agent framework |
| [qodo-ai/pr-agent](https://github.com/qodo-ai/pr-agent) | ~12k | PR ingestion, diff compression, GitHub hooks |
| [princeton-nlp/SWE-agent](https://github.com/princeton-nlp/SWE-agent) | ~15k | ACI pattern reference |
| [Aider-AI/aider](https://github.com/Aider-AI/aider) | ~48k | Git-native code assistant; codebase indexing |

---

## 6. Full Repository Reference (Top 50)

Consolidated and deduplicated from both research sources. Ranked by direct utility to the Blast Radius Analyzer.

| Rank | Repository | Domain | Decision | Key Utility |
|------|-----------|--------|----------|-------------|
| 1 | microsoft/graphrag | Knowledge Fusion | Adopt (baseline) | Leiden community detection; global summarization |
| 2 | joernio/joern | Code Analysis | Reference only | CPG schema design; AST+CFG+PDG unification |
| 3 | docling-project/docling | Doc Parsing | **Direct dependency** | Universal format parser with provenance tracking |
| 4 | ast-grep/ast-grep | Static Analysis | **Direct dependency** | Rust Tree-sitter AST search + MCP server |
| 5 | unclecode/crawl4ai | Web Crawling | **Direct dependency** | Async, LLM-friendly, noise-reduced Markdown |
| 6 | HKUDS/LightRAG | Graph Retrieval | **Direct dependency** | Incremental KG updates; dual-layer retrieval |
| 7 | browser-use/browser-use | UI Understanding | **Direct dependency** | Dynamic DOM + authenticated flow crawling |
| 8 | qodo-ai/pr-agent | PR Analysis | Reference + adapt | PR diff compression; GitHub webhook pattern |
| 9 | All-Hands-AI/OpenHands | AI Agents | **Direct dependency** | Sandboxed ACI; multi-agent delegation |
| 10 | moj-analytical-services/splink | Entity Resolution | **Direct dependency** | Probabilistic Fellegi-Sunter linkage |
| 11 | skyvern-ai/skyvern | UI Understanding | Inspiration only | Vision-based UI reasoning; AGPL — don't vendor |
| 12 | princeton-nlp/SWE-agent | AI Agents | Reference | ACI terminal formatting; context management patterns |
| 13 | lavague-ai/LaVague | Web Agents | Reference | BDD→DOM compilation; PRD→UI navigation concept |
| 14 | crytic/slither | Static Analysis | Reference | SlithIR intermediate representation design |
| 15 | langchain-ai/langchain | LLM Framework | Utility | RAG orchestration; Neo4j integration |
| 16 | run-llama/llama_index | Knowledge Integration | Utility | Structured/unstructured data bridging |
| 17 | BerriAI/litellm | AI Gateway | **Direct dependency** | Provider-agnostic LLM routing |
| 18 | Aider-AI/aider | AI Agents | Reference | Codebase indexing; TreeSitter context management |
| 19 | langgenius/dify | App Framework | Optional | Visual workflow orchestration for demos |
| 20 | ishepard/pydriller | Repository Mining | **Direct dependency** | Git diff extraction; commit history traversal |
| 21 | infiniflow/ragflow | RAG Engine | Optional | Deep document chunking strategies |
| 22 | deepset-ai/haystack | RAG Framework | Optional | Advanced retrieval pipeline orchestration |
| 23 | nomic-ai/gpt4all | Local LLMs | Optional | Local model for sensitive repo data |
| 24 | OSU-NLP-Group/HippoRAG | Graph Retrieval | **Adapt** | PPR confidence scoring algorithm |
| 25 | RexYing/gnn-model-explainer | Explainable AI | **Adapt** | GNNExplainer subgraph isolation for evidence |
| 26 | microsoft/CodeBERT | Code Embeddings | **Adopt** | GraphCodeBERT: data-flow aware code embeddings |
| 27 | web-arena-x/webarena | Web Crawling | Reference | AXTree DOM linearization methodology |
| 28 | swe-bench/SWE-bench | Evaluation | **Adopt (eval)** | Execution-based benchmark for impact prediction |
| 29 | AutoCodeRoverSG/auto-code-rover | AI Agents | **Adapt** | AST-aware program structure search APIs |
| 30 | browserbase/stagehand | Web Agents | Alternative | TypeScript Playwright agent SDK |
| 31 | SWEbench-related repos | Evaluation | Reference | Realistic software engineering task suite |
| 32 | steel-dev/steel-browser | Web Crawling | Alternative | Headless browser HTTP/WS API |
| 33 | SYSUSELab/RepoDoc | KG + Docs | **Adopt concepts** | RepoKG + incremental documentation from code |
| 34 | neo4j-labs/llm-graph-builder | KG Construction | Adopt | LLM → Neo4j extraction backend |
| 35 | Rahulnyk/knowledge_graph | KG Patterns | Reference | LLM → KG triple extraction pattern |
| 36 | anhaidgroup/deepmatcher | Entity Resolution | Reference | Sequence-pair classification framing |
| 37 | imamnurby/Transducer-Tuning | Knowledge Fusion | **Adopt** | GVE + ABFL: fuse CPG structure with LLM embeddings |
| 38 | OpenHands/software-agent-sdk | Agent SDK | Utility | Agent tool management framework |
| 39 | Bevel-Software/code-to-knowledge-graph | Code → KG | Reference | AST → graph extraction (JVM only) |
| 40 | SWE-agent/SWE-agent | AI Agents | Reference | Agentic issue resolution methodology |
| 41 | logspace-ai/langflow | Pipeline Builder | Optional | Visual graph for pipeline demos |
| 42 | Agenta-AI/agenta | LLMOps | Optional | Prompt management and evals for agents |
| 43 | Mintplex-Labs/anything-llm | Knowledge App | Optional | Desktop RAG + agent builder |
| 44 | pathwaycom/llm-app | Data Pipelines | Optional | Real-time sync with GitHub/Jira data |
| 45 | labring/FastGPT | KG App | Optional | Q&A platform over KG |
| 46 | chatchat-space/Langchain-Chatchat | Local RAG | Optional | Offline RAG for sensitive codebases |
| 47 | ForethoughtTech/AutoChain | Agent Orchestration | Reference | Lightweight agent testing framework |
| 48 | BoundaryML/baml | Prompt Engineering | Optional | Strongly typed LLM output → backend logic |
| 49 | 2dogsandanerd/ClawRag | Vector Integration | Optional | Docling + ChromaDB pipeline |
| 50 | lobehub/lobe-chat | Report UI | Optional | Chat interface for blast radius report delivery |

---

## 7. Literature Review — Key Papers by Component

### 7.1 Core Foundational Papers (Must Read)

| Paper | Year | Key Contribution | Decision |
|-------|------|-----------------|----------|
| Yamaguchi et al. — *Code Property Graphs* | 2014 | Unifies AST+CFG+PDG into a queryable graph; foundational for implementation layer | **Adopt** |
| Edge et al. (Microsoft) — *GraphRAG* | 2024 | Leiden community detection + map-reduce LLM generation for global KG summarization | **Adopt** |
| Guo et al. — *LightRAG* | 2024 | Incremental graph updates + dual-layer (vector+graph) retrieval; CI/CD viable | **Adopt** |
| Gutierrez et al. — *HippoRAG* | 2024 | PPR neurobiological memory model → confidence score routing | **Adapt** |
| Lewis et al. — *RAG* | 2020 | Dense retrieval + seq2seq generation; conceptual foundation | **Adapt** |

### 7.2 Code Analysis Papers

| Paper | Year | Key Contribution | Decision |
|-------|------|-----------------|----------|
| Guo et al. — *GraphCodeBERT* | 2021 | Data-flow graph guided masked attention; structurally aware code embeddings | **Adopt** |
| Imam et al. — *Transducer Tuning* | 2024 | GVE+ABFL: inject CPG structure into LLM embeddings without full fine-tuning | **Adopt** |
| CodeTIDAL5 — *Type inference for JS via CPG* | 2023 | Infers types in dynamic frontend languages; maintains backend→DOM chain of evidence | **Adopt** |
| Saimbhi — *CPG + CNN for vulnerability detection* | 2025 | Graph-based code vulnerability detection; inspires CPG node classification | **Consider** |
| ExplainVulD — *Edge-aware attention on CPGs* | 2025 | Gradient attribution on CPG edges; generates causal path evidence for reports | **Adopt** |
| Salih & Sarhan — *LLMs for static code analysis* (survey) | 2025 | Survey of LLM applications in static analysis; identifies interpretability wins | **Read** |

### 7.3 Requirements Traceability Papers

| Paper | Year | Key Contribution | Decision |
|-------|------|-----------------|----------|
| Wang et al. — *RC-TLR benchmark* | 2024 | Empirical comparison of 6 traceability methods; RandomForest + TAROT work best | **Read** |
| UserTrace — *Zero-shot traceability* | 2025 | LLM-as-judge zero-shot pipeline for PRD→code link generation | **Adapt** |
| T-SimCSE — *Contrastive learning for traceability* | 2026 | Specificity reward mechanism; unsupervised semantic link scoring | **Adapt** |
| ReqToCode — *Compile-time traceability* | 2026 | Embeds traceability as compile-time constants; great concept, impractical for us | **Ignore** |

### 7.4 Change Impact Analysis Papers

| Paper | Year | Key Contribution | Decision |
|-------|------|-----------------|----------|
| Kretsou et al. — *CIA systematic mapping study* | 2021 | Enumerates CIA metrics: instability, change-proneness, changeability | **Read** |
| Gligoric et al. — *Ekstazi: Lightweight Test Selection* | 2015 | DFS transitive dependency mapping; adapt for static PKG traversal | **Adapt** |
| Abdurhman & Lee — *FCP2Vec* | 2023 | Skip-gram embeddings on commit logs → co-change prediction; +21% recall | **Adapt** |
| Plyusnin et al. — *T-TS: Targeted Test Selection* | 2025 | ML-based test selection; 15% of tests, 95% failure detection | **Adapt** |
| Xu et al. — *RepoDoc* | 2026 | RepoKG + semantic impact propagation + incremental LLM doc generation | **Adopt concepts** |

### 7.5 GUI / DOM Understanding Papers

| Paper | Year | Key Contribution | Decision |
|-------|------|-----------------|----------|
| Wang et al. — *Screen2Vec* | 2021 | Multi-modal autoencoder (CNN+Transformer) for GUI semantic embeddings | **Adopt** |
| Zhou et al. — *WebArena* | 2024 | DOM linearization → AXTree; realistic dynamic web evaluation environment | **Adapt** |
| Tang et al. — *Survey on LLM GUI Agents* | 2025 | Taxonomy: Perception, Exploration, Planning, Interaction | **Read** |

### 7.6 AI Agents for Software Engineering

| Paper | Year | Key Contribution | Decision |
|-------|------|-----------------|----------|
| Yang et al. — *SWE-agent* | 2024 | Agent-Computer Interface (ACI) with constrained terminal commands | **Adapt** |
| Zhang et al. — *AutoCodeRover* | 2024 | AST-aware program structure APIs; spectrum-based fault localization | **Adapt** |
| Jimenez et al. — *SWE-bench* | 2024 | Execution-based benchmark on real GitHub issues; use for system evaluation | **Adopt (eval)** |
| Aleti et al. — *Trustworthy AI SE* | 2026 | Trustworthiness dimensions (transparency, epistemic humility, ethics) for AI agents | **Read** |

### 7.7 Explainability & Human-in-the-Loop

| Paper | Year | Key Contribution | Decision |
|-------|------|-----------------|----------|
| Ying et al. — *GNNExplainer* | 2019 | Mutual information masking to isolate explanatory subgraphs | **Adopt** |
| Arora et al. — *XAI in SE survey* | 2025 | Maps LIME/SHAP/counterfactuals to SDLC phases; most XAI in maintenance | **Read** |
| Wu et al. — *HITL for ML survey* | 2022 | Categorizes HITL into data/model/system layers; active learning | **Consider** |

### 7.8 Knowledge Graph Construction

| Paper | Year | Key Contribution | Decision |
|-------|------|-----------------|----------|
| Zou et al. — *SW Knowledge Graph Q&A* | 2021 | Code-centric KG ontology; two-layer plugin framework; deployed in Apache projects | **Adopt** |
| Wang et al. — *KG in SE survey* | 2023 | SLR of 100+ papers on KGs in SE; taxonomy and best practices | **Read** |
| Peshevski et al. — *AI agents for product KG* | 2025 | Three-agent LLM pipeline for autonomous KG population; 97% property coverage | **Consider** |
| Han et al. — *GraphRAG survey* | 2025 | Conceptual GraphRAG framework: retriever → organizer → generator | **Read** |
| Romero-Arjona et al. — *LLMs in MSR survey* | 2026 | Taxonomy of LLM applications in repository mining (85 papers) | **Read** |

### 7.9 Entity Resolution & Knowledge Fusion

| Paper | Year | Key Contribution | Decision |
|-------|------|-----------------|----------|
| Mudgal et al. — *DeepMatcher* | 2018 | Sequence-pair classification with RNNs for entity matching across noisy data | **Adapt** (upgrade to cross-encoder Transformer) |
| Spadini et al. — *PyDriller* | 2018 | Lazy-loading Git API with topological sort; industry standard | **Adopt** |

---

## 8. Graph Schema Design

### 8.1 Node Types

```cypher
// Requirements Layer
(:Requirement {id, text, source_doc, page, bbox, coverage_status})
(:Feature {id, name, description})
(:UserStory {id, actor, action, outcome})

// UI/DOM Layer
(:Page {url, title, screenshot_path})
(:UIComponent {selector, label, type, bounding_box, page_url})
(:UserFlow {id, description, start_page, end_page})

// Code Layer
(:CodeFile {path, language, repo, last_modified})
(:Function {name, signature, file_path, line_start, line_end})
(:APIEndpoint {method, route, handler_function, file_path})
(:DBQuery {type, table, file_path})
(:PRDiff {pr_number, title, author, changed_files})
```

### 8.2 Edge Types

```cypher
// Requirements → UI
(:Requirement)-[:COVERED_BY]->(:UIComponent)
(:Requirement)-[:TESTED_VIA]->(:UserFlow)
(:Feature)-[:CONTAINS]->(:Requirement)

// UI → Code
(:UIComponent)-[:RENDERED_BY]->(:Function)
(:UIComponent)-[:CALLS_API]->(:APIEndpoint)
(:Page)-[:NAVIGATES_TO {action}]->(:Page)
(:UserFlow)-[:INCLUDES]->(:UIComponent)

// Code → Code (CPG edges)
(:Function)-[:CALLS]->(:Function)
(:Function)-[:DATA_FLOWS_TO]->(:Function)
(:Function)-[:CONTROLS]->(:Function)
(:APIEndpoint)-[:HANDLED_BY]->(:Function)
(:Function)-[:QUERIES]->(:DBQuery)

// PR Delta
(:PRDiff)-[:MODIFIES]->(:CodeFile)
(:PRDiff)-[:MODIFIES]->(:Function)
```

### 8.3 Modeling Absence (Critical Design Requirement)

Absence is not the lack of a node — it is a **first-class property** on existing nodes:

```cypher
// A requirement with no UI coverage
(:Requirement {coverage_status: "MISSING"})
  // No outbound COVERED_BY edge exists

// Query to find uncovered requirements
MATCH (r:Requirement)
WHERE NOT (r)-[:COVERED_BY]->(:UIComponent)
SET r.coverage_status = "MISSING"
RETURN r

// A UIComponent with no linked code
(:UIComponent {traceability_status: "ORPHANED"})
  // No inbound RENDERED_BY edge from any Function

// A Function changed in PR with no UI path
(:Function {blast_exposure: "UNKNOWN"})
  // Changed in PR but no outbound path to any UIComponent
```

This models the three types of absence:
1. **Requirement absence** — requirement exists in PRD but no UI/code covers it
2. **UI orphan** — UI component exists but no code function renders it (dead UI)
3. **Dark change** — code changed in PR but no traceable path to any UI or requirement (highest risk)

### 8.4 Query Examples

```cypher
-- 1. Blast radius of a PR: all UI affected transitively
MATCH (pr:PRDiff {pr_number: 42})-[:MODIFIES]->(f:Function)
CALL apoc.path.subgraphAll(f, {
  relationshipFilter: "CALLS>|DATA_FLOWS_TO>|RENDERED_BY>|CALLS_API>",
  maxLevel: 6
}) YIELD nodes, relationships
RETURN nodes, relationships

-- 2. Requirements losing coverage due to this PR
MATCH (pr:PRDiff {pr_number: 42})-[:MODIFIES]->(f:Function)
<-[:RENDERED_BY]-(ui:UIComponent)
<-[:COVERED_BY]-(r:Requirement)
RETURN r.id, r.text, ui.label

-- 3. Dark changes (code changed, no UI path)
MATCH (pr:PRDiff {pr_number: 42})-[:MODIFIES]->(f:Function)
WHERE NOT (f)-[:RENDERED_BY|CALLS_API*1..5]->(:UIComponent)
RETURN f.name, f.file_path AS "Untraced change"

-- 4. All missing requirements
MATCH (r:Requirement)
WHERE NOT (r)-[:COVERED_BY]->(:UIComponent)
  AND NOT (r)-[:TESTED_VIA]->(:UserFlow)
RETURN r.id, r.text, r.source_doc
```

---

## 9. Blast Radius Algorithm Design

### 9.1 Step-by-Step

```
Input: PR diff (list of changed files/functions)

Step 1 — Seed Node Extraction
  PyDriller.get_modified_files(pr) → [file1, func1, func2, ...]
  Query KG: MATCH (f:Function) WHERE f.name IN changed_functions

Step 2 — Forward Impact Propagation (Deterministic)
  DFS from each seed node following:
  CALLS → DATA_FLOWS_TO → RENDERED_BY → CALLS_API → COVERS
  Collect all reachable nodes with hop distance

Step 3 — PPR Confidence Scoring (HippoRAG algorithm)
  For each seed node s:
    Initialize PPR vector: p[s] = 1.0, p[all others] = 0.0
    Iterate: p_new[v] = α * Σ(p[u]/degree(u)) + (1-α) * personalization[v]
    Converge at iteration ≤ 20
  Confidence(node) = PPR score after convergence

Step 4 — Threshold Classification
  > 0.7  → HIGH confidence impact
  0.4–0.7 → MEDIUM confidence
  < 0.4  → LOW confidence / investigate
  No path found → DARK CHANGE (flag separately)

Step 5 — Ambiguity Resolution (LLM Agent)
  For MEDIUM confidence nodes:
    OpenHands ACI agent invoked with:
      - The subgraph around the ambiguous node
      - The PR diff context
      - Tools: query_graph(), search_ast(), read_file()
    Agent returns: CONFIRMED | DISMISSED | NEEDS_HUMAN

Step 6 — Report Assembly
  Group findings by confidence tier
  Attach provenance (PRD page, bbox, code line)
  Identify absent requirements (coverage_status = MISSING)
  Generate natural language summary via LLM
```

### 9.2 Handling Edge Cases

| Situation | Handling |
|-----------|----------|
| PR changes a utility function called everywhere | Cap DFS at depth 6; report "broad impact — high risk" |
| PRD feature with zero UI/code nodes | Flag as `MISSING` in report; list as untestable |
| UI component with no code ancestor | Flag as `ORPHANED`; note it's dead/legacy UI |
| Changed function not in KG | Add ephemeral node; set blast_exposure = `UNKNOWN` |
| Conflicting traceability signals | Show both; report lower confidence score |
| LLM agent cannot resolve ambiguity | Escalate to human with rationale and evidence trail |

---

## 10. Confidence Handling & Human-in-the-Loop

### Confidence Representation

Every node in the blast radius output carries:

```json
{
  "node_id": "UIComponent::checkout_button",
  "impact_confidence": 0.82,
  "confidence_method": "PPR",
  "hop_distance_from_seed": 3,
  "evidence_path": [
    "cart_controller.py:handleSubmit()",
    "payment_api.py:charge()",
    "checkout.html:#submit-btn"
  ],
  "traceability_link_quality": "HIGH",
  "human_review_required": false
}
```

### When the System Stops and Asks a Human

Three escalation triggers:

1. **Confidence < 0.4 AND node is a Requirement** — potential regression in a stated product promise; always surface to human
2. **`DARK CHANGE`** — code modified in PR with no traceable path to any UI or requirement; could be a hidden risk or dead code — human decides
3. **Agent conflict** — LLM ACI agent investigation returns contradictory signals (both CONFIRMED and DISMISSED from different reasoning paths)

Human interface: a Markdown comment posted to the PR by pr-agent, flagged with `[NEEDS HUMAN REVIEW]` and a structured rationale block.

---

## 11. Evaluation Strategy

### 11.1 Correctness — Single Run

| Metric | Method |
|--------|--------|
| Precision | Of reported impacts, % that are real (verified by manually running affected tests) |
| Recall | Of real impacts, % caught by the system |
| Absence recall | Of genuinely uncovered requirements, % flagged as MISSING |
| Explanation quality | Human evaluator rates evidence trace (1–5) on clarity and accuracy |

### 11.2 Stability — 100 Runs

```
For the same PR input:
- KG state is snapshotted and reused (deterministic graph)
- PPR is deterministic given fixed edge weights
- Only LLM calls introduce variance

Measure:
- Report output variance (same PR, 3 LLM calls): measure Jaccard similarity of impact sets
- Confidence score variance: ±0.05 is acceptable; >0.15 is a reliability failure
- ACI agent path variance: log full agent trajectory; flag if agent takes contradictory paths
```

### 11.3 Benchmark Against SWE-bench

Use SWE-bench PRs as the gold standard:
1. Ingest SWE-bench PR
2. Generate blast radius (which functions, files predicted as impacted)
3. Check: do the SWE-bench failing tests cover exactly the predicted blast radius?
4. Compute F1 over test predictions

### 11.4 Ablation Studies

| Ablation | What It Tests |
|----------|--------------|
| Remove entity resolution (Splink) | Does PRD→code linking degrade? |
| Remove PPR, use BFS only | Do confidence scores become less calibrated? |
| Remove Docling provenance | Does report evidence quality drop? |
| Remove ACI agent | How many ambiguities go unresolved? |

---

## 12. Scope Decisions & What to Cut

### Recommended 16-Hour Allocation

| Stage | Recommended Depth | Time |
|-------|-----------------|------|
| **Crawl** | Moderate — Crawl4AI static + browser-use for 2–3 key flows | 3 hrs |
| **Ingest** | Deep — Docling + LLM entity extraction for 1 real PRD | 2 hrs |
| **Graph** | **Deep** — Neo4j schema, 3 layers, absence modeling, seeding data | 5 hrs |
| **Reason** | **Deep** — PyDriller + PPR + report generation for 1 real PR | 4 hrs |
| Buffer / docs | — | 2 hrs |

### What to Explicitly Cut (and say so in the design doc)

| Cut | Why It's Defensible |
|-----|-------------------|
| Full CPG via Joern | JVM overhead kills 16-hour timeline; ast-grep covers structural needs |
| Multi-repo analysis | Single repo is sufficient to demonstrate the concept |
| Entity resolution via Splink | Complex setup; can approximate with LLM fuzzy matching for prototype |
| GNNExplainer training | Pre-trained explainability sufficient; training is overkill for prototype |
| Vision-based UI (Skyvern) | AGPL license + inference latency; AXTree approach via browser-use sufficient |
| Real-time CI/CD hook | Demonstrate offline; note architecture supports real-time via pr-agent webhook |
| Multi-language support | Target one language (Python or JS) to keep CPG depth high |

### What Must NOT Be Cut

- Modeling absence in the graph schema (it's explicitly asked for)
- A working blast radius report for a real PR (it's the deliverable)
- Honest scope discussion in the design document
- The three-layer graph structure (it's the core requirement)

---

## 13. What to Build Next (Extension Roadmap)

Ordered by value:

### Priority 1: Full Code Property Graph via Joern
**Why first:** Currently ast-grep provides structural search but not full CPG (no data-flow, taint tracking). CPG is the lossless foundation. With CPG: dark changes become traceable, type inference (CodeTIDAL5) works, ExplainVulD edge attribution works properly. **Estimated effort:** 1–2 weeks.

### Priority 2: Real-Time CI/CD Integration via pr-agent webhook
**Why second:** Currently the system is offline/batch. Integrating pr-agent's GitHub webhook turns this into a live PR check. The incremental graph update via LightRAG is already designed for this. Moves the tool from prototype to production tool. **Estimated effort:** 3–5 days.

### Priority 3: Trained Entity Resolution with Splink + Active Learning
**Why third:** Current fuzzy LLM matching for PRD→code linking is probabilistic but unvalidated. Splink's Fellegi-Sunter model with EM training on labeled examples from the target codebase would dramatically improve cross-layer link quality. Adding a HITL feedback loop (developer confirms/dismisses entity links) trains the model incrementally. This is the highest-ROI accuracy improvement. **Estimated effort:** 1 week.

**Bonus (4th):** Evaluation harness against SWE-bench — turns the system from a demo into a benchmarked tool with a published F1 score.

---

## 14. Phased Implementation Blueprint

### Phase 1: Data Ingestion (Day 1)

```bash
# 1. Install dependencies
pip install crawl4ai browser-use docling pydriller lightrag-hku splink

# 2. Set up Neo4j (Docker)
docker run -p 7474:7474 -p 7687:7687 neo4j:latest

# 3. Crawl the target app
from crawl4ai import AsyncWebCrawler
# → produces Markdown + metadata per page

# 4. Parse the PRD
from docling.document_converter import DocumentConverter
# → produces DoclingDocument with provenance

# 5. Index the code repo
# ast-grep: sg scan --rule rules/functions.yaml ./repo
# pydriller: repo.traverse_commits()
```

### Phase 2: Graph Construction (Day 1–2)

```python
# Schema setup in Neo4j
# Create constraints, indexes on :Requirement(id), :Function(name+file), etc.

# Entity extraction: Docling → Requirements nodes
# Code indexing: ast-grep output → Function/APIEndpoint nodes
# UI crawl: browser-use AXTree → Page/UIComponent nodes

# Entity resolution: LLM fuzzy match (prototype) or Splink (production)
# Cross-layer edges: COVERED_BY, RENDERED_BY, CALLS

# Absence flagging:
# MATCH (r:Requirement) WHERE NOT (r)-[:COVERED_BY]->() SET r.coverage_status="MISSING"
```

### Phase 3: Blast Radius Reasoning (Day 2)

```python
# 1. Pick a real PR from the target repo
# 2. PyDriller: extract changed functions
# 3. Seed nodes: query KG for matching Function nodes
# 4. PPR traversal (HippoRAG algorithm) or simple DFS
# 5. Collect impacted nodes by confidence tier
# 6. LLM report generation with evidence paths
# 7. Output: Markdown report
```

### Phase 4: Report + Demo (Day 2)

```
1. Format report (see Section 3.6 template)
2. Verify provenance links back to PRD
3. Record Loom: show graph in Neo4j Browser, show PR, show report
4. Write design doc (use this reference document as outline)
```

---

## 15. Design Document Checklist

Use this checklist when writing the 8–12 page design document:

### Required Sections (from Assignment Brief)

- [ ] **Agent decomposition** — stages, boundaries, deterministic vs. LLM-driven decisions
- [ ] **Graph schema** — all node/edge types, cross-layer connections, how absence is modeled with a concrete Cypher query
- [ ] **Confidence handling** — PPR scores, escalation thresholds, when human review is triggered
- [ ] **Eval approach** — precision/recall definition, 100-run stability, SWE-bench connection
- [ ] **Scope decisions** — explicitly name what was cut, why, and what a full system would look like
- [ ] **What you'd build next** — three things, in order, with reasoning

### Recommended Additional Sections

- [ ] Technology choices with alternatives considered (and why not chosen)
- [ ] Graph schema justification against at least 2 specific Cypher queries
- [ ] How absence is a first-class schema concern (not a runtime check)
- [ ] Sample blast radius report (include in doc or as appendix)
- [ ] Architecture diagram (three-layer graph + pipeline)
- [ ] Limitations and failure modes

### Tone Guidance

- Write as if defending to senior engineers
- Be opinionated — don't say "we could use X or Y"; say "we use X because Y, and Y has these tradeoffs"
- Name cuts before they're discovered — proactive honesty scores higher than polished incompleteness
- Concrete evidence for claims: cite papers or repos from this document

---

## Appendix A: Research Gaps Identified

Both literature reviews converge on the same gaps — these are opportunities to differentiate:

1. **No unified semantic linker across all three layers** — most systems handle one or two artifact types; this architecture targets all three
2. **Explainable CIA is rare** — most systems return binary impact (affected/not); an evidence-backed causal path is novel
3. **Real-time incremental GraphRAG in CI/CD** — GraphRAG is too slow for PR hooks; LightRAG + PPR solves this
4. **Brittle traceability** — ReqToCode requires developer discipline; zero-shot UserTrace + T-SimCSE provides autonomous self-healing links
5. **HITL interfaces for CIA** — no existing tool lets developers validate/correct automated impact analysis in the PR review flow

---

## Appendix B: Recommended Reading Order

For a fresh start on this project, read in this sequence:

1. **Yamaguchi (2014) — CPG** — understand the code layer foundation
2. **Edge/Microsoft (2024) — GraphRAG** — understand the macro KG architecture
3. **Guo (2024) — LightRAG** — understand incremental updates (critical for CI/CD)
4. **Gutierrez (2024) — HippoRAG** — understand PPR confidence scoring
5. **Yang (2024) — SWE-agent** — understand ACI toolset design
6. **Zhang (2024) — AutoCodeRover** — understand AST-aware code search
7. **Wang (2024) — RC-TLR** — understand requirements-to-code traceability state of the art
8. **Xu (2026) — RepoDoc** — understand impact propagation via KG
9. **Ying (2019) — GNNExplainer** — understand explainability subgraph extraction
10. **Zhou (2024) — WebArena** — understand AXTree DOM linearization

---

*Document synthesized from: Assignment Brief (Testsigma), Deep Research — Literature Review (ChatGPT), Deep Research — Top Repositories (ChatGPT), Deep Research — Literature Review (Gemini), Deep Research — Repository Analysis (Gemini). Last consolidated: July 2026.*
