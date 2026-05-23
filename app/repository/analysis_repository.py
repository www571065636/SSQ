from __future__ import annotations

import json

from app.models.dto import AnalysisSnapshotDTO
from app.repository.db import Database
from app.utils.date import now_iso


class AnalysisRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def init_table(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS analysis_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            snapshot_date TEXT NOT NULL,
            based_on_issue TEXT NOT NULL,
            window_size INTEGER NOT NULL,
            red_frequency_json TEXT NOT NULL,
            blue_frequency_json TEXT NOT NULL,
            weighted_red_frequency_json TEXT NOT NULL DEFAULT '{}',
            weighted_blue_frequency_json TEXT NOT NULL DEFAULT '{}',
            layered_frequency_json TEXT NOT NULL DEFAULT '{}',
            omission_json TEXT NOT NULL,
            hot_cold_json TEXT NOT NULL,
            pattern_stats_json TEXT NOT NULL,
            feature_stats_json TEXT NOT NULL DEFAULT '{}',
            strategy_metrics_json TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL
        )
        """
        conn = self.database.connect()
        conn.execute(sql)
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(analysis_snapshots)").fetchall()}
        if "weighted_red_frequency_json" not in columns:
            conn.execute("ALTER TABLE analysis_snapshots ADD COLUMN weighted_red_frequency_json TEXT NOT NULL DEFAULT '{}'")
        if "weighted_blue_frequency_json" not in columns:
            conn.execute("ALTER TABLE analysis_snapshots ADD COLUMN weighted_blue_frequency_json TEXT NOT NULL DEFAULT '{}'")
        if "layered_frequency_json" not in columns:
            conn.execute("ALTER TABLE analysis_snapshots ADD COLUMN layered_frequency_json TEXT NOT NULL DEFAULT '{}'")
        if "feature_stats_json" not in columns:
            conn.execute("ALTER TABLE analysis_snapshots ADD COLUMN feature_stats_json TEXT NOT NULL DEFAULT '{}'")
        if "strategy_metrics_json" not in columns:
            conn.execute("ALTER TABLE analysis_snapshots ADD COLUMN strategy_metrics_json TEXT NOT NULL DEFAULT '{}'")

    def save_snapshot(self, snapshot: AnalysisSnapshotDTO) -> int:
        sql = """
        INSERT INTO analysis_snapshots (
            snapshot_date, based_on_issue, window_size, red_frequency_json,
            blue_frequency_json, weighted_red_frequency_json, weighted_blue_frequency_json,
            layered_frequency_json, omission_json, hot_cold_json, pattern_stats_json,
            feature_stats_json, strategy_metrics_json, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        hot_cold = {"hot_numbers": snapshot.hot_numbers, "cold_numbers": snapshot.cold_numbers}
        layered_frequency = {
            "red": snapshot.layered_red_frequency,
            "blue": snapshot.layered_blue_frequency,
        }
        params = (
            snapshot.snapshot_date,
            snapshot.based_on_issue,
            snapshot.window_size,
            json.dumps(snapshot.red_frequency, ensure_ascii=False),
            json.dumps(snapshot.blue_frequency, ensure_ascii=False),
            json.dumps(snapshot.weighted_red_frequency, ensure_ascii=False),
            json.dumps(snapshot.weighted_blue_frequency, ensure_ascii=False),
            json.dumps(layered_frequency, ensure_ascii=False),
            json.dumps(snapshot.omission_map, ensure_ascii=False),
            json.dumps(hot_cold, ensure_ascii=False),
            json.dumps(snapshot.pattern_stats, ensure_ascii=False),
            json.dumps(snapshot.feature_stats, ensure_ascii=False),
            json.dumps(snapshot.strategy_metrics, ensure_ascii=False),
            now_iso(),
        )
        conn = self.database.connect()
        cursor = conn.execute(sql, params)
        return int(cursor.lastrowid)

    def get_latest_snapshot(self) -> AnalysisSnapshotDTO | None:
        sql = "SELECT * FROM analysis_snapshots ORDER BY id DESC LIMIT 1"
        conn = self.database.connect()
        row = conn.execute(sql).fetchone()
        if not row:
            return None
        hot_cold = json.loads(row["hot_cold_json"])
        layered_frequency = json.loads(row["layered_frequency_json"]) if row["layered_frequency_json"] else {}
        return AnalysisSnapshotDTO(
            based_on_issue=row["based_on_issue"],
            snapshot_date=row["snapshot_date"],
            window_size=row["window_size"],
            red_frequency={int(k): float(v) for k, v in json.loads(row["red_frequency_json"]).items()},
            blue_frequency={int(k): float(v) for k, v in json.loads(row["blue_frequency_json"]).items()},
            weighted_red_frequency={int(k): float(v) for k, v in json.loads(row["weighted_red_frequency_json"]).items()},
            weighted_blue_frequency={int(k): float(v) for k, v in json.loads(row["weighted_blue_frequency_json"]).items()},
            layered_red_frequency={
                str(layer): {int(k): float(v) for k, v in values.items()}
                for layer, values in layered_frequency.get("red", {}).items()
            },
            layered_blue_frequency={
                str(layer): {int(k): float(v) for k, v in values.items()}
                for layer, values in layered_frequency.get("blue", {}).items()
            },
            omission_map={str(k): int(v) for k, v in json.loads(row["omission_json"]).items()},
            hot_numbers=[int(item) for item in hot_cold["hot_numbers"]],
            cold_numbers=[int(item) for item in hot_cold["cold_numbers"]],
            pattern_stats=json.loads(row["pattern_stats_json"]),
            feature_stats=json.loads(row["feature_stats_json"]) if row["feature_stats_json"] else {},
            strategy_metrics=json.loads(row["strategy_metrics_json"]) if row["strategy_metrics_json"] else {},
            snapshot_id=int(row["id"]),
        )
