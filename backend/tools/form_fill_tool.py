from google.genai import types
import json, re
from lib.gemini_helper import get_gemini_model
from lib.session_context import current_session_id
from lib.gcp_helper import gcp_helper

async def form_fill_tool(form_fields: list, resume_profile: dict) -> dict:
    """
    Maps form fields to resume data using Gemini, then actually fills them
    in the browser using navigate_tool.
    """
    from lib.session_context import check_pause
    await check_pause()

    from tools.navigate_tool import navigate_tool

    model = get_gemini_model()
    prompt = f"""
    Map these form fields to the resume profile and return JSON only (no markdown):
    Form fields: {json.dumps(form_fields)}
    Resume: {json.dumps(resume_profile)}
    
    Return: {{
      "fillable": [{{"field_label": "", "value": ""}}],
      "needs_user_input": [{{"field_label": "", "reason": ""}}]
    }}
    """
    response = model.generate_content(prompt)
    json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
    mapping = json.loads(json_match.group()) if json_match else {"fillable": [], "needs_user_input": []}

    filled = []
    failed = []

    # Actually fill each field in the browser
    for field in mapping.get("fillable", []):
        label = field.get("field_label", "")
        value = field.get("value", "")
        if not label or not value:
            continue
        result = await navigate_tool(
            action="fill",
            selector_description=label,
            input_text=str(value)
        )
        if result.get("success"):
            filled.append(label)
        else:
            failed.append(label)

    return {
        "filled_fields": filled,
        "failed_fields": failed,
        "needs_user_input": mapping.get("needs_user_input", []),
        "success": len(filled) > 0
    }


async def cover_letter_tool(
    job_title: str,
    company_name: str,
    job_requirements: str,
    resume_profile: dict
) -> dict:
    """Generates a tailored cover letter."""
    model = get_gemini_model()
    prompt = f"""Write a concise, compelling cover letter (3 paragraphs max) for:
    Role: {job_title} at {company_name}
    Requirements: {job_requirements}
    Candidate Profile: {json.dumps(resume_profile)}
    
    Be specific, professional, and highlight the top 2-3 matching skills."""
    response = model.generate_content(prompt)
    return {"cover_letter": response.text, "success": True}


async def mark_job_applied_tool(job_title: str, company: str, match_score: int) -> dict:
    """Call immediately after successfully submitting a job application."""
    session_id = current_session_id.get()
    if session_id:
        try:
            from routers.websocket import manager
            import datetime

            application = {
                "job_title": job_title,
                "company": company,
                "match_score": match_score,
                "status": "applied",
                "timestamp": datetime.datetime.utcnow().isoformat()
            }

            # Persist to Firestore
            gcp_helper.append_application(session_id, application)

            await manager.broadcast(session_id, {
                "type": "job_applied",
                **application
            })
        except Exception as e:
            print(f"mark_applied error: {e}")
    return {"success": True, "message": "Marked as applied."}


async def mark_job_skipped_tool(job_title: str, company: str, reason: str) -> dict:
    """Call when deciding not to apply to a job."""
    session_id = current_session_id.get()
    if session_id:
        try:
            from routers.websocket import manager
            import datetime

            application = {
                "job_title": job_title,
                "company": company,
                "match_score": 0,
                "status": "skipped",
                "reason": reason,
                "timestamp": datetime.datetime.utcnow().isoformat()
            }

            # Persist to Firestore
            session_data = gcp_helper.get_session(session_id) or {}
            apps = session_data.get("applications", [])
            apps.append(application)
            session_data["applications"] = apps
            gcp_helper.save_session(session_id, session_data)

            await manager.broadcast(session_id, {
                "type": "job_skipped",
                **application
            })
        except Exception as e:
            print(f"mark_skipped error: {e}")
    return {"success": True, "message": "Marked as skipped."}
