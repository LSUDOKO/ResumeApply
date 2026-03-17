import json
import asyncio
from pathlib import Path

class LocalDatabase:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.db_path = self.data_dir / "db.json"
        self.resume_dir = self.data_dir / "resumes"
        self._lock = asyncio.Lock()

        self.data_dir.mkdir(exist_ok=True)
        self.resume_dir.mkdir(exist_ok=True)

        if not self.db_path.exists():
            with open(self.db_path, "w") as f:
                json.dump({"sessions": {}}, f)

    def _read(self):
        try:
            with open(self.db_path, "r") as f:
                return json.load(f)
        except Exception:
            return {"sessions": {}}

    def _write(self, data):
        with open(self.db_path, "w") as f:
            json.dump(data, f, indent=2)

    # ── sync helpers (used at startup / non-concurrent paths) ──────────────
    def get_session(self, session_id: str):
        return self._read()["sessions"].get(session_id)

    def save_resume(self, filename: str, content: bytes) -> str:
        path = self.resume_dir / filename
        with open(path, "wb") as f:
            f.write(content)
        return str(path)

    # ── async-safe writes ───────────────────────────────────────────────────
    async def save_session_async(self, session_id: str, data: dict):
        async with self._lock:
            db = self._read()
            db["sessions"][session_id] = data
            self._write(db)

    async def append_application(self, session_id: str, application: dict):
        async with self._lock:
            db = self._read()
            session = db["sessions"].setdefault(session_id, {})
            session.setdefault("applications", []).append(application)
            self._write(db)

    # ── sync save kept for non-async callers (router startup etc.) ──────────
    def save_session(self, session_id: str, data: dict):
        db = self._read()
        db["sessions"][session_id] = data
        self._write(db)

    def get_applications(self, session_id: str) -> list:
        session = self.get_session(session_id)
        return session.get("applications", []) if session else []

db = LocalDatabase()
