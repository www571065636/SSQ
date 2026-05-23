from __future__ import annotations

import json

from app.models.dto import RecommendationDTO
from app.repository.db import Database
from app.utils.date import now_iso
from app.utils.validators import format_red_numbers, parse_red_numbers, validate_recommendation


class RecommendationRepository:
    MAX_RECOMMENDATIONS = 1000

    def __init__(self, database: Database) -> None:
        self.database = database

    def init_table(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_no TEXT NOT NULL,
            recommend_date TEXT NOT NULL,
            target_issue_no TEXT,
            strategy_name TEXT NOT NULL,
            red_numbers TEXT NOT NULL,
            blue_number TEXT NOT NULL,
            feature_summary TEXT NOT NULL,
            snapshot_id INTEGER,
            push_status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
        conn = self.database.connect()
        conn.execute(sql)

    def save_batch(self, items: list[RecommendationDTO], push_status: str = "pending") -> int:
        inserted = 0
        sql = """
        INSERT INTO recommendations (
            batch_no, recommend_date, target_issue_no, strategy_name, red_numbers,
            blue_number, feature_summary, snapshot_id, push_status, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        conn = self.database.connect()
        for item in items:
            validated = validate_recommendation(item)
            cursor = conn.execute(
                sql,
                (
                    validated.batch_no,
                    validated.recommend_date,
                    validated.target_issue_no,
                    validated.strategy_name,
                    format_red_numbers(validated.red_numbers),
                    f"{validated.blue_number:02d}",
                    json.dumps(validated.feature_summary, ensure_ascii=False),
                    validated.snapshot_id,
                    push_status,
                    now_iso(),
                ),
            )
            validated.recommendation_id = int(cursor.lastrowid)
            inserted += 1
        self._trim_history(conn)
        return inserted

    def list_by_issue(self, issue_no: str) -> list[RecommendationDTO]:
        sql = "SELECT * FROM recommendations WHERE target_issue_no = ? ORDER BY id ASC"
        conn = self.database.connect()
        rows = conn.execute(sql, (issue_no,)).fetchall()
        return [self._row_to_dto(row) for row in rows]

    def list_unchecked(self) -> list[RecommendationDTO]:
        sql = """
        SELECT r.* FROM recommendations r
        LEFT JOIN check_results c ON c.recommendation_id = r.id
        WHERE c.id IS NULL
        ORDER BY r.id ASC
        """
        conn = self.database.connect()
        rows = conn.execute(sql).fetchall()
        return [self._row_to_dto(row) for row in rows]

    def list_recent(self, limit: int = 20) -> list[RecommendationDTO]:
        sql = "SELECT * FROM recommendations ORDER BY recommend_date DESC, id DESC LIMIT ?"
        conn = self.database.connect()
        rows = conn.execute(sql, (limit,)).fetchall()
        return [self._row_to_dto(row) for row in rows]

    def list_all(self) -> list[RecommendationDTO]:
        sql = "SELECT * FROM recommendations ORDER BY recommend_date DESC, id DESC"
        conn = self.database.connect()
        rows = conn.execute(sql).fetchall()
        return [self._row_to_dto(row) for row in rows]

    def update_push_status(self, batch_no: str, status: str) -> None:
        conn = self.database.connect()
        conn.execute("UPDATE recommendations SET push_status = ? WHERE batch_no = ?", (status, batch_no))

    def _trim_history(self, conn) -> None:
        rows = conn.execute(
            "SELECT id FROM recommendations ORDER BY recommend_date DESC, id DESC LIMIT -1 OFFSET ?",
            (self.MAX_RECOMMENDATIONS,),
        ).fetchall()
        if not rows:
            return
        delete_ids = [int(row["id"]) for row in rows]
        placeholders = ",".join("?" for _ in delete_ids)
        table_names = {str(row["name"]) for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
        if "check_results" in table_names:
            conn.execute(f"DELETE FROM check_results WHERE recommendation_id IN ({placeholders})", delete_ids)
        conn.execute(f"DELETE FROM recommendations WHERE id IN ({placeholders})", delete_ids)

    @staticmethod
    def _row_to_dto(row) -> RecommendationDTO:
        return RecommendationDTO(
            batch_no=row["batch_no"],
            recommend_date=row["recommend_date"],
            target_issue_no=row["target_issue_no"],
            strategy_name=row["strategy_name"],
            red_numbers=parse_red_numbers(row["red_numbers"]),
            blue_number=int(row["blue_number"]),
            feature_summary=json.loads(row["feature_summary"]),
            snapshot_id=row["snapshot_id"],
            recommendation_id=row["id"],
        )
