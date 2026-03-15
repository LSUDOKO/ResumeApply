import google.generativeai as genai
import base64, io, os
from playwright.async_api import async_playwright
import PIL.Image
from lib.gemini_helper import get_gemini_model
from lib.session_context import current_session_id

# Global browser instance
_browser = None
_page = None

async def get_browser():
    global _browser, _page
    if _browser is None:
        playwright = await async_playwright().start()
        _browser = await playwright.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        _page = await _browser.new_page(
            viewport={"width": 1280, "height": 800}
        )
    return _browser, _page

async def take_screenshot_tool(
    action_context: str
) -> dict:
    """
    Takes a screenshot of the current browser state,
    sends it to the frontend via WebSocket, and returns
    a Gemini Vision analysis of what's visible.
    """
    _, page = await get_browser()
    
    # Take screenshot
    screenshot_bytes = await page.screenshot(
        type="jpeg", quality=80, full_page=False
    )
    screenshot_b64 = base64.b64encode(screenshot_bytes).decode()
    
    # Send to frontend via WebSocket
    try:
        session_id = current_session_id.get()
        if session_id:
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
        f"Analyze this browser screenshot. Context: {action_context}. Return JSON with visible_jobs and form_fields."
    ])
    
    import json, re
    json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
    analysis = json.loads(json_match.group()) if json_match else {}
    
    return {
        "page_analysis": analysis,
        "screenshot_sent": True,
        "current_url": page.url
    }
