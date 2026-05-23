from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


DEFAULT_CONFIG: dict[str, Any] = {
    "app": {"timezone": "Asia/Shanghai", "log_level": "INFO", "scheduled_log_path": "logs/scheduled_jobs.log"},
    "database": {"driver": "sqlite", "path": "data/ssq_app.db"},
    "crawler": {
        "source_type": "json_file",
        "source_name": "sample",
        "source_url": "data/sample_draws.json",
        "timeout_seconds": 10,
        "retry_times": 2,
        "issue_count": 100,
    },
    "analysis": {
        "rolling_window": 30,
        "hot_ratio": 0.3,
        "cold_ratio": 0.3,
        "hot_top_n": 10,
        "cold_top_n": 10,
        "recent_window": 30,
        "mid_window": 100,
        "recent_weight": 1.8,
        "mid_weight": 1.25,
        "base_weight": 1.0,
        "backtest_lookback": 60,
    },
    "recommendation": {
        "daily_count": 5,
        "candidate_pool_size": 300,
        "sum_range": [85, 110],
        "odd_even_allowed": ["3:3", "4:2", "2:4"],
        "zone_allowed": ["2:2:2", "1:2:3", "3:2:1", "2:1:3", "3:1:2"],
        "max_attempts": 500,
    },
    "strategy": {
        "adjust_cycle_issues": 100,
        "enabled": [
            {"name": "random", "weight": 0.4, "params": {}},
            {"name": "hot_cold", "weight": 0.4, "params": {"hot_count": 4, "cold_count": 2}},
            {"name": "pattern_filter", "weight": 0.2, "params": {}},
        ],
    },
    "notifier": {
        "enabled": False,
        "default_channel": "console",
        "target": "",
        "serverchan_sendkey": "",
        "wecom_webhook": "",
    },
    "scheduler": {"prepare_time": "20:00", "result_time": "21:30", "draw_days": ["tue", "thu", "sun"]},
    "prize_rules": {
        "first": None,
        "second": None,
        "third": 3000,
        "fourth": 200,
        "fifth": 10,
        "sixth": 5,
    },
}


class ConfigService:
    def __init__(self) -> None:
        self._config: dict[str, Any] = {}

    def load(self, path: str = "config.json") -> dict[str, Any]:
        config = json.loads(json.dumps(DEFAULT_CONFIG))
        config_path = Path(path)
        if config_path.exists():
            loaded = json.loads(config_path.read_text(encoding="utf-8"))
            _deep_merge(config, loaded)
        self._apply_env_overrides(config)
        self.validate(config)
        self._config = config
        return config

    def validate(self, config: dict[str, Any]) -> None:
        db_path = config["database"]["path"]
        if not db_path:
            raise ValueError("database.path is required")
        rolling_window = int(config["analysis"]["rolling_window"])
        if rolling_window <= 0:
            raise ValueError("analysis.rolling_window must be positive")
        daily_count = int(config["recommendation"]["daily_count"])
        if daily_count <= 0:
            raise ValueError("recommendation.daily_count must be positive")

    def get(self, key_path: str, default: Any = None) -> Any:
        if not self._config:
            self.load()
        current: Any = self._config
        for key in key_path.split("."):
            if not isinstance(current, dict) or key not in current:
                return default
            current = current[key]
        return current

    def _apply_env_overrides(self, config: dict[str, Any]) -> None:
        if os.getenv("SSQ_DB_PATH"):
            config["database"]["path"] = os.environ["SSQ_DB_PATH"]
        if os.getenv("SSQ_SOURCE_URL"):
            config["crawler"]["source_url"] = os.environ["SSQ_SOURCE_URL"]
        if os.getenv("SSQ_SOURCE_TYPE"):
            config["crawler"]["source_type"] = os.environ["SSQ_SOURCE_TYPE"]
        if os.getenv("SSQ_NOTIFIER_ENABLED"):
            config["notifier"]["enabled"] = os.environ["SSQ_NOTIFIER_ENABLED"].lower() == "true"


def _deep_merge(base: dict[str, Any], extra: dict[str, Any]) -> None:
    for key, value in extra.items():
        if isinstance(value, dict) and isinstance(base.get(key), dict):
            _deep_merge(base[key], value)
        else:
            base[key] = value
