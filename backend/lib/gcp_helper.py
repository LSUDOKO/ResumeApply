"""
Unified GCP helper — wraps Firestore for session persistence and GCS for resume storage.
Falls back to in-memory/local stores if GCP is unavailable.
"""
import os
from typing import Optional

_in_memory: dict = {}

class GCPHelper:
    def __init__(self):
        self._db = None
        self._storage_client = None
        self._collection = "sessions"
        self._bucket_name = os.getenv("GCS_BUCKET")
        self._project_id = os.getenv("PROJECT_ID")

    def _get_db(self):
        if self._db is None:
            try:
                from google.cloud import firestore
                # Google libraries automatically look for GOOGLE_APPLICATION_CREDENTIALS
                self._db = firestore.Client(project=self._project_id)
                print(f"Firestore initialized for project: {self._project_id}")
            except Exception as e:
                print(f"Firestore unavailable, using in-memory store: {e}")
                self._db = "memory"
        return self._db

    def _get_storage(self):
        if self._storage_client is None:
            try:
                from google.cloud import storage
                self._storage_client = storage.Client(project=self._project_id)
                print(f"GCS initialized for project: {self._project_id}")
            except Exception as e:
                print(f"GCS unavailable: {e}")
                self._storage_client = "memory"
        return self._storage_client

    def get_session(self, session_id: str) -> Optional[dict]:
        db = self._get_db()
        if db == "memory":
            return _in_memory.get(session_id)
        try:
            doc = db.collection(self._collection).document(session_id).get()
            return doc.to_dict() if doc.exists else None
        except Exception as e:
            print(f"Firestore get error: {e}")
            return _in_memory.get(session_id)

    def save_session(self, session_id: str, data: dict):
        _in_memory[session_id] = data
        db = self._get_db()
        if db == "memory":
            return
        try:
            db.collection(self._collection).document(session_id).set(data)
        except Exception as e:
            print(f"Firestore save error: {e}")

    def append_application(self, session_id: str, application: dict):
        session_data = self.get_session(session_id) or {}
        apps = session_data.get("applications", [])
        apps.append(application)
        session_data["applications"] = apps
        self.save_session(session_id, session_data)

    def upload_resume(self, filename: str, content: bytes) -> str:
        """Uploads to GCS and returnsgs:// URI, or local fallback."""
        client = self._get_storage()
        if client == "memory" or not self._bucket_name:
            return f"local://{filename}"
        
        try:
            bucket = client.bucket(self._bucket_name)
            if not bucket.exists():
                bucket = client.create_bucket(self._bucket_name)
            
            blob = bucket.blob(f"resumes/{filename}")
            blob.upload_from_string(content, content_type="application/octet-stream")
            return f"gs://{self._bucket_name}/resumes/{filename}"
        except Exception as e:
            print(f"GCS upload error: {e}")
            return f"local://{filename}"

gcp_helper = GCPHelper()
