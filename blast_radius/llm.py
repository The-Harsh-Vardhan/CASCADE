"""
blast_radius/llm.py — Centralised LLM client wrapper with multi-key rotation.

All pipeline phases import from here. Never instantiate the Gemini client
directly in phase code — always go through call_llm() or call_llm_json().

Usage:
    from blast_radius.llm import call_llm, call_llm_json

    # Plain text response
    text = await call_llm("Summarise this requirement: ...")

    # Structured JSON response (raises ValueError if parsing fails)
    data = await call_llm_json(
        prompt="Extract requirements as JSON array...",
        schema_hint='[{"id": str, "label": str, "text": str}]'
    )

Key rotation:
    If GEMINI_API_KEY_1 through GEMINI_API_KEY_5 are set, keys are cycled
    round-robin. On a 429 (quota exhausted), the next key is tried immediately.
    This effectively multiplies the daily free-tier quota by the number of keys.
"""
from __future__ import annotations

import itertools
import json
import logging
import re
import threading
from typing import Any

import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env file automatically if present
load_dotenv()

# ── Multi-key pool ─────────────────────────────────────────────────────────────

from blast_radius.config import settings as _settings

_api_keys: list[str] = _settings.gemini_api_keys   # raises EnvironmentError if none set
_key_cycle = itertools.cycle(_api_keys)
_key_lock   = threading.Lock()
_MODEL_NAME = _settings.gemini_model

logger.info(
    "LLM client initialised: model=%s | %d key(s) in rotation",
    _MODEL_NAME, len(_api_keys),
)


def _next_key() -> str:
    """Return the next API key in the round-robin cycle (thread-safe)."""
    with _key_lock:
        return next(_key_cycle)


def _make_model(api_key: str, temperature: float) -> genai.GenerativeModel:
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(
        model_name=_MODEL_NAME,
        generation_config=GenerationConfig(
            temperature=temperature,
            top_p=0.95,
            max_output_tokens=16384,
        ),
    )


def _is_quota_error(exc: Exception) -> bool:
    msg = str(exc)
    return "429" in msg or "RESOURCE_EXHAUSTED" in msg or "quota" in msg.lower()


# ── Public API ─────────────────────────────────────────────────────────────────

async def call_llm(prompt: str, *, temperature: float | None = None) -> str:
    """
    Send a prompt and return the text response.

    Cycles through all configured API keys on 429 quota errors.
    Raises RuntimeError only if ALL keys are exhausted.
    """
    temp = temperature if temperature is not None else 0.2
    n_keys = len(_api_keys)
    last_exc: Exception | None = None

    for attempt in range(n_keys):
        api_key = _next_key()
        try:
            model = _make_model(api_key, temp)
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as exc:
            if _is_quota_error(exc):
                key_hint = api_key[:12] + "..."
                logger.warning(
                    "Key %d/%d (%s) quota exhausted (429). Rotating to next key.",
                    attempt + 1, n_keys, key_hint,
                )
                last_exc = exc
                continue   # try next key
            # Non-quota error — raise immediately
            raise RuntimeError(f"LLM call failed: {exc}") from exc

    # All keys exhausted
    raise RuntimeError(
        f"All {n_keys} Gemini API key(s) returned 429 quota errors. "
        "Daily limits reached across all keys. Try again tomorrow, "
        "or upgrade to a paid plan for higher quotas."
    ) from last_exc


async def call_llm_json(
    prompt: str,
    schema_hint: str = "",
    *,
    temperature: float = 0.1,
) -> Any:
    """
    Send a prompt and parse the response as JSON.

    Strips ```json fences automatically.
    Raises ValueError if the response cannot be parsed as JSON.
    Inherits multi-key rotation from call_llm().
    """
    full_prompt = prompt
    if schema_hint:
        full_prompt += (
            f"\n\nRespond ONLY with valid JSON matching this schema — "
            f"no explanation, no markdown fences:\n{schema_hint}"
        )
    else:
        full_prompt += "\n\nRespond ONLY with valid JSON. No explanation, no markdown fences."

    raw = await call_llm(full_prompt, temperature=temperature)

    # Strip ```json ... ``` fences if present
    cleaned = re.sub(r"^```(?:json)?\s*", "", raw.strip(), flags=re.IGNORECASE)
    cleaned = re.sub(r"\s*```$", "", cleaned.strip())

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("JSON parse failed.\nRaw response:\n%s", raw)
        raise ValueError(
            f"LLM did not return valid JSON: {exc}\n"
            f"Raw response (first 500 chars): {raw[:500]}"
        ) from exc


def call_llm_sync(prompt: str, *, temperature: float | None = None) -> str:
    """
    Synchronous wrapper for use in non-async contexts (e.g. smoke tests, render.py).
    Prefer call_llm() in async pipeline code.
    """
    import asyncio
    return asyncio.run(call_llm(prompt, temperature=temperature))


def call_llm_json_sync(prompt: str, schema_hint: str = "") -> Any:
    """Synchronous wrapper for call_llm_json."""
    import asyncio
    return asyncio.run(call_llm_json(prompt, schema_hint))
