"""Opt-in, user-controlled SQLite memory; never save tool outputs or retrieved pages.

Reading preferences must not create a database or any parent directories.
Only explicit set commands initialize the memory database.
"""

import sqlite3
from contextlib import closing
from pathlib import Path


class MemoryStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path).expanduser()

    def _connect(self, mode="ro"):
        if mode == "create":
            self.db_path.parent.mkdir(parents=True, exist_ok=True)
            db = sqlite3.connect(self.db_path)
            db.execute("""CREATE TABLE IF NOT EXISTS memory (
                project TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL,
                PRIMARY KEY(project, key))""")
            return db
        if mode not in ("ro", "rw"):
            raise ValueError("Invalid memory access mode")
        # URI read/write modes refuse to create a database if it was removed.
        return sqlite3.connect(self.db_path.resolve().as_uri() + "?mode=" + mode, uri=True)

    def set(self, project: str, key: str, value: str):
        with closing(self._connect("create")) as db, db:
            db.execute("INSERT OR REPLACE INTO memory(project, key, value) VALUES (?, ?, ?)",
                       (project, key, value))

    def get(self, project: str, key: str) -> str | None:
        if not self.db_path.is_file():
            return None
        with closing(self._connect()) as db:
            row = db.execute("SELECT value FROM memory WHERE project = ? AND key = ?",
                             (project, key)).fetchone()
        return row[0] if row else None

    def all(self, project: str) -> dict[str, str]:
        if not self.db_path.is_file():
            return {}
        with closing(self._connect()) as db:
            rows = db.execute("SELECT key, value FROM memory WHERE project = ? ORDER BY key", (project,))
            return dict(rows.fetchall())

    def delete(self, project: str, key: str):
        if not self.db_path.is_file():
            return
        with closing(self._connect("rw")) as db, db:
            db.execute("DELETE FROM memory WHERE project = ? AND key = ?", (project, key))
