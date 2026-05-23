from __future__ import annotations

from app.repository.db import Database
from app.utils.date import now_iso


class JobRepository:
    MAX_JOB_RUNS = 100

    def __init__(self, database: Database) -> None:
        self.database = database

    def init_table(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS job_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name TEXT NOT NULL,
            run_at TEXT NOT NULL,
            status TEXT,
            message TEXT,
            duration_ms INTEGER
        )
        """
        conn = self.database.connect()
        conn.execute(sql)

    def create_run(self, job_name: str) -> int:
        conn = self.database.connect()
        cursor = conn.execute(
            "INSERT INTO job_runs (job_name, run_at) VALUES (?, ?)",
            (job_name, now_iso()),
        )
        return int(cursor.lastrowid)

    def finish_run(self, run_id: int, status: str, message: str, duration_ms: int) -> None:
        conn = self.database.connect()
        conn.execute(
            "UPDATE job_runs SET status = ?, message = ?, duration_ms = ? WHERE id = ?",
            (status, message, duration_ms, run_id),
        )
        self._trim_history(conn)

    def list_recent(self, limit: int = 20) -> list[dict]:
        conn = self.database.connect()
        rows = conn.execute(
            "SELECT id, job_name, run_at, status, message, duration_ms FROM job_runs ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def get_latest_success(self, job_name: str) -> dict | None:
        conn = self.database.connect()
        row = conn.execute(
            """
            SELECT id, job_name, run_at, status, message, duration_ms
            FROM job_runs
            WHERE job_name = ? AND status = 'success'
            ORDER BY id DESC
            LIMIT 1
            """,
            (job_name,),
        ).fetchone()
        return dict(row) if row else None

    def _trim_history(self, conn) -> None:
        rows = conn.execute(
            "SELECT id FROM job_runs ORDER BY id DESC LIMIT -1 OFFSET ?",
            (self.MAX_JOB_RUNS,),
        ).fetchall()
        if not rows:
            return
        delete_ids = [int(row["id"]) for row in rows]
        placeholders = ",".join("?" for _ in delete_ids)
        conn.execute(f"DELETE FROM job_runs WHERE id IN ({placeholders})", delete_ids)
