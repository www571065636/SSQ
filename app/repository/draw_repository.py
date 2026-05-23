from __future__ import annotations

import json
from typing import Iterable

from app.models.dto import DrawResultDTO
from app.repository.db import Database
from app.utils.date import now_iso
from app.utils.validators import validate_draw


class DrawRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def init_table(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS draw_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            issue_no TEXT UNIQUE NOT NULL,
            draw_date TEXT NOT NULL,
            red_1 INTEGER NOT NULL,
            red_2 INTEGER NOT NULL,
            red_3 INTEGER NOT NULL,
            red_4 INTEGER NOT NULL,
            red_5 INTEGER NOT NULL,
            red_6 INTEGER NOT NULL,
            blue_1 INTEGER NOT NULL,
            source_name TEXT NOT NULL,
            source_url TEXT NOT NULL,
            raw_payload TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
        conn = self.database.connect()
        conn.execute(sql)

    def save_many(self, draws: list[DrawResultDTO]) -> int:
        return sum(1 for draw in draws if self.save_one(draw))

    def save_one(self, draw: DrawResultDTO) -> bool:
        validated = validate_draw(draw)
        payload = json.dumps(validated.raw_payload, ensure_ascii=False) if isinstance(validated.raw_payload, dict) else validated.raw_payload
        sql = """
        INSERT INTO draw_results (
            issue_no, draw_date, red_1, red_2, red_3, red_4, red_5, red_6, blue_1,
            source_name, source_url, raw_payload, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(issue_no) DO NOTHING
        """
        params = (
            validated.issue_no,
            validated.draw_date,
            *validated.red_numbers,
            validated.blue_number,
            validated.source_name,
            validated.source_url,
            payload,
            now_iso(),
            now_iso(),
        )
        conn = self.database.connect()
        cursor = conn.execute(sql, params)
        return cursor.rowcount > 0

    def get_latest(self) -> DrawResultDTO | None:
        sql = "SELECT * FROM draw_results ORDER BY draw_date DESC, issue_no DESC LIMIT 1"
        conn = self.database.connect()
        row = conn.execute(sql).fetchone()
        return self._row_to_dto(row) if row else None

    def get_by_issue(self, issue_no: str) -> DrawResultDTO | None:
        sql = "SELECT * FROM draw_results WHERE issue_no = ?"
        conn = self.database.connect()
        row = conn.execute(sql, (issue_no,)).fetchone()
        return self._row_to_dto(row) if row else None

    def list_by_range(self, start_date: str, end_date: str) -> list[DrawResultDTO]:
        sql = """
        SELECT * FROM draw_results
        WHERE draw_date BETWEEN ? AND ?
        ORDER BY issue_no ASC
        """
        conn = self.database.connect()
        rows = conn.execute(sql, (start_date, end_date)).fetchall()
        return [self._row_to_dto(row) for row in rows]

    def list_latest(self, limit: int) -> list[DrawResultDTO]:
        sql = "SELECT * FROM draw_results ORDER BY draw_date DESC, issue_no DESC LIMIT ?"
        conn = self.database.connect()
        rows = conn.execute(sql, (limit,)).fetchall()
        return [self._row_to_dto(row) for row in reversed(rows)]

    def list_all(self) -> list[DrawResultDTO]:
        conn = self.database.connect()
        rows = conn.execute("SELECT * FROM draw_results ORDER BY issue_no ASC").fetchall()
        return [self._row_to_dto(row) for row in rows]

    def list_recent(self, limit: int = 30) -> list[DrawResultDTO]:
        sql = "SELECT * FROM draw_results ORDER BY draw_date DESC, issue_no DESC LIMIT ?"
        conn = self.database.connect()
        rows = conn.execute(sql, (limit,)).fetchall()
        return [self._row_to_dto(row) for row in rows]

    def exists_issue(self, issue_no: str) -> bool:
        conn = self.database.connect()
        row = conn.execute("SELECT 1 FROM draw_results WHERE issue_no = ?", (issue_no,)).fetchone()
        return row is not None

    def count(self) -> int:
        conn = self.database.connect()
        row = conn.execute("SELECT COUNT(*) AS total FROM draw_results").fetchone()
        return int(row["total"]) if row else 0

    @staticmethod
    def _row_to_dto(row) -> DrawResultDTO:
        return DrawResultDTO(
            issue_no=row["issue_no"],
            draw_date=row["draw_date"],
            red_numbers=[row["red_1"], row["red_2"], row["red_3"], row["red_4"], row["red_5"], row["red_6"]],
            blue_number=row["blue_1"],
            source_name=row["source_name"],
            source_url=row["source_url"],
            raw_payload=row["raw_payload"],
        )
