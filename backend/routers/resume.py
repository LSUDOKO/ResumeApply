from fastapi import APIRouter, UploadFile, File, HTTPException
import json, os, uuid, re, tempfile, pathlib
from lib.gcp_helper import gcp_helper
from google.genai import types
from lib.gemini_helper import get_gemini_model

router = APIRouter()

GCS_BUCKET = os.environ.get("GCS_BUCKET", "")
PROJECT_ID = os.environ.get("PROJECT_ID", "")

RESUME_PROMPT = """
Parse this resume and extract the following as JSON only, no markdown:
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

@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    content = await file.read()

    # 1. Upload to GCS
    try:
        from google.cloud import storage
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(GCS_BUCKET)
        if not bucket.exists():
            bucket = client.create_bucket(GCS_BUCKET)
        
        blob = bucket.blob(f"resumes/{file.filename}")
        blob.upload_from_string(content, content_type="application/octet-stream")
        resume_url = f"gs://{GCS_BUCKET}/resumes/{file.filename}"
    except Exception as e:
        print(f"GCS upload failed: {e}")
        resume_url = f"local://{file.filename}"

    # 2. Parse with Gemini using modern SDK and inline bytes
    model = get_gemini_model()
    profile = None
    last_error = "Unknown error"

    try:
        # Use inline bytes to save specialized quota
        part = types.Part.from_bytes(
            data=content,
            mime_type="application/pdf" if file.filename.lower().endswith(".pdf") else "image/jpeg"
        )
        
        response = model.generate_content([part, RESUME_PROMPT])
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            profile = json.loads(match.group())
            print(f"Resume parsed successfully")
    except Exception as e:
        print(f"Parsing error: {e}")
        last_error = str(e)

    if not profile:
        is_quota = "429" in last_error
        detail = (
            "Gemini API Quota Exceeded (429). Wait 60s or manually fill your profile."
            if is_quota else
            f"Resume parsing failed. Error: {last_error}"
        )
        raise HTTPException(status_code=429 if is_quota else 500, detail=detail)

    profile["resume_url"] = resume_url

    # 3. Persist session to Firestore
    session_id = str(uuid.uuid4())
    gcp_helper.save_session(session_id, {
        "profile": profile,
        "created_at": session_id,
        "status": "profile_ready"
    })

    return {"session_id": session_id, "profile": profile}
