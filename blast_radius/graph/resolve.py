"""
blast_radius/graph/resolve.py — Entity resolution: Requirements ↔ CodeFunctions.

Two-stage pipeline:
  1. Vectorized cosine similarity (sentence-transformers all-MiniLM-L6-v2)
     with keyword pre-filter — reduces LLM calls by ~60-80%
  2. Gemini LLM reranker via call_llm_json() for confirmed links

v4 fixes applied:
  P2-24: cosine threshold raised to 0.60 (from 0.45 — too many false positives)
  P0-22: fn_labels[j] used directly instead of broken functions.index(fn)
  P0-21: IMPLEMENTS is CodeFunction → Requirement (from_id=fn, to_id=req)
  LLM:   uses call_llm_json (never direct Gemini/Anthropic calls)
"""

import json
import re
from typing import Optional

import numpy as np
from sentence_transformers import SentenceTransformer
from sentence_transformers import util as st_util

from blast_radius.llm import call_llm_json_sync as call_llm_json
from blast_radius.models import Requirement, CodeFunction, EntityLink, PageSnapshot

_model: Optional[SentenceTransformer] = None


def _encoder() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


# ── Keyword pre-filter ────────────────────────────────────────────────────────

# Words too generic to be meaningful in keyword matching (BUG-14)
_STOPWORDS = {
    "page", "component", "module", "function", "service", "handler",
    "route", "type", "interface", "model", "schema", "data", "item",
    "list", "user", "get", "set", "create", "update", "delete",
}


def _keyword_overlap(req: Requirement, fn_label: str) -> bool:
    """
    Pre-filter: True if any non-trivial keyword from the requirement overlaps
    with the function's file path or name.
    Prevents sending irrelevant pairs to the LLM.
    """
    fn_lower = fn_label.lower()
    for kw in req.related_ui_keywords:
        for word in kw.lower().split():
            if len(word) >= 4 and word not in _STOPWORDS and word in fn_lower:
                return True
    # Also check domain words directly from requirement text
    req_words = set(re.findall(r"\b[a-z]{4,}\b", req.text.lower())) - _STOPWORDS
    fn_words = set(re.findall(r"\b[a-z]{4,}\b", fn_lower)) - _STOPWORDS
    return bool(req_words & fn_words)


# ── Main resolution ───────────────────────────────────────────────────────────

def resolve_requirements_to_functions(
    requirements: list[Requirement],
    functions: list[CodeFunction],
    *,
    cosine_threshold: float = 0.25,   # calibrated for NL-requirement → code-name cross-domain
    llm_rerank_threshold: float = 0.65,
    run_id: str = "v1",
) -> list[EntityLink]:
    """
    Two-stage entity resolution: Requirements -> CodeFunctions (IMPLEMENTS edges).

    Stage 1: Sentence embedding cosine similarity on FUNCTION NAMES (not file paths).
             Cosine threshold 0.25 is calibrated for cross-domain NL-to-code matching.
             Top-10 candidates per requirement selected; LLM is the quality gate.
    Stage 2: Gemini LLM reranker via call_llm_json_sync for final confirmation.

    Returns EntityLink list where from_id=CodeFunction, to_id=Requirement.
    """
    if not requirements or not functions:
        print("[resolve] WARNING: empty requirements or functions list")
        return []

    links: list[EntityLink] = []
    req_texts = [r.text for r in requirements]
    # KEY FIX: embed function NAMES only (not file paths)
    # File paths degrade cosine similarity dramatically (0.26 max vs 0.40 with names)
    fn_labels = [f.name for f in functions]
    # Keep full labels for display/evidence only
    fn_full_labels = [f"{f.file}:{f.name}" for f in functions]

    print(f"[resolve] Encoding {len(req_texts)} requirements and {len(fn_labels)} functions...")
    enc = _encoder()
    req_embeddings = enc.encode(req_texts, normalize_embeddings=True, convert_to_tensor=True)
    fn_embeddings  = enc.encode(fn_labels,  normalize_embeddings=True, convert_to_tensor=True)

    # Cosine similarity matrix: shape (len(reqs), len(fns))
    sim_matrix = st_util.cos_sim(req_embeddings, fn_embeddings)

    # Build candidate pairs: top-5 per requirement above threshold
    # Capped at 5 to stay within the Gemini free-tier daily quota (20 req/day)
    # Keyword overlap boosts ranking but is NOT a hard gate — LLM is the quality filter
    candidates: list[tuple[int, int, float, float]] = []
    for i, req in enumerate(requirements):
        scores = sim_matrix[i].tolist()
        top_idx = sorted(range(len(scores)), key=lambda x: scores[x], reverse=True)[:5]
        for j in top_idx:
            score = float(scores[j])
            if score >= cosine_threshold:
                has_overlap = _keyword_overlap(req, fn_full_labels[j])
                adjusted = score * (1.2 if has_overlap else 1.0)
                candidates.append((i, j, score, adjusted))

    # Sort by adjusted score — best pairs first
    candidates.sort(key=lambda x: x[3], reverse=True)

    if not candidates:
        print(
            f"[resolve] No candidates above cosine threshold ({cosine_threshold}). "
            "Graph will have no IMPLEMENTS edges. "
            "Blast radius will classify all changed functions as DARK_CHANGE."
        )
        return links

    print(f"[resolve] {len(candidates)} candidates for LLM reranking (or cosine-only fallback)")

    # LLM reranker in batches of 10
    # Falls back to cosine-only if quota is exhausted (429 / RuntimeError)
    COSINE_FALLBACK_THRESHOLD = 0.35  # accept without LLM if quota exhausted
    quota_exhausted = False
    batch_size = 10

    for batch_start in range(0, len(candidates), batch_size):
        batch = candidates[batch_start:batch_start + batch_size]
        prompt_items = []
        for req_idx, fn_idx, score, _adj in batch:
            req = requirements[req_idx]
            # v4 fix P0-22: use precomputed index, never functions.index()
            prompt_items.append({
                "req_id": req.requirement_id,
                "req_text": req.text,
                "fn_id": functions[fn_idx].function_id,
                "fn_label": fn_full_labels[fn_idx],
                "cosine_score": round(score, 3),
            })

        if quota_exhausted:
            # Quota exhausted — accept high-confidence cosine-only matches directly
            for req_idx, fn_idx, score, _adj in batch:
                if score >= COSINE_FALLBACK_THRESHOLD:
                    req = requirements[req_idx]
                    links.append(EntityLink(
                        from_id=functions[fn_idx].function_id,
                        to_id=req.requirement_id,
                        rel_type="IMPLEMENTS",
                        confidence=round(score, 3),
                        evidence=f"cosine-only fallback (LLM quota exhausted); score={score:.3f}",
                        source="cosine_only",
                        run_id=run_id,
                    ))
            continue

        prompt = (
            "You are reviewing candidate requirement-to-code mappings for Documenso, "
            "a document signing SaaS platform (TypeScript/Node.js). "
            "Functions include tRPC procedures, lib/server-only business logic for "
            "documents, envelopes, recipients, attachments, permissions, and webhooks.\n\n"
            "For each candidate pair, decide if the function plausibly IMPLEMENTS the "
            "requirement. A positive match requires a logical functional relationship — "
            "shared vocabulary alone is NOT sufficient.\n\n"
            'Return ONLY a JSON array. Each element must have:\n'
            '  "req_id": string\n'
            '  "fn_id": string\n'
            '  "confirmed": boolean\n'
            '  "confidence": float (0.0-1.0)\n'
            '  "reason": string (one sentence, < 20 words)\n\n'
            f"Candidates:\n{json.dumps(prompt_items, indent=2)}"
        )

        try:
            results = call_llm_json(prompt)
            if not isinstance(results, list):
                print(f"[resolve] WARNING: LLM returned non-list: {type(results)}. Skipping batch.")
                continue
        except (ValueError, RuntimeError) as e:
            err_str = str(e)
            if "429" in err_str or "quota" in err_str.lower() or "RESOURCE_EXHAUSTED" in err_str:
                print(
                    f"[resolve] LLM quota exhausted (429). "
                    f"Switching to cosine-only fallback (threshold={COSINE_FALLBACK_THRESHOLD})."
                )
                quota_exhausted = True
                # Process this batch under cosine-only immediately
                for req_idx, fn_idx, score, _adj in batch:
                    if score >= COSINE_FALLBACK_THRESHOLD:
                        req = requirements[req_idx]
                        links.append(EntityLink(
                            from_id=functions[fn_idx].function_id,
                            to_id=req.requirement_id,
                            rel_type="IMPLEMENTS",
                            confidence=round(score, 3),
                            evidence=f"cosine-only fallback (LLM quota exhausted); score={score:.3f}",
                            source="cosine_only",
                            run_id=run_id,
                        ))
            else:
                print(f"[resolve] LLM reranker error: {e}. Skipping batch.")
            continue

        for result in results:
            if not result.get("confirmed"):
                continue
            confidence = float(result.get("confidence", 0.5))
            if confidence < llm_rerank_threshold:
                continue
            # v4 fix P0-21: IMPLEMENTS = CodeFunction -> Requirement
            links.append(EntityLink(
                from_id=result["fn_id"],
                to_id=result["req_id"],
                rel_type="IMPLEMENTS",
                confidence=confidence,
                evidence=result.get("reason", "LLM reranker confirmed"),
                source="cosine_sim+llm",
                run_id=run_id,
            ))

    llm_count = sum(1 for l in links if l.source == "cosine_sim+llm")
    cosine_count = sum(1 for l in links if l.source == "cosine_only")
    print(f"[resolve] {len(links)} IMPLEMENTS links: {llm_count} LLM-confirmed, {cosine_count} cosine-only")
    return links


def resolve_ui_to_functions(
    snapshots: list[PageSnapshot],
    functions: list[CodeFunction],
    *,
    run_id: str = "v1",
) -> list[EntityLink]:
    """
    Match CodeFunction files to Pages via URL path segment matching.
    Creates RENDERS edges: CodeFunction → Page.

    v4 fix: Page node IDs use 'page:{sha}' format to match UPSERT_PAGE in writer.py.
    """
    links: list[EntityLink] = []

    for snap in snapshots:
        # Extract meaningful route segments (skip short/generic ones)
        raw_path = snap.url.split("//", 1)[-1]          # strip scheme
        raw_path = raw_path.split("/", 1)[-1] if "/" in raw_path else ""  # strip host
        route_parts = [
            p for p in raw_path.rstrip("/").split("/")
            if p and len(p) >= 4 and p not in _STOPWORDS
        ]
        if not route_parts:
            continue

        page_id = f"page:{snap.url_sha256}"  # must match UPSERT_PAGE

        for fn in functions:
            for part in route_parts:
                if part.lower() in fn.file.lower():
                    links.append(EntityLink(
                        from_id=fn.function_id,
                        to_id=page_id,
                        rel_type="RENDERS",
                        confidence=0.70,
                        evidence=f"URL segment '{part}' in file path '{fn.file}'",
                        source="url_pattern",
                        run_id=run_id,
                    ))
                    break  # one RENDERS per function per page

    print(f"[resolve] {len(links)} RENDERS links (URL segment pattern)")
    return links
