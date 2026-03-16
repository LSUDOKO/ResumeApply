import os
from supabase import create_client, Client
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class SupabaseDB:
    def __init__(self):
        url: str = os.environ.get("SUPABASE_URL")
        key: str = os.environ.get("SUPABASE_KEY")
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")
        self.client: Client = create_client(url, key)

    # --- Database Operations ---

    def save_resume_metadata(self, name: str, email: str, phone: str, profile_json: dict, resume_url: str):
        """Saves resume profile and metadata to the 'resumes' table."""
        data = {
            "name": name,
            "email": email,
            "phone": phone,
            "current_role": profile_json.get("current_role"),
            "years_experience": profile_json.get("years_experience"),
            "skills": profile_json.get("skills"),
            "education": profile_json.get("education"),
            "summary": profile_json.get("summary"),
            "resume_url": resume_url,
            "profile_json": profile_json
        }
        response = self.client.table("resumes").insert(data).execute()
        return response.data[0] if response.data else None

    def save_session(self, session_id: str, profile_id: str, status: str = "profile_ready"):
        """Creates or updates an agent session in 'agent_sessions'."""
        data = {
            "id": session_id,
            "profile_id": profile_id,
            "status": status
        }
        # Using upsert to handle both creation and updates
        response = self.client.table("agent_sessions").upsert(data).execute()
        return response.data[0] if response.data else None

    def get_session(self, session_id: str):
        """Retrieves session data joining with profile metadata."""
        response = self.client.table("agent_sessions").select("*, profile:resumes(*)").eq("id", session_id).single().execute()
        return response.data

    def add_application(self, session_id: str, job_title: str, company: str, status: str, match_score: int, reason: str = "", cover_letter: str = ""):
        """Logs a job application or skip in 'applications'."""
        data = {
            "session_id": session_id,
            "job_title": job_title,
            "company": company,
            "status": status,
            "match_score": match_score,
            "reason": reason,
            "cover_letter": cover_letter
        }
        response = self.client.table("applications").insert(data).execute()
        return response.data[0] if response.data else None

    # --- Storage Operations ---

    def upload_resume_file(self, filename: str, content: bytes):
        """Uploads file to Supabase 'resumes' bucket and returns public URL."""
        bucket_name = "resumes"
        # Supabase storage expects a file path identifier
        file_path = f"public/{filename}"
        
        # Upload
        self.client.storage.from_(bucket_name).upload(
            path=file_path,
            file=content,
            file_options={"content-type": "application/pdf"}
        )
        
        # Get Public URL
        response = self.client.storage.from_(bucket_name).get_public_url(file_path)
        return response

db = SupabaseDB()
