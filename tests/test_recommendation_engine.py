from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from app.analyzer.service import AnalysisService
from app.models.dto import DrawResultDTO
from app.recommender.service import RecommendationService
from app.repository.analysis_repository import AnalysisRepository
from app.repository.db import Database
from app.repository.draw_repository import DrawRepository
from app.repository.recommendation_repository import RecommendationRepository


def _build_config(db_path: str) -> dict:
    return {
        "database": {"path": db_path},
        "analysis": {
            "hot_top_n": 10,
            "cold_top_n": 10,
            "recent_window": 30,
            "mid_window": 60,
            "recent_weight": 1.8,
            "mid_weight": 1.2,
            "base_weight": 1.0,
            "backtest_lookback": 20,
        },
        "recommendation": {
            "daily_count": 5,
            "candidate_pool_size": 80,
            "sum_range": [85, 110],
            "odd_even_allowed": ["3:3", "4:2", "2:4"],
            "zone_allowed": ["2:2:2", "1:2:3", "2:1:3", "3:2:1"],
            "max_attempts": 200,
        },
        "strategy": {
            "enabled": [
                {"name": "random", "weight": 0.4, "params": {}},
                {"name": "hot_cold", "weight": 0.4, "params": {"hot_count": 4, "cold_count": 2}},
                {"name": "pattern_filter", "weight": 0.2, "params": {}},
            ]
        },
    }


def _make_db_path() -> str:
    root = Path(__file__).resolve().parent / ".runtime"
    root.mkdir(parents=True, exist_ok=True)
    return str(root / f"{uuid4().hex}.db")


def _sample_draw(issue: int, blue: int) -> DrawResultDTO:
    base = ((issue - 1) % 28) + 1
    reds = sorted({base, ((base + 3 - 1) % 33) + 1, ((base + 7 - 1) % 33) + 1, ((base + 12 - 1) % 33) + 1, ((base + 18 - 1) % 33) + 1, ((base + 25 - 1) % 33) + 1})
    while len(reds) < 6:
        candidate = ((reds[-1] + 5 - 1) % 33) + 1
        if candidate not in reds:
            reds.append(candidate)
    return DrawResultDTO(
        issue_no=f"2026{issue:03d}",
        draw_date=f"2026-01-{((issue - 1) % 28) + 1:02d}",
        red_numbers=sorted(reds[:6]),
        blue_number=((blue - 1) % 16) + 1,
        source_name="test",
        source_url="test://sample",
    )


def test_analysis_snapshot_contains_enhanced_metrics() -> None:
    db_path = _make_db_path()
    db = Database(db_path)
    draw_repo = DrawRepository(db)
    analysis_repo = AnalysisRepository(db)
    draw_repo.init_table()
    analysis_repo.init_table()
    draws = [_sample_draw(index, index) for index in range(1, 81)]
    draw_repo.save_many(draws)
    service = AnalysisService(draw_repo, analysis_repo, _build_config(db_path))

    snapshot = service.build_snapshot()

    assert snapshot.window_size == 80
    assert "recent_30" in snapshot.layered_red_frequency
    assert snapshot.weighted_red_frequency
    assert "feature_outcomes" in snapshot.feature_stats
    assert "hot_cold" in snapshot.strategy_metrics


def test_recommendation_uses_enhanced_feature_summary() -> None:
    db_path = _make_db_path()
    db = Database(db_path)
    draw_repo = DrawRepository(db)
    analysis_repo = AnalysisRepository(db)
    recommendation_repo = RecommendationRepository(db)
    draw_repo.init_table()
    analysis_repo.init_table()
    recommendation_repo.init_table()
    draws = [_sample_draw(index, index + 2) for index in range(1, 81)]
    draw_repo.save_many(draws)
    config = _build_config(db_path)
    snapshot = AnalysisService(draw_repo, analysis_repo, config).build_snapshot()

    items = RecommendationService(draw_repo, analysis_repo, recommendation_repo, config).generate_daily(3)

    assert len(items) == 3
    assert snapshot.strategy_metrics
    for item in items:
        assert "score" in item.feature_summary
        assert "feature_alignment_score" in item.feature_summary
        assert "route_012" in item.feature_summary
        assert "consecutive_pairs" in item.feature_summary


def test_analysis_snapshot_roundtrip_reads_new_fields() -> None:
    db_path = _make_db_path()
    db = Database(db_path)
    draw_repo = DrawRepository(db)
    analysis_repo = AnalysisRepository(db)
    draw_repo.init_table()
    analysis_repo.init_table()
    draw_repo.save_many([_sample_draw(index, index + 1) for index in range(1, 50)])
    config = _build_config(db_path)
    AnalysisService(draw_repo, analysis_repo, config).build_snapshot()

    latest = analysis_repo.get_latest_snapshot()

    assert latest is not None
    assert latest.weighted_blue_frequency
    assert latest.layered_blue_frequency["full"]
    assert latest.feature_stats["span_avg"] >= 0
