# Workflow: /scope-first

Trigger this workflow at the START of any new coding session.
Do not write code until the scope summary is approved.

---

## Steps

1. Read all reference docs listed in AGENTS.md (in order)

2. Load the blast-radius-domain skill and audit-guard skill

3. Produce a scope summary covering:
   - What the v4 plan proposes to build across all 6 phases
   - What the audit flagged as the 3 highest-risk issues
   - Which 2 phases you recommend going deep on (quality over coverage)
   - Explicit list of what you will cut, with one-sentence defense per cut
   - Which audit bugs you will fix vs. defer
   - Proposed 6-step execution order for this session with clear outputs
     at each step

4. Output the scope summary as a formatted Markdown table + prose.
   Do not write any code.

5. Wait for explicit approval before proceeding.

---

## What good scope looks like

Good: "We will implement Phase 0 (skeleton), Phase 3 (code analysis), and
Phase 5 (blast radius) to full depth. Phase 1 (crawler) will be stubbed with
fixture data so Phase 3 and 5 have real inputs. Phase 2 (ingest) will use a
simplified httpx fetch instead of Docling. Phase 4 (graph build) will be
minimal — enough to wire Phases 3 and 5 together. We cut Phase 6 (HTML report)
and will deliver only the Markdown report."

Bad: "We will implement all 6 phases." (No cuts named. Will produce shallow
output across all phases.)
