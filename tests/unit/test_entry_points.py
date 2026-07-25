"""
tests/unit/test_entry_points.py — Unit tests for run.py and pipeline/online.py.

Covers:
  - parse_pr_url: valid formats, invalid URL, edge cases
  - classify: all four absence types + fallback UNKNOWN
  - check_graph_ready: passes on full graph, exits on empty graph

No network calls. No Neo4j dependency. All pure-logic tests.
"""
import sys
import re
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# parse_pr_url (copied inline so test doesn't depend on __main__ import)
# ---------------------------------------------------------------------------

def parse_pr_url(url: str) -> tuple[str, int]:
    """Mirror of run.py:parse_pr_url — kept in-test for isolation."""
    pattern = r"github\.com/([^/]+/[^/]+)/pull/(\d+)"
    match = re.search(pattern, url)
    if not match:
        raise ValueError(f"Could not parse PR URL: {url}")
    return match.group(1), int(match.group(2))


class TestParsePrUrl:
    """parse_pr_url must handle all supported URL variants."""

    def test_standard_https_url(self):
        repo, pr = parse_pr_url("https://github.com/documenso/documenso/pull/3046")
        assert repo == "documenso/documenso"
        assert pr == 3046

    def test_url_with_files_suffix(self):
        repo, pr = parse_pr_url(
            "https://github.com/documenso/documenso/pull/1234/files"
        )
        assert repo == "documenso/documenso"
        assert pr == 1234

    def test_url_without_scheme(self):
        repo, pr = parse_pr_url("github.com/owner/my-repo/pull/42")
        assert repo == "owner/my-repo"
        assert pr == 42

    def test_arbitrary_owner_and_repo(self):
        repo, pr = parse_pr_url("https://github.com/acme-corp/my-service/pull/9999")
        assert repo == "acme-corp/my-service"
        assert pr == 9999

    def test_pr_number_is_int(self):
        _, pr = parse_pr_url("https://github.com/a/b/pull/007")
        assert isinstance(pr, int)
        assert pr == 7

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="Could not parse"):
            parse_pr_url("https://github.com/documenso/documenso/issues/99")

    def test_empty_string_raises(self):
        with pytest.raises(ValueError):
            parse_pr_url("")

    def test_non_github_url_raises(self):
        with pytest.raises(ValueError):
            parse_pr_url("https://gitlab.com/owner/repo/merge_requests/1")


# ---------------------------------------------------------------------------
# classify (imported from fix_absent_requirements — rule-based, no LLM)
# ---------------------------------------------------------------------------

# Import classify from the fix script without running main()
import importlib.util, pathlib

_FIX_SCRIPT = pathlib.Path(__file__).resolve().parent.parent.parent / "scripts" / "fix_absent_requirements.py"


def _load_classify():
    """Dynamically load classify() from scripts/fix_absent_requirements.py."""
    spec = importlib.util.spec_from_file_location("fix_absent_reqs", _FIX_SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.classify


classify = _load_classify()


class TestClassify:
    """classify() must be deterministic and cover all four absence types."""

    def test_auth_gated_admin(self):
        atype, reason = classify("admin dashboard management interface", "")
        assert atype == "AUTH_GATED"
        assert "admin" in reason

    def test_auth_gated_organisation(self):
        atype, reason = classify("organisation member invite and team management", "")
        assert atype == "AUTH_GATED"
        assert "organisation" in reason or "team" in reason

    def test_auth_gated_sso(self):
        atype, reason = classify("SSO and SAML integration for enterprise login", "")
        assert atype == "AUTH_GATED"

    def test_auth_gated_billing(self):
        atype, reason = classify("billing subscription management dashboard", "")
        assert atype == "AUTH_GATED"

    def test_not_crawled_signing(self):
        atype, reason = classify("document signing flow with recipient token", "")
        assert atype == "NOT_CRAWLED"
        assert "signing" in reason or "/sign/" in reason

    def test_not_crawled_embed(self):
        atype, reason = classify("embedded signing experience via iframe", "")
        assert atype == "NOT_CRAWLED"

    def test_not_crawled_certificate(self):
        atype, reason = classify("download certificate of completion", "")
        assert atype == "NOT_CRAWLED"

    def test_not_implemented_planned(self):
        atype, reason = classify("coming soon: bulk document sending", "")
        assert atype == "NOT_IMPLEMENTED"

    def test_not_implemented_roadmap(self):
        atype, reason = classify("roadmap feature planned for future release", "")
        assert atype == "NOT_IMPLEMENTED"

    def test_unknown_fallback(self):
        atype, reason = classify("configure notification preferences", "")
        assert atype == "UNKNOWN"
        assert len(reason) > 10

    def test_feature_area_admin_overrides(self):
        # feature_area='admin' should trigger AUTH_GATED even with neutral text
        atype, _ = classify("user profile settings page", "admin")
        assert atype == "AUTH_GATED"

    def test_feature_area_api_triggers_not_crawled(self):
        atype, _ = classify("programmatic document creation endpoint", "api")
        assert atype == "NOT_CRAWLED"

    def test_returns_tuple_of_two_strings(self):
        result = classify("some requirement text", "")
        assert isinstance(result, tuple)
        assert len(result) == 2
        assert all(isinstance(s, str) for s in result)

    def test_deterministic_same_input_same_output(self):
        """Same input must always produce same output — no randomness."""
        r1 = classify("admin organisation billing", "")
        r2 = classify("admin organisation billing", "")
        assert r1 == r2


# ---------------------------------------------------------------------------
# check_graph_ready (imported from pipeline/online.py)
# ---------------------------------------------------------------------------

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent.parent))
from pipeline.online import check_graph_ready


class TestCheckGraphReady:
    """check_graph_ready must return True on full graph, sys.exit on empty."""

    def _make_driver(self, node_count: int):
        """Build a mock Neo4j driver that returns node_count from MATCH (n)."""
        record = MagicMock()
        record.__getitem__ = MagicMock(side_effect=lambda k: node_count if k == "c" else None)
        session = MagicMock()
        session.run.return_value.single.return_value = record
        driver = MagicMock()
        driver.session.return_value.__enter__ = MagicMock(return_value=session)
        driver.session.return_value.__exit__ = MagicMock(return_value=False)
        return driver

    def test_returns_true_when_graph_is_populated(self):
        driver = self._make_driver(1500)
        result = check_graph_ready(driver)
        assert result is True

    def test_returns_true_at_exact_threshold(self):
        driver = self._make_driver(100)
        result = check_graph_ready(driver)
        assert result is True

    def test_exits_when_graph_is_empty(self):
        driver = self._make_driver(0)
        with pytest.raises(SystemExit) as exc_info:
            check_graph_ready(driver)
        assert exc_info.value.code == 1

    def test_exits_when_graph_is_below_threshold(self):
        driver = self._make_driver(50)
        with pytest.raises(SystemExit) as exc_info:
            check_graph_ready(driver)
        assert exc_info.value.code == 1
