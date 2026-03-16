from fastapi import APIRouter, UploadFile, File, HTTPException
import google.generativeai as genai
import json, os, uuid
from lib.supabase_db import db as supabase

router = APIRouter()

# Configure Gemini
if "GEMINI_API_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    content = await file.read()
    
    # 1. Upload to Supabase Storage
    try:
        storage_resp = supabase.upload_resume_file(file.filename, content)
        # get_public_url returns an object with a public_url property in some versions, 
        # but my wrapper returns the full URL string if optimized.
        resume_url = str(storage_resp) 
    except Exception as e:
        print(f"Supabase storage error: {e}")
        resume_url = "local-fallback"

    # 2. Parse with Gemini (Using optimized helper)
    profile = None
    
    import tempfile, pathlib
    with tempfile.NamedTemporaryFile(
        suffix=pathlib.Path(file.filename).suffix, 
        delete=False
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    try:
        from lib.gemini_helper import get_gemini_json_model
        model = get_gemini_json_model()
        gemini_file = genai.upload_file(tmp_path)
        
        prompt = """
        Parse this resume and extract the following as JSON only:
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
        profile = json.loads(response.text)
        
    except Exception as e:
        print(f"Extraction error: {e}")
        last_error = str(e)
        if "429" in last_error:
            raise HTTPException(
                status_code=429, 
                detail="Gemini API Quota Exceeded (429). You've reached the free tier limit. You can wait 60s or manually fill your profile below."
            )
        raise HTTPException(status_code=500, detail=f"Failed to parse resume: {e}")
    finally:
        # Clean up temp file
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    # 3. Save to Supabase DB
    try:
        profile_record = supabase.save_resume_metadata(
            name=profile.get("name"),
            email=profile.get("email"),
            phone=profile.get("phone"),
            profile_json=profile,
            resume_url=resume_url
        )
        
        # 4. Create Session
        session_id = str(uuid.uuid4())
        supabase.save_session(session_id, profile_record["id"])
        
        return {"session_id": session_id, "profile": profile}
    except Exception as e:
        print(f"Supabase DB error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")
