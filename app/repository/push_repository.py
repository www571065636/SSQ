from __future__ import annotations

from app.models.dto import PushResultDTO
from app.repository.db import Database
from app.utils.date import now_iso


class PushRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def init_table(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS push_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            batch_no TEXT NOT NULL,
            channel TEXT NOT NULL,
            target TEXT NOT NULL,
            message_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            response_body TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        """
        conn = self.database.connect()
        conn.execute(sql)

    def save(self, result: PushResultDTO) -> None:
        conn = self.database.connect()
        conn.execute(
            """
            INSERT INTO push_records (
                batch_no, channel, target, message_type, payload, response_body, status, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.batch_no,
                result.channel,
                result.target,
                result.message_type,
                result.payload,
                result.response_body,
                result.status,
                now_iso(),
            ),
        )
