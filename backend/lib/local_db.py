import json
import os
import shutil
from pathlib import Path

class LocalDatabase:
    def __init__(self, data_dir="data"):
        self.data_dir = Path(data_dir)
        self.db_path = self.data_dir / "db.json"
        self.resume_dir = self.data_dir / "resumes"
        
        # Ensure directories exist
        self.data_dir.mkdir(exist_ok=True)
        self.resume_dir.mkdir(exist_ok=True)
        
        if not self.db_path.exists():
            with open(self.db_path, "w") as f:
                json.dump({"sessions": {}}, f)

    def _read_db(self):
        try:
            with open(self.db_path, "r") as f:
                return json.load(f)
        except:
            return {"sessions": {}}

    def _write_db(self, data):
        with open(self.db_path, "w") as f:
            json.dump(data, f, indent=2)

    def save_session(self, session_id, data):
        db = self._read_db()
        db["sessions"][session_id] = data
        self._write_db(db)

    def get_session(self, session_id):
        db = self._read_db()
        return db["sessions"].get(session_id)

    def save_resume(self, filename, content):
        path = self.resume_dir / filename
        with open(path, "wb") as f:
            f.write(content)
        return str(path)

db = LocalDatabase()
