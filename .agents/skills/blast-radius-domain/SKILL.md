# Skill: blast-radius-domain

## When to load this skill
Load this skill whenever working on ANY part of the Blast Radius Analyzer:
implementing a phase, debugging a pipeline step, writing tests, or generating
the design document. This skill encodes the domain knowledge that makes the
difference between generic code and correct code for this specific project.

---

## Domain Concepts You Must Know

### What "blast radius" means here
When a developer merges a Pull Request, some functions change. Those functions
may call other functions, render UI elements, or implement product requirements.
The "blast radius" is the set of UI elements, user flows, and requirements that
could be broken or degraded by the PR — propagated through the knowledge graph
via Personalized PageRank (PPR) + DFS.

### The three graph layers
```
Layer 1 — Requirements:  what was intended (from the PRD/README)
Layer 2 — UI/DOM:        what was built (from the Playwright crawl)
Layer 3 — Code:          how it was built (from ast-grep AST extraction)
```
The graph connects these three layers. A PR change enters at Layer 3
(CodeFunction), propagates via CALLS/RENDERS edges to Layer 2 (UIElement),
then via COVERS edges to Layer 1 (Requirement).

### What "absence" means
A `GapNode` is created when a Requirement exists in the PRD but has NO
corresponding CodeFunction or UIElement linked in the graph. This is NOT an
error — it is a finding. Absent requirements appear in the "Absent Requirements"
section of the report and signal untested or unimplemented features.

### Confidence vs. Impact
- `impact_score`: how far the PPR activation propagated (0.0–1.0)
- `traceability_confidence`: how confident the entity resolution was that
  the edge between layers is correct (0.0–1.0)
- `risk_tier`: HIGH (impact ≥ 0.5), MEDIUM (≥ 0.2), LOW (< 0.2)

### Dark changes
A "dark change" is a CodeFunction that changed in the PR but has NO traceable
path to any UIElement or Requirement. Dark changes appear in the report as
"⚫ Dark Changes" — they warrant manual investigation.

---

## Target Application Context

App:    https://app.documenso.com (open-source e-signature platform)
Repo:   https://github.com/documenso/documenso
Stack:  TypeScript / Next.js / Prisma / tRPC / Turborepo monorepo

### Key directory paths in the Documenso repo
```
packages/trpc/server/routers/   ← tRPC API layer (Phase 3 scan target)
packages/lib/server-only/       ← business logic (Phase 3 scan target)
apps/web/src/                   ← Next.js frontend (Phase 3 scan target)
packages/prisma/schema.prisma   ← DB schema
```

### Good PR targets (touch both tRPC and lib)
- document.ts router + document/ lib
- recipient.ts router + recipient/ lib
- template.ts router + template/ lib

### Bad PR targets (avoid — produce trivial blast radius)
- Only .md files
- Only apps/marketing/
- Only packages/prisma/migrations/
- Only packages/ui/ styling

---

## ast-grep Rules (TypeScript)

Two rule files live in `rules/`:

### rules/ts-functions.yml — extracts function/method declarations
Matches: `function`, `arrow function`, `method_definition`
Output fields: name, file, start_line, end_line, signature

### rules/trpc-procedures.yml — extracts tRPC procedure definitions
Matches: `.query()`, `.mutation()`, `.subscription()` on a procedure builder
Output fields: procedure_name, router_file, type (query/mutation)

**Critical:** `fn.file` from ast-grep output must be normalized to the same
format as `cf.path` in CodeFunction models before any comparison.
Use `verify_path_alignment(functions, delta)` before Phase 5.

---

## Entity Resolution Logic

Phase 4 links CodeFunction nodes to Requirement nodes:

1. Keyword pre-filter: require ≥1 overlapping content word (skip stopwords).
   Threshold is deliberately loose — filter is for speed, not precision.
2. Cosine similarity on sentence-transformer embeddings. Threshold: 0.60.
3. LLM reranker: for pairs above threshold, ask Claude whether the code
   function plausibly implements the requirement. Binary yes/no.
4. IMPLEMENTS edge created only if LLM says yes.

**Known issue (P2-PHASE4-03):** keyword "page" matches everything — exclude
common layout words from the pre-filter stoplist.

---

## PPR Scoring

Phase 5 uses NetworkX's `pagerank()` with personalization:
- Seed nodes: the CodeFunction IDs changed in the PR (from PRDelta)
- Personalization dict: seed nodes get weight 1.0, others 0.0
- alpha: 0.85 (standard damping)

**Known issue (P1-PHASE5-02):** Requirement nodes at the end of long chains
score near 0 because PPR damping compounds. Fix: apply 2.5x multiplier to
sink nodes (nodes with no outgoing edges) before tier assignment.

Evidence paths must show human-readable labels, not node IDs or SHA hashes:
`"createDocument() → /documents page → 'Document creation' requirement"`
NOT: `"fn_a3f2 → ui_9b12 → req_cc01"`

---

## Report Quality Checklist

Before marking the report complete, verify:
- [ ] Executive summary uses no technical jargon
- [ ] Every HIGH finding has an evidence path with readable labels
- [ ] Absent requirements section present (even if empty)
- [ ] Dark changes section present (even if empty)
- [ ] Coverage statistics table at the bottom
- [ ] No raw SHA hashes visible anywhere in the rendered output
- [ ] HTML renders without XSS (escape LLM-generated content — autoescape=True)

---

## One-Time Human Setup Reminder

These cannot be automated — a human must do them before running the pipeline:
1. Create Documenso account at https://app.documenso.com/signup
2. Select a target PR using `gh pr list` command (see AGENTS.md)
3. Pin the merge SHA with `gh pr view $PR_NUMBER --json mergeCommit`
4. Clone the Documenso repo to data/repos/documenso
5. Fill in .env from .env.example

If credentials are missing, Phase 1 auth crawl and Phase 4 RENDERS check
will both fail hard. Auth is mandatory — not optional.
