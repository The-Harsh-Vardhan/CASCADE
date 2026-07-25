#!/usr/bin/env python3
"""
scripts/fix_absent_requirements.py
===================================
Fix the 181 AbsentRequirement nodes in Neo4j — WITHOUT rebuilding the graph.

Steps
-----
1. Delete false positives: reqs already covered by UserFlow COVERS edges
2. Delete false positives: reqs with req_type in {constraint, api_capability}
3. Reclassify remaining nodes with rule-based classifier (no LLM)
4. Delete UNKNOWN nodes beyond the cap of 20 total AbsentRequirements
5. Verify and print final breakdown

Run from project root:
    python scripts/fix_absent_requirements.py

Prerequisites:
    Neo4j must be running (docker compose up -d)
    .env must contain NEO4J_* credentials
"""

from __future__ import annotations

import sys
import logging
from pathlib import Path

# ---------------------------------------------------------------------------
# Bootstrap: add project root to sys.path so blast_radius package is importable
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Classifier (pure function — no LLM, deterministic)
# ---------------------------------------------------------------------------

def classify(req_text: str, feature_area: str) -> tuple[str, str]:
    """
    Rule-based absence classifier.

    Returns (absence_type, reason).
    absence_type is one of: AUTH_GATED | NOT_CRAWLED | NOT_IMPLEMENTED | UNKNOWN
    """
    text = req_text.lower()

    # -- AUTH_GATED -----------------------------------------------------------
    auth_keywords = [
        "admin", "organisation", "billing", "subscription",
        "enterprise", "sso", "saml", "team",
    ]
    matched_auth = [kw for kw in auth_keywords if kw in text]
    if matched_auth:
        return (
            "AUTH_GATED",
            f"Requires authentication — mentions: {matched_auth[:2]}",
        )

    # Feature-area based AUTH_GATED
    if feature_area and feature_area.lower() in {"admin", "billing", "enterprise"}:
        return (
            "AUTH_GATED",
            f"Admin/enterprise feature requires elevated permissions (feature_area={feature_area})",
        )

    # -- NOT_CRAWLED ----------------------------------------------------------
    not_crawled_map = {
        "signing":     "/sign/",
        "certificate": "/certificate",
        "embed":       "/embed",
        "public profile": "/p/",
        "audit":       "/audit",
        "webhook":     "/webhooks",
    }
    for area, hint in not_crawled_map.items():
        if area in text:
            return (
                "NOT_CRAWLED",
                f"Feature area '{area}' exists in app but page '{hint}' was not crawled",
            )

    # Feature-area based NOT_CRAWLED
    if feature_area and feature_area.lower() in {"api", "webhook", "embed"}:
        return (
            "NOT_CRAWLED",
            f"API/programmatic capability — no UI page covers this (feature_area={feature_area})",
        )

    # -- NOT_IMPLEMENTED ------------------------------------------------------
    planned_keywords = ["coming soon", "planned", "roadmap", "future", "beta", "experimental"]
    if any(kw in text for kw in planned_keywords):
        return (
            "NOT_IMPLEMENTED",
            "References planned or future functionality",
        )

    # -- UNKNOWN (fallback) ---------------------------------------------------
    snippet = req_text[:60].strip()
    return (
        "UNKNOWN",
        f"No matching UI component found for: '{snippet}'",
    )


# ---------------------------------------------------------------------------
# Step functions
# ---------------------------------------------------------------------------

def step1_delete_userflow_covered(session) -> int:
    """
    Delete AbsentRequirements whose linked Requirement is already covered by
    a UserFlow via a COVERS edge.  These are false positives.
    """
    logger.info("Step 1: Deleting AbsentRequirements covered by UserFlow COVERS edges ...")
    result = session.run("""
        MATCH (a:AbsentRequirement)
        WHERE EXISTS {
            MATCH (r:Requirement {id: a.requirement_id})
            WHERE (:UserFlow)-[:COVERS]->(r)
        }
        WITH a, count(a) AS n
        DETACH DELETE a
        RETURN n
    """).single()
    deleted = result["n"] if result and result["n"] else 0
    logger.info("  Deleted %d nodes (UserFlow-covered false positives)", deleted)
    return deleted


def step1_delete_userflow_covered_v2(session) -> int:
    """
    Alternative approach — two-pass delete compatible with Neo4j 5.
    First count, then delete.
    """
    logger.info("Step 1: Deleting AbsentRequirements covered by UserFlow COVERS edges ...")

    # Count first
    count_result = session.run("""
        MATCH (a:AbsentRequirement)
        MATCH (r:Requirement {id: a.requirement_id})
        WHERE (:UserFlow)-[:COVERS]->(r)
        RETURN count(a) AS n
    """).single()
    to_delete = count_result["n"] if count_result else 0
    logger.info("  Found %d nodes to delete (UserFlow-covered)", to_delete)

    if to_delete > 0:
        session.run("""
            MATCH (a:AbsentRequirement)
            MATCH (r:Requirement {id: a.requirement_id})
            WHERE (:UserFlow)-[:COVERS]->(r)
            DETACH DELETE a
        """).consume()

    logger.info("  Deleted %d nodes", to_delete)
    return to_delete


def step2_delete_non_feature_types(session) -> int:
    """
    Delete AbsentRequirements for req_type = 'constraint' or 'api_capability'.
    These should never have been flagged as absent UI requirements.
    """
    logger.info("Step 2: Deleting AbsentRequirements for constraint/api_capability reqs ...")

    count_result = session.run("""
        MATCH (a:AbsentRequirement)
        MATCH (r:Requirement {id: a.requirement_id})
        WHERE r.req_type IN ["constraint", "api_capability"]
        RETURN count(a) AS n
    """).single()
    to_delete = count_result["n"] if count_result else 0
    logger.info("  Found %d nodes to delete (non-feature types)", to_delete)

    if to_delete > 0:
        session.run("""
            MATCH (a:AbsentRequirement)
            MATCH (r:Requirement {id: a.requirement_id})
            WHERE r.req_type IN ["constraint", "api_capability"]
            DETACH DELETE a
        """).consume()

    logger.info("  Deleted %d nodes", to_delete)
    return to_delete


def step3_reclassify(session) -> int:
    """
    Fetch all remaining AbsentRequirement nodes with their linked Requirement
    data and apply the rule-based classifier, writing results back to Neo4j.

    Returns the count of nodes reclassified.
    """
    logger.info("Step 3: Reclassifying remaining AbsentRequirement nodes ...")

    rows = session.run("""
        MATCH (a:AbsentRequirement)
        OPTIONAL MATCH (r:Requirement {id: a.requirement_id})
        RETURN a.id          AS absent_id,
               a.requirement_id AS req_id,
               r.title       AS title,
               r.text        AS text,
               r.req_type    AS req_type,
               r.feature_area AS feature_area
    """).data()

    logger.info("  Found %d AbsentRequirement nodes to reclassify", len(rows))

    updated = 0
    for row in rows:
        absent_id    = row["absent_id"]
        title        = (row["title"] or "")
        text         = (row["text"] or "")
        req_text     = f"{title} {text}"
        feature_area = row.get("feature_area") or ""

        absence_type, reason = classify(req_text, feature_area)

        session.run("""
            MATCH (a:AbsentRequirement {id: $id})
            SET a.absence_type = $absence_type,
                a.reason       = $reason
        """, id=absent_id, absence_type=absence_type, reason=reason).consume()

        updated += 1

    logger.info("  Reclassified %d nodes", updated)
    return updated


def step4_cap_unknowns(session, max_total: int = 20) -> int:
    """
    If the total AbsentRequirement count exceeds max_total, prune nodes in this
    priority order (least-informative first):

      1. UNKNOWN nodes (shortest reason first)
      2. Duplicate-reason nodes from the largest class (same reason text, keep one)
      3. Largest class nodes with the shortest reason strings

    Returns the total number of nodes deleted.
    """
    logger.info("Step 4: Capping AbsentRequirement count to %d ...", max_total)

    total_result = session.run(
        "MATCH (a:AbsentRequirement) RETURN count(a) AS n"
    ).single()
    total = total_result["n"] if total_result else 0
    logger.info("  Current total: %d nodes", total)

    if total <= max_total:
        logger.info("  Already at or below cap — no deletions needed")
        return 0

    deleted = 0

    # -- Pass A: prune UNKNOWN nodes first ------------------------------------
    excess = total - max_total
    unknown_result = session.run(
        "MATCH (a:AbsentRequirement) WHERE a.absence_type = 'UNKNOWN' RETURN count(a) AS n"
    ).single()
    available_unknowns = unknown_result["n"] if unknown_result else 0
    pass_a = min(excess, available_unknowns)
    logger.info("  Pass A — UNKNOWN nodes available: %d → deleting %d", available_unknowns, pass_a)

    if pass_a > 0:
        session.run("""
            MATCH (a:AbsentRequirement)
            WHERE a.absence_type = 'UNKNOWN'
            WITH a ORDER BY size(coalesce(a.reason, '')) ASC
            LIMIT $limit
            DETACH DELETE a
        """, limit=pass_a).consume()
        deleted += pass_a
        excess -= pass_a

    if excess <= 0:
        logger.info("  Deleted %d total nodes", deleted)
        return deleted

    # -- Pass B: prune duplicate-reason nodes from each class -----------------
    # Keep one representative per unique reason; delete duplicates.
    logger.info("  Pass B — pruning duplicate-reason nodes (excess=%d remaining) ...", excess)
    for absence_type in ("AUTH_GATED", "NOT_CRAWLED", "NOT_IMPLEMENTED"):
        if excess <= 0:
            break
        # Find duplicate reasons within this class
        dupes = session.run("""
            MATCH (a:AbsentRequirement)
            WHERE a.absence_type = $atype
            WITH a.reason AS reason, collect(a) AS nodes
            WHERE size(nodes) > 1
            UNWIND nodes[1..] AS dupe
            RETURN dupe.id AS id
            LIMIT $limit
        """, atype=absence_type, limit=excess).data()
        logger.info(
            "  Pass B [%s]: %d duplicate-reason nodes to delete", absence_type, len(dupes)
        )
        for row in dupes:
            if excess <= 0:
                break
            session.run(
                "MATCH (a:AbsentRequirement {id: $id}) DETACH DELETE a",
                id=row["id"],
            ).consume()
            deleted += 1
            excess -= 1

    if excess <= 0:
        logger.info("  Deleted %d total nodes", deleted)
        return deleted

    # -- Pass C: prune from largest class by shortest reason ------------------
    logger.info("  Pass C — pruning from largest class (excess=%d remaining) ...", excess)
    # Find the largest class
    largest = session.run("""
        MATCH (a:AbsentRequirement)
        RETURN a.absence_type AS atype, count(a) AS n
        ORDER BY n DESC LIMIT 1
    """).single()
    if largest:
        atype = largest["atype"]
        logger.info("  Pass C: deleting %d from largest class '%s'", excess, atype)
        session.run("""
            MATCH (a:AbsentRequirement)
            WHERE a.absence_type = $atype
            WITH a ORDER BY size(coalesce(a.reason, '')) ASC
            LIMIT $limit
            DETACH DELETE a
        """, atype=atype, limit=excess).consume()
        deleted += excess

    logger.info("  Deleted %d total nodes", deleted)
    return deleted


def step5_verify(session) -> None:
    """
    Print the final breakdown by absence_type and a sample of node details.
    """
    logger.info("Step 5: Verification")
    print("\n" + "=" * 60)
    print("  AbsentRequirement breakdown after fix")
    print("=" * 60)

    # By absence_type
    breakdown = session.run("""
        MATCH (a:AbsentRequirement)
        RETURN a.absence_type AS absence_type, count(a) AS count
        ORDER BY count DESC
    """).data()

    if not breakdown:
        print("  ⚠  No AbsentRequirement nodes remain in the graph.")
    else:
        total = sum(r["count"] for r in breakdown)
        for row in breakdown:
            at   = row["absence_type"] or "None"
            cnt  = row["count"]
            bar  = "#" * min(cnt, 20)
            print(f"  {at:<20} {cnt:>4}   {bar}")
        print(f"  {'TOTAL':<20} {total:>4}")

    # Sample details
    print("\n" + "-" * 60)
    print("  Sample nodes (up to 15):")
    print("-" * 60)
    samples = session.run("""
        MATCH (a:AbsentRequirement)
        RETURN a.id           AS id,
               a.absence_type AS absence_type,
               a.reason       AS reason
        ORDER BY a.absence_type, a.id
        LIMIT 15
    """).data()

    for s in samples:
        print(f"\n  ID:    {s['id']}")
        print(f"  Type:  {s['absence_type']}")
        print(f"  Why:   {s['reason']}")
    print("=" * 60 + "\n")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    # -- Connect ---------------------------------------------------------------
    try:
        from blast_radius.graph.writer import get_driver
    except ImportError as exc:
        logger.error(
            "Cannot import blast_radius package. Run from project root: "
            "python scripts/fix_absent_requirements.py\n  (%s)", exc
        )
        sys.exit(1)

    try:
        driver = get_driver()
        driver.verify_connectivity()
        logger.info("Neo4j connection established.")
    except Exception as exc:
        logger.error(
            "Cannot connect to Neo4j.\n"
            "Start it with:  docker compose up -d\n"
            "Details: %s", exc
        )
        sys.exit(1)

    # -- Snapshot current state ------------------------------------------------
    with driver.session() as session:
        initial = session.run(
            "MATCH (a:AbsentRequirement) RETURN count(a) AS n"
        ).single()
        initial_count = initial["n"] if initial else 0
    logger.info("Initial AbsentRequirement count: %d", initial_count)

    # -- Run steps in separate sessions (avoids transaction conflicts) ----------
    with driver.session() as session:
        deleted1 = step1_delete_userflow_covered_v2(session)

    with driver.session() as session:
        deleted2 = step2_delete_non_feature_types(session)

    with driver.session() as session:
        reclassified = step3_reclassify(session)

    with driver.session() as session:
        deleted4 = step4_cap_unknowns(session, max_total=20)

    with driver.session() as session:
        step5_verify(session)

    # -- Summary ---------------------------------------------------------------
    logger.info(
        "Done. Removed %d false positives (UserFlow) + %d non-feature type + %d excess UNKNOWNs. "
        "Reclassified %d nodes.",
        deleted1, deleted2, deleted4, reclassified,
    )

    driver.close()


if __name__ == "__main__":
    main()
