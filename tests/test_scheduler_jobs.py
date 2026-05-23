from __future__ import annotations

import json
from pathlib import Path
from uuid import uuid4

from app.bootstrap import build_container
from app.models.dto import DrawResultDTO


def _runtime_root() -> Path:
    root = Path(__file__).resolve().parent / ".runtime"
    root.mkdir(parents=True, exist_ok=True)
    return root


def _config_path(db_path: str, log_path: str) -> Path:
    path = _runtime_root() / f"scheduler-{uuid4().hex}.json"
    path.write_text(
        json.dumps(
            {
                "database": {"path": db_path},
                "app": {"scheduled_log_path": log_path},
                "crawler": {
                    "source_type": "json_file",
                    "source_name": "sample",
                    "source_url": "data/sample_draws.json",
                    "issue_count": 100,
                },
                "recommendation": {"daily_count": 2, "candidate_pool_size": 40},
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return path


def _draw(issue: int) -> DrawResultDTO:
    reds = [issue % 28 + 1, issue % 28 + 3, issue % 28 + 7, issue % 28 + 11, issue % 28 + 15, issue % 28 + 19]
    reds = sorted((((value - 1) % 33) + 1) for value in reds)
    return DrawResultDTO(
        issue_no=f"2026{issue:03d}",
        draw_date=f"2026-03-{((issue - 1) % 28) + 1:02d}",
        red_numbers=reds,
        blue_number=((issue - 1) % 16) + 1,
        source_name="test",
        source_url="test://sample",
    )


def test_drawday_result_job_writes_check_log() -> None:
    root = _runtime_root()
    db_path = str(root / f"{uuid4().hex}.db")
    log_path = str(root / f"{uuid4().hex}.log")
    container = build_container(str(_config_path(db_path, log_path)))
    container.init_db()

    payload = container.run_drawday_result_job()

    assert payload["checked_issue"] is not None
    content = Path(log_path).read_text(encoding="utf-8")
    assert "drawday_result" in content
    assert "winning_numbers" in content


def test_drawday_prepare_job_writes_recommendation_log() -> None:
    root = _runtime_root()
    db_path = str(root / f"{uuid4().hex}.db")
    log_path = str(root / f"{uuid4().hex}.log")
    container = build_container(str(_config_path(db_path, log_path)))
    container.init_db()
    container.draw_repository.save_many([_draw(index) for index in range(1, 55)])

    payload = container.run_drawday_prepare_job()

    assert payload["recommendations"]
    content = Path(log_path).read_text(encoding="utf-8")
    assert "drawday_prepare" in content
    assert "recommendations" in content
