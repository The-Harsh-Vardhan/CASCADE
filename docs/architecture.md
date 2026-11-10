# Architecture

[Back to overview](index.html)

CASCADE has an offline pipeline that builds the knowledge graph once and an online pipeline that analyzes a PR against it. The diagram below (Mermaid source) is rendered natively in the [GitHub README](https://github.com/The-Harsh-Vardhan/CASCADE#architecture).

```
flowchart TB
    subgraph OFF["OFFLINE: build the graph once"]
        P1["Phase 1 crawl/ - Playwright + Gemini page analysis"]
        P2["Phase 2 ingest/ - httpx + BeautifulSoup + Gemini"]
        P3["Phase 3 code/ - ast-grep rules + GitHub API"]
        P4["Phase 4 graph/ + fusion/ - MiniLM cosine + Gemini rerank, absence detection"]
        Seed["flows/seeder + api/seeder"]
        P1 -->|page snapshots| P4
        P2 -->|requirements.json| P4
        P3 -->|call_graph.json| P4
    end
    Art[("data/ JSON artifacts")]
    Neo[("Neo4j")]
    P4 -->|source of truth for Phase 5| Art
    P4 -->|optional write| Neo
    Seed --> Neo
    subgraph ON["ONLINE: python run.py PR_URL"]
        Run["pipeline/online.py"] -->|GitHub REST| Delta["PR delta"]
        Delta -->|seed functions| P5["Phase 5 reason/ - Personalized PageRank"]
        P5 -->|risk tiers, dark changes| P6["Phase 6 report/"]
        P6 --> Out["md, html, docx, pdf"]
    end
    Neo -.->|readiness check| Run
    Art --> P5
```

## Offline pipeline

| Phase | Module | What it does |
|---|---|---|
| 1 | `blast_radius/crawl` | Playwright crawl of app.documenso.com; Gemini analyses each page into UI components and flows |
| 2 | `blast_radius/ingest` | Fetches Documenso documentation with httpx, extracts typed requirements with Gemini, deduplicates |
| 3 | `blast_radius/code` | `ast-grep` rules (`rules/`) extract functions and tRPC procedures; builds the call graph and fetches the PR delta |
| 4 | `blast_radius/graph`, `blast_radius/fusion` | Sentence-transformer cosine plus Gemini reranking for `IMPLEMENTS`; URL matching for `RENDERS`; keyword matching for `COVERS`; three-type absence detection; writes `data/graph/entity_links.json` and optionally Neo4j |

`pipeline/offline.py` runs Phase 4 and seeds the `UserFlow` and `APIEndpoint` nodes. Phases 1 to 3 run through `scripts/run_pipeline.py --phase N`.

## Online pipeline

`run.py` parses the PR URL and calls `pipeline/online.py`, which checks that Neo4j holds a populated graph (at least 100 nodes), fetches the changed files from the GitHub REST API into `data/code/pr_N.json`, runs Phase 5 (`blast_radius/reason`: NetworkX Personalized PageRank seeded at the changed functions, HIGH / MEDIUM / LOW risk tiers, dark changes) and Phase 6 (`blast_radius/report`: Markdown, HTML, DOCX and PDF, with a Gemini executive summary and a structured fallback when quota is exhausted).

LLM calls are limited to Phases 1, 2, 4 and 6 and always go through `blast_radius/llm.py`, which rotates up to five Gemini keys on 429s. Phase 5 is deterministic.

## Graph schema

Three layers: Requirements (`Requirement`, `GapNode` / `AbsentRequirement`), UI and flows (`UIElement`, `UserFlow`) and Code (`CodeFunction`). Edges: `IMPLEMENTS` (code to requirement), `RENDERS` (code to page), `COVERS` (page or flow to requirement), `CALLS` (code to code), `BELONGS_TO` (page to flow step) and `ABSENT_FROM` (gap to requirement). The full rationale is in the [design document](https://github.com/The-Harsh-Vardhan/CASCADE/blob/main/submission/design%20document/design_document_expanded.md).
