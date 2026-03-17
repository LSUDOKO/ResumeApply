import google.generativeai as genai
import base64, io, os
from playwright.async_api import async_playwright
import PIL.Image
from lib.gemini_helper import get_gemini_model
from lib.session_context import current_session_id

# Per-session browser instances
_browsers: dict = {}
_pages: dict = {}
_playwright_instance = None

async def get_browser(session_id: str = None):
    global _playwright_instance
    if session_id is None:
        session_id = current_session_id.get() or "default"

    if session_id not in _browsers:
        if _playwright_instance is None:
            _playwright_instance = await async_playwright().start()
        browser = await _playwright_instance.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled']
        )
        page = await browser.new_page(
            viewport={"width": 1280, "height": 800},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        # Basic stealth
        await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        _browsers[session_id] = browser
        _pages[session_id] = page

    return _browsers[session_id], _pages[session_id]


async def close_browser(session_id: str):
    if session_id in _browsers:
        await _browsers[session_id].close()
        del _browsers[session_id]
        del _pages[session_id]


async def take_screenshot_tool(action_context: str) -> dict:
    """
    Takes a screenshot of the current browser state,
    sends it to the frontend via WebSocket, and returns
    a Gemini Vision analysis of what's visible.
    """
    from lib.session_context import check_pause
    await check_pause()

    session_id = current_session_id.get() or "default"
    _, page = await get_browser(session_id)

    screenshot_bytes = await page.screenshot(type="jpeg", quality=80, full_page=False)
    screenshot_b64 = base64.b64encode(screenshot_bytes).decode()

    # Send to frontend via WebSocket
    try:
        from routers.websocket import manager
        await manager.broadcast(session_id, {
            "type": "screenshot",
            "data": screenshot_b64,
            "context": action_context,
            "url": page.url
        })
    except Exception as e:
        print(f"WS broadcast error: {e}")

    # Analyze with Gemini Vision
    model = get_gemini_model()
    img = PIL.Image.open(io.BytesIO(screenshot_bytes))

    response = model.generate_content([
        img,
        f"""Analyze this browser screenshot. Context: {action_context}.
        Return JSON only (no markdown) with:
        {{
          "visible_jobs": [{{"title": "", "company": "", "location": "", "easy_apply": true/false}}],
          "form_fields": [{{"label": "", "type": "", "required": true/false}}],
          "current_page_type": "job_listing|job_detail|login|form|other",
          "needs_login": true/false,
          "captcha_detected": false,
          "page_summary": ""
        }}"""
    ])

    import json, re
    json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
    analysis = json.loads(json_match.group()) if json_match else {"page_summary": response.text}

    return {
        "page_analysis": analysis,
        "screenshot_sent": True,
        "current_url": page.url
    }
