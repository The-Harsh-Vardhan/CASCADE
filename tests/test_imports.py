"""
tests/test_imports.py — Phase 0 import smoke test.
"""
def test_config_import():
    from blast_radius.config import settings
    assert settings.target_url == "https://app.documenso.com"
    assert settings.pr_number == 0  # Default before Phase 3


def test_models_import():
    from blast_radius.models import (
        PageSnapshot, Requirement, CodeFunction, PRDelta, BlastRadiusReport
    )
    req = Requirement(
        requirement_id="REQ-0001",
        text="Test requirement",
        provenance={"source_file": "README.md", "excerpt": "Test"}
    )
    assert req.requirement_id == "REQ-0001"


def test_llm_import():
    from blast_radius.llm import call_llm
    assert callable(call_llm)
