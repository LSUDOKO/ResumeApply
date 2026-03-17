import google.generativeai as genai
import PIL.Image, io, json, re
from lib.gemini_helper import get_gemini_model
from lib.session_context import current_session_id


async def navigate_tool(
    url: str = None,
    action: str = None,
    selector_description: str = None,
    input_text: str = None
) -> dict:
    """
    Controls browser navigation and interaction using visual descriptions.
    Actions: navigate, click, type, scroll, press_enter, get_text
    """
    from tools.screenshot_tool import get_browser
    session_id = current_session_id.get() or "default"
    _, page = await get_browser(session_id)

    # --- NAVIGATE ---
    if url:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
            await page.wait_for_timeout(2000)
            return {"success": True, "url": page.url, "action": "navigate"}
        except Exception as e:
            return {"success": False, "reason": str(e)}

    # --- CLICK by visual description ---
    if action == "click" and selector_description:
        screenshot_bytes = await page.screenshot(type="jpeg", quality=80)
        img = PIL.Image.open(io.BytesIO(screenshot_bytes))
        model = get_gemini_model()
        response = model.generate_content([
            img,
            f"""Find the UI element matching: '{selector_description}'.
            Return JSON only: {{"x": number, "y": number, "found": true/false, "confidence": "high/medium/low"}}"""
        ])
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        coords = json.loads(json_match.group()) if json_match else {}

        if coords.get("found") and coords.get("x") and coords.get("y"):
            await page.mouse.click(coords["x"], coords["y"])
            await page.wait_for_timeout(1500)
            return {"success": True, "clicked_at": coords, "action": "click"}
        return {"success": False, "reason": f"Element not found: {selector_description}"}

    # --- TYPE text ---
    if action == "type" and input_text is not None:
        await page.keyboard.type(input_text, delay=40)
        await page.wait_for_timeout(500)
        return {"success": True, "typed": input_text}

    # --- CLEAR + TYPE (for form fields) ---
    if action == "fill" and selector_description and input_text is not None:
        screenshot_bytes = await page.screenshot(type="jpeg", quality=80)
        img = PIL.Image.open(io.BytesIO(screenshot_bytes))
        model = get_gemini_model()
        response = model.generate_content([
            img,
            f"Find input field labeled '{selector_description}'. Return JSON only: {{\"x\": number, \"y\": number, \"found\": true/false}}"
        ])
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        coords = json.loads(json_match.group()) if json_match else {}

        if coords.get("found") and coords.get("x"):
            await page.mouse.click(coords["x"], coords["y"])
            await page.wait_for_timeout(300)
            await page.keyboard.press("Control+a")
            await page.keyboard.type(input_text, delay=40)
            await page.wait_for_timeout(500)
            return {"success": True, "filled": selector_description, "value": input_text}
        return {"success": False, "reason": f"Field not found: {selector_description}"}

    # --- PRESS KEY ---
    if action == "press_enter":
        await page.keyboard.press("Enter")
        await page.wait_for_timeout(1500)
        return {"success": True, "action": "press_enter"}

    # --- SCROLL ---
    if action == "scroll":
        direction = input_text or "down"
        delta = 600 if direction == "down" else -600
        await page.evaluate(f"window.scrollBy(0, {delta})")
        await page.wait_for_timeout(500)
        return {"success": True, "action": "scroll", "direction": direction}

    # --- GET PAGE TEXT ---
    if action == "get_text":
        text = await page.evaluate("document.body.innerText")
        return {"success": True, "text": text[:3000]}  # limit size

    return {"success": False, "reason": "Invalid action or missing parameters"}
