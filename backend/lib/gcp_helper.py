"""
Unified GCP helper — wraps Firestore for session persistence.
Falls back to in-memory dict if Firestore is unavailable (local dev).
"""
import os
from typing import Optional

_in_memory: dict = {}


class GCPHelper:
    def __init__(self):
        self._db = None
        self._collection = "sessions"

    def _get_db(self):
        if self._db is None:
            try:
                from google.cloud import firestore
                self._db = firestore.Client(project=os.getenv("PROJECT_ID"))
            except Exception as e:
                print(f"Firestore unavailable, using in-memory store: {e}")
                self._db = "memory"
        return self._db

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
        _in_memory[session_id] = data  # always keep in-memory copy
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


gcp_helper = GCPHelper()
