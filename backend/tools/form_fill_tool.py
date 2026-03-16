"""
application_tools.py
====================
OPTIMIZED for Gemini Free API tier:
  - Batched API calls      → fewer round-trips, stays inside rate limits
  - response_mime_type     → guaranteed JSON, no regex fragility
  - Flash model            → fastest free-tier model, lowest token cost
  - Exponential back-off   → survives 429s gracefully
  - Screenshot cache       → one capture per fill cycle, reused for all fields
  - Single-call coord map  → all fields located in ONE vision call
  - Prompt compression     → lean prompts = fewer tokens = higher throughput
"""

import asyncio
import json
import logging
import time
from functools import wraps
from typing import Any

import google.generativeai as genai
import PIL.Image
import io

from lib.gemini_helper import get_gemini_model

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────
FLASH_MODEL   = "gemini-1.5-flash-latest"   # fastest + cheapest on free tier
MAX_RETRIES   = 4
BASE_DELAY    = 2.0                          # seconds; doubles each retry
SCREENSHOT_Q  = 75                           # JPEG quality (balance size vs clarity)
TYPE_DELAY_MS = 20                           # keyboard type delay (ms)
CLICK_WAIT_MS = 400                          # post-click settle time (ms)


# ─────────────────────────────────────────────
# Retry decorator  (handles free-tier 429s)
# ─────────────────────────────────────────────
def with_retry(fn):
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        delay = BASE_DELAY
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return await fn(*args, **kwargs) if asyncio.iscoroutinefunction(fn) else fn(*args, **kwargs)
            except Exception as exc:
                is_rate_limit = "429" in str(exc) or "quota" in str(exc).lower()
                if attempt == MAX_RETRIES or not is_rate_limit:
                    logger.error("Failed after %d attempt(s): %s", attempt, exc)
                    raise
                logger.warning("Rate-limited. Retry %d/%d in %.1fs…", attempt, MAX_RETRIES, delay)
                await asyncio.sleep(delay)
                delay *= 2   # exponential back-off
    return wrapper


# ─────────────────────────────────────────────
# Gemini helpers
# ─────────────────────────────────────────────
def _get_flash_model(response_json: bool = True) -> genai.GenerativeModel:
    """Return a Flash model; optionally force JSON output (zero parse failures)."""
    cfg = genai.GenerationConfig(
        temperature=0.2,
        **({"response_mime_type": "application/json"} if response_json else {})
    )
    return genai.GenerativeModel(FLASH_MODEL, generation_config=cfg)


def _safe_json(text: str, fallback: Any = None) -> Any:
    """Parse JSON, returning fallback on failure. Strips markdown fences."""
    cleaned = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("JSON parse failed on: %s", text[:120])
        return fallback


# ─────────────────────────────────────────────
# Screenshot helper
# ─────────────────────────────────────────────
async def _capture(page) -> PIL.Image.Image:
    """Capture page screenshot once and return PIL Image."""
    raw = await page.screenshot(type="jpeg", quality=SCREENSHOT_Q)
    return PIL.Image.open(io.BytesIO(raw))


# ─────────────────────────────────────────────
# TOOL 1 – form_fill_tool
# ─────────────────────────────────────────────
@with_retry
async def form_fill_tool(
    form_fields: list[dict],
    resume_profile: dict,
) -> dict:
    """
    Fills application form fields using resume data + Playwright.

    Optimizations vs original:
      1. One API call to map ALL fields → resume values (no per-field call).
      2. One vision API call to locate ALL coordinates at once.
      3. JSON mime type = no regex, no parse failures.
      4. Single screenshot reused for the entire coordinate-lookup batch.
      5. Retry/back-off on rate limits.
    """
    from tools.screenshot_tool import get_browser
    _, page = await get_browser()

    model_text   = _get_flash_model(response_json=True)
    model_vision = _get_flash_model(response_json=True)

    # ── Step 1: Map ALL fields to resume values in one call ────────────────
    mapping_prompt = (
        "You are a job-application assistant. "
        "Map each form field to the best matching value from the resume.\n\n"
        f"FORM FIELDS:\n{json.dumps(form_fields, indent=2)}\n\n"
        f"RESUME:\n{json.dumps(resume_profile, indent=2)}\n\n"
        "Return a JSON array. Each element must have:\n"
        "  field_name         – exact field name from input\n"
        "  value              – value to enter (string, empty string if unknown)\n"
        "  selector_hint      – short visual description of how to find this field on screen\n"
        "  field_type         – one of: text | dropdown | checkbox | radio | textarea\n"
        "Only include fields where value is non-empty."
    )

    raw_map = model_text.generate_content(mapping_prompt)
    mappings: list[dict] = _safe_json(raw_map.text, fallback=[])

    if not mappings:
        logger.warning("Field-mapping returned empty; aborting fill.")
        return {"mappings": [], "filled_count": 0, "success": False, "error": "mapping_failed"}

    # ── Step 2: Locate ALL field coordinates in ONE vision call ───────────
    screenshot_img = await _capture(page)

    # Build a compact field list for the vision prompt
    field_hints = [
        {"id": i, "hint": m["selector_hint"], "type": m.get("field_type", "text")}
        for i, m in enumerate(mappings)
    ]

    coord_prompt = (
        "You are given a screenshot of a web form and a list of fields to locate.\n"
        "For every field, return its click coordinates (center of the input element).\n\n"
        f"FIELDS:\n{json.dumps(field_hints, indent=2)}\n\n"
        "Return a JSON array where each element has:\n"
        "  id  – same id from input\n"
        "  x   – pixel x coordinate\n"
        "  y   – pixel y coordinate\n"
        "  found – true/false\n"
        "If a field is not visible, set found=false and omit x/y."
    )

    raw_coords = model_vision.generate_content([screenshot_img, coord_prompt])
    coord_list: list[dict] = _safe_json(raw_coords.text, fallback=[])
    coord_map  = {c["id"]: c for c in coord_list if c.get("found")}

    # ── Step 3: Interact with each field ──────────────────────────────────
    filled_count = 0
    errors: list[str] = []

    for i, item in enumerate(mappings):
        val         = str(item.get("value", "")).strip()
        field_type  = item.get("field_type", "text")
        coords      = coord_map.get(i)

        if not val or not coords:
            continue

        x, y = coords.get("x"), coords.get("y")
        if not (x and y):
            continue

        try:
            await page.mouse.click(x, y)
            await page.wait_for_timeout(CLICK_WAIT_MS)

            if field_type in ("text", "textarea"):
                # Clear existing content first
                await page.keyboard.press("Control+a")
                await page.keyboard.press("Backspace")
                await page.keyboard.type(val, delay=TYPE_DELAY_MS)

            elif field_type == "dropdown":
                # Try native select, fall back to typing
                try:
                    await page.select_option(f"select:near([x='{x}'][y='{y}'])", label=val)
                except Exception:
                    await page.keyboard.type(val, delay=TYPE_DELAY_MS)

            elif field_type == "checkbox":
                # Already clicked above; only type if it needs a value
                pass

            filled_count += 1
            await page.wait_for_timeout(CLICK_WAIT_MS)

        except Exception as exc:
            err_msg = f"Field '{item.get('field_name')}': {exc}"
            logger.warning(err_msg)
            errors.append(err_msg)

    return {
        "mappings":     mappings,
        "filled_count": filled_count,
        "total_fields": len(mappings),
        "errors":       errors,
        "success":      filled_count > 0,
    }


# ─────────────────────────────────────────────
# TOOL 2 – cover_letter_tool
# ─────────────────────────────────────────────
@with_retry
async def cover_letter_tool(
    job_title: str,
    company_name: str,
    job_requirements: str,
    resume_profile: dict,
) -> dict:
    """
    Generates a tailored, ATS-optimised cover letter.

    Optimizations:
      - Structured prompt → richer output in one pass
      - Flash model       → fast, free-tier friendly
      - Plain text output (not JSON) → no mime-type overhead for prose
      - Returns both full letter + 3-bullet summary for quick review
    """
    model = _get_flash_model(response_json=False)

    # Compress resume to key facts only (saves tokens)
    key_facts = {
        "name":        resume_profile.get("name", ""),
        "title":       resume_profile.get("current_title", ""),
        "skills":      resume_profile.get("skills", [])[:15],   # top 15
        "experience":  resume_profile.get("experience", [])[:3], # top 3 roles
        "education":   resume_profile.get("education", [])[:2],
        "achievements": resume_profile.get("achievements", [])[:5],
    }

    prompt = f"""Write a compelling, ATS-optimised cover letter for the role below.
Tone: professional yet personable. Length: 3 paragraphs (≈250 words).
Weave in keywords from the requirements naturally.

ROLE: {job_title} at {company_name}
REQUIREMENTS: {job_requirements}
CANDIDATE: {json.dumps(key_facts)}

Structure:
1. Opening – hook + role name + company name
2. Middle  – 2-3 specific achievements matched to requirements
3. Closing – call to action

After the letter, add a line: ---KEYWORDS_USED--- followed by a comma-separated
list of requirement keywords you included.
"""

    response = model.generate_content(prompt)
    full_text = response.text.strip()

    # Split letter body from keyword summary
    parts  = full_text.split("---KEYWORDS_USED---")
    letter = parts[0].strip()
    kws    = [k.strip() for k in parts[1].split(",")] if len(parts) > 1 else []

    return {
        "cover_letter":    letter,
        "keywords_used":   kws,
        "word_count":      len(letter.split()),
        "success":         bool(letter),
    }


async def mark_job_applied_tool(
    job_title: str,
    company: str,
    match_score: int,
    cover_letter: str = "",
) -> dict:
    """
    Broadcasts and persists a job_applied event to Supabase.
    """
    from lib.supabase_db import db as supabase
    from lib.session_context import current_session_id
    
    session_id = current_session_id.get()
    if session_id:
        try:
            supabase.add_application(
                session_id=session_id,
                job_title=job_title,
                company=company,
                status="applied",
                match_score=match_score,
                cover_letter=cover_letter
            )
        except Exception as e:
            logger.error(f"Failed to persist application to Supabase: {e}")

    await _broadcast(
        event_type="job_applied",
        job_title=job_title,
        company=company,
        match_score=match_score,
        cover_letter=cover_letter or "Auto-filled application submitted.",
    )
    return {"success": True, "message": "Marked as applied."}


async def mark_job_skipped_tool(
    job_title: str,
    company: str,
    reason: str,
) -> dict:
    """
    Broadcasts and persists a job_skipped event to Supabase.
    """
    from lib.supabase_db import db as supabase
    from lib.session_context import current_session_id
    
    session_id = current_session_id.get()
    if session_id:
        try:
            supabase.add_application(
                session_id=session_id,
                job_title=job_title,
                company=company,
                status="skipped",
                match_score=0,
                reason=reason
            )
        except Exception as e:
            logger.error(f"Failed to persist skip to Supabase: {e}")

    await _broadcast(
        event_type="job_skipped",
        job_title=job_title,
        company=company,
        match_score=0,
        reason=reason,
    )
    return {"success": True, "message": "Marked as skipped."}


# ─────────────────────────────────────────────
# Internal broadcast helper
# ─────────────────────────────────────────────
async def _broadcast(**payload: Any) -> None:
    """Send a WebSocket broadcast; silently swallow all errors."""
    from lib.session_context import current_session_id
    session_id = current_session_id.get()
    if not session_id:
        return
    try:
        from routers.websocket import manager
        await manager.broadcast(session_id, payload)
    except Exception as exc:
        logger.debug("Broadcast suppressed: %s", exc)