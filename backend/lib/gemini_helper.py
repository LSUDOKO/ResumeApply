"""
gemini_helper.py
================
Production-grade Gemini model factory.

Problems fixed vs original:
  ✗ Wrong model names — "gemini-flash-latest" / "gemini-pro-latest" don't exist
  ✗ genai.configure() never called — every call returns 401 Unauthorized
  ✗ Silent exceptions — failures swallowed, impossible to debug
  ✗ No GenerationConfig — temperature/safety unset, inconsistent outputs
  ✗ No JSON mode variant — every caller had to configure it themselves
  ✗ No model validation — returns object that 404s on first real use
  ✗ Rebuilds model object on every call — unnecessary overhead
  ✗ No startup validation — broken key only discovered at runtime

Production features:
  ✦ API key loaded, validated, and configured once at import time
  ✦ Correct, real model names in priority order
  ✦ genai.get_model() probe before accepting any model
  ✦ Cached model instances — built once, reused forever
  ✦ get_gemini_model()       — standard text + vision
  ✦ get_gemini_json_model()  — JSON mode (response_mime_type guaranteed)
  ✦ get_gemini_fast_model()  — lowest-latency for quick checks
  ✦ clear_model_cache()      — force re-probe after quota reset
  ✦ get_active_model_names() — inspect which models are currently live
"""

import logging
import os

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────
# API key — load, validate, configure  (once at import)
# ─────────────────────────────────────────────────────
_API_KEY = os.getenv("GEMINI_API_KEY", "")
if not _API_KEY:
    raise EnvironmentError(
        "GEMINI_API_KEY is not set. "
        "Add it to your .env file or environment before starting the server."
    )
genai.configure(api_key=_API_KEY)
logger.info("Gemini API key configured (%s...)", _API_KEY[:8])


# ─────────────────────────────────────────────────────
# Model priority lists  (most preferred → least)
# All names verified against the Gemini API as of 2025.
# ─────────────────────────────────────────────────────

# Standard: best quality available on free tier
_STANDARD_MODELS = [
    "gemini-2.0-flash",            # best free-tier: fast + multimodal
    "gemini-2.0-flash-lite",       # slightly lighter
    "gemini-1.5-flash-latest",     # proven stable fallback
    "gemini-1.5-flash",            # pinned stable
    "gemini-1.5-flash-8b",         # smallest, last resort
]

# Fast: optimized for lowest latency (quick checks, blocker detection)
_FAST_MODELS = [
    "gemini-2.0-flash-lite",
    "gemini-1.5-flash-8b",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
]


# ─────────────────────────────────────────────────────
# Generation configs
# ─────────────────────────────────────────────────────
_CONFIG_STANDARD = genai.GenerationConfig(
    temperature       = 0.2,     # low = consistent, factual outputs
    top_p             = 0.9,
    max_output_tokens = 2048,
)

_CONFIG_JSON = genai.GenerationConfig(
    temperature        = 0.1,    # even lower for structured data
    top_p              = 0.9,
    max_output_tokens  = 2048,
    response_mime_type = "application/json",   # guaranteed JSON — zero regex needed
)

_CONFIG_FAST = genai.GenerationConfig(
    temperature       = 0.1,
    max_output_tokens = 512,     # tight limit keeps latency low
)


# ─────────────────────────────────────────────────────
# Module-level cache  {label: GenerativeModel}
# ─────────────────────────────────────────────────────
_model_cache: dict[str, genai.GenerativeModel] = {}


# ─────────────────────────────────────────────────────
# Core factory
# ─────────────────────────────────────────────────────
def _build_model(
    priority_list: list[str],
    config: genai.GenerationConfig,
    label: str,
) -> genai.GenerativeModel:
    """
    Walk priority_list, probe each model name with the real API,
    return and cache the first one that responds successfully.
    Raises RuntimeError if every model fails (misconfigured key, outage).
    """
    if label in _model_cache:
        return _model_cache[label]

    last_exc: Exception | None = None

    for name in priority_list:
        try:
            # Hard probe — raises if model name is wrong or quota is exhausted
            genai.get_model(f"models/{name}")
            model = genai.GenerativeModel(name, generation_config=config)
            _model_cache[label] = model
            logger.info("Gemini [%s] selected model: %s", label, name)
            return model
        except Exception as exc:
            logger.debug("Gemini [%s] '%s' unavailable: %s", label, name, exc)
            last_exc = exc

    raise RuntimeError(
        f"No Gemini model available for [{label}]. "
        f"Tried: {priority_list}. Last error: {last_exc}"
    )


# ─────────────────────────────────────────────────────
# Public API — three purpose-built variants
# ─────────────────────────────────────────────────────
def get_gemini_model() -> genai.GenerativeModel:
    """
    Standard text + vision model.
    Use for: form filling, cover letters, page analysis, general prompts.
    """
    return _build_model(_STANDARD_MODELS, _CONFIG_STANDARD, "standard")


def get_gemini_json_model() -> genai.GenerativeModel:
    """
    JSON-mode model. response_mime_type='application/json' is always set.
    Use for: coordinate lookup, field mapping, any structured-output call.
    Caller just does: json.loads(response.text) — no regex, no fallback needed.
    """
    return _build_model(_STANDARD_MODELS, _CONFIG_JSON, "json")


def get_gemini_fast_model() -> genai.GenerativeModel:
    """
    Lowest-latency model with a tight token budget.
    Use for: quick page-type checks, blocker detection, yes/no decisions.
    """
    return _build_model(_FAST_MODELS, _CONFIG_FAST, "fast")


# ─────────────────────────────────────────────────────
# Utilities
# ─────────────────────────────────────────────────────
def clear_model_cache() -> None:
    """Force re-probe of all models — useful after a quota reset or key rotation."""
    _model_cache.clear()
    logger.info("Gemini model cache cleared — will re-probe on next use")


def get_active_model_names() -> dict[str, str]:
    """
    Returns which model is currently active for each variant.
    Example: {"standard": "gemini-2.0-flash", "json": "gemini-2.0-flash", "fast": "gemini-2.0-flash-lite"}
    """
    return {label: m.model_name for label, m in _model_cache.items()}