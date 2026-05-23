from __future__ import annotations

from statistics import mean

from app.analyzer.backtest import BacktestAnalyzer
from app.analyzer.frequency import FrequencyAnalyzer
from app.analyzer.omission import OmissionAnalyzer
from app.analyzer.pattern import PatternAnalyzer
from app.models.dto import AnalysisSnapshotDTO
from app.repository.analysis_repository import AnalysisRepository
from app.repository.draw_repository import DrawRepository
from app.utils.date import today_str


class AnalysisService:
    def __init__(
        self,
        draw_repository: DrawRepository,
        analysis_repository: AnalysisRepository,
        config: dict,
    ) -> None:
        self.draw_repository = draw_repository
        self.analysis_repository = analysis_repository
        self.config = config
        self.frequency_analyzer = FrequencyAnalyzer()
        self.omission_analyzer = OmissionAnalyzer()
        self.pattern_analyzer = PatternAnalyzer()
        self.backtest_analyzer = BacktestAnalyzer()

    def build_snapshot(self, window_size: int | None = None) -> AnalysisSnapshotDTO:
        if window_size:
            draws = self.draw_repository.list_latest(window_size)
            effective_window = window_size
        else:
            draws = self.draw_repository.list_all()
            effective_window = len(draws)
        if not draws:
            raise ValueError("no draw data available, please run sync-history first")
        latest = draws[-1]
        red_frequency = self.frequency_analyzer.calc_red_frequency(draws)
        blue_frequency = self.frequency_analyzer.calc_blue_frequency(draws)
        weights = self._build_time_weights(draws)
        weighted_red_frequency = self.frequency_analyzer.calc_weighted_red_frequency(draws, weights)
        weighted_blue_frequency = self.frequency_analyzer.calc_weighted_blue_frequency(draws, weights)
        omission_map = self.omission_analyzer.calc_omission(draws)
        hot_numbers, cold_numbers = self._detect_hot_and_cold(red_frequency)
        pattern_stats = self.pattern_analyzer.calc_pattern_stats(draws)
        layered_red_frequency, layered_blue_frequency = self._build_layered_frequency(draws)
        feature_stats = self._build_feature_stats(draws, pattern_stats)
        strategy_metrics = self.backtest_analyzer.calc_strategy_metrics(
            draws,
            max_lookback=int(self.config["analysis"].get("backtest_lookback", 60)),
        )
        feature_stats["feature_outcomes"] = self.backtest_analyzer.calc_feature_outcomes(draws)
        snapshot = AnalysisSnapshotDTO(
            based_on_issue=latest.issue_no,
            snapshot_date=today_str(),
            window_size=effective_window,
            red_frequency=red_frequency,
            blue_frequency=blue_frequency,
            weighted_red_frequency=weighted_red_frequency,
            weighted_blue_frequency=weighted_blue_frequency,
            layered_red_frequency=layered_red_frequency,
            layered_blue_frequency=layered_blue_frequency,
            omission_map=omission_map,
            hot_numbers=hot_numbers,
            cold_numbers=cold_numbers,
            pattern_stats=pattern_stats,
            feature_stats=feature_stats,
            strategy_metrics=strategy_metrics,
        )
        snapshot.snapshot_id = self.analysis_repository.save_snapshot(snapshot)
        return snapshot

    def _detect_hot_and_cold(self, red_frequency: dict[int, float]) -> tuple[list[int], list[int]]:
        hot_top_n = int(self.config["analysis"].get("hot_top_n", 10))
        cold_top_n = int(self.config["analysis"].get("cold_top_n", 10))
        ordered = sorted(red_frequency.items(), key=lambda item: (item[1], item[0]))
        cold_numbers = [number for number, _ in ordered[:cold_top_n]]
        hot_numbers = [number for number, _ in ordered[-hot_top_n:]]
        hot_numbers.sort()
        cold_numbers.sort()
        return hot_numbers, cold_numbers

    def _build_time_weights(self, draws: list) -> list[float]:
        size = len(draws)
        recent_weight = float(self.config["analysis"].get("recent_weight", 1.8))
        mid_weight = float(self.config["analysis"].get("mid_weight", 1.25))
        base_weight = float(self.config["analysis"].get("base_weight", 1.0))
        recent_window = min(int(self.config["analysis"].get("recent_window", 30)), size)
        mid_window = min(int(self.config["analysis"].get("mid_window", 100)), size)
        weights = []
        start_recent = size - recent_window
        start_mid = size - mid_window
        for index in range(size):
            if index >= start_recent:
                weights.append(recent_weight)
            elif index >= start_mid:
                weights.append(mid_weight)
            else:
                weights.append(base_weight)
        return weights

    def _build_layered_frequency(self, draws: list) -> tuple[dict[str, dict[int, float]], dict[str, dict[int, float]]]:
        total = len(draws)
        windows = {
            "recent_30": min(30, total),
            "mid_100": min(100, total),
            "full": total,
        }
        red_layers: dict[str, dict[int, float]] = {}
        blue_layers: dict[str, dict[int, float]] = {}
        for layer_name, size in windows.items():
            subset = draws[-size:] if size else []
            red_layers[layer_name] = self.frequency_analyzer.calc_red_frequency(subset)
            blue_layers[layer_name] = self.frequency_analyzer.calc_blue_frequency(subset)
        return red_layers, blue_layers

    def _build_feature_stats(self, draws: list, pattern_stats: dict) -> dict:
        sums = [sum(draw.red_numbers) for draw in draws]
        span_avg = float(pattern_stats.get("span_avg", 0))
        consecutive_counts = pattern_stats.get("consecutive_pairs", {})
        repeat_counts = pattern_stats.get("repeat_with_prev", {})
        tail_variety = pattern_stats.get("tail_variety", {})
        ac_values = [int(key) for key, count in pattern_stats.get("ac_values", {}).items() for _ in range(int(count))]
        return {
            "sum_avg": round(mean(sums), 2) if sums else 0,
            "sum_std_proxy": round((max(sums) - min(sums)) / 6, 2) if len(sums) >= 2 else 0,
            "span_avg": span_avg,
            "ac_avg": round(mean(ac_values), 2) if ac_values else 0,
            "consecutive_mode": self._mode_from_counter(consecutive_counts),
            "repeat_mode": self._mode_from_counter(repeat_counts),
            "tail_variety_mode": self._mode_from_counter(tail_variety),
        }

    @staticmethod
    def _mode_from_counter(counter_map: dict) -> int:
        if not counter_map:
            return 0
        ordered = sorted(counter_map.items(), key=lambda item: (int(item[1]), int(item[0])), reverse=True)
        return int(ordered[0][0])
