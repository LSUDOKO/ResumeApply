import google.generativeai as genai
import PIL.Image, io
from tools.screenshot_tool import get_browser
from lib.gemini_helper import get_gemini_model

async def navigate_tool(
    url: str = None,
    action: str = None,
    selector_description: str = None,
    input_text: str = None
) -> dict:
    """
    Controls browser navigation and interaction using visual descriptions.
    """
    _, page = await get_browser()
    
    if url:
        await page.goto(url, wait_until="networkidle", timeout=30000)
        await page.wait_for_timeout(1500)
        return {"success": True, "url": page.url, "action": "navigate"}
    
    if action == "click" and selector_description:
        screenshot_bytes = await page.screenshot(type="jpeg", quality=80)
        img = PIL.Image.open(io.BytesIO(screenshot_bytes))
        
        model = get_gemini_model()
        response = model.generate_content([
            img,
            f"Find the UI element matching: '{selector_description}'. Return JSON with x, y coordinates."
        ])
        
        import json, re
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        coords = json.loads(json_match.group()) if json_match else {}
        
        if coords.get("x") and coords.get("y"):
            await page.mouse.click(coords["x"], coords["y"])
            await page.wait_for_timeout(1000)
            return {"success": True, "clicked_at": coords}
        return {"success": False, "reason": "Element not found"}

    if action == "type" and input_text:
        await page.keyboard.type(input_text, delay=50)
        return {"success": True, "typed": input_text}
    
    if action == "scroll":
        await page.evaluate("window.scrollBy(0, 600)")
        return {"success": True}
        
    return {"success": False, "reason": "Invalid action"}
