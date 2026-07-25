"""
blast_radius/fusion/mapper.py -- Absence detection for the full three-type taxonomy.

Implements:
  Type 1: UI-Absent Requirements   -- requirements with no matching UIComponent in any page
  Type 2: Dark Code functions       -- changed code with no traceable path to UI or Requirement
  Type 3: Orphaned UI components    -- interactive UI elements with no covering Requirement

run_fusion() is the single entry point. It computes all three lists and persists
outputs/requirements/fusion_candidates.json.

LLM usage: only in detect_ui_absent_requirements() for absence-type classification.
Import: from blast_radius.llm import call_llm_json_sync as call_llm_json  (sync, phase 4).

v1: initial implementation
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional

from blast_radius.llm import call_llm_json_sync as call_llm_json
from blast_radius.models import Requirement, EntityLink

logger = logging.getLogger(__name__)

# -- Type aliases --------------------------------------------------------------

# PageAnalysis comes from crawl/page_analysis.py (dataclass, not Pydantic).
# We accept duck-typed objects (real PageAnalysis or plain dicts from JSON).
PageAnalysis = Any          # has .url, .title, .ui_components, .requires_auth
RelationshipCandidate = EntityLink  # IMPLEMENTS / COVERS candidates from resolve.py

# -- Stopwords (shared with resolve.py) ---------------------------------------
_STOPWORDS = {
    "page", "component", "module", "function", "service", "handler",
    "type", "interface", "model", "schema", "data", "item",
    "list", "user", "get", "set", "create", "update", "delete",
    "button", "with", "this", "that", "from", "have", "will",
    "their", "there", "here", "when", "what", "which", "some",
}
_ENGLISH_STOPWORDS = {
    "a", "an", "the", "and", "or", "but", "if", "then", "else", "when", "at", "by", "for", "with",
    "about", "against", "between", "into", "through", "during", "before", "after", "above", "below",
    "to", "from", "up", "upon", "down", "in", "out", "on", "off", "over", "under", "again", "further",
    "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each",
    "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so",
    "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now", "is", "are", "was",
    "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing",
    "documenso", "document", "documents", "user", "users", "page", "app", "application"
}
_ALL_STOPWORDS = _STOPWORDS | _ENGLISH_STOPWORDS


_FEATURE_REQ_TYPES = {"feature", "user_story"}

# -- Result dataclasses --------------------------------------------------------

@dataclass
class AbsentRequirement:
    """A requirement that has no UIComponent match after fusion."""
    id: str                    # f"ABSENT-{req.requirement_id}"
    requirement_id: str
    absence_type: str          # NOT_CRAWLED | NOT_IMPLEMENTED | AUTH_GATED | UNKNOWN
    reason: str
    confidence: float = 0.90
    evidence: str = ""
    closest_page_url: str = ""


# -- Internal helpers ----------------------------------------------------------

def _extract_ui_words(page_analyses: list[PageAnalysis]) -> dict[str, set[str]]:
    """
    Build a mapping of {page_url -> set of meaningful words} from all ui_components.

    Handles both string components (legacy crawl format) and dict components
    (PageAnalysis LLM-enriched format with label/purpose fields).
    """
    page_vocab: dict[str, set[str]] = {}
    for pa in page_analyses:
        url = getattr(pa, "url", None) or (pa.get("url") if isinstance(pa, dict) else "")
        if not url:
            continue
        words: set[str] = set()
        # Add URL path words
        path = url.split("//", 1)[-1]
        path = path.split("/", 1)[-1] if "/" in path else ""
        words |= set(re.findall(r"\b[a-z]{3,}\b", path.lower())) - _STOPWORDS

        comps = getattr(pa, "ui_components", None)
        if comps is None and isinstance(pa, dict):
            comps = pa.get("ui_components", [])
        if not isinstance(comps, list):
            comps = []

        for comp in comps:
            if isinstance(comp, str):
                # Legacy format: plain string label
                words |= set(re.findall(r"\b[a-z]{3,}\b", comp.lower())) - _STOPWORDS
            elif isinstance(comp, dict):
                # LLM-enriched format: {label, purpose, type, is_interactive, ...}
                label = comp.get("label", "") or ""
                purpose = comp.get("purpose", "") or ""
                combined = f"{label} {purpose}"
                words |= set(re.findall(r"\b[a-z]{3,}\b", combined.lower())) - _STOPWORDS

        page_vocab[url] = words
    return page_vocab


def _req_keywords(req: Requirement) -> set[str]:
    """Extract all meaningful words from a requirement's text + ui keywords."""
    words = set(re.findall(r"\b[a-z]{4,}\b", req.text.lower())) - _STOPWORDS
    for kw in req.related_ui_keywords:
        words |= set(re.findall(r"\b[a-z]{3,}\b", kw.lower())) - _STOPWORDS
    return words


_llm_quota_exhausted = False

def _classify_absence_rule_based(req: Requirement, page_analyses: list) -> tuple[str, str]:
    """
    Classify absence type without LLM calls.

    Classify absence type without LLM calls.
    Rules based on requirement content + available pages.
    """
    req_text = (req.title + " " + req.text).lower()

    # AUTH_GATED: features that require login to access
    auth_keywords = ["admin", "team", "organisation", "billing",
                     "subscription", "enterprise", "sso", "saml"]
    matched_auth = [kw for kw in auth_keywords if kw in req_text]
    if matched_auth:
        return ("AUTH_GATED",
                f"Requirement mentions auth-gated feature: {matched_auth[:2]}")

    # NOT_CRAWLED: feature exists in app but page wasn't crawled
    # Check if any page URL suggests this area exists
    page_urls = []
    for p in page_analyses:
        url = getattr(p, "url", None) or (p.get("url") if isinstance(p, dict) else "")
        if url:
            page_urls.append(url)

    area_indicators = {
        "signing": "/sign",
        "embed": "/embed",
        "public": "/p/",
        "certificate": "/certificate",
    }
    for area, url_hint in area_indicators.items():
        if area in req_text and not any(url_hint in u for u in page_urls):
            return ("NOT_CRAWLED",
                    f"Feature area '{area}' not crawled (no page URL contains '{url_hint}')")

    # NOT_IMPLEMENTED: explicitly marked as coming soon or planned
    planned_keywords = ["coming soon", "planned", "roadmap", "future", "beta"]
    if any(kw in req_text for kw in planned_keywords):
        return ("NOT_IMPLEMENTED",
                "Requirement references planned/future functionality")

    # Default: UNKNOWN but with useful context
    return ("UNKNOWN",
            f"No UI component or API endpoint matches requirement: '{req.title[:60]}'")


def _find_closest_page(req: Requirement, page_analyses: list):
    """Find the page most likely to contain this requirement if it existed."""
    req_words = set((req.title + " " + req.text).lower().split())
    best_page = None
    best_score = -1
    for page in page_analyses:
        url = getattr(page, "url", None) or (page.get("url") if isinstance(page, dict) else "")
        page_title = getattr(page, "title", None) or (page.get("title", "") if isinstance(page, dict) else "")
        page_words = set(url.lower().replace("/", " ").replace("-", " ").replace("_", " ").split())
        if page_title:
            page_words.update(page_title.lower().split())
        score = len(req_words & page_words)
        if score > best_score:
            best_score = score
            best_page = page
    return best_page


# -- Type 1: UI-Absent Requirements -------------------------------------------

def detect_ui_absent_requirements(
    requirements: list[Requirement],
    page_analyses: list[PageAnalysis],
    existing_implements_candidates: list[RelationshipCandidate],
    api_endpoints: list[dict] = None,
    driver = None,
) -> list[AbsentRequirement]:
    """
    A requirement is UI-absent if ALL of the following hold:
      1. req_type in ["feature", "user_story"] (not constraint or api_capability)
      2. Zero IMPLEMENTS candidates exist after fusion
      3. Zero keyword overlap with ANY crawled page UI components (< 2 matching words)
      4. Zero keyword overlap with ANY APIEndpoint path or description (< 2 matching words)
      5. The requirement is not already covered by a UserFlow via COVERS edge in Neo4j
    """
    # 1. Load existing COVERS edges from Neo4j to exclude already-covered reqs
    covered_req_ids = set()
    if driver:
        try:
            with driver.session() as session:
                result = session.run("""
                    MATCH (f:UserFlow)-[:COVERS]->(r:Requirement)
                    RETURN r.id AS req_id
                """)
                covered_req_ids = {r["req_id"] for r in result if r.get("req_id")}
        except Exception as exc:
            logger.debug("[fusion] Could not fetch UserFlow COVERS edges: %s", exc)

    # 2. Also exclude reqs covered by APIEndpoints
    api_covered = set()
    if api_endpoints:
        for ep in api_endpoints:
            ep_path = ep.get("path", "") if isinstance(ep, dict) else getattr(ep, "path", "")
            ep_desc = ep.get("description", "") if isinstance(ep, dict) else getattr(ep, "description", "")
            ep_text = (ep_path + " " + ep_desc).lower()
            ep_words = set(ep_text.split())
            for req in requirements:
                req_text = (req.title + " " + req.text).lower()
                overlap = len(set(req_text.split()) & ep_words)
                if overlap >= 2:
                    req_id = getattr(req, "requirement_id", None) or getattr(req, "id", None)
                    if req_id:
                        api_covered.add(req_id)

    # 3. Build UI vocabulary from crawled pages
    ui_vocab = set()
    for page in page_analyses:
        comps = getattr(page, "ui_components", None)
        if comps is None and isinstance(page, dict):
            comps = page.get("ui_components", [])
        if isinstance(comps, list):
            for comp in comps:
                label = comp if isinstance(comp, str) else (comp.get("label", "") if isinstance(comp, dict) else getattr(comp, "label", ""))
                if label:
                    words = set(re.findall(r"\b[a-z]{3,}\b", label.lower())) - _ALL_STOPWORDS
                    ui_vocab.update(words)

    absent: list[AbsentRequirement] = []

    for req in requirements:
        req_id = getattr(req, "requirement_id", None) or getattr(req, "id", None)

        # Gate 1: Only feature / user_story requirement types
        if req.req_type not in ("feature", "user_story"):
            continue

        # Gate 2: Skip if already covered by UserFlow
        if req_id in covered_req_ids:
            continue

        # Gate 3: Skip if already covered by API endpoint
        if req_id in api_covered:
            continue

        # Gate 4: Skip if has IMPLEMENTS candidates
        has_impl = any(
            (c.to_id == req_id or getattr(c, "to_id", None) == req_id)
            for c in existing_implements_candidates
        )
        if has_impl:
            continue

        # Gate 5: Check UI keyword overlap (need < 2 matching words)
        req_words = set(re.findall(r"\b[a-z]{3,}\b", (req.title + " " + req.text).lower())) - _ALL_STOPWORDS
        overlap = len(req_words & ui_vocab)
        if overlap >= 2:
            continue


        # Rule-based absence classification
        absence_type, reason = _classify_absence_rule_based(req, page_analyses)

        # Find closest page for MISSING_FROM edge
        closest_page = _find_closest_page(req, page_analyses)
        closest_url = ""
        if closest_page:
            closest_url = getattr(closest_page, "url", None) or (closest_page.get("url") if isinstance(closest_page, dict) else "")

        evidence = (
            f"req_type={req.req_type}; no IMPLEMENTS link; UI overlap={overlap}; "
            f"closest_page={closest_url}"
        )

        absent.append(AbsentRequirement(
            id=f"ABSENT-{req_id}",
            requirement_id=req_id,
            absence_type=absence_type,
            reason=reason,
            confidence=0.90,
            evidence=evidence,
            closest_page_url=closest_url,
        ))

    logger.info("[fusion] Type 1 absent requirements: %d", len(absent))
    return absent



# -- Type 2: Dark Code Functions -----------------------------------------------

def detect_dark_code_functions(
    changed_functions: list[str],
    driver,  # Neo4j driver -- caller passes None if Neo4j is down
) -> list[dict]:
    """
    For each changed function name/id, check if there is ANY path of length <= 5
    from that CodeFunction to any Page or Requirement node.

    Cypher checks:
      - Is there a RENDERS path from this function to any Page? (UI coverage)
      - Is there an IMPLEMENTS path from this function to any Requirement? (req coverage)

    A "dark change" has NO traceable UI or requirement coverage.
    Returns list of finding dicts. Returns [] if driver is None (soft failure).
    """
    if driver is None:
        logger.debug("[fusion] No Neo4j driver -- skipping dark code detection")
        return []

    # Note: we check the ABSENCE of coverage paths, not the presence.
    # We run two OPTIONAL MATCH queries to gather any existing coverage.
    _DARK_CYPHER = """
    MATCH (f:CodeFunction)
    WHERE f.name = $name OR f.id = $name
    OPTIONAL MATCH (f)-[:RENDERS*1..3]->(p:Page)
    OPTIONAL MATCH (f)-[:IMPLEMENTS*1..3]->(r:Requirement)
    WITH f, collect(DISTINCT p) AS pages, collect(DISTINCT r) AS reqs
    WHERE size(pages) = 0 AND size(reqs) = 0
    RETURN f.name AS fn_name, f.file AS file_path, f.id AS fn_id
    """

    findings: list[dict] = []
    for fn_name in changed_functions:
        if not fn_name:
            continue
        try:
            with driver.session() as session:
                result = session.run(_DARK_CYPHER, {"name": fn_name})
                records = result.data()
                for rec in records:
                    findings.append({
                        "function_name": rec.get("fn_name", fn_name),
                        "file_path": rec.get("file_path", "unknown"),
                        "function_id": rec.get("fn_id", fn_name),
                        "dark_change": True,
                        "risk": "UNKNOWN -- no UI or requirement coverage found",
                        "recommendation": "Manual review required",
                    })
        except Exception as exc:
            logger.warning("[fusion] Dark code query failed for %s: %s", fn_name, exc)

    logger.info("[fusion] Type 2 dark code functions: %d / %d changed", len(findings), len(changed_functions))
    return findings


# -- Type 3: Orphaned UI Components -------------------------------------------

def detect_orphaned_ui_components(
    page_analyses: list[PageAnalysis],
    requirements: list[Requirement],
    existing_implements_candidates: list[RelationshipCandidate],
) -> list[dict]:
    """
    A UIComponent is orphaned if no Requirement covers it.

    Strategy:
      - For each interactive component in the page analyses, check whether any
        requirement shares meaningful keyword overlap with that component's label.
      - "Interactive" = a component whose label or type suggests actionability.
        (For string-only components we use a heuristic hint classifier.)

    Returns list of {component_label, page_url, type, reason}.
    """
    # Build per-requirement keyword set once
    req_kw_sets: list[tuple[str, set[str]]] = [
        (req.requirement_id, _req_keywords(req))
        for req in requirements
    ]
    # All requirement words combined (for fast pruning)
    all_req_words: set[str] = set()
    for _, kws in req_kw_sets:
        all_req_words |= kws

    _INTERACTIVE_ROLES = {
        "button", "input", "form", "select", "textarea", "modal",
        "dropdown", "checkbox", "radio", "link", "tab",
    }
    _INTERACTIVE_LABEL_HINTS = {
        "button", "input", "submit", "upload", "download", "create",
        "delete", "edit", "sign", "send", "invite", "add", "remove",
        "save", "cancel", "confirm", "approve", "reject", "accept",
        "search", "filter", "export", "import", "share", "copy",
    }

    def _is_interactive(comp: Any) -> bool:
        """Return True if the component appears user-interactive."""
        if isinstance(comp, str):
            label_lower = comp.lower()
            return any(hint in label_lower for hint in _INTERACTIVE_LABEL_HINTS)
        elif isinstance(comp, dict):
            if comp.get("is_interactive"):
                return True
            role = (comp.get("type") or comp.get("role") or "").lower()
            if role in _INTERACTIVE_ROLES:
                return True
            label_lower = (comp.get("label") or "").lower()
            return any(hint in label_lower for hint in _INTERACTIVE_LABEL_HINTS)
        return False

    def _comp_label(comp: Any) -> str:
        if isinstance(comp, str):
            return comp
        elif isinstance(comp, dict):
            return comp.get("label") or comp.get("name") or str(comp)
        return str(comp)

    def _comp_type(comp: Any) -> str:
        if isinstance(comp, dict):
            return comp.get("type") or comp.get("role") or "element"
        return "element"

    orphaned: list[dict] = []
    seen: set[tuple[str, str]] = set()  # (label, url) dedup

    for pa in page_analyses:
        url = getattr(pa, "url", None) or (pa.get("url") if isinstance(pa, dict) else "")
        comps = getattr(pa, "ui_components", None)
        if comps is None and isinstance(pa, dict):
            comps = pa.get("ui_components", [])
        if not isinstance(comps, list):
            continue

        for comp in comps:
            if not _is_interactive(comp):
                continue

            label = _comp_label(comp)
            key = (label, url)
            if key in seen:
                continue
            seen.add(key)

            comp_words = set(re.findall(r"\b[a-z]{3,}\b", label.lower())) - _STOPWORDS

            # Fast prune: any overlap with any requirement?
            if not (comp_words & all_req_words):
                orphaned.append({
                    "component_label": label,
                    "page_url": url,
                    "type": _comp_type(comp),
                    "reason": "No requirement covers this component",
                })
                continue

            # Fine-grained check: need >= 1 req with >= 1 word overlap
            covered = False
            for _req_id, req_kws in req_kw_sets:
                if comp_words & req_kws:
                    covered = True
                    break
            if not covered:
                orphaned.append({
                    "component_label": label,
                    "page_url": url,
                    "type": _comp_type(comp),
                    "reason": "No requirement covers this component",
                })

    logger.info("[fusion] Type 3 orphaned UI components: %d", len(orphaned))
    return orphaned


# -- run_fusion -- single entry point ------------------------------------------

def _load_page_analyses_from_outputs() -> list[Any]:
    """
    Load PageAnalysis dicts from outputs/crawl/*.json (or data/crawl/*.json).
    Handles both individual page JSON files and the summary.json list.
    """
    from blast_radius.config import settings
    candidates = [
        settings.data_dir.parent / "outputs" / "crawl",
        settings.data_dir / "crawl",
        Path("outputs/crawl"),
        Path("data/crawl"),
    ]
    analyses: list[dict] = []
    for crawl_dir in candidates:
        crawl_path = Path(crawl_dir)
        if not crawl_path.is_dir():
            continue

        # Try summary.json first (it has all pages in one list)
        summary_path = crawl_path / "summary.json"
        if summary_path.exists():
            try:
                data = json.loads(summary_path.read_text(encoding="utf-8"))
                if isinstance(data, list):
                    analyses.extend(d for d in data if isinstance(d, dict) and "url" in d)
            except Exception:
                pass

        # Also scan individual page JSONs for anything not in summary
        for json_file in sorted(crawl_path.glob("*.json")):
            if json_file.name in ("summary.json", "manifest.json"):
                continue
            try:
                data = json.loads(json_file.read_text(encoding="utf-8"))
                if isinstance(data, dict) and "url" in data:
                    analyses.append(data)
            except Exception:
                pass

        if analyses:
            break

    # Deduplicate by URL (keep first occurrence)
    seen: set[str] = set()
    deduped: list[dict] = []
    for pa in analyses:
        url = pa.get("url", "")
        if url and url not in seen:
            seen.add(url)
            deduped.append(pa)

    logger.info("[fusion] Loaded %d page analyses from disk", len(deduped))
    return deduped



# -- map_requirements_to_ui_v2 -------------------------------------------------

def _get_page_entities(page_analyses: list[PageAnalysis]) -> dict[str, list[dict]]:
    """
    Build {page_url -> list of UIElement-like dicts} from page analyses.
    Each element dict has: id, label, role, page_url, page_entity
    """
    result: dict[str, list[dict]] = {}
    for pa in page_analyses:
        url = getattr(pa, "url", None) or (pa.get("url") if isinstance(pa, dict) else "")
        entity = getattr(pa, "documenso_entity", None) or (pa.get("documenso_entity", "general") if isinstance(pa, dict) else "general")
        comps = getattr(pa, "ui_components", None)
        if comps is None and isinstance(pa, dict):
            comps = pa.get("ui_components", [])
        if not isinstance(comps, list) or not url:
            continue

        elements = []
        for idx, comp in enumerate(comps):
            if isinstance(comp, str):
                label = comp
                role = "element"
            elif isinstance(comp, dict):
                label = comp.get("label") or comp.get("name") or ""
                role = comp.get("type") or comp.get("role") or "element"
            else:
                continue
            # Build synthetic ID that matches write_ui_elements in writer.py
            import hashlib
            sha = getattr(pa, "url_sha256", None) or (pa.get("url_sha256") if isinstance(pa, dict) else None)
            if not sha:
                sha = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
            elem_id = f"ui:{sha}:{idx}"
            elements.append({"id": elem_id, "label": label, "role": role,
                             "page_url": url, "page_entity": entity})
        result[url] = elements
    return result


def _llm_match_ui_to_req(
    req: Requirement,
    page_url: str,
    component_labels: list[str],
) -> tuple[Optional[int], float, str]:
    """
    Tier 3: Ask the LLM which component on this page most directly implements
    the requirement. Returns (best_component_index, confidence, reason) or
    (None, 0, reason) if no match.
    """
    global _llm_quota_exhausted
    if _llm_quota_exhausted:
        return None, 0.0, "LLM quota exhausted"

    prompt = (
        "You are matching a Documenso requirement to UI components on a page.\n\n"
        f"Requirement: {req.text[:300]}\n"
        f"UI keywords: {req.related_ui_keywords[:6]}\n"
        f"Page URL: {page_url}\n"
        f"Components on this page (0-indexed):\n"
        + "\n".join(f"  {i}: {lbl}" for i, lbl in enumerate(component_labels[:20]))
        + "\n\nWhich component MOST DIRECTLY implements the requirement? "
        "If none clearly does, say null.\n"
        'Respond ONLY as JSON: {"index": <int or null>, "confidence": <0.0-1.0>, '
        '"reason": "<one sentence>"}'
    )
    try:
        result = call_llm_json(prompt)
        if isinstance(result, dict):
            idx = result.get("index")
            conf = float(result.get("confidence", 0.55))
            reason = result.get("reason", "LLM semantic match")
            if idx is not None:
                return int(idx), min(conf, 0.55), reason  # cap at 0.55 for LLM tier
    except Exception as exc:
        err_str = str(exc)
        if "429" in err_str or "quota" in err_str.lower() or "RESOURCE_EXHAUSTED" in err_str:
            _llm_quota_exhausted = True
            logger.warning("[fusion] LLM quota exhausted in map_requirements_to_ui_v2. Skipping LLM tier.")
        else:
            logger.debug("[fusion] LLM UI match failed for req %s: %s", req.requirement_id, exc)
    return None, 0.0, "No LLM match"


def map_requirements_to_ui_v2(
    requirements: list[Requirement],
    page_analyses: list[PageAnalysis],
) -> list[EntityLink]:
    """
    Four-tier UIElement -> Requirement IMPLEMENTS candidates with grounded evidence.

    TIER 1 -- Exact multi-keyword match (confidence 0.90):
      2+ of req.related_ui_keywords appear as whole words in component label.
      Evidence: lists all matching keywords and the exact component label.

    TIER 2 -- Single keyword match (confidence 0.70):
      Exactly 1 keyword matches. Useful but not conclusive.

    TIER 3 -- Page-level feature_area match (confidence 0.65):
      req.feature_area matches page.documenso_entity AND req text words
      overlap with any component label on that page (>=1 word).

    TIER 4 -- LLM semantic match (confidence capped at 0.55, flagged):
      Batched LLM call for requirements that matched no UI by keywords.
      LLM must provide a specific component label and reason.

    Returns list[EntityLink] with rel_type='UI_IMPLEMENTS' (written via
    CREATE_UI_IMPLEMENTS in schema.py: UIElement -> Requirement).
    """
    # Build per-page element lists
    page_elements = _get_page_entities(page_analyses)
    all_elements = [el for els in page_elements.values() for el in els]

    candidates: list[EntityLink] = []
    unmatched_reqs: list[Requirement] = []  # for LLM tier

    for req in requirements:
        if req.req_type not in _FEATURE_REQ_TYPES:
            continue  # skip constraints / api_capability reqs

        req_kw_lower = [kw.lower() for kw in req.related_ui_keywords if kw.strip()]
        req_text_words = set(re.findall(r"\b[a-z]{4,}\b", req.text.lower())) - _STOPWORDS
        matched_this_req = False

        for el in all_elements:
            label = el["label"]
            if not label:
                continue
            label_lower = label.lower()
            # Tokenise label for whole-word matching
            label_words = set(re.findall(r"\b[a-z]{3,}\b", label_lower))

            # -- TIER 1: 2+ keyword exact match ----------------------------
            keyword_matches = [
                kw for kw in req_kw_lower
                if any(w in label_words for w in re.findall(r"\b[a-z]{3,}\b", kw))
            ]
            if len(keyword_matches) >= 2:
                candidates.append(EntityLink(
                    from_id=el["id"],
                    to_id=req.requirement_id,
                    rel_type="UI_IMPLEMENTS",
                    confidence=0.90,
                    evidence=(
                        f"Exact keyword match: {keyword_matches[:5]} found in "
                        f"component label '{label}' (page: {el['page_url']})"
                    ),
                    source="keyword_match_exact",
                ))
                matched_this_req = True
                continue

            # -- TIER 2: single keyword match --------------------------------
            if len(keyword_matches) == 1:
                candidates.append(EntityLink(
                    from_id=el["id"],
                    to_id=req.requirement_id,
                    rel_type="UI_IMPLEMENTS",
                    confidence=0.70,
                    evidence=(
                        f"Single keyword match: '{keyword_matches[0]}' found in "
                        f"component label '{label}' (page: {el['page_url']})"
                    ),
                    source="keyword_match_single",
                ))
                matched_this_req = True
                continue

        # -- TIER 3: page feature_area match ------------------------------
        if not matched_this_req:
            feature_area = getattr(req, "feature_area", "") or ""
            for page_url, elements in page_elements.items():
                if not elements:
                    continue
                page_entity = elements[0].get("page_entity", "")
                if feature_area and page_entity == feature_area:
                    # Pick the element on this page whose label overlaps most with req text
                    best_el = None
                    best_overlap = 0
                    for el in elements:
                        if not el["label"]:
                            continue
                        el_words = set(re.findall(r"\b[a-z]{4,}\b", el["label"].lower())) - _STOPWORDS
                        overlap = len(el_words & req_text_words)
                        if overlap > best_overlap:
                            best_overlap = overlap
                            best_el = el
                    if best_el and best_overlap >= 1:
                        candidates.append(EntityLink(
                            from_id=best_el["id"],
                            to_id=req.requirement_id,
                            rel_type="UI_IMPLEMENTS",
                            confidence=0.65,
                            evidence=(
                                f"Page feature_area match: req.feature_area='{feature_area}' "
                                f"== page.entity='{page_entity}'; best component: "
                                f"'{best_el['label']}' (overlap words: {best_overlap})"
                            ),
                            source="page_level_match",
                        ))
                        matched_this_req = True
                        break

        if not matched_this_req:
            unmatched_reqs.append(req)

    # -- TIER 4: LLM semantic match for still-unmatched reqs ---------------
    global _llm_quota_exhausted
    if not _llm_quota_exhausted and unmatched_reqs:
        logger.info("[fusion] Tier 4 LLM matching for %d unmatched reqs", len(unmatched_reqs))
        for req in unmatched_reqs:
            # Try each page that has elements
            for page_url, elements in page_elements.items():
                comp_labels = [el["label"] for el in elements if el["label"]]
                if not comp_labels:
                    continue
                idx, conf, reason = _llm_match_ui_to_req(req, page_url, comp_labels)
                if idx is not None and 0 <= idx < len(elements):
                    el = elements[idx]
                    candidates.append(EntityLink(
                        from_id=el["id"],
                        to_id=req.requirement_id,
                        rel_type="UI_IMPLEMENTS",
                        confidence=conf,
                        evidence=f"LLM semantic match (flagged for review): {reason}",
                        source="llm_semantic",
                    ))
                    break  # one LLM match per requirement

    tier_counts: dict[str, int] = {}
    for link in candidates:
        tier_counts[link.source] = tier_counts.get(link.source, 0) + 1
    logger.info(
        "[fusion] map_requirements_to_ui_v2: %d total UI_IMPLEMENTS candidates: %s",
        len(candidates), tier_counts
    )
    return candidates


def run_fusion(
    requirements: list[Requirement],
    page_analyses: list[Any],
    code_model: dict,
    driver=None,
) -> dict:
    """
    Single entry point for the fusion layer.

    Computes UIElement->Requirement IMPLEMENTS candidates (tiered) plus all three
    absence types, and saves outputs/requirements/fusion_candidates.json.

    Args:
        requirements:   Phase 2 Requirement objects
        page_analyses:  Phase 1 PageAnalysis objects or plain dicts; auto-loaded if empty
        code_model:     Phase 3 code model dict; key "functions" = list of names or CodeFunction objs
        driver:         Optional Neo4j driver for Type 2 dark code detection (None = skip)

    Returns:
        {
          "req_ui": list[EntityLink],    # UIElement->Requirement IMPLEMENTS (tiered)
          "ui_code": [],
          "absent": list[AbsentRequirement],
          "dark_code": list[dict],
          "orphaned_ui": list[dict],
        }
    """
    # Auto-load page analyses from disk if none supplied or if supplied objects lack ui_components
    has_ui_comps = False
    if page_analyses:
        first = page_analyses[0]
        if isinstance(first, dict) and "ui_components" in first:
            has_ui_comps = True
        elif getattr(first, "ui_components", None) is not None:
            has_ui_comps = True

    if not page_analyses or not has_ui_comps:
        logger.info("[fusion] Loading rich page analyses with ui_components from outputs/crawl/")
        page_analyses = _load_page_analyses_from_outputs()

    # -- Tiered UIElement->Requirement IMPLEMENTS candidates ------------------
    ui_implements = map_requirements_to_ui_v2(requirements, page_analyses)
    # Pass as implements_candidates so absence detection sees what IS matched
    implements_candidates: list[EntityLink] = ui_implements

    api_endpoints = code_model.get("api_endpoints", []) or code_model.get("endpoints", [])
    # -- Type 1: UI-Absent Requirements ----------------------------------------
    absent_reqs = detect_ui_absent_requirements(
        requirements, page_analyses, implements_candidates,
        api_endpoints=api_endpoints, driver=driver
    )


    # -- Type 2: Dark Code Functions -------------------------------------------
    changed_functions = code_model.get("functions", [])
    if isinstance(changed_functions, list) and changed_functions:
        fn_names: list[str] = []
        for fn in changed_functions:
            if isinstance(fn, str):
                fn_names.append(fn)
            elif hasattr(fn, "name"):
                fn_names.append(fn.name)
            elif isinstance(fn, dict):
                fn_names.append(fn.get("name") or fn.get("function_id") or "")
        dark_code = detect_dark_code_functions([n for n in fn_names if n], driver)
    else:
        dark_code = []

    # -- Type 3: Orphaned UI Components ----------------------------------------
    orphaned_ui = detect_orphaned_ui_components(
        page_analyses, requirements, implements_candidates
    )

    # -- Console summary -------------------------------------------------
    tier_counts: dict[str, int] = {}
    for link in ui_implements:
        tier_counts[link.source] = tier_counts.get(link.source, 0) + 1

    print(f"[fusion] UIElement->Req IMPLEMENTS: {len(ui_implements)}")
    for src in ("keyword_match_exact", "keyword_match_single", "page_level_match", "llm_semantic"):
        n = tier_counts.get(src, 0)
        if n:
            avg_c = sum(l.confidence for l in ui_implements if l.source == src) / n
            print(f"[fusion]   {src:<28} n={n:<4} avg_conf={avg_c:.2f}")
    print(f"[fusion] Absent requirements:    {len(absent_reqs)}")
    print(f"[fusion] Dark code functions:    {len(dark_code)}")
    print(f"[fusion] Orphaned UI components: {len(orphaned_ui)}")

    n_req = len(requirements)
    n_pages = len(page_analyses)
    if n_req >= 50 and n_pages >= 20:
        if len(absent_reqs) < 8:
            print(
                f"[fusion] WARNING: only {len(absent_reqs)} absent requirements with "
                f"{n_req} reqs and {n_pages} pages -- expected >= 8"
            )
        if len(orphaned_ui) < 10:
            print(
                f"[fusion] WARNING: only {len(orphaned_ui)} orphaned UI components -- expected >= 10"
            )

    # -- Persist fusion_candidates.json ----------------------------------------
    from blast_radius.config import settings
    out_dir = settings.data_dir.parent / "outputs" / "requirements"
    out_dir.mkdir(parents=True, exist_ok=True)
    fusion_path = out_dir / "fusion_candidates.json"

    payload = {
        "ui_implements": [l.model_dump() for l in ui_implements],
        "absent_requirements": [asdict(a) for a in absent_reqs],
        "dark_code": dark_code,
        "orphaned_ui": orphaned_ui,
        "summary": {
            "n_requirements": n_req,
            "n_page_analyses": n_pages,
            "n_ui_implements": len(ui_implements),
            "n_ui_implements_by_tier": tier_counts,
            "n_absent": len(absent_reqs),
            "n_dark_code": len(dark_code),
            "n_orphaned_ui": len(orphaned_ui),
        },
    }
    fusion_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"[fusion] Saved => {fusion_path}")

    return {
        "req_ui": ui_implements,
        "ui_code": [],
        "absent": absent_reqs,
        "dark_code": dark_code,
        "orphaned_ui": orphaned_ui,
    }

