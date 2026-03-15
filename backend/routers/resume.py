from fastapi import APIRouter, UploadFile, File
import google.generativeai as genai
import json, os, uuid
from lib.local_db import db

router = APIRouter()

# Configure Gemini
if "GEMINI_API_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    content = await file.read()
    
    # 1. Save to Local Storage
    try:
        local_path = db.save_resume(file.filename, content)
        gcs_url = f"file://{local_path}"
    except Exception as e:
        print(f"Local storage error: {e}")
        gcs_url = "memory-only"

    # 2. Parse with Gemini (Multi-model fallback)
    models_to_try = ["gemini-flash-latest", "gemini-2.0-flash", "gemini-pro-latest"]
    profile = None
    last_error = "Unknown error"

    import tempfile, pathlib
    with tempfile.NamedTemporaryFile(
        suffix=pathlib.Path(file.filename).suffix, 
        delete=False
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            gemini_file = genai.upload_file(tmp_path)
            
            prompt = """
            Parse this resume and extract the following as JSON only, 
            no markdown:
            {
              "name": "full name",
              "email": "email",
              "phone": "phone",
              "current_role": "current or most recent role",
              "years_experience": number,
              "skills": ["skill1", "skill2"],
              "education": "highest degree + institution",
              "current_ctc": "if mentioned",
              "preferred_roles": ["inferred target roles"],
              "summary": "2 sentence professional summary",
              "achievements": ["key achievement 1", "key achievement 2"],
              "projects": [{"name": "Project Name", "description": "Project details"}],
              "previous_roles": [{"title": "Role Title", "company": "Company", "duration": "Duration"}]
            }
            """
            
            response = model.generate_content([gemini_file, prompt])
            
            import re
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            profile = json.loads(json_match.group()) if json_match else None
            
            if profile:
                print(f"Success with model: {model_name}")
                break
        except Exception as e:
            print(f"Failed with {model_name}: {e}")
            last_error = str(e)
            continue

    if not profile:
        from fastapi import HTTPException
        error_msg = f"API Limit Reached. Models tried: {models_to_try}. Error: {last_error}"
        if "429" in last_error:
            error_msg = "Gemini API Quota Exceeded (429). You've reached the free tier limit. You can wait 60s or manually fill your profile below."
        raise HTTPException(status_code=429 if "429" in last_error else 500, detail=error_msg)

    profile["resume_url"] = gcs_url
    
    # 3. Store in Local DB
    session_id = str(uuid.uuid4())
    session_data = {
        "profile": profile,
        "created_at": str(uuid.uuid4()),
        "status": "profile_ready"
    }
    
    db.save_session(session_id, session_data)
    
    return {"session_id": session_id, "profile": profile}
