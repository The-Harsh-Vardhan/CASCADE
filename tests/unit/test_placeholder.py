"""
tests/unit/test_placeholder.py — Key rotation smoke tests.

Verifies that all 10 Gemini API keys are loaded from .env and that
the round-robin cycle covers every key. These tests make NO network calls.
"""
import itertools
from unittest.mock import patch

import pytest

from blast_radius.config import Settings


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_settings(**overrides) -> Settings:
    """Build a Settings object with 10 mock API keys (no .env read)."""
    base = {
        "GEMINI_API_KEY_1":  "key-aaa-001",
        "GEMINI_API_KEY_2":  "key-bbb-002",
        "GEMINI_API_KEY_3":  "key-ccc-003",
        "GEMINI_API_KEY_4":  "key-ddd-004",
        "GEMINI_API_KEY_5":  "key-eee-005",
        "GEMINI_API_KEY_6":  "key-fff-006",
        "GEMINI_API_KEY_7":  "key-ggg-007",
        "GEMINI_API_KEY_8":  "key-hhh-008",
        "GEMINI_API_KEY_9":  "key-iii-009",
        "GEMINI_API_KEY_10": "key-jjj-010",
    }
    base.update(overrides)
    # env_file=None prevents pydantic-settings from reading the real .env
    return Settings.model_validate(base)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestAllTenKeysLoaded:
    """Settings.gemini_api_keys must return all 10 non-empty keys in order."""

    def test_all_10_keys_loaded(self):
        s = _make_settings()
        keys = s.gemini_api_keys
        assert len(keys) == 10, f"Expected 10 keys, got {len(keys)}: {keys}"

    def test_keys_are_in_insertion_order(self):
        s = _make_settings()
        keys = s.gemini_api_keys
        assert keys[0] == "key-aaa-001"
        assert keys[4] == "key-eee-005"
        assert keys[9] == "key-jjj-010"

    def test_empty_keys_are_excluded(self):
        """Keys set to empty string must be filtered out."""
        s = _make_settings(GEMINI_API_KEY_3="", GEMINI_API_KEY_7="")
        keys = s.gemini_api_keys
        assert len(keys) == 8
        assert "key-ccc-003" not in keys
        assert "key-ggg-007" not in keys

    def test_fallback_single_key(self):
        """If numbered keys absent, falls back to GEMINI_API_KEY."""
        # Use _env_file=None to prevent pydantic-settings from reading the real .env
        with patch.dict("os.environ", {"GEMINI_API_KEY": "legacy-key"}, clear=True):
            s = Settings(_env_file=None)
        keys = s.gemini_api_keys
        assert keys == ["legacy-key"]

    def test_no_keys_raises(self):
        """No keys at all must raise EnvironmentError."""
        # clear=True wipes real env vars; _env_file=None skips .env reading
        with pytest.raises(EnvironmentError, match="No Gemini API key configured"):
            with patch.dict("os.environ", {}, clear=True):
                Settings(_env_file=None).gemini_api_keys


class TestKeyRotationCycles:
    """Round-robin over itertools.cycle must visit every key exactly once per N steps."""

    def test_all_10_keys_appear_in_20_steps(self):
        s = _make_settings()
        keys = s.gemini_api_keys
        cycle = itertools.cycle(keys)

        # Step the cycle 20 times (2 full rotations)
        seen = set()
        for _ in range(20):
            seen.add(next(cycle))

        assert seen == set(keys), (
            f"Expected all 10 keys to appear; missing: {set(keys) - seen}"
        )

    def test_rotation_is_round_robin_not_random(self):
        """The cycle must repeat the same sequence — deterministic order matters."""
        s = _make_settings()
        keys = s.gemini_api_keys
        cycle = itertools.cycle(keys)

        first_pass  = [next(cycle) for _ in range(10)]
        second_pass = [next(cycle) for _ in range(10)]

        assert first_pass == second_pass == keys, (
            "Second rotation must produce identical sequence to first rotation"
        )

    def test_8_key_pool_cycles_correctly(self):
        """Partial pool (8 of 10 keys set) must cycle only 8 distinct keys."""
        s = _make_settings(GEMINI_API_KEY_5="", GEMINI_API_KEY_10="")
        keys = s.gemini_api_keys
        assert len(keys) == 8

        cycle = itertools.cycle(keys)
        seen = set()
        for _ in range(16):  # 2 full passes
            seen.add(next(cycle))

        assert len(seen) == 8
        assert "key-eee-005" not in seen
        assert "key-jjj-010" not in seen
