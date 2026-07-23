"""
blast_radius/llm.py — centralised LLM client wrapper.

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
"""
from __future__ import annotations

import json
import logging
import os
import re
from typing import Any

import google.generativeai as genai
from google.generativeai.types import GenerationConfig
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load .env file automatically if present
load_dotenv()

# ── Initialise client once at import time ─────────────────────────────────────
_api_key = os.environ.get("GEMINI_API_KEY", "")
if not _api_key:
    raise EnvironmentError(
        "GEMINI_API_KEY is not set. "
        "Add it to .env or export it before running the pipeline."
    )

genai.configure(api_key=_api_key)

_MODEL_NAME = os.environ.get("GEMINI_MODEL", "gemini-flash-latest")
_model = genai.GenerativeModel(
    model_name=_MODEL_NAME,
    generation_config=GenerationConfig(
        temperature=0.2,       # Low temp for deterministic extraction
        top_p=0.95,
        max_output_tokens=8192,
    ),
)

logger.info("LLM client initialised: model=%s", _MODEL_NAME)


# ── Public API ─────────────────────────────────────────────────────────────────

async def call_llm(prompt: str, *, temperature: float | None = None) -> str:
    """
    Send a prompt and return the text response.
    Raises RuntimeError on API failure after retries.
    """
    temp = temperature if temperature is not None else 0.2
    gen_config = GenerationConfig(temperature=temp, top_p=0.95, max_output_tokens=8192)
    
    # Primary model attempt
    try:
        m = genai.GenerativeModel(model_name=_MODEL_NAME, generation_config=gen_config)
        response = m.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        logger.warning("LLM call with model %s failed: %s. Retrying with gemini-flash-latest...", _MODEL_NAME, e)
        try:
            m_fallback = genai.GenerativeModel(model_name="gemini-flash-latest", generation_config=gen_config)
            response = m_fallback.generate_content(prompt)
            return response.text.strip()
        except Exception as e2:
            raise RuntimeError(f"LLM call failed after retry: {e2}") from e2


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

    Args:
        prompt:      The full prompt text.
        schema_hint: Optional hint appended to prompt, e.g. '[{"id": ...}]'
        temperature: Lower = more deterministic. Default 0.1 for JSON tasks.
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
    except json.JSONDecodeError as e:
        logger.error("JSON parse failed.\nRaw response:\n%s", raw)
        raise ValueError(
            f"LLM did not return valid JSON: {e}\n"
            f"Raw response (first 500 chars): {raw[:500]}"
        ) from e


def call_llm_sync(prompt: str, *, temperature: float | None = None) -> str:
    """
    Synchronous wrapper for use in non-async contexts (e.g. smoke tests).
    Prefer call_llm() in async pipeline code.
    """
    import asyncio
    return asyncio.run(call_llm(prompt, temperature=temperature))


def call_llm_json_sync(prompt: str, schema_hint: str = "") -> Any:
    """Synchronous wrapper for call_llm_json."""
    import asyncio
    return asyncio.run(call_llm_json(prompt, schema_hint))
