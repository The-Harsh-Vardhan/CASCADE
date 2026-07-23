# Design Document Audit — Blast Radius Analyzer
**Reviewer:** Critical audit for Testsigma AI Engineer submission  
**Document version:** Pipeline v4  
**Target app:** Documenso / PR #3046

---

## Verdict Summary

This is a strong document — genuinely one of the better things you could submit for this assignment. The writing is precise, the architectural reasoning is defensible, and the scope honesty is real rather than performative. But it has specific weaknesses that a senior engineer will notice, and one structural hole that could cost you significantly on evaluation. They are documented in full below.

| Dimension | Score | Notes |
|---|---|---|
| Agent decomposition | ✅ Strong | Clean det/LLM separation, justified at each boundary |
| Graph schema | ⚠️ Good with gaps | Absence modeling works; edge coverage is thin |
| Confidence handling | ⚠️ Mixed | Two-score system is smart; thresholds lack justification |
| Eval approach | ❌ Weakest section | Smoke tests ≠ eval; recall is unaddressed |
| Scope decisions | ✅ Strong | Honest, specific, not defensive |
| What's next | ✅ Strong | Priority ordering is coherent and well-argued |
| Overall writing quality | ✅ Strong | Precise, confident, no filler |

---

## Section 1: Agent Decomposition — ✅ Strong, Minor Issues

### What works

The det/LLM separation is the best part of this document. The reasoning at each boundary is concrete: "the LLM is invoked at exactly two points — where natural language must become structure (Phase 2), and where cross-domain semantic disambiguation is necessary (Phase 4 reranker)." This is exactly the answer the evaluators want. You've pre-empted the "chain of prompts" objection with a specific and defensible counter-argument.

The input/output contracts per phase (`{url, title, selector_inventory, url_sha256}`, `Requirement[]`, `PRDelta`, etc.) show systems-level thinking. The document passes the senior-engineer test of "would I know what to hand off to someone building the adjacent module."

### Issues

**The Mermaid diagram has a logic gap that the document text partially contradicts.** Phase 1 feeds Phase 2 in the diagram, but the text says Phase 4 reads page snapshots from Phase 1 directly (`data/crawl/page_snapshots/*.json` → Phase 4, per the Appendix artifact schema). The diagram shows `P1 → P2 → P3 → P4` which misrepresents the actual data flow. The correct diagram would show P1 → P4 as a direct edge (which is in the fixed version but the narrative around it is still ambiguous).

**Phase 4 is described as "Hybrid" but the hybrid seam isn't clearly located.** The document says 4a is deterministic (cosine similarity) and 4b is LLM-driven (reranker). But a reader would reasonably ask: what triggers the handoff from 4a to 4b? Top-N means what N? Is N fixed or adaptive? The document says "top-N candidates" without ever saying what N is — and N matters because it bounds the LLM call count and therefore the quota pressure on the 10-key rotation pool.

**"Why this is not a chain of prompts" reads as defensive.** The evaluators don't need to be convinced with a subheading that explicitly names their concern. State the architecture, let the architecture speak. Anticipating an objection and explicitly refuting it draws attention to the objection itself.

---

## Section 2: Graph Schema — ⚠️ Good With Gaps

### What works

The three-layer model maps cleanly to organizational stakeholder ownership (PM → QA → Engineering), which is a smart framing. The GapNode design is correct and the offline-availability justification (Phase 5 reads `gap_nodes.json` directly even when Neo4j is unreachable) is a non-obvious engineering reason that shows you thought about it beyond the schema surface level.

The Cypher query is the right choice to anchor the schema section — it forces the schema to be concrete, and using `OPTIONAL MATCH` for the three path types (direct, call-graph-mediated, UI-mediated) is correct query design.

### Issues

**The node schema is missing `url_sha256` on UIElement in the formal definition.** The text in the UIElement property description says "`url_sha256` is the stable identifier — not the URL itself," but the formal schema block has `UIElement(id, label, url, selector, page_title)` with no `url_sha256` field. This is a contradiction inside a 300-line document. A senior engineer will notice.

**RENDERS edge confidence is stated as fixed 0.70 with no justification.** "Confidence 0.70" for a URL-segment pattern match is an arbitrary number. Why 0.70 and not 0.60 or 0.80? The IMPLEMENTS threshold (0.65) is at least explained as an LLM reranker output. The RENDERS threshold has no calibration story at all. This is a meaningful gap because RENDERS is the path through which UIElements can become blast radius findings — if the threshold is wrong, the UI layer is systematically over- or under-connected.

**The COVERS edge is under-specified.** The document says COVERS edges are created by "keyword matching between the UIElement's page title/selector and the Requirement's `related_ui_keywords`." There is no confidence score mentioned for COVERS edges, no threshold, and no explanation of what happens when there are zero keyword matches. The Section 5 scope admission ("COVERS edge creation from UIElement → Requirement — partially implemented; coverage is sparse") confirms this is thin, but sparse is a significant understatement if the UI → Requirement path is structurally absent from the graph.

**The CALLS edge is not discussed in the context of cycles.** Section 5 mentions "call-graph cycle detection" was deferred, noting TypeScript codebases have cyclic import graphs that "can cause PPR to assign inflated scores to nodes in tight cycles." This is a real problem but it's buried in Section 5. Section 2 should note the CALLS edge limitation at the point of schema definition, not just as a footnote in scope decisions.

**There is no `UserFlow` node.** The assignment explicitly asks for "which discovered user flows are affected." The schema has Requirement, UIElement, CodeFunction, and GapNode. There is no UserFlow concept. The document never explains this omission. A senior evaluator reading the assignment requirements will flag this immediately. Either: define UserFlow nodes and explain how crawling produces them, or explicitly scope out UserFlow and say why.

---

## Section 3: Confidence Handling — ⚠️ Mixed

### What works

The two-score system (impact_score × traceability_confidence = risk tier) is the document's cleverest design decision. Multiplying scores prevents high-PPR / low-semantic-confidence links from surfacing as HIGH findings — a real failure mode in single-score systems. This is worth having in the document.

The sink node problem and the 2.5× boost is the most technically sophisticated subsection. The math is right: α=0.85, depth-3 chain gives ≈ 0.001 for a requirement node. Explaining this as a mathematical artifact rather than a genuine low-confidence signal, and correcting for it explicitly, demonstrates graph literacy beyond what most candidates will show.

The dark change handling is honest: "all 32 changed functions are classified as dark changes" is treated as a true finding about the tRPC abstraction gap rather than as a pipeline failure. This is correct framing and shows engineering maturity.

### Issues

**The risk tier thresholds (0.5 / 0.2) are described as "calibrated for Documenso's graph density" but there is no calibration methodology.** What does calibration mean here? Did you run the pipeline on a PR with known blast radius and tune until the thresholds produced the right tier assignments? Or did you pick numbers that felt reasonable? The document says "a threshold of 0.5 therefore selects only directly-connected, strongly-linked requirements" — this is post-hoc reasoning, not calibration. A calibration methodology would look like: "we labeled 5 PR impacts manually, ran PPR, and set the HIGH threshold at the score that correctly classified 4/5." Without this, the thresholds are arbitrary and an evaluator will say so.

**The two-score multiplication is stated but never shown in an example.** The document defines `impact_score` and `traceability_confidence` but never shows what a concrete node looks like with both scores. An example like: "function `sendDocument()` changed in PR #3046 → IMPLEMENTS edge to 'document sending requirement' with traceability_confidence=0.82 → PPR impact_score=0.61 after sink boost → combined score 0.50 → HIGH tier" would make the system tangible. Without an example, the multiplication claim is untestable.

**The 2.5× sink boost is a post-hoc adjustment to PPR's fundamental mechanics.** This is worth flagging as a design smell, even if the correction is directionally right. Tuning an arbitrary multiplier to make sink nodes score in the "right" tier is substituting an engineering judgment call for a proper solution (such as using PPR with personalization on sink nodes, or switching to a different centrality measure). The document should acknowledge this limitation rather than presenting the boost as a clean solution.

**"When does the system stop and ask a human?" is answered too narrowly.** The section identifies three escalation triggers (LOW confidence, dark changes, absent requirements). But there are failure modes the system doesn't surface: what if Phase 2 extracts only 2 requirements? What if Phase 3 produces zero CodeFunction nodes (repo clone failure)? What if the LLM reranker returns malformed JSON and all 23 links fall back to cosine-only? These upstream failures would produce a report that looks complete but is garbage. None of them trigger a human review item under the current design.

---

## Section 4: Eval Approach — ❌ Weakest Section

This is the section that will cost you points. The assignment asks: "If we ran your system 100 times on the same input, how would we know which runs were correct?" The document does not answer this question. It answers adjacent questions instead.

### What the document actually provides

- Determinism claims for Phases 1–5 ✅ (correct and clear)
- Smoke tests for Phases 4, 5, 6 ✅ (narrow but honest)
- LLM phase evaluation by output count and manual sampling ⚠️ (weak but acknowledged)
- A definition of "correct" for PR #3046 specifically ✅ (good)

### What is missing

**No precision/recall definition over the blast radius finding itself.** The document defines what "correct" means abstractly ("every changed function appears in the report" and "every affected requirement has a traceable path"). But it never computes precision and recall against those definitions for PR #3046. The 100-runs question requires knowing: of N findings in a single run, how many are true positives? Between runs, how stable is N? None of this is quantified.

**Recall is explicitly abandoned.** The document says "recall cannot be measured without exhaustive ground-truth labeling" for Phase 4 — and then stops there. This is true but incomplete. You could partially bound recall: pick a specific requirement (e.g., "document sending"), manually trace which CodeFunctions implement it from the codebase, and verify whether those functions appear in the IMPLEMENTS edges. If `sendDocument()` implements "document sending" but doesn't appear in `entity_links.json`, you know you have a recall failure. This is tractable even without exhaustive labeling.

**The 100-runs question is never answered.** What actually varies across 100 runs? The document says "only borderline candidates near the 0.65 confidence threshold would vary." How many candidates are borderline? For PR #3046 specifically, are there any IMPLEMENTS edges near the 0.65 threshold that could flip? The document produced "23 LLM-confirmed, 0 cosine-only" — but doesn't say what the score distribution looks like. If all 23 are at 0.9+ confidence, the 100-run stability claim is credible. If 8 of them are at 0.66, it isn't.

**The Phase 6 eval is not an eval.** "Show the HTML report to someone who has not read the PR diff" is a user study, not an eval. It's a valid quality check but it's not how you know if the output is *right*. It's how you know if the output is *readable*. These are different. The evaluators are asking about correctness; this tests legibility.

**There is no reference to SWE-bench or any external benchmark.** The reference document explicitly mentions SWE-bench as a potential evaluation benchmark. Even dismissing it ("SWE-bench tests code generation, not impact analysis — not applicable here") would be better than silence. The absence suggests the external eval landscape wasn't considered.

---

## Section 5: Scope Decisions — ✅ Strong

This is the second-best section. The cuts are named specifically, not vaguely. "Docling's VLM mode requires CUDA and a GPU, which were not available in this submission environment" is the right level of specificity — it names the resource constraint and explains the fallback. "The attachment-management requirements from the PRD's diagram on page 4 were not extracted" tells the evaluator exactly what they won't see in the output.

The bug log (P0-21 through BUG-14) is effective. It demonstrates that the system was actually debugged rather than presented as always-correct, and the P0-21 direction bug (IMPLEMENTS edges pointing the wrong way) is exactly the kind of structural error that separates candidates who understand their graph from candidates who don't.

### Minor issues

**"Phase 5 (PPR) received medium depth" is undersold.** The sink node boost and multi-score system described in Section 3 are non-trivial. Calling Phase 5 "medium depth" undersells what was actually built there. Either the implementation is deeper than "medium" (in which case say so), or the write-up in Section 3 is more sophisticated than the implementation (in which case that's a problem).

**The tRPC limitation is described in three places.** Section 1, Section 3, Section 5, and Section 6 all mention the tRPC abstraction gap. By the fourth mention, a reader feels like you're over-explaining one limitation to compensate for others. Say it clearly once (Section 5), reference it once elsewhere (Section 6 is correct — the fix goes in "what's next"). Trim the other two references to one sentence each.

---

## Section 6: What's Next — ✅ Strong

The priority ordering is correct and the reasoning for the ordering is explicitly stated: "eval harness before call graph bridging because you need ground truth to confirm the fix works." This is mature engineering reasoning — most candidates would list "more features" and call it a day. The CI integration being third because "accuracy before availability" is exactly the right prioritization argument.

The tRPC bridge plan (ts-morph, procedure-name map, client-call pattern scan) is specific enough that a senior engineer could actually build it. That's the right level of detail for a "what's next" section.

---

## Cross-Cutting Issues

### The UserFlow omission is the biggest structural problem

The assignment explicitly requires: "which discovered user flows are affected." The graph schema has no UserFlow node. The Cypher query has no UserFlow path. The blast radius report has no UserFlow findings. The document never acknowledges this. This is not a scope cut that was named — it's a silent omission that will be caught by an evaluator reading the assignment requirements alongside the document.

Fix: Either add a UserFlow node to the schema (even if only partially populated by the crawl) with an explicit description of how Playwright navigation sequences produce them, or add a sentence to Section 5 explicitly scoping out UserFlow modeling with a reason ("UserFlow extraction requires stateful Playwright interaction scripts beyond the current crawl's BFS approach — see Section 6, item 3").

### The Gemini / key rotation pool is a credibility risk

Section 3 mentions "10 keys" in the key rotation pool, and the Appendix lists "10-key rotation pool: 10× daily quota headroom vs. single-key setup" as a configuration parameter. This is rotating free-tier API keys to exceed per-key rate limits. Some evaluators will read this neutrally as a resourceful engineering workaround. Others will read it as a terms-of-service violation. Regardless of intent, it's worth removing from the public configuration parameter table or reframing as "multiple project API keys" without drawing attention to the quota-avoidance motivation.

### The document never states total page count or reading time

The assignment says "roughly 8–12 pages." This document is ~2,100 words across 6 sections. At standard academic formatting that's approximately 5–6 pages — below the requested range. The Appendix adds structure but not analytical depth. Section 4 in particular reads short because it doesn't answer the 100-runs question. The document would benefit from expanding Section 4 with an actual run-variance analysis and a concrete recall measurement attempt.

### Missing: any diagram of the actual graph

Section 2 describes a four-node, four-edge-type schema. There is no visual. A simple node-and-edge diagram showing one concrete chain (e.g., `sendDocument:CodeFunction → CALLS → createEnvelopeFields:CodeFunction → IMPLEMENTS → "Custom field configuration":Requirement`) would make the schema tangible in a way that prose cannot. The mermaid flowchart in Section 1 shows the pipeline; there's nothing showing the graph. This is a missed opportunity.

### The `url_sha256` / `url` inconsistency

The UIElement schema block uses `url` as a property but the text says `url_sha256` is the stable identifier. This looks like a doc-vs-implementation divergence. If `url_sha256` is the node ID, it should appear in the schema block. If `url` is the ID and `url_sha256` is a secondary field, that should be made clear. Right now it's ambiguous.

---

## What Evaluators Will Say

**The senior engineer who likes it will say:** The det/LLM separation is exactly right. The sink node boost shows the author understands graph mathematics, not just the API. The scope honesty about tRPC and the call graph depth is rare — most candidates paper over this with vague language. The bug log is a sign of actual debugging, not a demo that was run once and presented.

**The senior engineer who is skeptical will say:** Section 4 doesn't answer the 100-runs question. The thresholds (0.5 / 0.2 / 0.65 / 2.5×) feel calibrated by feel, not measurement. There's no UserFlow in the graph and the document never explains why not. The Phase 4 hybrid handoff (top-N, what's N?) is underspecified. The Cypher query has no `LIMIT` and no index hint — it would full-scan on a large codebase.

**The PM evaluator will say:** The executive summary description is clear. "Dark changes" as a concept translates well to a QA lead. The table in Section 3 with risk tiers is readable. The report sample output (Appendix) is formatted like something a human would actually act on.

---

## Priority Fixes Before Submission

1. **Add UserFlow to the schema or explicitly scope it out with a reason.** This is the only true structural omission relative to the assignment requirements.

2. **Answer the 100-runs question concretely in Section 4.** Run the pipeline twice on PR #3046 with independent LLM calls, compare the IMPLEMENTS edges, report which (if any) flipped. Even if all 23 edges are stable across two runs, say so with evidence.

3. **Attempt a recall bound for Phase 4 on one requirement.** Pick "document sending," trace it manually in the codebase, check whether the ground-truth functions appear in `entity_links.json`. Report the result even if it's unflattering.

4. **Add a graph diagram** showing one concrete traversal path from changed function to affected requirement.

5. **Fix the `url_sha256` vs `url` inconsistency** in the UIElement schema block.

6. **Specify N in "top-N candidates"** for the Phase 4 hybrid handoff.

7. **Consolidate the tRPC limitation references** to one primary (Section 5) and brief references elsewhere.

---

*Audit complete. The document is in the top quartile of what will be submitted. The gaps above are the difference between "strong" and "exceptional."*
