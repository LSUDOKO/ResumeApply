from fastapi import APIRouter, UploadFile, File, HTTPException
import google.generativeai as genai
import json, os, uuid, re, tempfile, pathlib
from lib.local_db import db

router = APIRouter()

if "GEMINI_API_KEY" in os.environ:
    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

GCS_BUCKET = os.environ.get("GCS_BUCKET", "")
PROJECT_ID = os.environ.get("PROJECT_ID", "")


def _ensure_bucket(client, bucket_name: str):
    """Creates the GCS bucket if it doesn't exist."""
    from google.cloud import storage
    from google.api_core.exceptions import Conflict
    bucket = client.bucket(bucket_name)
    if not bucket.exists():
        try:
            bucket = client.create_bucket(bucket_name, project=PROJECT_ID)
            print(f"Created GCS bucket: {bucket_name}")
        except Conflict:
            pass  # created by another process simultaneously
    return bucket


def _upload_to_gcs(filename: str, content: bytes) -> str:
    """Uploads resume bytes to GCS, returns public gs:// URI. Falls back to local."""
    if not GCS_BUCKET:
        return None
    try:
        from google.cloud import storage
        client = storage.Client(project=PROJECT_ID)
        bucket = _ensure_bucket(client, GCS_BUCKET)
        blob = bucket.blob(f"resumes/{filename}")
        blob.upload_from_string(content, content_type="application/octet-stream")
        return f"gs://{GCS_BUCKET}/resumes/{filename}"
    except Exception as e:
        print(f"GCS upload failed, falling back to local: {e}")
        return None


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

    # 1. Upload to GCS (auto-creates bucket), fall back to local
    gcs_url = _upload_to_gcs(file.filename, content)
    if not gcs_url:
        try:
            local_path = db.save_resume(file.filename, content)
            gcs_url = f"file://{local_path}"
        except Exception as e:
            gcs_url = "memory-only"

    # 2. Parse with Gemini — write to temp file for upload
    with tempfile.NamedTemporaryFile(
        suffix=pathlib.Path(file.filename).suffix, delete=False
    ) as tmp:
        tmp.write(content)
        tmp_path = tmp.name

    profile = None
    last_error = "Unknown error"

    for model_name in ["gemini-2.0-flash", "gemini-1.5-flash", "gemini-1.5-pro"]:
        try:
            model = genai.GenerativeModel(model_name)
            gemini_file = genai.upload_file(tmp_path)
            response = model.generate_content([gemini_file, RESUME_PROMPT])
            match = re.search(r'\{.*\}', response.text, re.DOTALL)
            profile = json.loads(match.group()) if match else None
            if profile:
                print(f"Resume parsed with: {model_name}")
                break
        except Exception as e:
            print(f"Failed with {model_name}: {e}")
            last_error = str(e)

    try:
        os.unlink(tmp_path)
    except Exception:
        pass

    if not profile:
        is_quota = "429" in last_error
        detail = (
            "Gemini API Quota Exceeded (429). Wait 60s or manually fill your profile."
            if is_quota else
            f"Resume parsing failed. Error: {last_error}"
        )
        raise HTTPException(status_code=429 if is_quota else 500, detail=detail)

    profile["resume_url"] = gcs_url

    # 3. Persist session
    session_id = str(uuid.uuid4())
    db.save_session(session_id, {
        "profile": profile,
        "created_at": session_id,  # uuid as timestamp proxy
        "status": "profile_ready"
    })

    return {"session_id": session_id, "profile": profile}
