# Blast Radius — Keys 6-10 + Phase 4/5/6 Rerun + Design Doc

## What This Accomplishes

1. Extend `config.py` + `llm.py` to recognise GEMINI_API_KEY_6 through _10 (already set in `.env`)
2. Add a rotation smoke test that verifies all 10 keys are loaded
3. Rerun Phase 4 (graph build / entity resolution) with full LLM reranking now that quota
   pressure is relieved across 10 independent pools
4. Rerun Phase 5 (blast radius / PPR) and Phase 6 (report render) to refresh outputs
5. Commit + push after each phase
6. Write the complete 8-12 page design document in one pass using the design-doc skill

---

## Open Questions

> [!NOTE]
> No blockers — all 10 keys are already present in `.env`. The `.env` comment on line 29
> (`# Change this`) leaves a trailing space after the Neo4j password value —
> pydantic-settings may parse that as part of the password string.
> The fix is to strip the comment on that line. I will do this as part of step 1.

---

## Proposed Changes

### Step 1 — config.py: extend to 10 keys

#### [MODIFY] [config.py](file:///c:/D%20Drive/Projects/Summers%202026/Testsigma/blast_radius/config.py)

- Add `gemini_api_key_6` through `gemini_api_key_10` fields (same pattern as 1-5)
- Update the `gemini_api_keys` property to include them in the numbered list
- Update the docstring and the `EnvironmentError` message to say "_10" instead of "_5"
- Update `validate_and_print()` key-count line (no schema change needed — it calls `gemini_api_keys`)

#### [MODIFY] [.env](file:///c:/D%20Drive/Projects/Summers%202026/Testsigma/.env)

- Strip the inline comment from `NEO4J_PASSWORD` line (trailing ` # Change this` may be
  parsed as part of the password by pydantic-settings, causing auth failure with Neo4j)

---

### Step 2 — Rotation smoke test

#### [MODIFY] [tests/unit/test_placeholder.py](file:///c:/D%20Drive/Projects/Summers%202026/Testsigma/tests/unit/test_placeholder.py)

Replace the placeholder with a real unit test:
- `test_all_10_keys_loaded` — asserts `len(settings.gemini_api_keys) == 10`
- `test_key_rotation_cycles` — steps the round-robin 20 times, verifies all 10 distinct
  keys appear (covers the `itertools.cycle` path)
- Both tests are pure Python (no network calls) — they just read the patched settings object

Run: `python -m pytest tests/unit/test_placeholder.py -v`

---

### Step 3 — Phase 4 rerun (graph build + LLM reranking)

No code changes needed — the LLM rotation in `llm.py` + `resolve.py` already handles it.
With 10 independent quota pools, the `quota_exhausted` fallback path should never trigger.

Actions:
1. Confirm Neo4j is running: `docker compose up -d neo4j`
2. Run Phase 4: `python -m blast_radius.graph`
3. Check output for `[resolve] N IMPLEMENTS links: M LLM-confirmed, 0 cosine-only`
4. Commit: `git add -A && git commit -m "phase4: full LLM reranking with 10-key pool"`

---

### Step 4 — Phase 5 rerun (blast radius / PPR)

Run: `python -m blast_radius.reason`
Commit: `git add -A && git commit -m "phase5: blast radius refreshed with LLM-confirmed IMPLEMENTS edges"`

---

### Step 5 — Phase 6 rerun (report render)

Run: `python -m blast_radius.report`
Commit: `git add -A && git commit -m "phase6: report regenerated from higher-confidence graph"`

---

### Step 6 — Design document

#### [NEW] [docs/design_document.md](file:///c:/D%20Drive/Projects/Summers%202026/Testsigma/docs/design_document.md)

Full 8–12 page design document with all 6 required sections:
1. **Agent Decomposition** (~600 words) — 6-phase reasoning stages, deterministic vs. LLM
2. **Graph Schema with Justification** (~800 words) — node/edge types, GapNodes, Cypher query
3. **Confidence Handling Under Ambiguity** (~500 words) — tiers, dark changes, sink-node boost
4. **Eval Approach** (~500 words) — determinism, smoke tests, path alignment gate, LLM eval
5. **Scope Decisions** (~400 words) — what was cut, why, which bugs fixed vs. deferred
6. **What You'd Build Next** (~400 words) — top 3 priorities with reasoning

Commit: `git add docs/design_document.md && git commit -m "docs: add design document (all 6 sections)"`

---

## Verification Plan

### Automated Tests
```
python -m pytest tests/unit/test_placeholder.py -v
```
Pass condition: `2 passed` with `test_all_10_keys_loaded` and `test_key_rotation_cycles` green.

### Manual Verification
- Phase 4 stdout: `0 cosine-only` fallback links — confirms LLM reranker ran fully
- Phase 5: `data/blast_radius_*.json` timestamp updated
- Phase 6: `data/blast_radius_report_*.html` timestamp updated and opens in browser
- Design doc: renders in GitHub markdown viewer, visually ~10 pages at normal font

### Git Log (expected after all steps)
```
git log --oneline -6
```
Should show 5 commits: config, phase4, phase5, phase6, design-doc.

---

> [!IMPORTANT]
> **Push cadence**: After each phase commit, run `git push origin main` (or the active branch).
> Confirm the remote branch name before pushing — I will check with `git branch` first.
