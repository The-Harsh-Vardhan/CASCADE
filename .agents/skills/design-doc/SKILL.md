# Skill: design-doc

## When to load this skill
Load this skill when writing or expanding the design document. The design doc
is weighted equally with code in the evaluation. It must be 8–12 pages and
address specific questions. This skill provides the exact structure, word-count
targets, and the source material to draw from for each section.

---

## Required Sections (all mandatory)

The assignment requires these sections. Do not omit any of them.

---

### Section 1: Agent Decomposition (~600 words)

**The question:** What are the distinct stages of reasoning in your agent?
Where are the boundaries? What is deterministic vs. LLM-driven, and why?
"We are not looking for a chain of prompts dressed up as an agent."

**What to write:**
- Describe each of the 6 phases as a distinct reasoning stage
- For each phase, state: is it deterministic or LLM-driven?
- Justify WHY each mode was chosen (not just describe it)
- Name the boundaries — what is the input/output contract between stages?

**Source material:** Pull from the "Deterministic vs. LLM-Driven" table in
the v4 plan. The key insight to articulate: deterministic stages handle
structural facts (ASTs, graph writes, PPR math); LLM stages handle semantic
ambiguity (natural language → structured requirements, cross-vocabulary
entity resolution, human-readable synthesis).

**The distinction that impresses evaluators:** Explain that a "chain of prompts"
would just call an LLM at each step. The actual architecture uses deterministic
graph traversal (PPR + DFS) for impact propagation — the LLM is only invoked
where semantic understanding is genuinely required.

---

### Section 2: Graph Schema with Justification (~800 words)

**The question:** Your node and edge types, how they connect across the three
layers, and specifically how you model ABSENCE. Justify your schema against
a query you would need to run.

**What to write:**
- List all node types with their properties
- List all edge types with direction and semantic meaning
- Explain the three-layer structure and why it's organized that way
- Explain GapNodes specifically — what they are, when they're created, why
  this approach was chosen over alternatives
- Anchor the schema to a concrete query: e.g., "To find all requirements at
  risk from PR #1234, run: MATCH (cf:CodeFunction)-[:CALLS*]->(cf2)-[:RENDERS]
  ->(ui)-[:COVERS]->(r:Requirement) WHERE cf.id IN $changed_ids RETURN r"

**Schema reference (copy these exactly):**
```
Nodes:
  Requirement(id, label, source, text, coverage_status)
  UIElement(id, label, url, selector, page_title)
  CodeFunction(id, label, file, name, signature)
  GapNode(id, requirement_id)

Edges:
  IMPLEMENTS: CodeFunction → Requirement
  RENDERS:    CodeFunction → UIElement
  COVERS:     UIElement → Requirement
  CALLS:      CodeFunction → CodeFunction
```

**On absence:** GapNodes are created during Phase 4 for every Requirement
that has no IMPLEMENTS or COVERS edge after entity resolution. They are NOT
error nodes — they are first-class findings. The design choice to model
absence explicitly (rather than just as a missing query result) means the
blast radius report can surface them as "absent requirements" without requiring
a second query pass.

---

### Section 3: Confidence Handling Under Ambiguity (~500 words)

**The question:** When the agent isn't sure (PRD describes a feature you
can't find in the UI; code change touches a function you can't map to a
UI element), what happens? How is confidence represented? When does the
system stop and ask a human?

**What to write:**
- Explain the two confidence dimensions: impact_score (PPR propagation)
  and traceability_confidence (entity resolution strength)
- Describe the three tiers: HIGH ≥ 0.5, MEDIUM ≥ 0.2, LOW < 0.2
- Explain what happens at each tier in the report
- Describe the "manual review items" output — when does the system surface
  these vs. silently assign LOW?
- Explain dark changes as a confidence failure mode (changed function, no
  traceable path — surfaced explicitly, not silently dropped)
- Explain absent requirements as a separate confidence failure mode

**The sink node problem to mention:** PPR damping compounds over long chains,
causing Requirement nodes to score near 0 even when genuinely impacted.
The 2.5x sink boost is a deliberate correction to this artifact — worth
explaining as a confidence calibration decision.

---

### Section 4: Eval Approach (~500 words)

**The question:** How do you know your agent's output is right? If we ran
your system 100 times on the same input, how would we know which runs were
correct?

**What to write:**
- Determinism: phases 1–5 are deterministic given fixed inputs → same PR
  produces same blast radius every run (except LLM extraction in phases 2/4)
- Smoke tests: each phase has a smoke test with specific pass/fail conditions
  (describe 2–3 of the most meaningful ones)
- The path alignment check (verify_path_alignment) as a correctness gate —
  if it fails, the entire Phase 5 output is meaningless
- How you would evaluate the LLM-driven steps specifically:
  - Phase 2: count requirements extracted; < 5 from a full README is a signal
    of failure, not sparse PRD
  - Phase 4: entity resolution precision — manually check 10 IMPLEMENTS edges
    and verify they are semantically correct
  - Phase 6: the report is evaluated by showing it to someone who doesn't
    know the code and asking if it's actionable
- What "correct" means for the blast radius specifically: a correct report
  correctly identifies functions that changed AND traces them to affected
  requirements — the ground truth is the PR diff itself + manual code reading

---

### Section 5: Scope Decisions (~400 words)

**The question:** What did you cut, what did you go deep on, and why?
This section is NOT optional. Honest scope discussion scores higher than
polished work with hidden cuts.

**What to write:**
- State which 2 phases you went deep on
- For each phase you cut or simplified, name it explicitly and give the
  reason (time, complexity, dependency risk — not vague "future work")
- Name the audit bugs you fixed and the ones you deferred
- Be specific: "We cut the Docling OCR pipeline for docs.documenso.com
  and replaced it with httpx + text extraction because Docling's VLM mode
  requires CUDA which wasn't available in the submission environment."

**The tone that scores well:** opinionated, specific, unsentimental. Do not
apologize for cuts. Defend them as correct prioritization decisions.

---

### Section 6: What You'd Build Next (~400 words)

**The question:** The three highest-value things you would build next,
in order, with reasoning.

**Suggested answers grounded in the audit:**
1. Authenticated crawl hardening + CI integration — the biggest single
   risk to output quality; automated re-crawl on each PR
2. LLM extraction eval harness — phase 2 and 4 quality is currently
   unverified; add ground-truth labeled pairs and precision/recall metrics
3. Design document section completeness — P0-DOC-01 from the audit;
   50% of the assignment weight is the design doc, and its scaffolding
   was missing from the v4 plan

---

## Format Instructions

- Output as Markdown, 8–12 pages when rendered at normal font size
- Use `##` for section headers (matching the section names above)
- Include the graph schema as a code block
- Include at least one Cypher query as a concrete example
- Do NOT use bullet points as a substitute for reasoning — write prose
  for the analysis sections, bullets only for lists of concrete items
- Diagrams are welcome — use Mermaid if helpful
