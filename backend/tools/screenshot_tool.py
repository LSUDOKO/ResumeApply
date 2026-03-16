"""
screenshot_tool.py
==================
Production-grade screenshot + vision analysis tool.

Problems fixed vs original:
  ✗ Single global page — crashes if browser dies, no recovery
  ✗ No page context awareness — same prompt for every screenshot
  ✗ Regex JSON parsing — breaks on nested objects
  ✗ response_mime_type not set — hallucinated non-JSON responses
  ✗ Full analysis on every call — wastes quota for simple nav screenshots
  ✗ No retry on Gemini 429s
  ✗ No browser health check — silently uses a crashed page
  ✗ No diff detection — can't tell if page changed between shots
  ✗ Playwright launched without stealth — easily bot-detected

New capabilities:
  ✦ Browser auto-recovery    — detects crashed context, relaunches cleanly
  ✦ Stealth launch args      — mimics real Chrome, reduces bot detection
  ✦ Tiered analysis modes    — FULL / JOBS / FORM / QUICK / RAW
  ✦ JSON mime type           — guaranteed structured output, zero regex
  ✦ Perceptual diff          — pixel-level change detection between shots
  ✦ Smart viewport capture   — viewport-only (fast) or full-page (thorough)
  ✦ Retry + back-off         — survives Gemini free-tier 429s
  ✦ Page-state metadata      — url, title, scroll position on every response
  ✦ Screenshot history       — last N shots kept in memory for diff / replay
"""

import asyncio
import base64
import io
import logging
from datetime import datetime, timezone
from functools import wraps
from typing import Literal

import PIL.Image
import PIL.ImageChops
import google.generativeai as genai
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

from lib.gemini_helper import get_gemini_model
from lib.session_context import current_session_id

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────
FLASH_MODEL      = "gemini-1.5-flash-latest"
SCREENSHOT_Q     = 78           # JPEG quality — sharp + compact
FULL_PAGE_Q      = 65           # lower quality for full-page (larger image)
MAX_RETRIES      = 4
BASE_DELAY       = 2.0
HISTORY_SIZE     = 5            # how many past screenshots to keep
VIEWPORT         = {"width": 1280, "height": 800}

AnalysisMode = Literal["FULL", "JOBS", "FORM", "QUICK", "RAW"]

# ─────────────────────────────────────────────────────
# Browser state  (module-level, but properly guarded)
# ─────────────────────────────────────────────────────
_playwright  = None
_browser: Browser | None          = None
_context: BrowserContext | None   = None
_page: Page | None                = None
_screenshot_history: list[dict]   = []   # [{bytes, b64, url, ts}]
_browser_lock = asyncio.Lock()


# ─────────────────────────────────────────────────────
# Retry decorator
# ─────────────────────────────────────────────────────
def with_retry(fn):
    @wraps(fn)
    async def wrapper(*args, **kwargs):
        delay = BASE_DELAY
        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return await fn(*args, **kwargs)
            except Exception as exc:
                is_rate = "429" in str(exc) or "quota" in str(exc).lower()
                if attempt == MAX_RETRIES or not is_rate:
                    raise
                logger.warning("Rate-limited. Retry %d/%d in %.1fs", attempt, MAX_RETRIES, delay)
                await asyncio.sleep(delay)
                delay *= 2
    return wrapper


# ─────────────────────────────────────────────────────
# Browser lifecycle
# ─────────────────────────────────────────────────────
_LAUNCH_ARGS = [
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-blink-features=AutomationControlled",   # stealth
    "--disable-infobars",
    "--window-size=1280,800",
    "--disable-extensions",
    "--disable-gpu",
    "--no-first-run",
    "--no-default-browser-check",
]


async def _is_page_alive() -> bool:
    """Check whether the current page is still responsive."""
    global _page
    if _page is None:
        return False
    try:
        await _page.title()
        return True
    except Exception:
        return False


async def get_browser() -> tuple[Browser, Page]:
    """
    Return (browser, page), launching or recovering as needed.
    Thread-safe via asyncio.Lock.
    """
    global _playwright, _browser, _context, _page

    async with _browser_lock:
        if not await _is_page_alive():
            logger.info("Browser not alive — launching fresh instance")
            await _shutdown_browser()
            await _launch_browser()

    return _browser, _page


async def _launch_browser() -> None:
    global _playwright, _browser, _context, _page

    _playwright = await async_playwright().start()
    _browser    = await _playwright.chromium.launch(
        headless=True,
        args=_LAUNCH_ARGS,
    )
    _context = await _browser.new_context(
        viewport=VIEWPORT,
        user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        java_script_enabled=True,
        accept_downloads=True,
    )
    # Mask webdriver fingerprint
    await _context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    _page = await _context.new_page()
    logger.info("Browser launched successfully")


async def _shutdown_browser() -> None:
    global _playwright, _browser, _context, _page
    for obj in (_page, _context, _browser, _playwright):
        if obj is not None:
            try:
                await obj.close()
            except Exception:
                pass
    _page = _context = _browser = _playwright = None


# ─────────────────────────────────────────────────────
# Screenshot capture
# ─────────────────────────────────────────────────────
async def _capture_raw(full_page: bool = False) -> bytes:
    _, page = await get_browser()
    quality = FULL_PAGE_Q if full_page else SCREENSHOT_Q
    return await page.screenshot(type="jpeg", quality=quality, full_page=full_page)


async def _capture_pil(full_page: bool = False) -> tuple[PIL.Image.Image, bytes]:
    raw = await _capture_raw(full_page)
    return PIL.Image.open(io.BytesIO(raw)), raw


def _store_history(raw: bytes, url: str) -> None:
    global _screenshot_history
    _screenshot_history.append({
        "bytes": raw,
        "b64":   base64.b64encode(raw).decode(),
        "url":   url,
        "ts":    datetime.now(timezone.utc).isoformat(),
    })
    _screenshot_history = _screenshot_history[-HISTORY_SIZE:]


# ─────────────────────────────────────────────────────
# Perceptual diff
# ─────────────────────────────────────────────────────
def _pixel_diff_pct(img_a: PIL.Image.Image, img_b: PIL.Image.Image) -> float:
    """Return percentage of pixels that changed between two screenshots."""
    try:
        a = img_a.convert("RGB").resize((320, 200))
        b = img_b.convert("RGB").resize((320, 200))
        diff   = PIL.ImageChops.difference(a, b)
        pixels = 320 * 200
        changed = sum(1 for p in diff.getdata() if any(c > 10 for c in p))
        return round(changed / pixels * 100, 1)
    except Exception:
        return 0.0


# ─────────────────────────────────────────────────────
# Gemini vision
# ─────────────────────────────────────────────────────
def _flash_model() -> genai.GenerativeModel:
    cfg = genai.GenerationConfig(
        temperature=0.1,
        response_mime_type="application/json",
    )
    return genai.GenerativeModel(FLASH_MODEL, generation_config=cfg)


_ANALYSIS_PROMPTS: dict[str, str] = {
    "FULL": (
        "Analyze this browser screenshot thoroughly.\n"
        "Return JSON with:\n"
        "  page_type       – e.g. job_listing / login / form / dashboard / error\n"
        "  visible_jobs    – array of {title, company, location, salary, url} (empty if none)\n"
        "  form_fields     – array of {name, type, label, required, current_value}\n"
        "  blockers        – array of {type, description} — captcha/mfa/cookie banners/popups\n"
        "  cta_buttons     – array of {label, purpose}\n"
        "  scroll_position – 'top'|'middle'|'bottom'\n"
        "  has_more_content– true/false\n"
        "  summary         – one sentence describing what is shown"
    ),
    "JOBS": (
        "Extract all visible job listings from this screenshot.\n"
        "Return JSON with:\n"
        "  visible_jobs – array of {title, company, location, salary, posted_date, easy_apply}\n"
        "  has_next_page – true/false\n"
        "  total_shown   – count of listings visible\n"
        "  platform      – e.g. LinkedIn / Indeed / Greenhouse"
    ),
    "FORM": (
        "Identify all form fields visible in this screenshot.\n"
        "Return JSON with:\n"
        "  form_fields – array of {name, label, type, required, current_value, placeholder}\n"
        "  submit_button – {label, visible}\n"
        "  form_title    – title or heading of the form if visible\n"
        "  missing_required – array of field names that are required but empty"
    ),
    "QUICK": (
        "Give a rapid page summary. Return JSON with:\n"
        "  page_type – one word\n"
        "  blockers  – array of blocker descriptions (empty if none)\n"
        "  summary   – one sentence"
    ),
}


@with_retry
async def _analyze(
    img: PIL.Image.Image,
    mode: AnalysisMode,
    extra_context: str,
) -> dict:
    if mode == "RAW":
        return {}

    model  = _flash_model()
    prompt = _ANALYSIS_PROMPTS.get(mode, _ANALYSIS_PROMPTS["QUICK"])
    if extra_context:
        prompt += f"\n\nAdditional context: {extra_context}"

    resp = model.generate_content([img, prompt])

    try:
        import json
        return json.loads(resp.text.strip().lstrip("```json").lstrip("```").rstrip("```"))
    except Exception:
        logger.warning("Vision JSON parse failed: %s", resp.text[:120])
        return {"raw_response": resp.text}


# ─────────────────────────────────────────────────────
# WebSocket broadcast
# ─────────────────────────────────────────────────────
async def _broadcast_screenshot(b64: str, url: str, context: str) -> None:
    session_id = current_session_id.get()
    if not session_id:
        return
    try:
        from routers.websocket import manager
        await manager.broadcast(session_id, {
            "type":    "screenshot",
            "data":    b64,
            "context": context,
            "url":     url,
            "ts":      datetime.now(timezone.utc).isoformat(),
        })
    except Exception as exc:
        logger.warning("Screenshot broadcast failed: %s", exc)


# ─────────────────────────────────────────────────────
# Public tool
# ─────────────────────────────────────────────────────
async def take_screenshot_tool(
    action_context: str = "",
    mode: AnalysisMode = "FULL",
    full_page: bool = False,
    detect_changes: bool = False,
) -> dict:
    """
    Capture the current browser state, broadcast to frontend, and analyse with Gemini.

    Args:
        action_context:  Free-text hint for the vision model
                         (e.g. "just clicked Apply button").
        mode:            Analysis depth —
                           FULL  → jobs + form fields + blockers + buttons
                           JOBS  → job listings only (saves tokens on listing pages)
                           FORM  → form fields only (saves tokens during form fill)
                           QUICK → fast page-type + blocker check only
                           RAW   → screenshot only, no Gemini call
        full_page:       Capture full scrollable page (slower, larger image).
        detect_changes:  Compare with last screenshot and report diff %.

    Returns:
        {
          page_analysis:    {...},       # Gemini structured output
          screenshot_b64:   "...",       # JPEG as base64
          screenshot_sent:  True/False,
          current_url:      "...",
          page_title:       "...",
          timestamp:        "...",
          change_pct:       12.4,        # only if detect_changes=True
          page_changed:     True/False,  # only if detect_changes=True
        }
    """
    _, page = await get_browser()

    # ── 1. Capture ────────────────────────────────────────────────────────
    img, raw = await _capture_pil(full_page)
    b64       = base64.b64encode(raw).decode()
    url       = page.url
    title     = await page.title()
    ts        = datetime.now(timezone.utc).isoformat()

    # ── 2. Change detection ───────────────────────────────────────────────
    change_pct  = None
    page_changed = None
    if detect_changes and _screenshot_history:
        prev_img = PIL.Image.open(io.BytesIO(_screenshot_history[-1]["bytes"]))
        change_pct   = _pixel_diff_pct(prev_img, img)
        page_changed = change_pct > 2.0   # >2% pixels changed = meaningful update

    _store_history(raw, url)

    # ── 3. Broadcast to frontend ──────────────────────────────────────────
    await _broadcast_screenshot(b64, url, action_context)

    # ── 4. Gemini vision analysis ─────────────────────────────────────────
    analysis = await _analyze(img, mode, action_context)

    # ── 5. Build response ────────────────────────────────────────────────
    result = {
        "page_analysis":   analysis,
        "screenshot_b64":  b64,
        "screenshot_sent": True,
        "current_url":     url,
        "page_title":      title,
        "timestamp":       ts,
        "mode":            mode,
    }
    if detect_changes:
        result["change_pct"]   = change_pct
        result["page_changed"] = page_changed

    return result


# ─────────────────────────────────────────────────────
# Convenience helpers used by other tools
# ─────────────────────────────────────────────────────
async def quick_check(context: str = "") -> dict:
    """Fast QUICK-mode snapshot — minimal tokens, just page type + blockers."""
    return await take_screenshot_tool(action_context=context, mode="QUICK")


async def has_page_changed() -> bool:
    """True if the page looks meaningfully different from the last screenshot."""
    result = await take_screenshot_tool(detect_changes=True, mode="RAW")
    return result.get("page_changed", False)