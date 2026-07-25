"""
blast_radius/models.py -- Data contracts shared across all pipeline phases.
"""
from __future__ import annotations

from typing import Any, Optional
from pydantic import BaseModel, Field


# -- Phase 1: Crawl -----------------------------------------------------------

class Transition(BaseModel):
    action: str
    selector: Optional[str] = None
    source_url: str
    target_url: str
    screenshot_before: Optional[str] = None
    screenshot_after: Optional[str] = None


class AccessibilityItem(BaseModel):
    index: int
    tag: str
    role: Optional[str] = None
    name: str = ""
    selector: str


class PageSnapshot(BaseModel):
    url: str
    url_sha256: str
    dom_snapshot: str
    accessibility_tree: list[AccessibilityItem] = Field(default_factory=list)
    screenshot_path: str = ""
    transitions: list[Transition] = Field(default_factory=list)


class CrawlManifest(BaseModel):
    run_id: str
    started_at: str
    pages: list[str] = Field(default_factory=list)
    transitions: list[Transition] = Field(default_factory=list)


# -- Phase 2: Requirements -----------------------------------------------------

class Provenance(BaseModel):
    source_file: str
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    page: Optional[int] = None
    bbox: Optional[list[float]] = None
    excerpt: str = ""


class Requirement(BaseModel):
    requirement_id: str
    text: str
    req_type: str = "feature"  # "feature"|"user_story"|"constraint"|"api_capability"
    provenance: Provenance
    related_ui_keywords: list[str] = Field(default_factory=list)
    coverage_status: str = "UNKNOWN"  # "COVERED"|"MISSING"|"UNKNOWN"

    # -- Extended Phase 2 fields (added for richer ingestion) ------------------
    title: str = ""                                      # short name, ≤ 8 words
    description: str = ""                                # full requirement text
    feature_area: str = ""                               # signing|sending|templates|
                                                         # teams|webhooks|api|auth|
                                                         # admin|notifications
    acceptance_criteria: list[str] = Field(default_factory=list)
    related_api_endpoints: list[str] = Field(default_factory=list)
    priority: str = "secondary"                          # core|secondary|nice-to-have
    source: str = ""                                     # originating doc name


# -- Phase 3: Code -------------------------------------------------------------

class CodeFunction(BaseModel):
    function_id: str
    name: str
    file: str  # normalized path relative to repo root (forward slashes)
    start_line: int
    end_line: int = 0
    signature: str = ""
    calls: list[str] = Field(default_factory=list)   # function_ids this fn calls
    called_by: list[str] = Field(default_factory=list)  # function_ids that call this fn
    ast_node_type: str = "ts-function"  # "ts-function" | "trpc-procedure"
    is_trpc_procedure: bool = False
    trpc_procedure_name: Optional[str] = None
    trpc_procedure_type: Optional[str] = None  # "query" | "mutation" | "subscription"


class PRFileDelta(BaseModel):
    path: str  # normalized path relative to repo root (forward slashes)
    status: str  # "added" | "modified" | "removed" | "renamed"
    additions: int = 0
    deletions: int = 0
    patch: Optional[str] = None


# Alias so Phase 3 code can use either name
ChangedFile = PRFileDelta


class PRDelta(BaseModel):
    pr_number: int
    title: str
    body: str = ""
    author: str = ""
    merge_sha: str
    parent_sha: str = ""
    html_url: str = ""
    pr_url: str = ""
    changed_files: list[PRFileDelta] = Field(default_factory=list)
    changed_function_ids: list[str] = Field(default_factory=list)


# -- Phase 4: Graph & Absence --------------------------------------------------

class GapNode(BaseModel):
    gap_id: str
    requirement_id: str
    requirement_text: str
    reason: str = "No CodeFunction or UIElement linked to requirement"


class EntityLink(BaseModel):
    """Represents a resolved relationship edge before writing to Neo4j."""
    from_id: str           # CodeFunction.function_id
    to_id: str             # Requirement.requirement_id  or  Page node id
    rel_type: str          # "IMPLEMENTS" | "RENDERS"
    confidence: float = 1.0
    evidence: str = ""
    source: str = ""       # "cosine_sim+llm" | "url_pattern"
    run_id: str = "v1"


# -- Phase 5 & 6: Reasoning & Report -----------------------------------------

class AffectedNode(BaseModel):
    node_id: str
    node_type: str  # "Requirement" | "UIElement" | "Page" | "CodeFunction"
    label: str
    impact_score: float  # PPR score normalized 0.0 - 1.0
    traceability_confidence: float = 1.0
    risk_tier: str = "LOW"  # "HIGH" | "MEDIUM" | "LOW"
    evidence_path: list[str] = Field(default_factory=list)  # Human-readable labels path



class BlastRadiusReport(BaseModel):
    run_id: str
    pr_number: int
    pr_title: str
    pr_url: str
    mode: str = "PR_ANALYSIS"
    summary: str = ""
    changed_files: list[PRFileDelta] = Field(default_factory=list)
    seed_function_ids: list[str] = Field(default_factory=list)
    affected_ui_elements: list[AffectedNode] = Field(default_factory=list)
    affected_requirements: list[AffectedNode] = Field(default_factory=list)
    absent_requirements: list[AffectedNode] = Field(default_factory=list)
    dark_changes: list[str] = Field(default_factory=list)
    manual_review_items: list[str] = Field(default_factory=list)
    evidence_subgraph: list[dict[str, Any]] = Field(default_factory=list)
    confidence_scores: dict[str, float] = Field(default_factory=dict)

