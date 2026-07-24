# Phase 2: Requirements Ingestor — Rewrite Summary

## Result: SMOKE TEST PASSED ✅

| Metric | Result | Target |
|--------|--------|--------|
| Total requirements | **272–324** (varies by LLM run) | ≥ 50 |
| Feature areas covered | **9 / 8 required** | All 8 |
| Areas with ≥ 3 requirements | **9 / 9** | All |

## Area Breakdown (smoke test run)

| feature_area | Count | Status |
|---|---|---|
| admin | 24 | [OK] |
| api | 17 | [OK] |
| auth | 31 | [OK] |
| notifications | 17 | [OK] |
| sending | 84 | [OK] |
| signing | 17 | [OK] |
| teams | 26 | [OK] |
| templates | 32 | [OK] |
| webhooks | 24 | [OK] |

## Files Changed

| File | Change |
|------|--------|
| [fetch.py](file:///c:/D%20Drive/Projects/Summers%202026/Testsigma/blast_radius/ingest/fetch.py) | Replaced 6 broken `docs.documenso.com` URLs with **25 GitHub raw MDX files** from `apps/docs/content/docs/` |
| [extract.py](file:///c:/D%20Drive/Projects/Summers%202026/Testsigma/blast_radius/ingest/extract.py) | Exhaustive system prompt (per task spec); Jaccard-70% + exact-title dedup; controlled-vocab normalization |
| [__init__.py](file:///c:/D%20Drive/Projects/Summers%202026/Testsigma/blast_radius/ingest/__init__.py) | Save-before-print ordering; ASCII-safe output for Windows; per-area breakdown with [OK]/[!] flags |
| [models.py](file:///c:/D%20Drive/Projects/Summers%202026/Testsigma/blast_radius/models.py) | Extended `Requirement` with `title`, `description`, `feature_area`, `acceptance_criteria`, `related_api_endpoints`, `priority`, `source` |
| [llm.py](file:///c:/D%20Drive/Projects/Summers%202026/Testsigma/blast_radius/llm.py) | Raised `max_output_tokens` 8192 → 16384 to prevent JSON truncation on large API doc sources |
| [ingestor.py](file:///c:/D%20Drive/Projects/Summers%202026/Testsigma/ingestor.py) | **NEW** — root-level thin wrapper exposing `run_ingestion()` for smoke tests |

## Source Coverage (25 MDX files)

| Source group | Files | Feature areas covered |
|---|---|---|
| GitHub Markdown | README.md, CONTRIBUTING.md | sending, admin |
| users/documents | add-fields, send, upload, add-recipients, direct-links | signing, sending |
| users/templates | create, use | templates |
| users/organisations | overview, members, groups, create-team | teams |
| users/settings | security, api-tokens, profile | auth, admin |
| users/getting-started | send-first-document | sending |
| developers/webhooks | events, setup, verification | webhooks |
| developers/api | documents, recipients, templates | api |
| developers/getting-started | authentication, first-api-call | auth, api |
| docs root | index.mdx | overview/all |

## Outputs

- **Primary**: `outputs/requirements/requirements.json` — canonical output with new schema
- **Legacy**: `data/requirements/requirements.json` — Pydantic model_dump for Phase 4 graph builder

## Running

```bash
# Full pipeline (run_ingestion smoke test):
python -c "from ingestor import run_ingestion; r=run_ingestion(); print(f'Total: {len(r)}')"

# Via module:
python -m blast_radius.ingest
```
