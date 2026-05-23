from __future__ import annotations

import json
from pathlib import Path

from app.utils.date import now_iso


class JobLogger:
    def __init__(self, log_path: str = "logs/scheduled_jobs.log") -> None:
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, job_name: str, payload: dict) -> None:
        entry = {
            "logged_at": now_iso(),
            "job_name": job_name,
            "payload": payload,
        }
        with self.log_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
