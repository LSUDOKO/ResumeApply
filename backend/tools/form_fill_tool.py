import google.generativeai as genai
import json, re
from lib.gemini_helper import get_gemini_model

async def form_fill_tool(
    form_fields: list,
    resume_profile: dict
) -> dict:
    """
    Fills application form fields using resume data.
    """
    model = get_gemini_model()
    
    prompt = f"Map these form fields: {json.dumps(form_fields)} to this resume: {json.dumps(resume_profile)}. Return JSON with fillable and needs_user_input."
    response = model.generate_content(prompt)
    
    json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
    mapping = json.loads(json_match.group()) if json_match else {}
    
    # In a real scenario, we'd loop and fill. Returning status for now.
    return {
        "mapping": mapping,
        "success": True
    }

async def cover_letter_tool(
    job_title: str,
    company_name: str,
    job_requirements: str,
    resume_profile: dict
) -> dict:
    """
    Generates a tailored cover letter.
    """
    model = get_gemini_model()
    prompt = f"Write a cover letter for {job_title} at {company_name}. Requirements: {job_requirements}. Profile: {json.dumps(resume_profile)}"
    response = model.generate_content(prompt)
    
    return {
        "cover_letter": response.text,
        "success": True
    }

async def mark_job_applied_tool(
    job_title: str,
    company: str,
    match_score: int
) -> dict:
    """
    Call this tool immediately after successfully submitting a job application.
    """
    from lib.session_context import current_session_id
    session_id = current_session_id.get()
    if session_id:
        try:
            from routers.websocket import manager
            await manager.broadcast(session_id, {
                "type": "job_applied",
                "job_title": job_title,
                "company": company,
                "match_score": match_score,
                "cover_letter": "Auto-filled application submitted."
            })
        except Exception:
            pass
    return {"success": True, "message": "Marked as applied."}

async def mark_job_skipped_tool(
    job_title: str,
    company: str,
    reason: str
) -> dict:
    """
    Call this tool if you decide not to apply to a job (e.g., mismatch, requires manual login).
    """
    from lib.session_context import current_session_id
    session_id = current_session_id.get()
    if session_id:
        try:
            from routers.websocket import manager
            await manager.broadcast(session_id, {
                "type": "job_skipped",
                "job_title": job_title,
                "company": company,
                "match_score": 0,
                "reason": reason
            })
        except Exception:
            pass
    return {"success": True, "message": "Marked as skipped."}
