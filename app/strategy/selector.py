from __future__ import annotations

from app.strategy.hot_cold_strategy import HotColdStrategy
from app.strategy.pattern_filter_strategy import PatternFilterStrategy
from app.strategy.random_strategy import RandomStrategy
from app.utils.randomizer import create_rng


class StrategySelector:
    def __init__(self, seed: int | None = None) -> None:
        self.rng = create_rng(seed)
        self.registry = {
            "random": RandomStrategy(),
            "hot_cold": HotColdStrategy(),
            "pattern_filter": PatternFilterStrategy(),
        }

    def choose(self, enabled_strategies: list[dict]):
        active = [item for item in enabled_strategies if item.get("weight", 0) > 0 and item.get("name") in self.registry]
        if not active:
            raise ValueError("no enabled strategies configured")
        total_weight = sum(float(item["weight"]) for item in active)
        threshold = self.rng.random() * total_weight
        cumulative = 0.0
        for item in active:
            cumulative += float(item["weight"])
            if cumulative >= threshold:
                return self.registry[item["name"]], item
        last = active[-1]
        return self.registry[last["name"]], last

    def rebalance(self, recent_metrics: dict) -> list[dict]:
        configured = recent_metrics.get("configured", [])
        metrics = recent_metrics.get("metrics", {})
        if not configured:
            return []
        adjusted = []
        for item in configured:
            current_weight = float(item.get("weight", 0))
            metric = metrics.get(item.get("name"), {})
            recent_score = float(metric.get("recent_score", 0))
            adjusted_weight = current_weight * (1 + recent_score)
            adjusted.append({**item, "weight": adjusted_weight})
        total = sum(item["weight"] for item in adjusted) or 1.0
        return [{**item, "weight": round(item["weight"] / total, 6)} for item in adjusted]
