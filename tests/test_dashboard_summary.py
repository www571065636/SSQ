from __future__ import annotations

from uuid import uuid4
from pathlib import Path

from app.analyzer.service import AnalysisService
from app.bootstrap import build_container
from app.models.dto import CheckResultDTO, DrawResultDTO, RecommendationDTO
from app.repository.db import Database
from app.repository.recommendation_repository import RecommendationRepository
from app.repository.check_repository import CheckRepository
from app.repository.job_repository import JobRepository


def _db_path() -> str:
    root = Path(__file__).resolve().parent / ".runtime"
    root.mkdir(parents=True, exist_ok=True)
    return str(root / f"dashboard-{uuid4().hex}.db")


def _config_path(db_path: str) -> Path:
    path = Path(__file__).resolve().parent / ".runtime" / f"dashboard-{uuid4().hex}.json"
    path.write_text(
        f"""{{"database": {{"path": "{db_path.replace("\\", "\\\\")}"}}}}""",
        encoding="utf-8",
    )
    return path


def _draw(issue: int) -> DrawResultDTO:
    reds = [issue % 28 + 1, issue % 28 + 3, issue % 28 + 7, issue % 28 + 11, issue % 28 + 15, issue % 28 + 19]
    reds = sorted((((value - 1) % 33) + 1) for value in reds)
    return DrawResultDTO(
        issue_no=f"2026{issue:03d}",
        draw_date=f"2026-02-{((issue - 1) % 28) + 1:02d}",
        red_numbers=reds,
        blue_number=((issue - 1) % 16) + 1,
        source_name="test",
        source_url="test://sample",
    )


def test_dashboard_summary_contains_recommendation_and_check_stats() -> None:
    db_path = _db_path()
    config_path = _config_path(db_path)
    container = build_container(str(config_path))
    container.init_db()
    draws = [_draw(index) for index in range(1, 55)]
    container.draw_repository.save_many(draws)
    snapshot = AnalysisService(container.draw_repository, container.analysis_repository, container.config).build_snapshot()

    recommendation_repo = RecommendationRepository(Database(db_path))
    check_repo = CheckRepository(Database(db_path))
    recommendation_repo.init_table()
    check_repo.init_table()
    recommendation = RecommendationDTO(
        batch_no="b1",
        recommend_date="2026-05-23",
        target_issue_no="2026055",
        strategy_name="hot_cold",
        red_numbers=[1, 3, 8, 12, 18, 24],
        blue_number=6,
        feature_summary={"score": 12.3, "feature_alignment_score": 3.2, "sum": 66, "zones": "2:2:2", "route_012": "2:2:2"},
        snapshot_id=snapshot.snapshot_id,
    )
    recommendation_repo.save_batch([recommendation])
    saved = recommendation_repo.list_recent(1)[0]
    check_repo.save_results(
        [
            CheckResultDTO(
                recommendation_id=int(saved.recommendation_id or 0),
                issue_no="2026055",
                red_hits=2,
                blue_hit=True,
                prize_level="六等奖",
                prize_amount=5,
            )
        ]
    )

    summary = container.get_dashboard_data()

    assert summary["recommendation_stats"]["avg_score"] > 0
    assert summary["check_stats"]["checked_count"] == 1
    assert summary["check_stats"]["strategy_hit_board"][0]["strategy_name"] == "hot_cold"
    assert summary["check_stats"]["issue_trend"][0]["issue_no"] == "2026055"


def test_dashboard_summary_supports_issue_filter() -> None:
    db_path = _db_path()
    config_path = _config_path(db_path)
    container = build_container(str(config_path))
    container.init_db()
    draws = [_draw(index) for index in range(1, 55)]
    container.draw_repository.save_many(draws)
    snapshot = AnalysisService(container.draw_repository, container.analysis_repository, container.config).build_snapshot()

    recommendation_repo = RecommendationRepository(Database(db_path))
    check_repo = CheckRepository(Database(db_path))
    recommendation_repo.init_table()
    check_repo.init_table()

    items = [
        RecommendationDTO(
            batch_no="b1",
            recommend_date="2026-05-23",
            target_issue_no="2026052",
            strategy_name="hot_cold",
            red_numbers=[1, 3, 8, 12, 18, 24],
            blue_number=6,
            feature_summary={"score": 10.1, "feature_alignment_score": 3.0, "sum": 66, "zones": "2:2:2", "route_012": "2:2:2"},
            snapshot_id=snapshot.snapshot_id,
        ),
        RecommendationDTO(
            batch_no="b2",
            recommend_date="2026-05-23",
            target_issue_no="2026055",
            strategy_name="pattern_filter",
            red_numbers=[2, 4, 9, 16, 20, 28],
            blue_number=8,
            feature_summary={"score": 11.4, "feature_alignment_score": 3.5, "sum": 79, "zones": "2:2:2", "route_012": "3:2:1"},
            snapshot_id=snapshot.snapshot_id,
        ),
    ]
    recommendation_repo.save_batch(items)
    saved_items = recommendation_repo.list_all()
    for item in saved_items:
        check_repo.save_results(
            [
                CheckResultDTO(
                    recommendation_id=int(item.recommendation_id or 0),
                    issue_no=item.target_issue_no or "",
                    red_hits=1 if item.target_issue_no == "2026052" else 3,
                    blue_hit=item.target_issue_no == "2026055",
                    prize_level="六等奖" if item.target_issue_no == "2026055" else None,
                    prize_amount=5 if item.target_issue_no == "2026055" else None,
                )
            ]
        )

    summary = container.get_dashboard_data("2026054", "2026056")

    assert summary["check_stats"]["checked_count"] == 1
    assert summary["check_stats"]["issue_trend"][0]["issue_no"] == "2026055"
    assert summary["recent_recommendations"][0].target_issue_no == "2026055"


def test_score_cards_are_sorted_by_issue_desc_then_score_desc() -> None:
    db_path = _db_path()
    config_path = _config_path(db_path)
    container = build_container(str(config_path))
    container.init_db()
    draws = [_draw(index) for index in range(1, 40)]
    container.draw_repository.save_many(draws)
    snapshot = AnalysisService(container.draw_repository, container.analysis_repository, container.config).build_snapshot()

    recommendation_repo = RecommendationRepository(Database(db_path))
    recommendation_repo.init_table()
    recommendation_repo.save_batch(
        [
            RecommendationDTO(
                batch_no="b1",
                recommend_date="2026-05-23",
                target_issue_no="2026040",
                strategy_name="random",
                red_numbers=[1, 3, 8, 12, 18, 24],
                blue_number=6,
                feature_summary={"score": 8.1, "feature_alignment_score": 1.0, "sum": 66, "zones": "2:2:2", "route_012": "2:2:2"},
                snapshot_id=snapshot.snapshot_id,
            ),
            RecommendationDTO(
                batch_no="b2",
                recommend_date="2026-05-23",
                target_issue_no="2026040",
                strategy_name="hot_cold",
                red_numbers=[2, 4, 9, 16, 20, 28],
                blue_number=8,
                feature_summary={"score": 12.9, "feature_alignment_score": 3.5, "sum": 79, "zones": "2:2:2", "route_012": "3:2:1"},
                snapshot_id=snapshot.snapshot_id,
            ),
            RecommendationDTO(
                batch_no="b3",
                recommend_date="2026-05-23",
                target_issue_no="2026041",
                strategy_name="pattern_filter",
                red_numbers=[5, 7, 11, 19, 23, 30],
                blue_number=9,
                feature_summary={"score": 10.2, "feature_alignment_score": 2.7, "sum": 95, "zones": "1:2:3", "route_012": "2:1:3"},
                snapshot_id=snapshot.snapshot_id,
            ),
        ]
    )

    summary = container.get_dashboard_data()
    cards = summary["recommendation_stats"]["recent_score_cards"]

    assert [card["issue_no"] for card in cards[:3]] == ["2026041", "2026040", "2026040"]
    assert [card["score"] for card in cards[:3]] == [10.2, 12.9, 8.1]
    assert [item.target_issue_no for item in summary["recent_recommendations"][:3]] == ["2026041", "2026040", "2026040"]
    assert [item.feature_summary["score"] for item in summary["recent_recommendations"][:3]] == [10.2, 12.9, 8.1]


def test_recommendation_repository_keeps_only_latest_1000() -> None:
    db_path = _db_path()
    recommendation_repo = RecommendationRepository(Database(db_path))
    recommendation_repo.init_table()

    batch = []
    for index in range(1100):
        batch.append(
            RecommendationDTO(
                batch_no=f"b{index}",
                recommend_date="2026-05-23",
                target_issue_no=f"2026{index:03d}",
                strategy_name="random",
                red_numbers=[1, 2, 3, 4, 5, (index % 28) + 6],
                blue_number=((index % 16) + 1),
                feature_summary={"score": float(index), "feature_alignment_score": 0.0},
            )
        )

    recommendation_repo.save_batch(batch)
    rows = recommendation_repo.list_all()

    assert len(rows) == 1000
    assert rows[0].target_issue_no == "20261099"
    assert rows[-1].target_issue_no == "2026100"


def test_job_repository_keeps_only_latest_100() -> None:
    db_path = _db_path()
    job_repo = JobRepository(Database(db_path))
    job_repo.init_table()

    for index in range(120):
        run_id = job_repo.create_run(f"job_{index}")
        job_repo.finish_run(run_id, "success", f"ok_{index}", index)

    rows = job_repo.list_recent(200)

    assert len(rows) == 100
    assert rows[0]["job_name"] == "job_119"
    assert rows[-1]["job_name"] == "job_20"


def test_dashboard_recent_jobs_only_shows_10() -> None:
    db_path = _db_path()
    config_path = _config_path(db_path)
    container = build_container(str(config_path))
    container.init_db()

    for index in range(25):
        run_id = container.job_repository.create_run(f"job_{index}")
        container.job_repository.finish_run(run_id, "success", f"ok_{index}", index)

    summary = container.get_dashboard_data()

    assert len(summary["recent_jobs"]) == 10
    assert summary["recent_jobs"][0]["job_name"] == "job_24"
    assert summary["recent_jobs"][-1]["job_name"] == "job_15"
