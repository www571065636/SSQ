from __future__ import annotations

from statistics import mean

from app.models.dto import RecommendationDTO, StrategyContext
from app.repository.analysis_repository import AnalysisRepository
from app.repository.draw_repository import DrawRepository
from app.repository.recommendation_repository import RecommendationRepository
from app.strategy.selector import StrategySelector
from app.utils.date import next_issue_no, now_iso, today_str
from app.utils.draw_features import feature_map
from app.utils.validators import validate_recommendation


ENGINE_REVISION = "2026-05-23-r2"


class RecommendationService:
    def __init__(
        self,
        draw_repository: DrawRepository,
        analysis_repository: AnalysisRepository,
        recommendation_repository: RecommendationRepository,
        config: dict,
    ) -> None:
        self.draw_repository = draw_repository
        self.analysis_repository = analysis_repository
        self.recommendation_repository = recommendation_repository
        self.config = config
        self.selector = StrategySelector()

    def generate_daily(self, count: int = 5) -> list[RecommendationDTO]:
        snapshot = self.analysis_repository.get_latest_snapshot()
        if not snapshot:
            raise ValueError("no analysis snapshot available, please run analyze first")
        batch_no = now_iso().replace("-", "").replace(":", "").replace("T", "")
        target_issue = self.resolve_target_issue()
        enabled = self._resolve_enabled_strategies(snapshot)
        candidate_pool_size = max(int(self.config.get("recommendation", {}).get("candidate_pool_size", 300)), count * 20)
        candidates: list[RecommendationDTO] = []
        seen = set()
        attempts = 0
        while len(candidates) < candidate_pool_size and attempts < candidate_pool_size * 10:
            strategy, strategy_config = self.selector.choose(enabled)
            context = StrategyContext(
                snapshot=snapshot,
                config=self.config,
                strategy_params=strategy_config.get("params", {}),
                target_issue_no=target_issue,
                rng_seed=attempts + 1,
            )
            recommendation = strategy.generate(context)
            recommendation.batch_no = batch_no
            recommendation.recommend_date = today_str()
            recommendation.snapshot_id = snapshot.snapshot_id
            validated = validate_recommendation(recommendation)
            key = (tuple(validated.red_numbers), validated.blue_number)
            if key not in seen:
                seen.add(key)
                validated.feature_summary = self._build_feature_summary(validated, snapshot)
                candidates.append(validated)
            attempts += 1
        if len(candidates) < count:
            raise ValueError("failed to generate enough candidate recommendations")

        ranked = sorted(
            candidates,
            key=lambda item: (
                float(item.feature_summary["score"]),
                float(item.feature_summary["blue_score"]),
                -len(set(item.red_numbers) & set(snapshot.hot_numbers)),
            ),
            reverse=True,
        )
        selected = self._select_diverse_top(ranked, count)
        if len(selected) != count:
            raise ValueError("failed to generate enough unique recommendations")
        self.recommendation_repository.save_batch(selected)
        return selected

    def resolve_target_issue(self) -> str | None:
        latest = self.draw_repository.get_latest()
        if not latest:
            return None
        return next_issue_no(latest.issue_no)

    def _build_feature_summary(self, recommendation: RecommendationDTO, snapshot) -> dict:
        numbers = recommendation.red_numbers
        odd = sum(1 for value in numbers if value % 2 == 1)
        even = 6 - odd
        total = sum(numbers)
        hot_hits = len(set(numbers) & set(snapshot.hot_numbers))
        cold_hits = len(set(numbers) & set(snapshot.cold_numbers))
        latest_draw = self.draw_repository.get_latest()
        features = feature_map(numbers, latest_draw.red_numbers if latest_draw else None)
        zone_ratio = str(features["zones"])
        number_score = self._score_red_numbers(numbers, snapshot)
        pattern_score = self._score_pattern(numbers, snapshot)
        blue_score = self._score_blue(recommendation.blue_number, snapshot)
        strategy_bonus = self._strategy_bonus(recommendation.strategy_name)
        feature_alignment_score = self._score_feature_alignment(features, snapshot)
        final_score = round(number_score + pattern_score + blue_score + strategy_bonus + feature_alignment_score, 4)
        return {
            "sum": total,
            "odd_even": f"{odd}:{even}",
            "zones": zone_ratio,
            "hot_hits": hot_hits,
            "cold_hits": cold_hits,
            "consecutive_pairs": int(features["consecutive_pairs"]),
            "span": int(features["span"]),
            "ac": int(features["ac"]),
            "repeat_with_prev": int(features["repeat_with_prev"]),
            "tail_variety": int(features["tail_variety"]),
            "prime_composite": str(features["prime_composite"]),
            "route_012": str(features["route_012"]),
            "number_score": round(number_score, 4),
            "pattern_score": round(pattern_score, 4),
            "blue_score": round(blue_score, 4),
            "strategy_bonus": round(strategy_bonus, 4),
            "feature_alignment_score": round(feature_alignment_score, 4),
            "score": final_score,
        }

    def _score_red_numbers(self, numbers: list[int], snapshot) -> float:
        red_scores = []
        for number in numbers:
            freq = float(snapshot.weighted_red_frequency.get(number) or snapshot.red_frequency.get(number, 0))
            omission = int(snapshot.omission_map.get(f"red_{number:02d}", 0))
            omission_score = max(0.0, 1 - abs(omission - 8) / 12)
            hot_bonus = 0.12 if number in snapshot.hot_numbers else 0.0
            cold_bonus = 0.06 if number in snapshot.cold_numbers else 0.0
            layer_bonus = self._layer_consensus_bonus(number, snapshot.layered_red_frequency)
            red_scores.append(freq * 10 + omission_score + hot_bonus + cold_bonus + layer_bonus)
        return float(mean(red_scores))

    def _score_blue(self, blue_number: int, snapshot) -> float:
        freq = float(snapshot.weighted_blue_frequency.get(blue_number) or snapshot.blue_frequency.get(blue_number, 0))
        omission = int(snapshot.omission_map.get(f"blue_{blue_number:02d}", 0))
        omission_score = max(0.0, 1 - abs(omission - 4) / 8)
        layer_bonus = self._layer_consensus_bonus(blue_number, snapshot.layered_blue_frequency, top_n=5)
        return freq * 8 + omission_score + layer_bonus

    def _score_pattern(self, numbers: list[int], snapshot) -> float:
        pattern_stats = snapshot.pattern_stats
        feature_outcomes = snapshot.feature_stats.get("feature_outcomes", {})
        current_features = feature_map(numbers)
        odd = sum(1 for value in numbers if value % 2 == 1)
        even = 6 - odd
        odd_even_key = f"{odd}:{even}"
        zone_key = self._zone_ratio(numbers)
        sum_value = sum(numbers)
        odd_even_score = float(pattern_stats.get("odd_even", {}).get(odd_even_key, 0)) / max(snapshot.window_size, 1)
        zone_score = float(pattern_stats.get("zones", {}).get(zone_key, 0)) / max(snapshot.window_size, 1)
        avg_sum = float(pattern_stats.get("sum_avg", sum_value))
        sum_score = max(0.0, 1 - abs(sum_value - avg_sum) / 40)
        route_score = float(feature_outcomes.get("route_012", {}).get(str(current_features["route_012"]), 0))
        prime_score = float(feature_outcomes.get("prime_composite", {}).get(str(current_features["prime_composite"]), 0))
        return odd_even_score * 6 + zone_score * 6 + sum_score + route_score + prime_score

    def _score_feature_alignment(self, features: dict, snapshot) -> float:
        feature_stats = snapshot.feature_stats
        pattern_stats = snapshot.pattern_stats
        outcomes = feature_stats.get("feature_outcomes", {})
        consecutive_map = {
            int(key): int(value) for key, value in pattern_stats.get("consecutive_pairs", {}).items()
        }
        score = 0.0
        score += max(0.0, 1 - abs(int(features["span"]) - float(feature_stats.get("span_avg", features["span"]))) / 12)
        score += max(0.0, 1 - abs(int(features["ac"]) - float(feature_stats.get("ac_avg", features["ac"]))) / 4)
        score += 0.4 if int(features["consecutive_pairs"]) == int(feature_stats.get("consecutive_mode", features["consecutive_pairs"])) else 0.0
        score += 0.35 if int(features["repeat_with_prev"]) == int(feature_stats.get("repeat_mode", features["repeat_with_prev"])) else 0.0
        score += 0.25 if int(features["tail_variety"]) == int(feature_stats.get("tail_variety_mode", features["tail_variety"])) else 0.0
        score += float(outcomes.get("odd_even", {}).get(str(features["odd_even"]), 0))
        score += float(outcomes.get("zones", {}).get(str(features["zones"]), 0))
        score += consecutive_map.get(int(features["consecutive_pairs"]), 0) / max(snapshot.window_size, 1)
        return score

    @staticmethod
    def _zone_ratio(numbers: list[int]) -> str:
        zone1 = sum(1 for value in numbers if 1 <= value <= 11)
        zone2 = sum(1 for value in numbers if 12 <= value <= 22)
        zone3 = 6 - zone1 - zone2
        return f"{zone1}:{zone2}:{zone3}"

    @staticmethod
    def _strategy_bonus(strategy_name: str) -> float:
        bonus_map = {"random": 0.08, "hot_cold": 0.18, "pattern_filter": 0.22}
        return bonus_map.get(strategy_name, 0.0)

    @staticmethod
    def _select_diverse_top(ranked: list[RecommendationDTO], count: int) -> list[RecommendationDTO]:
        selected: list[RecommendationDTO] = []
        for candidate in ranked:
            if len(selected) >= count:
                break
            if all(len(set(item.red_numbers) & set(candidate.red_numbers)) <= 4 for item in selected):
                selected.append(candidate)
        if len(selected) < count:
            for candidate in ranked:
                if candidate not in selected:
                    selected.append(candidate)
                if len(selected) >= count:
                    break
        return selected[:count]

    def _resolve_enabled_strategies(self, snapshot) -> list[dict]:
        configured = self.config["strategy"]["enabled"]
        adjusted = self.selector.rebalance({"configured": configured, "metrics": snapshot.strategy_metrics or {}})
        return adjusted or configured

    @staticmethod
    def _layer_consensus_bonus(number: int, layered_frequency: dict[str, dict[int, float]], top_n: int = 8) -> float:
        if not layered_frequency:
            return 0.0
        bonus = 0.0
        for layer_values in layered_frequency.values():
            ranked = sorted(layer_values.items(), key=lambda item: (item[1], item[0]), reverse=True)[:top_n]
            if any(candidate == number for candidate, _ in ranked):
                bonus += 0.08
        return bonus
