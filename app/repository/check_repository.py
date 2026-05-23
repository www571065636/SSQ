from __future__ import annotations

from app.models.dto import CheckResultDTO
from app.repository.db import Database
from app.utils.date import now_iso


class CheckRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def init_table(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS check_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recommendation_id INTEGER NOT NULL,
            issue_no TEXT NOT NULL,
            red_hits INTEGER NOT NULL,
            blue_hit INTEGER NOT NULL,
            prize_level TEXT,
            prize_amount REAL,
            checked_at TEXT NOT NULL,
            UNIQUE(recommendation_id, issue_no)
        )
        """
        conn = self.database.connect()
        conn.execute(sql)

    def save_results(self, items: list[CheckResultDTO]) -> int:
        sql = """
        INSERT INTO check_results (
            recommendation_id, issue_no, red_hits, blue_hit, prize_level, prize_amount, checked_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(recommendation_id, issue_no) DO NOTHING
        """
        inserted = 0
        conn = self.database.connect()
        for item in items:
            cursor = conn.execute(
                sql,
                (
                    item.recommendation_id,
                    item.issue_no,
                    item.red_hits,
                    int(item.blue_hit),
                    item.prize_level,
                    item.prize_amount,
                    now_iso(),
                ),
            )
            inserted += max(cursor.rowcount, 0)
        return inserted

    def exists_for_issue(self, issue_no: str) -> bool:
        conn = self.database.connect()
        row = conn.execute("SELECT 1 FROM check_results WHERE issue_no = ? LIMIT 1", (issue_no,)).fetchone()
        return row is not None

    def list_recent(self, limit: int = 20) -> list[dict]:
        sql = """
        SELECT recommendation_id, issue_no, red_hits, blue_hit, prize_level, prize_amount, checked_at
        FROM check_results
        ORDER BY checked_at DESC, id DESC
        LIMIT ?
        """
        conn = self.database.connect()
        rows = conn.execute(sql, (limit,)).fetchall()
        return [dict(row) for row in rows]

    def list_all(self) -> list[dict]:
        sql = """
        SELECT recommendation_id, issue_no, red_hits, blue_hit, prize_level, prize_amount, checked_at
        FROM check_results
        ORDER BY checked_at DESC, id DESC
        """
        conn = self.database.connect()
        rows = conn.execute(sql).fetchall()
        return [dict(row) for row in rows]
