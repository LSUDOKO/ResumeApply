"""
navigate_tool.py
================
ELITE browser navigator — optimized for accuracy, speed, and Gemini free-tier API.

Features:
  ✦ Smart element detection  – Gemini vision with bounding-box + fallback selector
  ✦ Batched actions          – execute multiple steps in one call
  ✦ DOM-first strategy       – tries cheap DOM lookup before any API call
  ✦ Adaptive waiting         – waits for real network idle, not fixed sleeps
  ✦ Auto-scroll to element   – finds off-screen elements automatically
  ✦ Retry + back-off         – survives rate limits and flaky pages
  ✦ Full action coverage     – click, type, scroll, hover, select, clear,
                               press_key, wait, back, forward, reload, extract
  ✦ Page-state snapshot      – every response includes url + title
"""

import asyncio
import io
import json
import logging
from functools import wraps
from typing import Any

import PIL.Image
import google.generativeai as genai

from tools.screenshot_tool import get_browser
from lib.gemini_helper import get_gemini_model

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────
FLASH_MODEL      = "gemini-1.5-flash-latest"
MAX_RETRIES      = 4
BASE_DELAY       = 2.0          # seconds; doubles on each retry
SCREENSHOT_Q     = 72           # JPEG quality — sharp enough, small enough
NAV_TIMEOUT      = 30_000       # ms — page.goto timeout
IDLE_TIMEOUT     = 8_000        # ms — networkidle timeout after goto
CLICK_SETTLE     = 600          # ms — pause after click
TYPE_DELAY       = 22           # ms — keyboard.type char delay
SCROLL_PX        = 700          # px — default scroll step
VIEWPORT         = {"width": 1280, "height": 800}

# Common semantic → CSS selector shortcuts (avoids API calls entirely)
SEMANTIC_SELECTORS: dict[str, list[str]] = {
    "search box":      ["input[type='search']", "input[name='q']", "input[placeholder*='search' i]"],
    "email":           ["input[type='email']", "input[name='email']"],
    "password":        ["input[type='password']"],
    "username":        ["input[name='username']", "input[name='user']", "input[id*='user' i]"],
    "submit":          ["button[type='submit']", "input[type='submit']"],
    "next button":     ["button:has-text('Next')", "a:has-text('Next')"],
    "continue button": ["button:has-text('Continue')", "a:has-text('Continue')"],
    "sign in":         ["button:has-text('Sign in')", "button:has-text('Log in')", "a:has-text('Sign in')"],
    "close":           ["button[aria-label*='close' i]", "button:has-text('×')"],
}


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
                is_rate  = "429" in str(exc) or "quota" in str(exc).lower()
                is_last  = attempt == MAX_RETRIES
                if is_last or not is_rate:
                    raise
                logger.warning("Rate-limited. Retry %d/%d in %.1fs", attempt, MAX_RETRIES, delay)
                await asyncio.sleep(delay)
                delay *= 2
    return wrapper


# ─────────────────────────────────────────────────────
# Gemini helpers
# ─────────────────────────────────────────────────────
def _flash(json_mode: bool = True) -> genai.GenerativeModel:
    cfg = genai.GenerationConfig(
        temperature=0.1,
        **({"response_mime_type": "application/json"} if json_mode else {}),
    )
    return genai.GenerativeModel(FLASH_MODEL, generation_config=cfg)


def _parse(text: str, fallback: Any = None) -> Any:
    cleaned = text.strip().lstrip("```json").lstrip("```").rstrip("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        logger.debug("JSON parse failed: %s", text[:120])
        return fallback


# ─────────────────────────────────────────────────────
# Page utilities
# ─────────────────────────────────────────────────────
async def _screenshot(page) -> PIL.Image.Image:
    raw = await page.screenshot(type="jpeg", quality=SCREENSHOT_Q)
    return PIL.Image.open(io.BytesIO(raw))


async def _page_state(page) -> dict:
    return {"url": page.url, "title": await page.title()}


async def _dom_find(page, description: str) -> dict | None:
    """
    Try cheap DOM lookup before calling Gemini.
    Returns {x, y} center of the first matching element, or None.
    """
    key = description.lower().strip()
    candidates = SEMANTIC_SELECTORS.get(key, [])

    # Also try direct text match for buttons / links
    candidates += [
        f"button:has-text('{description}')",
        f"a:has-text('{description}')",
        f"[aria-label='{description}']",
        f"[placeholder='{description}']",
        f"[title='{description}']",
    ]

    for sel in candidates:
        try:
            el = page.locator(sel).first
            box = await el.bounding_box()
            if box:
                return {
                    "x": box["x"] + box["width"]  / 2,
                    "y": box["y"] + box["height"] / 2,
                }
        except Exception:
            continue
    return None


async def _vision_find(page, description: str, scroll_attempts: int = 2) -> dict | None:
    """
    Use Gemini vision to locate an element. Scrolls down if not found on first pass.
    Returns {x, y} or None.
    """
    model = _flash(json_mode=True)
    prompt = (
        "Examine this screenshot and find the UI element described below.\n"
        f"ELEMENT: '{description}'\n\n"
        "Return JSON with:\n"
        "  found  – true/false\n"
        "  x      – horizontal center pixel (integer)\n"
        "  y      – vertical center pixel (integer)\n"
        "  label  – what you found (short string)\n"
        "If not found, set found=false and omit x, y."
    )

    for attempt in range(scroll_attempts + 1):
        img  = await _screenshot(page)
        resp = model.generate_content([img, prompt])
        data = _parse(resp.text, {})

        if data.get("found") and data.get("x") and data.get("y"):
            logger.debug("Vision found '%s' at (%s, %s) — attempt %d", description, data["x"], data["y"], attempt)
            return {"x": data["x"], "y": data["y"]}

        if attempt < scroll_attempts:
            # Scroll down and try again
            await page.evaluate(f"window.scrollBy(0, {SCROLL_PX})")
            await page.wait_for_timeout(400)

    return None


async def _find_element(page, description: str) -> dict | None:
    """DOM-first → Vision fallback. Most accurate, fewest API calls."""
    coords = await _dom_find(page, description)
    if coords:
        logger.debug("DOM found '%s' at (%s, %s)", description, coords["x"], coords["y"])
        return coords
    return await _vision_find(page, description)


# ─────────────────────────────────────────────────────
# Individual action handlers
# ─────────────────────────────────────────────────────
async def _act_navigate(page, url: str) -> dict:
    await page.set_viewport_size(VIEWPORT)
    await page.goto(url, wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
    try:
        await page.wait_for_load_state("networkidle", timeout=IDLE_TIMEOUT)
    except Exception:
        pass  # networkidle timeout is non-fatal
    return {"action": "navigate", **await _page_state(page)}


async def _act_click(page, description: str) -> dict:
    coords = await _find_element(page, description)
    if not coords:
        return {"success": False, "reason": f"Element not found: '{description}'"}
    await page.mouse.click(coords["x"], coords["y"])
    await page.wait_for_timeout(CLICK_SETTLE)
    try:
        await page.wait_for_load_state("networkidle", timeout=3000)
    except Exception:
        pass
    return {"success": True, "action": "click", "coords": coords, **await _page_state(page)}


async def _act_type(page, text: str, description: str | None = None) -> dict:
    if description:
        coords = await _find_element(page, description)
        if coords:
            await page.mouse.click(coords["x"], coords["y"])
            await page.wait_for_timeout(300)
    await page.keyboard.type(text, delay=TYPE_DELAY)
    return {"success": True, "action": "type", "typed": text}


async def _act_clear_and_type(page, text: str, description: str) -> dict:
    coords = await _find_element(page, description)
    if not coords:
        return {"success": False, "reason": f"Field not found: '{description}'"}
    await page.mouse.click(coords["x"], coords["y"])
    await page.wait_for_timeout(200)
    await page.keyboard.press("Control+a")
    await page.keyboard.press("Backspace")
    await page.keyboard.type(text, delay=TYPE_DELAY)
    return {"success": True, "action": "clear_and_type", "typed": text}


async def _act_hover(page, description: str) -> dict:
    coords = await _find_element(page, description)
    if not coords:
        return {"success": False, "reason": f"Element not found: '{description}'"}
    await page.mouse.move(coords["x"], coords["y"])
    await page.wait_for_timeout(400)
    return {"success": True, "action": "hover", "coords": coords}


async def _act_select(page, description: str, option: str) -> dict:
    coords = await _find_element(page, description)
    if not coords:
        return {"success": False, "reason": f"Dropdown not found: '{description}'"}
    try:
        # Try native <select>
        el = page.locator(f"select:near([x='{int(coords['x'])}'])")
        await el.select_option(label=option)
    except Exception:
        # Fallback: click dropdown, then click option
        await page.mouse.click(coords["x"], coords["y"])
        await page.wait_for_timeout(400)
        option_coords = await _vision_find(page, option)
        if option_coords:
            await page.mouse.click(option_coords["x"], option_coords["y"])
        else:
            return {"success": False, "reason": f"Option '{option}' not found in dropdown"}
    return {"success": True, "action": "select", "selected": option}


async def _act_scroll(page, direction: str = "down", px: int = SCROLL_PX) -> dict:
    delta = px if direction == "down" else -px
    await page.evaluate(f"window.scrollBy(0, {delta})")
    await page.wait_for_timeout(300)
    return {"success": True, "action": "scroll", "direction": direction, "px": px}


async def _act_press_key(page, key: str) -> dict:
    await page.keyboard.press(key)
    await page.wait_for_timeout(300)
    return {"success": True, "action": "press_key", "key": key}


async def _act_wait(page, ms: int = 2000) -> dict:
    await page.wait_for_timeout(ms)
    return {"success": True, "action": "wait", "ms": ms}


async def _act_back(page) -> dict:
    await page.go_back(wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
    return {"success": True, "action": "back", **await _page_state(page)}


async def _act_forward(page) -> dict:
    await page.go_forward(wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
    return {"success": True, "action": "forward", **await _page_state(page)}


async def _act_reload(page) -> dict:
    await page.reload(wait_until="domcontentloaded", timeout=NAV_TIMEOUT)
    return {"success": True, "action": "reload", **await _page_state(page)}


async def _act_extract(page, description: str) -> dict:
    """
    Extract visible text content from a described region/element.
    Uses vision for location, then grabs innerText from the nearest DOM node.
    """
    coords = await _find_element(page, description)
    if not coords:
        # Fall back to full-page Gemini extraction
        model = _flash(json_mode=False)
        img   = await _screenshot(page)
        resp  = model.generate_content([img, f"Extract the text content of: '{description}'. Return only the extracted text."])
        return {"success": True, "action": "extract", "text": resp.text.strip()}

    text = await page.evaluate(
        """([x, y]) => {
            const el = document.elementFromPoint(x, y);
            return el ? (el.innerText || el.textContent || el.value || '') : '';
        }""",
        [coords["x"], coords["y"]],
    )
    return {"success": True, "action": "extract", "text": text.strip()}


async def _act_screenshot(page) -> dict:
    """Returns page state; the screenshot itself is used internally only."""
    state = await _page_state(page)
    return {"success": True, "action": "screenshot", **state}


# ─────────────────────────────────────────────────────
# Dispatch table
# ─────────────────────────────────────────────────────
ACTION_MAP = {
    "navigate":       lambda page, kw: _act_navigate(page, kw["url"]),
    "click":          lambda page, kw: _act_click(page, kw["selector_description"]),
    "type":           lambda page, kw: _act_type(page, kw["input_text"], kw.get("selector_description")),
    "clear_and_type": lambda page, kw: _act_clear_and_type(page, kw["input_text"], kw["selector_description"]),
    "hover":          lambda page, kw: _act_hover(page, kw["selector_description"]),
    "select":         lambda page, kw: _act_select(page, kw["selector_description"], kw["input_text"]),
    "scroll":         lambda page, kw: _act_scroll(page, kw.get("direction", "down"), int(kw.get("px", SCROLL_PX))),
    "press_key":      lambda page, kw: _act_press_key(page, kw["input_text"]),
    "wait":           lambda page, kw: _act_wait(page, int(kw.get("ms", 2000))),
    "back":           lambda page, kw: _act_back(page),
    "forward":        lambda page, kw: _act_forward(page),
    "reload":         lambda page, kw: _act_reload(page),
    "extract":        lambda page, kw: _act_extract(page, kw["selector_description"]),
    "screenshot":     lambda page, kw: _act_screenshot(page),
}


# ─────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────
@with_retry
async def navigate_tool(
    url:                  str | None = None,
    action:               str | None = None,
    selector_description: str | None = None,
    input_text:           str | None = None,
    # Extended params
    direction:            str | None = "down",
    px:                   int | None = SCROLL_PX,
    ms:                   int | None = 2000,
    steps:                list[dict] | None = None,
) -> dict:
    """
    Elite browser navigator. Supports single actions and batched step lists.

    Single-action usage (backward-compatible):
        await navigate_tool(url="https://example.com")
        await navigate_tool(action="click", selector_description="Sign in button")
        await navigate_tool(action="type", input_text="hello@email.com",
                            selector_description="email field")
        await navigate_tool(action="scroll", direction="down", px=500)
        await navigate_tool(action="press_key", input_text="Enter")
        await navigate_tool(action="extract", selector_description="job title")

    Batched usage (executes steps sequentially, one screenshot / API call each):
        await navigate_tool(steps=[
            {"action": "navigate",  "url": "https://linkedin.com"},
            {"action": "click",     "selector_description": "Sign in"},
            {"action": "type",      "selector_description": "email", "input_text": "me@x.com"},
            {"action": "press_key", "input_text": "Tab"},
            {"action": "type",      "selector_description": "password", "input_text": "secret"},
            {"action": "click",     "selector_description": "Sign in button"},
        ])

    Returns:
        Single action  → dict with result fields
        Batched steps  → {"results": [...], "success": True, "steps_run": N}
    """
    _, page = await get_browser()

    # ── Batched mode ──────────────────────────────────────────────────────
    if steps:
        results   = []
        succeeded = 0
        for i, step in enumerate(steps):
            act = step.get("action") or ("navigate" if step.get("url") else None)
            if not act:
                results.append({"step": i, "success": False, "reason": "No action specified"})
                continue
            kw = {**step, "direction": step.get("direction", direction), "px": step.get("px", px), "ms": step.get("ms", ms)}
            try:
                result = await ACTION_MAP[act](page, kw)
                result["step"] = i
                results.append(result)
                if result.get("success", True):
                    succeeded += 1
            except KeyError:
                results.append({"step": i, "success": False, "reason": f"Unknown action: '{act}'"})
            except Exception as exc:
                logger.warning("Step %d (%s) failed: %s", i, act, exc)
                results.append({"step": i, "action": act, "success": False, "reason": str(exc)})

        return {"results": results, "steps_run": len(steps), "succeeded": succeeded, "success": succeeded > 0}

    # ── Single-action mode (backward-compatible) ──────────────────────────
    # Resolve action from shorthand params
    if url and not action:
        action = "navigate"

    if not action:
        return {"success": False, "reason": "No action or url provided"}

    handler = ACTION_MAP.get(action)
    if not handler:
        return {"success": False, "reason": f"Unknown action: '{action}'"}

    kw = {
        "url":                  url,
        "selector_description": selector_description,
        "input_text":           input_text,
        "direction":            direction,
        "px":                   px,
        "ms":                   ms,
    }
    result = await handler(page, kw)
    result.setdefault("success", True)
    return result