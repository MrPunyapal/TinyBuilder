"""Opt-in, user-controlled SQLite memory; never save tool outputs or retrieved pages."""

import sqlite3
from contextlib import closing
from pathlib import Path


class MemoryStore:
    def __init__(self, db_path: Path):
        self.db_path = Path(db_path).expanduser()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute("""CREATE TABLE IF NOT EXISTS memory (
                project TEXT NOT NULL, key TEXT NOT NULL, value TEXT NOT NULL,
                PRIMARY KEY(project, key))""")

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def set(self, project: str, key: str, value: str):
        with closing(self._connect()) as db, db:
            db.execute("INSERT OR REPLACE INTO memory(project, key, value) VALUES (?, ?, ?)",
                       (project, key, value))

    def get(self, project: str, key: str) -> str | None:
        with closing(self._connect()) as db, db:
            row = db.execute("SELECT value FROM memory WHERE project = ? AND key = ?",
                             (project, key)).fetchone()
        return row[0] if row else None

    def all(self, project: str) -> dict[str, str]:
        with closing(self._connect()) as db, db:
            rows = db.execute("SELECT key, value FROM memory WHERE project = ? ORDER BY key", (project,))
            return dict(rows.fetchall())

    def delete(self, project: str, key: str):
        with closing(self._connect()) as db, db:
            db.execute("DELETE FROM memory WHERE project = ? AND key = ?", (project, key))
