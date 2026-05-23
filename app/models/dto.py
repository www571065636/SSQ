from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(slots=True)
class DrawResultDTO:
    issue_no: str
    draw_date: str
    red_numbers: list[int]
    blue_number: int
    source_name: str
    source_url: str
    raw_payload: str | None = None


@dataclass(slots=True)
class AnalysisSnapshotDTO:
    based_on_issue: str
    snapshot_date: str
    window_size: int
    red_frequency: dict[int, float]
    blue_frequency: dict[int, float]
    omission_map: dict[str, int]
    hot_numbers: list[int]
    cold_numbers: list[int]
    pattern_stats: dict[str, Any]
    weighted_red_frequency: dict[int, float] = field(default_factory=dict)
    weighted_blue_frequency: dict[int, float] = field(default_factory=dict)
    layered_red_frequency: dict[str, dict[int, float]] = field(default_factory=dict)
    layered_blue_frequency: dict[str, dict[int, float]] = field(default_factory=dict)
    feature_stats: dict[str, Any] = field(default_factory=dict)
    strategy_metrics: dict[str, Any] = field(default_factory=dict)
    snapshot_id: int | None = None


@dataclass(slots=True)
class StrategyContext:
    snapshot: AnalysisSnapshotDTO
    config: dict[str, Any]
    strategy_params: dict[str, Any]
    target_issue_no: str | None = None
    rng_seed: int | None = None


@dataclass(slots=True)
class RecommendationDTO:
    batch_no: str
    recommend_date: str
    target_issue_no: str | None
    strategy_name: str
    red_numbers: list[int]
    blue_number: int
    feature_summary: dict[str, Any] = field(default_factory=dict)
    snapshot_id: int | None = None
    recommendation_id: int | None = None


@dataclass(slots=True)
class CheckResultDTO:
    recommendation_id: int
    issue_no: str
    red_hits: int
    blue_hit: bool
    prize_level: str | None
    prize_amount: float | None


@dataclass(slots=True)
class PushResultDTO:
    batch_no: str
    channel: str
    target: str
    message_type: str
    payload: str
    response_body: str
    status: str
