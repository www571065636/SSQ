from __future__ import annotations

import sqlite3
from pathlib import Path


class Database:
    def __init__(self, db_path: str) -> None:
        self.db_path = db_path
        db_file = Path(db_path)
        db_file.parent.mkdir(parents=True, exist_ok=True)
        journal_file = db_file.with_name(f"{db_file.name}-journal")
        if journal_file.exists() and (not db_file.exists() or db_file.stat().st_size == 0):
            try:
                journal_file.unlink(missing_ok=True)
            except PermissionError:
                pass

    def connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.db_path, isolation_level=None, timeout=30, check_same_thread=False)
        connection.row_factory = sqlite3.Row
        # Some sandboxed Windows workspaces reject SQLite journal file writes.
        # Use memory journal mode so the project remains runnable in this environment.
        connection.execute("PRAGMA journal_mode=MEMORY")
        connection.execute("PRAGMA synchronous=OFF")
        connection.execute("PRAGMA temp_store=MEMORY")
        return connection
