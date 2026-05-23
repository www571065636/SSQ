from __future__ import annotations

from collections import defaultdict
from statistics import mean

from app.models.dto import DrawResultDTO
from app.utils.draw_features import feature_map


class BacktestAnalyzer:
    def calc_strategy_metrics(self, draws: list[DrawResultDTO], max_lookback: int = 60) -> dict[str, dict]:
        if len(draws) < 20:
            return {}

        metrics: dict[str, dict] = {}
        for strategy_name in ("random", "hot_cold", "pattern_filter"):
            evaluations = []
            for index in range(12, len(draws)):
                history = draws[max(0, index - max_lookback):index]
                current = draws[index]
                score = self._evaluate_strategy(strategy_name, history, current)
                evaluations.append(score)
            if not evaluations:
                continue
            avg_red_hits = mean(item["red_hits"] for item in evaluations)
            blue_hit_rate = mean(1 if item["blue_hit"] else 0 for item in evaluations)
            prize_hit_rate = mean(1 if item["prize_hit"] else 0 for item in evaluations)
            metrics[strategy_name] = {
                "samples": len(evaluations),
                "avg_red_hits": round(avg_red_hits, 4),
                "blue_hit_rate": round(blue_hit_rate, 4),
                "prize_hit_rate": round(prize_hit_rate, 4),
                "recent_score": round(avg_red_hits * 0.55 + blue_hit_rate * 0.25 + prize_hit_rate * 0.20, 4),
            }
        return metrics

    def calc_feature_outcomes(self, draws: list[DrawResultDTO]) -> dict[str, dict]:
        if not draws:
            return {}
        counters: dict[str, defaultdict[str, list[float]]] = {
            "odd_even": defaultdict(list),
            "zones": defaultdict(list),
            "route_012": defaultdict(list),
            "prime_composite": defaultdict(list),
        }
        previous = None
        for draw in draws:
            features = feature_map(draw.red_numbers, previous)
            normalized_sum = sum(draw.red_numbers) / 200
            spread_score = features["span"] / 32
            continuity_penalty = max(0.0, 1 - int(features["consecutive_pairs"]) / 5)
            outcome = round(normalized_sum * 0.5 + spread_score * 0.3 + continuity_penalty * 0.2, 4)
            counters["odd_even"][str(features["odd_even"])].append(outcome)
            counters["zones"][str(features["zones"])].append(outcome)
            counters["route_012"][str(features["route_012"])].append(outcome)
            counters["prime_composite"][str(features["prime_composite"])].append(outcome)
            previous = draw.red_numbers
        return {
            name: {key: round(mean(values), 4) for key, values in values_by_key.items()}
            for name, values_by_key in counters.items()
        }

    def _evaluate_strategy(self, strategy_name: str, history: list[DrawResultDTO], current: DrawResultDTO) -> dict[str, float | bool]:
        history_red_sets = [set(draw.red_numbers) for draw in history]
        red_counter = defaultdict(int)
        blue_counter = defaultdict(int)
        for draw in history:
            for number in draw.red_numbers:
                red_counter[number] += 1
            blue_counter[draw.blue_number] += 1

        if strategy_name == "hot_cold":
            hot = sorted(red_counter, key=lambda number: (red_counter[number], number), reverse=True)[:10]
            cold = sorted(red_counter, key=lambda number: (red_counter[number], number))[:10]
            predicted = set(hot[:4] + cold[:2])
            blue = max(blue_counter, key=blue_counter.get, default=1)
        elif strategy_name == "pattern_filter":
            ordered = sorted(history, key=lambda item: sum(item.red_numbers))
            median_draw = ordered[len(ordered) // 2] if ordered else current
            predicted = set(median_draw.red_numbers)
            blue = median_draw.blue_number
        else:
            predicted = set(history[-1].red_numbers if history else current.red_numbers)
            blue = history[-1].blue_number if history else current.blue_number

        red_hits = len(predicted & set(current.red_numbers))
        blue_hit = blue == current.blue_number
        prize_hit = red_hits >= 4 or (red_hits >= 3 and blue_hit) or (red_hits <= 2 and blue_hit)
        return {"red_hits": float(red_hits), "blue_hit": blue_hit, "prize_hit": prize_hit}
