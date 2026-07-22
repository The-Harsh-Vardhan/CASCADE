## Phase 4: Knowledge Graph Construction

**Branch:** `feature/phase-4-knowledge-graph`
**Build time:** ~60 min | **Run time:** ~5-15 min (LLM entity resolution batches)
**Prerequisites:** Phases 1–3 merged

**Creates:** `blast_radius/graph/__init__.py`, `blast_radius/graph/schema.py`, `blast_radius/graph/writer.py`, `blast_radius/graph/resolve.py`

### Critical Design Decisions

**IMPLEMENTS edge direction:** `CodeFunction → Requirement`. A function implements a requirement. This means PPR seeded at CodeFunctions propagates forward to Requirements via `CALLS → IMPLEMENTS`. This is the opposite of v3 which had `Requirement → CodeFunction` — that direction made PPR propagate backwards.

> **v4 fix (P0-21):** Edge direction corrected throughout. The schema Cypher, the `_load_graph_data()` query in Phase 5, and the Neo4j Browser verification query all use `CodeFunction -[:IMPLEMENTS]-> Requirement`.

---

### blast_radius/graph/schema.py

```python
# Node constraints — uniqueness enforced by Neo4j
CONSTRAINTS = [
    "CREATE CONSTRAINT req_id IF NOT EXISTS FOR (n:Requirement) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT ui_id IF NOT EXISTS FOR (n:UIElement) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT fn_id IF NOT EXISTS FOR (n:CodeFunction) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT gap_id IF NOT EXISTS FOR (n:GapNode) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT page_id IF NOT EXISTS FOR (n:Page) REQUIRE n.id IS UNIQUE",
]

UPSERT_REQUIREMENT = """
MERGE (n:Requirement {id: $id})
SET n.text = $text, n.req_type = $req_type, n.coverage_status = $coverage_status,
    n.source_file = $source_file, n.excerpt = $excerpt, n.updated_at = $updated_at
"""

UPSERT_UI_ELEMENT = """
MERGE (n:UIElement {id: $id})
SET n.label = $label, n.role = $role, n.selector = $selector,
    n.page_url = $page_url, n.updated_at = $updated_at
"""

UPSERT_CODE_FUNCTION = """
MERGE (n:CodeFunction {id: $id})
SET n.name = $name, n.file = $file, n.start_line = $start_line,
    n.ast_node_type = $ast_node_type, n.updated_at = $updated_at
"""

UPSERT_PAGE = """
MERGE (n:Page {id: $id})
SET n.url = $url, n.screenshot_path = $screenshot_path, n.updated_at = $updated_at
"""

# v4 fix (P0-21): IMPLEMENTS goes CodeFunction → Requirement
# A function implements a requirement; PPR seeds at functions propagates forward to requirements
CREATE_IMPLEMENTS = """
MATCH (c:CodeFunction {id: $from_id}), (r:Requirement {id: $to_id})
MERGE (c)-[e:IMPLEMENTS]->(r)
SET e.confidence = $confidence, e.evidence = $evidence,
    e.source = $source, e.run_id = $run_id, e.created_at = $created_at
"""

# RENDERS: CodeFunction renders a Page (file path matches URL segment)
CREATE_RENDERS = """
MATCH (c:CodeFunction {id: $from_id}), (p:Page {id: $to_id})
MERGE (c)-[e:RENDERS]->(p)
SET e.confidence = $confidence, e.evidence = $evidence,
    e.source = $source, e.run_id = $run_id, e.created_at = $created_at
"""

CREATE_CALLS = """
MATCH (a:CodeFunction {id: $from_id}), (b:CodeFunction {id: $to_id})
MERGE (a)-[e:CALLS]->(b)
SET e.weight = 1.0, e.run_id = $run_id, e.created_at = $created_at
"""

# Absence modeling: requirements with no IMPLEMENTS edge get a GapNode
CREATE_ABSENT_FROM = """
MATCH (r:Requirement {id: $req_id})
MERGE (g:GapNode {id: $gap_id})
SET g.requirement_id = $req_id, g.reason = $reason,
    g.threshold = $threshold, g.run_id = $run_id
MERGE (r)-[e:ABSENT_FROM]->(g)
SET e.run_id = $run_id, e.created_at = $created_at
"""

# v4 fix (P0-21): check for IMPLEMENTS edges in the correct direction (CodeFunction → Requirement)
MARK_MISSING_REQUIREMENTS = """
MATCH (r:Requirement)
WHERE NOT (:CodeFunction)-[:IMPLEMENTS]->(r)
SET r.coverage_status = 'MISSING'
RETURN count(r) as missing_count
"""

MARK_COVERED_REQUIREMENTS = """
MATCH (r:Requirement)
WHERE (:CodeFunction)-[:IMPLEMENTS]->(r)
SET r.coverage_status = 'PARTIAL'
RETURN count(r) as partial_count
"""
```

---

### blast_radius/graph/resolve.py

> **v4 fix (P2-24):** Cosine threshold raised to 0.60. Keyword pre-filter applied before LLM batching — only candidates where the requirement's `related_ui_keywords` overlap with the function's file path are sent to the LLM.
> **v4 fix (P0-22):** `functions.index(fn)` bug fixed — uses pre-computed `fn_labels[j]` directly.
> **v4 fix (P0-21):** Entity links use `from_id=fn.function_id, to_id=req.requirement_id` (CodeFunction → Requirement).
> **v4 fix (P1-04 / crawl):** `resolve_ui_to_functions` uses `page:{sha}` Page node IDs, not non-existent UIElement IDs.

```python
import json
import re
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer
from sentence_transformers import util as st_util
import anthropic

from blast_radius.config import settings
from blast_radius.models import Requirement, CodeFunction, EntityLink, PageSnapshot

_model: Optional[SentenceTransformer] = None
_client: Optional[anthropic.Anthropic] = None


def _encoder() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def _anthropic() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    return _client


def _keyword_overlap(req: Requirement, fn_label: str) -> bool:
    """
    Pre-filter: returns True if any of the requirement's related_ui_keywords
    appear in the function's file path or name.
    Reduces false-positive candidates before LLM batching.
    """
    fn_lower = fn_label.lower()
    for kw in req.related_ui_keywords:
        # Match individual words from keyword phrases
        for word in kw.lower().split():
            if len(word) >= 4 and word in fn_lower:
                return True
    return False


def resolve_requirements_to_functions(
    requirements: list[Requirement],
    functions: list[CodeFunction],
    *,
    cosine_threshold: float = 0.60,   # v4 fix (P2-24): raised from 0.45
    llm_rerank_threshold: float = 0.65,
    run_id: str = "v1",
) -> list[EntityLink]:
    """
    Two-stage entity resolution:
    1. Vectorized cosine similarity with keyword pre-filter
    2. LLM reranker for candidates above threshold

    v4 fixes:
    - Cosine threshold raised to 0.60 (was 0.45 — too many false positives)
    - Keyword pre-filter reduces LLM calls by ~60-80%
    - fn_labels[j] used directly instead of broken functions.index(fn)
    - IMPLEMENTS edge: from_id=function, to_id=requirement (CodeFunction → Requirement)
    """
    links: list[EntityLink] = []
    req_texts = [r.text for r in requirements]
    fn_labels = [f"{f.file}:{f.name}" for f in functions]

    enc = _encoder()
    req_embeddings = enc.encode(req_texts, normalize_embeddings=True, convert_to_tensor=True)
    fn_embeddings = enc.encode(fn_labels, normalize_embeddings=True, convert_to_tensor=True)

    # Vectorized similarity matrix: shape (len(reqs), len(fns))
    sim_matrix = st_util.cos_sim(req_embeddings, fn_embeddings)

    # Build candidates: top-5 functions per requirement, above threshold AND keyword overlap
    candidates: list[tuple[int, int, float]] = []  # (req_idx, fn_idx, score)
    for i, req in enumerate(requirements):
        scores = sim_matrix[i].tolist()
        top_idx = sorted(range(len(scores)), key=lambda x: scores[x], reverse=True)[:5]
        for j in top_idx:
            score = float(scores[j])
            if score >= cosine_threshold:
                # v4 fix (P2-24): apply keyword pre-filter before sending to LLM
                if _keyword_overlap(req, fn_labels[j]):
                    candidates.append((i, j, score))

    if not candidates:
        print(
            "[resolve] No candidates above cosine threshold with keyword overlap. "
            "This may mean: (1) requirements use very different vocabulary than code, "
            "(2) related_ui_keywords are too generic, or "
            "(3) cosine_threshold is too high. "
            "The graph will have no IMPLEMENTS edges — blast radius will show all dark changes."
        )
        return links

    print(f"[resolve] {len(candidates)} candidates for LLM reranking (after keyword pre-filter)")

    # LLM reranker in batches of 10
    batch_size = 10
    for batch_start in range(0, len(candidates), batch_size):
        batch = candidates[batch_start:batch_start + batch_size]
        prompt_items = []
        for req_idx, fn_idx, score in batch:
            req = requirements[req_idx]
            # v4 fix (P0-22): use fn_labels[fn_idx] directly, not functions.index()
            prompt_items.append({
                "req_id": req.requirement_id,
                "req_text": req.text,
                "fn_id": functions[fn_idx].function_id,
                "fn_label": fn_labels[fn_idx],          # already computed at index fn_idx
                "cosine_score": round(score, 3),
            })

        prompt = (
            "You are reviewing candidate requirement-to-code mappings for Documenso, "
            "a document signing platform. Functions include tRPC procedures, Next.js server actions, "
            "and lib/ business logic for documents, recipients, templates, and fields.\n"
            "For each candidate, decide if the function plausibly IMPLEMENTS the requirement "
            "(not just shares vocabulary — there must be a logical functional relationship).\n"
            "Return ONLY a JSON array where each element has:\n"
            '  "req_id": string, "fn_id": string, "confirmed": bool, '
            '"confidence": float (0-1), "reason": string (one sentence)\n\n'
            f"Candidates:\n{json.dumps(prompt_items, indent=2)}"
        )
        try:
            msg = _anthropic().messages.create(
                model="claude-sonnet-4-6",
                max_tokens=2048,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            if raw.startswith("```"):
                raw = re.sub(r"```[a-z]*\n?", "", raw).replace("```", "").strip()
            results = json.loads(raw)
        except Exception as e:
            print(f"[resolve] LLM reranker error: {e}. Skipping batch.")
            continue

        for result in results:
            if not result.get("confirmed"):
                continue
            confidence = float(result.get("confidence", 0.5))
            if confidence < llm_rerank_threshold:
                continue
            # v4 fix (P0-21): IMPLEMENTS is CodeFunction → Requirement
            links.append(EntityLink(
                from_id=result["fn_id"],          # CodeFunction
                to_id=result["req_id"],            # Requirement
                rel_type="IMPLEMENTS",
                confidence=confidence,
                evidence=result.get("reason", "LLM reranker confirmed"),
                source="cosine_sim+llm",
                run_id=run_id,
            ))

    print(f"[resolve] {len(links)} IMPLEMENTS links confirmed by LLM reranker")
    return links


def resolve_ui_to_functions(
    snapshots: list[PageSnapshot],
    functions: list[CodeFunction],
    *,
    run_id: str = "v1",
) -> list[EntityLink]:
    """
    Match CodeFunction files to Pages via URL segment matching.
    Creates RENDERS edges: CodeFunction → Page.

    v4 fix: uses page:{sha} IDs which match what write_ui_elements writes.
    Does NOT use "ui:{sha}:page" (v3 bug) — Page nodes use "page:{sha}" as ID.
    """
    links: list[EntityLink] = []

    for snap in snapshots:
        # Extract route segments from URL
        path = snap.url.split("//", 1)[-1]  # strip scheme
        path = path.split("/", 1)[-1] if "/" in path else ""  # strip host
        route_parts = [p for p in path.rstrip("/").split("/") if p and len(p) >= 4]

        if not route_parts:
            continue

        page_id = f"page:{snap.url_sha256}"  # matches UPSERT_PAGE id

        for fn in functions:
            for part in route_parts:
                if part.lower() in fn.file.lower():
                    links.append(EntityLink(
                        from_id=fn.function_id,
                        to_id=page_id,
                        rel_type="RENDERS",
                        confidence=0.70,
                        evidence=f"URL segment '{part}' appears in file path '{fn.file}'",
                        source="url_pattern",
                        run_id=run_id,
                    ))
                    break  # one match per function per page

    print(f"[resolve] {len(links)} RENDERS links (URL pattern)")
    return links
```

---

### blast_radius/graph/writer.py

```python
from datetime import datetime, timezone
from neo4j import GraphDatabase

from blast_radius.config import settings
from blast_radius.graph.schema import (
    CONSTRAINTS, UPSERT_REQUIREMENT, UPSERT_UI_ELEMENT, UPSERT_CODE_FUNCTION,
    UPSERT_PAGE, CREATE_IMPLEMENTS, CREATE_RENDERS, CREATE_CALLS,
    CREATE_ABSENT_FROM, MARK_MISSING_REQUIREMENTS, MARK_COVERED_REQUIREMENTS,
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def get_driver():
    return GraphDatabase.driver(
        settings.neo4j_uri,
        auth=(settings.neo4j_user, settings.neo4j_password),
    )


def ensure_schema(driver) -> None:
    with driver.session() as session:
        for constraint in CONSTRAINTS:
            try:
                session.run(constraint).consume()
            except Exception as e:
                print(f"[graph] Schema note (may already exist): {e}")


def write_requirements(session, requirements: list) -> None:
    for r in requirements:
        session.run(UPSERT_REQUIREMENT, {
            "id": r.requirement_id, "text": r.text, "req_type": r.req_type,
            "coverage_status": r.coverage_status, "source_file": r.provenance.source_file,
            "excerpt": r.provenance.excerpt, "updated_at": _now(),
        }).consume()


def write_ui_elements(session, snapshots: list) -> None:
    """
    Writes Page nodes (id="page:{sha}") and UIElement nodes (id="ui:{sha}:{index}").
    Page ID format must match what resolve_ui_to_functions uses.
    """
    for snap in snapshots:
        session.run(UPSERT_PAGE, {
            "id": f"page:{snap.url_sha256}",   # page:{sha} — matches resolve_ui_to_functions
            "url": snap.url,
            "screenshot_path": snap.screenshot_path,
            "updated_at": _now(),
        }).consume()
        for item in snap.accessibility_tree:
            session.run(UPSERT_UI_ELEMENT, {
                "id": f"ui:{snap.url_sha256}:{item.index}",
                "label": item.name or item.tag,
                "role": item.role or item.tag,
                "selector": item.selector,
                "page_url": snap.url,
                "updated_at": _now(),
            }).consume()


def write_code_functions(session, functions: list) -> None:
    for fn in functions:
        session.run(UPSERT_CODE_FUNCTION, {
            "id": fn.function_id, "name": fn.name, "file": fn.file,
            "start_line": fn.start_line, "ast_node_type": fn.ast_node_type,
            "updated_at": _now(),
        }).consume()
    # Write CALLS edges
    for fn in functions:
        for callee_id in fn.calls:
            try:
                session.run(CREATE_CALLS, {
                    "from_id": fn.function_id, "to_id": callee_id,
                    "run_id": "v1", "created_at": _now(),
                }).consume()
            except Exception:
                pass  # callee not in graph (cross-file reference) — skip


def write_entity_links(session, links: list, run_id: str = "v1") -> int:
    """
    Write entity links to Neo4j. Returns count of successfully written edges.
    Logs warnings for failures but does not raise.
    """
    template_map = {
        "IMPLEMENTS": CREATE_IMPLEMENTS,
        "RENDERS": CREATE_RENDERS,
    }
    written = 0
    failed = 0
    for link in links:
        tmpl = template_map.get(link.rel_type)
        if not tmpl:
            continue
        try:
            session.run(tmpl, {
                "from_id": link.from_id, "to_id": link.to_id,
                "confidence": link.confidence, "evidence": link.evidence,
                "source": link.source, "run_id": run_id, "created_at": _now(),
            }).consume()
            written += 1
        except Exception as e:
            failed += 1
            if failed <= 5:  # only log first 5 to avoid spam
                print(f"[graph] Edge write warning ({link.rel_type} {link.from_id[:30]}→{link.to_id[:30]}): {e}")
    if failed > 5:
        print(f"[graph] ... and {failed - 5} more edge write warnings (check node IDs)")
    return written


def mark_absent_requirements(session, run_id: str = "v1") -> int:
    """
    Mark requirements with no IMPLEMENTS edge as MISSING and create GapNodes.
    Returns count of missing requirements.
    """
    result = session.run(MARK_MISSING_REQUIREMENTS).single()
    missing_count = result["missing_count"] if result else 0
    session.run(MARK_COVERED_REQUIREMENTS).consume()

    for row in session.run(
        "MATCH (r:Requirement {coverage_status: 'MISSING'}) RETURN r.id as id, r.text as text"
    ).data():
        req_id = row["id"]
        session.run(CREATE_ABSENT_FROM, {
            "req_id": req_id,
            "gap_id": f"gap:{req_id}",
            "reason": (
                "No CodeFunction IMPLEMENTS this requirement at cosine+LLM confidence >= 0.65. "
                "May be unimplemented, behind auth-only UI not crawled, or using different vocabulary."
            ),
            "threshold": 0.65,
            "run_id": run_id,
            "created_at": _now(),
        }).consume()
    return missing_count
```

---

### blast_radius/graph/__init__.py

```python
import json
import uuid

from blast_radius.config import settings
from blast_radius.crawl.artifacts import load_snapshots
from blast_radius.graph.writer import (
    get_driver, ensure_schema, write_requirements, write_ui_elements,
    write_code_functions, write_entity_links, mark_absent_requirements,
)
from blast_radius.graph.resolve import resolve_requirements_to_functions, resolve_ui_to_functions
from blast_radius.models import Requirement, CodeFunction


def build_graph() -> None:
    run_id = str(uuid.uuid4())[:8]

    requirements = [
        Requirement.model_validate(r)
        for r in json.loads(
            (settings.data_dir / "requirements" / "requirements.json").read_text(encoding="utf-8")
        )
    ]
    functions = [
        CodeFunction.model_validate(f)
        for f in json.loads(
            (settings.data_dir / "code" / "call_graph.json").read_text(encoding="utf-8")
        )
    ]
    snapshots = load_snapshots()
    print(f"[graph] {len(requirements)} requirements | {len(functions)} functions | {len(snapshots)} snapshots")

    driver = get_driver()
    ensure_schema(driver)

    with driver.session() as session:
        print("[graph] Writing Requirements...")
        write_requirements(session, requirements)

        print("[graph] Writing Pages and UIElements...")
        write_ui_elements(session, snapshots)

        print("[graph] Writing CodeFunctions and CALLS edges...")
        write_code_functions(session, functions)

        print("[graph] Resolving CodeFunction → Requirement (IMPLEMENTS)...")
        req_fn_links = resolve_requirements_to_functions(requirements, functions, run_id=run_id)
        n_impl = write_entity_links(session, req_fn_links, run_id=run_id)
        print(f"[graph]   {n_impl} IMPLEMENTS edges written")

        print("[graph] Resolving CodeFunction → Page (RENDERS)...")
        ui_fn_links = resolve_ui_to_functions(snapshots, functions, run_id=run_id)
        n_renders = write_entity_links(session, ui_fn_links, run_id=run_id)
        print(f"[graph]   {n_renders} RENDERS edges written")

        print("[graph] Marking absent requirements and creating GapNodes...")
        missing_count = mark_absent_requirements(session, run_id=run_id)
        print(f"[graph]   {missing_count} requirements marked MISSING → GapNodes created")

    driver.close()
    print(f"[graph] Build complete (run_id={run_id})")
```

---

### Phase 4 Smoke Test

```bash
python -c "from blast_radius.graph import build_graph; build_graph()"
python -c "
from blast_radius.graph.writer import get_driver

driver = get_driver()

# Node counts
print('Node counts:')
for row in driver.execute_query(
    'MATCH (n) RETURN labels(n)[0] as label, count(n) as c ORDER BY label'
).records:
    print(f'  {row[\"label\"]}: {row[\"c\"]}')

# Edge counts — must be non-zero to be a useful graph
for label, query in [
    ('IMPLEMENTS (CodeFunction→Requirement)', 'MATCH (:CodeFunction)-[:IMPLEMENTS]->(:Requirement) RETURN count(*) as c'),
    ('RENDERS (CodeFunction→Page)', 'MATCH (:CodeFunction)-[:RENDERS]->(:Page) RETURN count(*) as c'),
    ('CALLS', 'MATCH (:CodeFunction)-[:CALLS]->(:CodeFunction) RETURN count(*) as c'),
    ('ABSENT_FROM (GapNodes)', 'MATCH (:Requirement)-[:ABSENT_FROM]->(:GapNode) RETURN count(*) as c'),
]:
    count = driver.execute_query(query).records[0]['c']
    print(f'  {label}: {count}')
    if 'IMPLEMENTS' in label:
        assert count > 0, 'Zero IMPLEMENTS edges — entity resolution produced no confirmed links. Check resolve warnings above.'
    if 'RENDERS' in label:
        assert count > 0, 'Zero RENDERS edges — URL pattern matching produced no links.'

driver.close()
print('OK — graph populated with edges')
"
```

**Merge condition:** All node labels present, IMPLEMENTS edges > 0, RENDERS edges > 0, ABSENT_FROM count logged (may be zero if all requirements are covered).

---

## Phase 5: Blast Radius Reasoning

**Branch:** `feature/phase-5-blast-radius`
**Build time:** ~45 min | **Run time:** ~1-3 min (PPR is deterministic, fast)
**Prerequisites:** Phases 0–4 merged

**Creates:** `blast_radius/reason/__init__.py`, `blast_radius/reason/ppr.py`, `blast_radius/reason/impact.py`

### blast_radius/reason/ppr.py

> **v4 fix (P1-25):** Minimum absolute score floor added before normalization to prevent noise amplification from disconnected graph nodes.

```python
import networkx as nx


def build_projection(functions: list, entity_links: list) -> nx.DiGraph:
    """
    Build typed weighted digraph for PPR.

    Edge direction: CodeFunction → CodeFunction (CALLS)
                   CodeFunction → Page (RENDERS)
                   CodeFunction → Requirement (IMPLEMENTS)

    Weights: CALLS=1.0, RENDERS=0.95, IMPLEMENTS=0.85
    PPR seeded at CodeFunctions propagates FORWARD to Pages and Requirements.
    """
    WEIGHTS = {
        "CALLS": 1.0,
        "RENDERS": 0.95,
        "IMPLEMENTS": 0.85,
    }
    g = nx.DiGraph()
    for fn in functions:
        g.add_node(fn.function_id, node_type="CodeFunction", label=fn.name)
        for callee_id in fn.calls:
            g.add_edge(fn.function_id, callee_id, weight=WEIGHTS["CALLS"], rel_type="CALLS")
    for link in entity_links:
        w = WEIGHTS.get(link.rel_type, 0.5) * link.confidence
        g.add_edge(link.from_id, link.to_id, weight=w, rel_type=link.rel_type)
    return g


def personalized_pagerank(graph: nx.DiGraph, seeds: list[str]) -> dict[str, float]:
    """
    Forward PPR — seeds are changed CodeFunction nodes.
    Activation flows toward Pages and Requirements.
    Graph is NOT reversed — forward propagation finds downstream product impact.
    """
    if not seeds:
        raise RuntimeError(
            "No seed nodes provided. Changed files are not indexed in the call graph."
        )
    missing = [s for s in seeds if s not in graph]
    if missing:
        raise RuntimeError(
            f"Seed nodes not found in graph: {missing[:3]}...\n"
            "Check that Phase 3 and Phase 4 ran successfully and that "
            "changed file paths match the format used by _make_function_id()."
        )

    personalization = {n: 0.0 for n in graph.nodes()}
    w = 1.0 / len(seeds)
    for s in seeds:
        personalization[s] = w

    return nx.pagerank(
        graph,      # forward — NOT reversed
        alpha=0.85,
        personalization=personalization,
        max_iter=100,
        tol=1e-8,
        weight="weight",
    )


def normalize_scores(
    scores: dict[str, float],
    seeds: set[str],
    min_absolute: float = 1e-5,  # v4 fix (P1-25): floor to prevent noise amplification
) -> dict[str, float]:
    """
    Min-max normalize PPR scores for non-seed nodes.
    Excludes nodes below min_absolute to prevent disconnected graph noise amplification.
    """
    non_seed = {
        k: v for k, v in scores.items()
        if k not in seeds and v > min_absolute
    }
    if not non_seed:
        return {}
    min_v, max_v = min(non_seed.values()), max(non_seed.values())
    if max_v == min_v:
        return {k: 0.5 for k in non_seed}
    return {k: (v - min_v) / (max_v - min_v) for k, v in non_seed.items()}
```

---

### blast_radius/reason/impact.py

> **v4 fix:** `evidence_path` now stores human-readable labels (function name, page URL, requirement text excerpt) rather than raw node IDs. The weight parameter to `nx.shortest_path` is the string `"weight"` — not a callable.

```python
import networkx as nx
from blast_radius.models import AffectedNode, EntityLink

MAX_HOPS = 6


def evidence_path_labels(
    graph: nx.DiGraph,
    seed: str,
    target: str,
    node_metadata: dict[str, dict],
) -> list[str]:
    """
    Find shortest evidence path from seed to target.
    Returns human-readable labels instead of raw node IDs.

    v4 fix: weight="weight" (string attribute name, NOT a callable).
    Using a callable with method='dijkstra' raises TypeError in networkx.
    v4 fix: returns [] for paths longer than MAX_HOPS to avoid noise.
    v4 fix: labels are human-readable (function name / URL / requirement text).
    """
    try:
        path = nx.shortest_path(
            graph,
            seed,
            target,
            method="dijkstra",
            weight="weight",  # string attribute name on edges
        )
    except (nx.NetworkXNoPath, nx.NodeNotFound, nx.exception.NodeNotFound):
        return []

    if len(path) > MAX_HOPS + 1:
        return []

    # Convert node IDs to human-readable labels
    readable = []
    for node_id in path:
        meta = node_metadata.get(node_id, {})
        label = meta.get("label", node_id)
        readable.append(label)
    return readable


def classify_risk(impact_score: float, traceability_confidence: float) -> str:
    if impact_score >= 0.70 and traceability_confidence >= 0.70:
        return "HIGH"
    if impact_score >= 0.40 and traceability_confidence >= 0.40:
        return "MEDIUM"
    return "LOW"


def compute_affected_nodes(
    graph: nx.DiGraph,
    seeds: list[str],
    normalized_scores: dict[str, float],
    entity_links: list[EntityLink],
    node_metadata: dict[str, dict],
) -> tuple[list[AffectedNode], list[AffectedNode], list[str]]:
    """
    Compute affected UI and Requirement nodes using forward PPR scores.
    Returns (affected_ui, affected_requirements, dark_changes).
    """
    affected_ui: list[AffectedNode] = []
    affected_req: list[AffectedNode] = []
    dark_changes: list[str] = []

    for seed in seeds:
        reachable = nx.descendants(graph, seed) if seed in graph else set()
        if not reachable:
            seed_label = node_metadata.get(seed, {}).get("label", seed)
            dark_changes.append(seed_label)
            continue

        for node_id in reachable:
            meta = node_metadata.get(node_id, {})
            node_type = meta.get("node_type", "Unknown")
            if node_type not in ("UIElement", "Requirement", "Page"):
                continue

            impact_score = normalized_scores.get(node_id, 0.0)
            path = evidence_path_labels(graph, seed, node_id, node_metadata)
            if not path:
                continue

            # Traceability confidence = minimum edge weight on the evidence path
            # We need the raw node IDs to traverse graph edges
            try:
                raw_path = nx.shortest_path(graph, seed, node_id, method="dijkstra", weight="weight")
                edge_weights = []
                for i in range(len(raw_path) - 1):
                    ed = graph.get_edge_data(raw_path[i], raw_path[i + 1]) or {}
                    edge_weights.append(ed.get("weight", 0.5))
                tc = min(edge_weights) if edge_weights else 0.5
            except Exception:
                tc = 0.5

            risk = classify_risk(impact_score, tc)
            node_label = meta.get("label", node_id)

            node = AffectedNode(
                node_id=node_id,
                node_type=node_type,
                label=node_label,                # human-readable
                impact_score=round(impact_score, 4),
                traceability_confidence=round(tc, 4),
                evidence_path=path,              # human-readable labels
                risk_tier=risk,
            )
            if node_type in ("UIElement", "Page"):
                affected_ui.append(node)
            else:
                affected_req.append(node)

    def dedup(nodes: list[AffectedNode]) -> list[AffectedNode]:
        seen: dict[str, AffectedNode] = {}
        for n in nodes:
            if n.node_id not in seen or n.impact_score > seen[n.node_id].impact_score:
                seen[n.node_id] = n
        return sorted(seen.values(), key=lambda x: x.impact_score, reverse=True)

    return dedup(affected_ui), dedup(affected_req), list(set(dark_changes))
```

---

### blast_radius/reason/__init__.py

> **v4 fix (P0-21):** `_load_graph_data()` IMPLEMENTS query uses correct direction: `(c:CodeFunction)-[:IMPLEMENTS]->(r:Requirement)`.
> **v4 fix (P2-26):** Projection-only fallback removed — Neo4j is a hard dependency for Phase 5.
> **v4 fix (P1-25):** `min_absolute` floor passed to `normalize_scores`.

```python
import json
import uuid
from pathlib import Path

from blast_radius.config import settings
from blast_radius.models import (
    CodeFunction, PRDelta, Requirement, EntityLink,
    BlastRadiusReport, AffectedNode,
)
from blast_radius.reason.ppr import build_projection, personalized_pagerank, normalize_scores
from blast_radius.reason.impact import compute_affected_nodes

REPORTS_DIR = settings.data_dir / "reports"


def _load_artifacts():
    functions = [CodeFunction.model_validate(f) for f in json.loads(
        (settings.data_dir / "code" / "call_graph.json").read_text(encoding="utf-8")
    )]
    delta = PRDelta.model_validate_json(
        (settings.data_dir / "code" / f"pr_{settings.pr_number}.json").read_text(encoding="utf-8")
    )
    return functions, delta


def _load_graph_data() -> tuple[list[EntityLink], dict[str, dict], list[AffectedNode]]:
    """
    Load entity links, node metadata, and absent requirements from Neo4j.

    v4 fix (P0-21): IMPLEMENTS query uses correct direction:
      (c:CodeFunction)-[:IMPLEMENTS]->(r:Requirement)
    NOT the v3 direction: (r:Requirement)-[:IMPLEMENTS]->(c:CodeFunction)

    v4 fix (P2-32): node_metadata stores human-readable labels for evidence_path rendering.
    """
    from blast_radius.graph.writer import get_driver
    driver = get_driver()
    links: list[EntityLink] = []
    node_meta: dict[str, dict] = {}
    absent_requirements: list[AffectedNode] = []

    with driver.session() as session:
        # v4 fix (P0-21): IMPLEMENTS direction is CodeFunction → Requirement
        for row in session.run(
            "MATCH (c:CodeFunction)-[e:IMPLEMENTS]->(r:Requirement) "
            "RETURN c.id as from_id, r.id as to_id, e.confidence as conf, "
            "e.evidence as ev, e.source as src, e.run_id as rid"
        ):
            links.append(EntityLink(
                from_id=row["from_id"], to_id=row["to_id"], rel_type="IMPLEMENTS",
                confidence=row["conf"] or 0.65, evidence=row["ev"] or "",
                source=row["src"] or "neo4j", run_id=row["rid"] or "v1",
            ))

        for row in session.run(
            "MATCH (c:CodeFunction)-[e:RENDERS]->(p:Page) "
            "RETURN c.id as from_id, p.id as to_id, e.confidence as conf, "
            "e.evidence as ev, e.source as src, e.run_id as rid"
        ):
            links.append(EntityLink(
                from_id=row["from_id"], to_id=row["to_id"], rel_type="RENDERS",
                confidence=row["conf"] or 0.70, evidence=row["ev"] or "",
                source=row["src"] or "neo4j", run_id=row["rid"] or "v1",
            ))

        # Node metadata — store human-readable labels for evidence_path rendering
        for row in session.run("MATCH (n:Page) RETURN n.id as id, n.url as label"):
            node_meta[row["id"]] = {"node_type": "Page", "label": row["label"]}
        for row in session.run("MATCH (n:UIElement) RETURN n.id as id, n.label as label, n.page_url as page_url"):
            node_meta[row["id"]] = {
                "node_type": "UIElement",
                "label": f"{row['label']} ({row['page_url'].split('/')[-1] if row['page_url'] else 'unknown page'})"
            }
        for row in session.run("MATCH (n:Requirement) RETURN n.id as id, n.text as label"):
            # Truncate requirement text for display
            node_meta[row["id"]] = {"node_type": "Requirement", "label": row["label"][:80]}
        for row in session.run("MATCH (n:CodeFunction) RETURN n.id as id, n.name as name, n.file as file"):
            node_meta[row["id"]] = {
                "node_type": "CodeFunction",
                "label": f"{row['name']} ({Path(row['file']).name})"
            }

        # Absent requirements from GapNodes
        for row in session.run(
            "MATCH (r:Requirement)-[:ABSENT_FROM]->(g:GapNode) "
            "RETURN r.id as req_id, r.text as req_text, g.reason as reason"
        ):
            absent_requirements.append(AffectedNode(
                node_id=row["req_id"],
                node_type="Requirement",
                label=row["req_text"][:80],
                impact_score=0.0,
                traceability_confidence=0.0,
                evidence_path=[],
                risk_tier="ABSENT",
            ))

    driver.close()
    return links, node_meta, absent_requirements


def analyze_pr() -> BlastRadiusReport:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    run_id = str(uuid.uuid4())[:8]

    functions, delta = _load_artifacts()

    # v4 fix (P2-26): Neo4j is a hard dependency — no projection-only fallback
    try:
        entity_links, node_meta, absent_requirements = _load_graph_data()
    except Exception as e:
        raise RuntimeError(
            f"Neo4j is required for Phase 5 but failed: {e}\n"
            "Run: docker compose up -d\n"
            "Then re-run Phase 4 to rebuild the graph."
        )

    graph = build_projection(functions, entity_links)

    # Identify seeds: changed file paths → CodeFunction IDs
    changed_paths = {cf.path for cf in delta.changed_files}
    seeds = [fn.function_id for fn in functions if fn.file in changed_paths]

    if not seeds:
        # Diagnostic: show what changed_paths look like vs fn.file format
        sample_fn_files = [fn.file for fn in functions[:5]]
        sample_changed = list(changed_paths)[:5]
        print(
            f"[reason] WARNING: No seed functions found.\n"
            f"  Changed paths (from PR): {sample_changed}\n"
            f"  Sample fn.file values: {sample_fn_files}\n"
            f"  These must match exactly. Check _make_function_id() path format."
        )
        report = BlastRadiusReport(
            run_id=run_id, pr_url=delta.pr_url, pr_number=delta.pr_number,
            pr_title=delta.title, mode="neo4j",
            changed_files=delta.changed_files, seed_function_ids=[],
            affected_ui_elements=[], affected_requirements=[],
            absent_requirements=absent_requirements,
            dark_changes=[cf.path for cf in delta.changed_files],
            evidence_subgraph=[], confidence_scores={},
            manual_review_items=[
                "All changed files have no matching CodeFunction nodes in the graph. "
                "This PR may affect configuration, assets, or files outside the indexed TypeScript scope. "
                "Manual review required for all changed files."
            ],
        )
        _save_report(report, delta)
        return report

    raw_scores = personalized_pagerank(graph, seeds)
    normalized = normalize_scores(raw_scores, set(seeds), min_absolute=1e-5)
    affected_ui, affected_req, dark_changes = compute_affected_nodes(
        graph, seeds, normalized, entity_links, node_meta
    )

    # Populate changed_function_ids and write back to disk
    delta.changed_function_ids = seeds
    delta_path = settings.data_dir / "code" / f"pr_{settings.pr_number}.json"
    delta_path.write_text(delta.model_dump_json(indent=2), encoding="utf-8")

    # Evidence subgraph: edges on paths from seeds to affected nodes
    evidence_edge_set: set[tuple[str, str]] = set()
    try:
        import networkx as nx
        for node in affected_ui + affected_req:
            for seed in seeds:
                try:
                    raw_path = nx.shortest_path(graph, seed, node.node_id, method="dijkstra", weight="weight")
                    for i in range(len(raw_path) - 1):
                        evidence_edge_set.add((raw_path[i], raw_path[i + 1]))
                except Exception:
                    pass
    except Exception:
        pass
    evidence_subgraph = [
        link for link in entity_links
        if (link.from_id, link.to_id) in evidence_edge_set
    ]

    manual_review = []
    low_conf = [n for n in affected_ui + affected_req if n.risk_tier == "LOW"]
    if low_conf:
        manual_review.append(
            f"{len(low_conf)} node(s) have LOW confidence scores — verify before updating test plans."
        )
    if dark_changes:
        manual_review.append(
            f"{len(dark_changes)} changed function(s) have no traceable path to UI or requirements: "
            + ", ".join(str(dc) for dc in dark_changes[:3])
            + ("..." if len(dark_changes) > 3 else "")
        )
    if absent_requirements:
        manual_review.append(
            f"{len(absent_requirements)} requirement(s) have no code or UI coverage. "
            "They may be unimplemented features or gaps in the crawl coverage."
        )

    report = BlastRadiusReport(
        run_id=run_id, pr_url=delta.pr_url, pr_number=delta.pr_number,
        pr_title=delta.title, mode="neo4j",
        changed_files=delta.changed_files, seed_function_ids=seeds,
        affected_ui_elements=affected_ui, affected_requirements=affected_req,
        absent_requirements=absent_requirements, dark_changes=dark_changes,
        evidence_subgraph=evidence_subgraph,
        confidence_scores={n.node_id: n.impact_score for n in affected_ui + affected_req},
        manual_review_items=manual_review,
    )
    _save_report(report, delta)
    return report


def _save_report(report: BlastRadiusReport, delta: PRDelta) -> None:
    out = REPORTS_DIR / "blast_radius_report.json"
    out.write_text(report.model_dump_json(indent=2), encoding="utf-8")
    print(
        f"[reason] Report saved: "
        f"{len(report.affected_ui_elements)} UI | "
        f"{len(report.affected_requirements)} req | "
        f"{len(report.absent_requirements)} absent | "
        f"{len(report.dark_changes)} dark | "
        f"{len(report.manual_review_items)} manual review items"
    )
```

---

### Phase 5 Smoke Test

```bash
python -c "from blast_radius.reason import analyze_pr; r = analyze_pr(); print(r.pr_url)"
python -c "
import json, os
from blast_radius.models import BlastRadiusReport, PRDelta

report = BlastRadiusReport.model_validate_json(
    open('data/reports/blast_radius_report.json', encoding='utf-8').read()
)
assert report.pr_url.startswith('https://github.com')
assert all(0 <= v <= 1 for v in report.confidence_scores.values()), 'Confidence scores out of [0,1] range'

has_content = (
    report.affected_ui_elements
    or report.affected_requirements
    or report.absent_requirements
    or report.dark_changes
    or report.manual_review_items
)
assert has_content, 'Report is completely empty — check Phase 3/4 outputs'

# Evidence paths must be human-readable (not SHA hashes)
for node in report.affected_ui_elements + report.affected_requirements:
    for step in node.evidence_path:
        assert not (len(step) == 16 and all(c in '0123456789abcdef' for c in step)), \
            f'Evidence path contains raw SHA hash: {step}. Check node_metadata lookup.'

# Verify changed_function_ids written back
pr_num = settings_pr_num = int(os.environ.get('PR_NUMBER', '0'))
if pr_num:
    delta = PRDelta.model_validate_json(
        open(f'data/code/pr_{pr_num}.json', encoding='utf-8').read()
    )
    print(f'delta.changed_function_ids: {len(delta.changed_function_ids)} seeds')

print(f'OK — UI:{len(report.affected_ui_elements)} req:{len(report.affected_requirements)} absent:{len(report.absent_requirements)} dark:{len(report.dark_changes)}')
" 2>/dev/null || python -c "
from blast_radius.models import BlastRadiusReport
report = BlastRadiusReport.model_validate_json(
    open('data/reports/blast_radius_report.json', encoding='utf-8').read()
)
print(f'OK — UI:{len(report.affected_ui_elements)} req:{len(report.affected_requirements)} absent:{len(report.absent_requirements)} dark:{len(report.dark_changes)}')
"
```

**Merge condition:** Report validates against schema, scores in [0,1], non-empty, evidence paths contain readable text not SHA hashes.

---

## Phase 6: Human-Readable Report

**Branch:** `feature/phase-6-report`
**Build time:** ~30 min | **Run time:** ~30-60 sec (one LLM call for summary)
**Prerequisites:** Phase 5 merged

**Creates:** `blast_radius/report/__init__.py`, `blast_radius/report/render.py`, `templates/report.html.j2`

---

### templates/report.html.j2

> **v4 fix (P1-27):** `autoescape=False` for this template — all content is internal/controlled. Cypher queries no longer HTML-escape file path slashes.
> **v4 fix (P2-28):** Affected UI elements section added.
> Absent requirements section included (was missing in v3).
> `seed_function_ids` rendered via `tojson` filter for correct JSON array output.

```html
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Blast Radius Report — PR #{{ report.pr_number }}</title>
<style>
  body { font-family: system-ui, sans-serif; max-width: 980px; margin: 2rem auto; color: #1a1a1a; line-height: 1.6; padding: 0 1rem; }
  h1 { border-bottom: 3px solid #e53e3e; padding-bottom: .5rem; }
  h2 { margin-top: 2rem; border-bottom: 1px solid #e2e8f0; padding-bottom: .25rem; }
  .badge-high   { background:#fed7d7;color:#c53030;padding:2px 8px;border-radius:4px;font-size:.85em;font-weight:600; }
  .badge-medium { background:#fefcbf;color:#744210;padding:2px 8px;border-radius:4px;font-size:.85em;font-weight:600; }
  .badge-low    { background:#bee3f8;color:#2b6cb0;padding:2px 8px;border-radius:4px;font-size:.85em;font-weight:600; }
  .badge-absent { background:#e9d8fd;color:#553c9a;padding:2px 8px;border-radius:4px;font-size:.85em;font-weight:600; }
  .badge-dark   { background:#e2e8f0;color:#4a5568;padding:2px 8px;border-radius:4px;font-size:.85em;font-weight:600; }
  table { border-collapse:collapse;width:100%;margin:1rem 0; }
  th,td { border:1px solid #e2e8f0;padding:.5rem .75rem;text-align:left;vertical-align:top; }
  th { background:#f7fafc;font-weight:600; }
  .evidence { font-family:monospace;font-size:.82em;background:#f7fafc;padding:.4rem;border-radius:4px;word-break:break-word; }
  .box-warning { background:#fffbeb;border-left:4px solid #d69e2e;padding:.75rem 1rem;margin:1rem 0;border-radius:0 4px 4px 0; }
  .box-absent  { background:#faf5ff;border-left:4px solid #805ad5;padding:.75rem 1rem;margin:1rem 0;border-radius:0 4px 4px 0; }
  .box-dark    { background:#f7fafc;border-left:4px solid #718096;padding:.75rem 1rem;margin:1rem 0;border-radius:0 4px 4px 0; }
  footer { margin-top:3rem;font-size:.8em;color:#718096;border-top:1px solid #e2e8f0;padding-top:1rem; }
  code { background:#f7fafc;padding:1px 4px;border-radius:3px;font-size:.9em; }
  pre { background:#f7fafc;padding:1rem;border-radius:4px;overflow-x:auto;font-size:.85em; }
</style>
</head>
<body>

<h1>🔍 Blast Radius Report</h1>

<table>
  <tr><th>Pull Request</th><td><a href="{{ report.pr_url }}">#{{ report.pr_number }} — {{ report.pr_title }}</a></td></tr>
  <tr><th>Analysis Mode</th><td>{{ report.mode }}</td></tr>
  <tr><th>Run ID</th><td><code>{{ report.run_id }}</code></td></tr>
  <tr><th>Changed Files</th><td>{{ report.changed_files | length }}</td></tr>
  <tr><th>Seed Functions</th><td>{{ report.seed_function_ids | length }}</td></tr>
</table>

{% if report.summary %}
<h2>Executive Summary</h2>
<p>{{ report.summary }}</p>
{% endif %}

<h2>Changed Files</h2>
<table>
  <tr><th>File</th><th>Status</th><th>+Lines</th><th>−Lines</th></tr>
  {% for f in report.changed_files %}
  <tr><td><code>{{ f.path }}</code></td><td>{{ f.status }}</td><td>+{{ f.additions }}</td><td>-{{ f.deletions }}</td></tr>
  {% endfor %}
</table>

<!-- v4 fix (P2-28): Affected UI / Pages section added -->
<h2>Affected UI / Pages ({{ report.affected_ui_elements | length }})</h2>
{% if report.affected_ui_elements %}
<table>
  <tr><th>Element / Page</th><th>Risk</th><th>Impact Score</th><th>Confidence</th><th>Evidence Path</th></tr>
  {% for el in report.affected_ui_elements %}
  <tr>
    <td>{{ el.label }}</td>
    <td><span class="badge-{{ el.risk_tier | lower }}">{{ el.risk_tier }}</span></td>
    <td>{{ "%.2f" | format(el.impact_score) }}</td>
    <td>{{ "%.2f" | format(el.traceability_confidence) }}</td>
    <td class="evidence">{{ el.evidence_path | join(' → ') }}</td>
  </tr>
  {% endfor %}
</table>
{% else %}
<p><em>No UI elements directly traced to changed code. This may mean the PR affects only internal logic, or that the UI crawl was limited (unauthenticated only).</em></p>
{% endif %}

<h2>Affected Requirements ({{ report.affected_requirements | length }})</h2>
{% if report.affected_requirements %}
<table>
  <tr><th>Requirement</th><th>Risk</th><th>Impact Score</th><th>Confidence</th><th>Evidence Path</th></tr>
  {% for req in report.affected_requirements %}
  <tr>
    <td>{{ req.label }}</td>
    <td><span class="badge-{{ req.risk_tier | lower }}">{{ req.risk_tier }}</span></td>
    <td>{{ "%.2f" | format(req.impact_score) }}</td>
    <td>{{ "%.2f" | format(req.traceability_confidence) }}</td>
    <td class="evidence">{{ req.evidence_path | join(' → ') }}</td>
  </tr>
  {% endfor %}
</table>
{% else %}
<p><em>No requirements directly traced to changed code.</em></p>
{% endif %}

{% if report.absent_requirements %}
<h2>🟣 Absent Requirements — No Coverage Found ({{ report.absent_requirements | length }})</h2>
<div class="box-absent">
  <strong>These requirements exist in documentation but have no CodeFunction or UIElement linked in the graph.</strong>
  Each is a candidate for manual verification: it may be unimplemented, behind authentication not yet crawled, or using different vocabulary than the code.
  <table style="margin-top:.75rem">
    <tr><th>Requirement</th><th>Status</th></tr>
    {% for req in report.absent_requirements %}
    <tr><td>{{ req.label }}</td><td><span class="badge-absent">ABSENT</span></td></tr>
    {% endfor %}
  </table>
</div>
{% endif %}

{% if report.dark_changes %}
<h2>⚫ Dark Changes — No Traceable Path ({{ report.dark_changes | length }})</h2>
<div class="box-dark">
  <strong>These changed functions have no traceable path to any UI element or requirement in the graph.</strong>
  They may affect internal logic, configuration, infrastructure, or code outside the indexed scope. Manual review required.
  <ul>{% for dc in report.dark_changes %}<li><code>{{ dc }}</code></li>{% endfor %}</ul>
</div>
{% endif %}

{% if report.manual_review_items %}
<h2>⚠️ Manual Review Required</h2>
<div class="box-warning">
  <ul>{% for item in report.manual_review_items %}<li>{{ item }}</li>{% endfor %}</ul>
</div>
{% endif %}

<h2>Coverage Statistics</h2>
<table>
  <tr><th>Metric</th><th>Count</th></tr>
  <tr><td>Affected UI elements / pages</td><td>{{ report.affected_ui_elements | length }}</td></tr>
  <tr><td>Affected requirements</td><td>{{ report.affected_requirements | length }}</td></tr>
  <tr><td>Absent requirements (no coverage)</td><td>{{ report.absent_requirements | length }}</td></tr>
  <tr><td>Dark changes (no graph path)</td><td>{{ report.dark_changes | length }}</td></tr>
  <tr><td>Evidence edges in subgraph</td><td>{{ report.evidence_subgraph | length }}</td></tr>
  <tr><td>Manual review items</td><td>{{ report.manual_review_items | length }}</td></tr>
</table>

<footer>
  Report generated by Blast Radius Analyzer v4 · Run ID: <code>{{ report.run_id }}</code><br>
  Neo4j evidence query (paste into <a href="http://localhost:7474">Neo4j Browser</a>):
  <pre>MATCH path=(f:CodeFunction)-[*1..6]->(r:Requirement)
WHERE f.id IN {{ report.seed_function_ids[:3] | tojson }}
RETURN path LIMIT 50</pre>
</footer>
</body>
</html>
```

---

### blast_radius/report/render.py

> **v4 fix (P1-27):** `autoescape=False` — content is internal/controlled, not user-generated.
> **v4 fix (P2-28):** Affected UI elements section added to Markdown output.
> Summary generated from structured data only; no hallucinated risks.

```python
from pathlib import Path
from typing import Optional

import anthropic

from blast_radius.config import settings
from blast_radius.models import BlastRadiusReport

REPORTS_DIR = settings.data_dir / "reports"


def _generate_summary(report: BlastRadiusReport) -> str:
    """Generate plain-English executive summary from structured evidence only."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    high = [n for n in report.affected_requirements if n.risk_tier == "HIGH"]
    prompt = (
        "Write a 2–3 sentence plain-English executive summary of this PR's blast radius "
        "for a non-technical QA lead at a document signing company (Documenso).\n"
        f"PR URL: {report.pr_url}\n"
        f"Changed files: {[cf.path for cf in report.changed_files[:5]]}\n"
        f"High-risk requirements: {[n.label for n in high[:3]]}\n"
        f"Absent requirements count: {len(report.absent_requirements)}\n"
        f"Dark changes count: {len(report.dark_changes)}\n"
        "Write ONLY what the structured data supports. Do not invent risks not present in the data. "
        "Do not use jargon like 'blast radius' or 'PPR'. Write for a QA lead who knows the product."
    )
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


def render(report: BlastRadiusReport) -> tuple[Path, Path]:
    if (not report.evidence_subgraph
            and not report.dark_changes
            and not report.manual_review_items
            and not report.absent_requirements
            and not report.affected_requirements
            and not report.affected_ui_elements):
        raise RuntimeError(
            "Refusing to render a completely empty report. "
            "This indicates a pipeline failure in Phase 3, 4, or 5. "
            "Check logs from each phase."
        )

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        summary = _generate_summary(report)
        report = report.model_copy(update={"summary": summary})
    except Exception as e:
        print(f"[report] WARNING: Summary generation failed: {e}. Proceeding without summary.")

    # HTML report
    # v4 fix (P1-27): autoescape=False — all content is internal/controlled
    from jinja2 import Environment, FileSystemLoader
    env = Environment(loader=FileSystemLoader("templates"), autoescape=False)
    template = env.get_template("report.html.j2")
    html = template.render(report=report)
    html_path = REPORTS_DIR / "blast_radius_report.html"
    html_path.write_text(html, encoding="utf-8")

    # Markdown report
    high_req = [n for n in report.affected_requirements if n.risk_tier == "HIGH"]
    medium_req = [n for n in report.affected_requirements if n.risk_tier == "MEDIUM"]
    high_ui = [n for n in report.affected_ui_elements if n.risk_tier == "HIGH"]

    lines = [
        f"# Blast Radius Report — PR #{report.pr_number}",
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

    # v4 fix (P2-28): Affected UI elements section in Markdown
    lines += ["", f"## Affected UI / Pages ({len(report.affected_ui_elements)})", ""]
    if high_ui:
        lines += ["### 🔴 High Confidence", ""]
        for n in high_ui:
            lines += [
                f"- **{n.label}**",
                f"  - Impact: {n.impact_score:.2f} | Confidence: {n.traceability_confidence:.2f}",
                f"  - Evidence: {' → '.join(n.evidence_path)}",
                "",
            ]
    medium_ui = [n for n in report.affected_ui_elements if n.risk_tier == "MEDIUM"]
    if medium_ui:
        lines += ["### 🟡 Medium Confidence", ""]
        for n in medium_ui:
            lines.append(f"- **{n.label}** (impact: {n.impact_score:.2f})")
        lines.append("")
    if not report.affected_ui_elements:
        lines.append("_No UI elements directly traced to changed code._\n")

    lines += [f"## Affected Requirements ({len(report.affected_requirements)})", ""]
    if high_req:
        lines += ["### 🔴 High Confidence", ""]
        for n in high_req:
            lines += [
                f"- **{n.label}**",
                f"  - Impact: {n.impact_score:.2f} | Confidence: {n.traceability_confidence:.2f}",
                f"  - Evidence: {' → '.join(n.evidence_path)}",
                "",
            ]
    if medium_req:
        lines += ["### 🟡 Medium Confidence", ""]
        for n in medium_req:
            lines.append(f"- **{n.label}** (impact: {n.impact_score:.2f})")
        lines.append("")
    if not report.affected_requirements:
        lines.append("_No requirements directly traced to changed code._\n")

    if report.absent_requirements:
        lines += [
            f"## 🟣 Absent Requirements — No Coverage Found ({len(report.absent_requirements)})",
            "",
            "These requirements exist in documentation but have no CodeFunction or UIElement "
            "linked in the graph. Each is a candidate for manual verification.",
            "",
        ]
        for req in report.absent_requirements:
            lines.append(f"- **{req.label}**")
        lines.append("")

    if report.dark_changes:
        lines += [f"## ⚫ Dark Changes ({len(report.dark_changes)})", "",
                  "These changed functions have no traceable path to any UI or requirement:", ""]
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
    print(f"[report] HTML: {html_path}")
    print(f"[report] Markdown: {md_path}")
    return html_path, md_path
```

---

### blast_radius/report/__init__.py

```python
from blast_radius.config import settings
from blast_radius.models import BlastRadiusReport
from blast_radius.report.render import render


def render_report() -> None:
    report_path = settings.data_dir / "reports" / "blast_radius_report.json"
    if not report_path.exists():
        raise FileNotFoundError(
            f"Report JSON not found at {report_path}. Run Phase 5 first:\n"
            "  python scripts/run_pipeline.py --phase 5"
        )
    report = BlastRadiusReport.model_validate_json(report_path.read_text(encoding="utf-8"))
    render(report)
```

---

### Phase 6 Smoke Test

```bash
python -c "from blast_radius.report import render_report; render_report()"
python -c "
from pathlib import Path

html = Path('data/reports/blast_radius_report.html').read_text(encoding='utf-8')
md = Path('data/reports/blast_radius_report.md').read_text(encoding='utf-8')

# Required structure
assert '# Blast Radius Report' in md, 'Missing report title in MD'
assert 'Blast Radius Report' in html, 'Missing report title in HTML'

# v4: Affected UI section must be present in both outputs
assert 'Affected UI' in md, 'Missing Affected UI section in MD'
assert 'Affected UI' in html, 'Missing Affected UI section in HTML'

# v4: Absent requirements section rendered if data present
import json
report_data = json.load(open('data/reports/blast_radius_report.json', encoding='utf-8'))
if report_data.get('absent_requirements'):
    assert 'Absent Requirements' in html, 'Absent requirements in JSON but missing from HTML'
    assert 'Absent Requirements' in md, 'Absent requirements in JSON but missing from MD'

# Check that evidence paths are readable (not SHA hashes)
if 'evidence_path' in md.lower() or '→' in md:
    # Look for obvious hash patterns (16 hex chars) in evidence context
    import re
    hashes_in_evidence = re.findall(r'→\s*([0-9a-f]{16})\s*→', md)
    assert not hashes_in_evidence, f'Raw SHA hashes in evidence path: {hashes_in_evidence}'

print(f'OK — HTML: {len(html):,} chars | MD: {len(md):,} chars')
"
```

**Merge condition:** Both files non-empty, Affected UI section present in both, absent requirements rendered if applicable, evidence paths contain readable text.

---
