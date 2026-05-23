from __future__ import annotations

from app.models.dto import RecommendationDTO, StrategyContext
from app.strategy.random_strategy import RandomStrategy
from app.utils.draw_features import feature_map


class PatternFilterStrategy:
    name = "pattern_filter"

    def __init__(self) -> None:
        self.random_strategy = RandomStrategy()

    def generate(self, context: StrategyContext) -> RecommendationDTO:
        sum_range = self._resolve_sum_range(context)
        odd_even_allowed = self._resolve_allowed(context.snapshot.pattern_stats.get("odd_even", {}), context.config["recommendation"].get("odd_even_allowed", []), 3)
        zone_allowed = self._resolve_allowed(context.snapshot.pattern_stats.get("zones", {}), context.config["recommendation"].get("zone_allowed", []), 5)
        route_allowed = self._resolve_allowed(context.snapshot.pattern_stats.get("route_012", {}), [], 4)
        max_attempts = int(context.config["recommendation"].get("max_attempts", 500))
        for attempt in range(max_attempts):
            candidate = self.random_strategy.generate(context)
            if self._passes(candidate.red_numbers, sum_range, odd_even_allowed, zone_allowed, route_allowed):
                candidate.strategy_name = self.name
                return candidate
        candidate = self.random_strategy.generate(context)
        candidate.strategy_name = self.name
        return candidate

    @staticmethod
    def _passes(
        numbers: list[int],
        sum_range: list[int],
        odd_even_allowed: set[str],
        zone_allowed: set[str],
        route_allowed: set[str],
    ) -> bool:
        total = sum(numbers)
        if not (sum_range[0] <= total <= sum_range[1]):
            return False
        features = feature_map(numbers)
        if odd_even_allowed and str(features["odd_even"]) not in odd_even_allowed:
            return False
        if zone_allowed and str(features["zones"]) not in zone_allowed:
            return False
        if route_allowed and str(features["route_012"]) not in route_allowed:
            return False
        return True

    @staticmethod
    def _resolve_allowed(counter_map: dict, fallback: list[str], limit: int) -> set[str]:
        if counter_map:
            ranked = sorted(counter_map.items(), key=lambda item: (int(item[1]), item[0]), reverse=True)[:limit]
            return {str(key) for key, _ in ranked}
        return set(fallback)

    @staticmethod
    def _resolve_sum_range(context: StrategyContext) -> list[int]:
        pattern_stats = context.snapshot.pattern_stats
        default_range = context.config["recommendation"].get("sum_range", [85, 110])
        avg_sum = float(pattern_stats.get("sum_avg", sum(default_range) / 2))
        spread = float(context.snapshot.feature_stats.get("sum_std_proxy", 12))
        lower = max(21, int(avg_sum - spread))
        upper = min(183, int(avg_sum + spread))
        return [lower, upper]
