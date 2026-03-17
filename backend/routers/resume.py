from fastapi import APIRouter, UploadFile, File, HTTPException
import json, uuid, re, io, asyncio
from lib.gcp_helper import gcp_helper
from lib.gemini_helper import get_gemini_model

router = APIRouter()

RESUME_PROMPT = """
Extract resume data and return structured JSON only, no markdown:
{
  "name": "", 
  "email": "", 
  "phone": "",
  "current_role": "", 
  "years_experience": 0,
  "skills": [], 
  "education": "",
  "preferred_roles": [], 
  "summary": "",
  "achievements": [], 
  "projects": [],
  "previous_roles": []
}
Resume Text:
"""

def extract_text_locally(content: bytes) -> str:
    """
    CPU-bound task: Extracts text using pypdf.
    Returns plain text or empty string on failure.
    """
    try:
        from pypdf import PdfReader
        reader = PdfReader(io.BytesIO(content))
        text_parts = [page.extract_text() or "" for page in reader.pages]
        return "\n".join(text_parts).strip()[:10000] # Limit to 10k tokens
    except Exception as e:
        print(f"pypdf extraction failed: {e}")
        return ""

@router.post("/upload")
async def upload_resume(file: UploadFile = File(...)):
    content = await file.read()

    # 1. Upload to GCS via helper
    resume_url = gcp_helper.upload_resume(file.filename, content)

    # 2. Local Text Extraction (Offloaded to thread to avoid blocking loop)
    is_pdf = file.filename.lower().endswith(".pdf")
    if is_pdf:
        resume_text = await asyncio.to_thread(extract_text_locally, content)
    else:
        # Fallback for plain text files (UTF-8)
        resume_text = content.decode("utf-8", errors="ignore").strip()[:10000]

    if not resume_text:
        raise HTTPException(status_code=422, detail="Could not extract text from file.")

    # 3. High-Speed Processing with Gemini 2.5 Flash-Lite
    model = get_gemini_model()
    profile = None
    last_error = "Unknown error"

    try:
        # Send clean text to Gemini (Express Lane)
        response = await model.generate_content_async(RESUME_PROMPT + resume_text)
        match = re.search(r'\{.*\}', response.text, re.DOTALL)
        if match:
            profile = json.loads(match.group())
            print(f"Resume parsed successfully via Express Lane")
    except Exception as e:
        print(f"Parsing error: {e}")
        last_error = str(e)

    if not profile:
        is_quota = "429" in last_error
        detail = (
            "Gemini API Rate Limit hit. Please wait a few seconds."
            if is_quota else
            f"Resume parsing failed: {last_error}"
        )
        raise HTTPException(status_code=429 if is_quota else 500, detail=detail)

    profile["resume_url"] = resume_url

    # 4. Save metadata to Firestore
    session_id = str(uuid.uuid4())
    gcp_helper.save_session(session_id, {
        "profile": profile,
        "created_at": session_id,
        "status": "profile_ready"
    })

    return {"session_id": session_id, "profile": profile}
