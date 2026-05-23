from __future__ import annotations

from collections import Counter

from app.models.dto import DrawResultDTO
from app.utils.draw_features import feature_map


class PatternAnalyzer:
    def calc_pattern_stats(self, draws: list[DrawResultDTO]) -> dict:
        odd_even: Counter[str] = Counter()
        big_small: Counter[str] = Counter()
        zones: Counter[str] = Counter()
        consecutive_pairs: Counter[int] = Counter()
        spans: list[int] = []
        ac_values: Counter[int] = Counter()
        repeat_with_prev: Counter[int] = Counter()
        tail_variety: Counter[int] = Counter()
        prime_composite: Counter[str] = Counter()
        route_012: Counter[str] = Counter()
        sums: list[int] = []
        previous_numbers: list[int] | None = None
        for draw in draws:
            features = feature_map(draw.red_numbers, previous_numbers)
            odd_even[str(features["odd_even"])] += 1
            big_small[str(features["big_small"])] += 1
            zones[str(features["zones"])] += 1
            consecutive_pairs[int(features["consecutive_pairs"])] += 1
            spans.append(int(features["span"]))
            ac_values[int(features["ac"])] += 1
            repeat_with_prev[int(features["repeat_with_prev"])] += 1
            tail_variety[int(features["tail_variety"])] += 1
            prime_composite[str(features["prime_composite"])] += 1
            route_012[str(features["route_012"])] += 1
            sums.append(sum(draw.red_numbers))
            previous_numbers = draw.red_numbers
        return {
            "odd_even": dict(odd_even),
            "big_small": dict(big_small),
            "zones": dict(zones),
            "consecutive_pairs": dict(consecutive_pairs),
            "span_min": min(spans) if spans else 0,
            "span_max": max(spans) if spans else 0,
            "span_avg": round(sum(spans) / len(spans), 2) if spans else 0,
            "ac_values": dict(ac_values),
            "repeat_with_prev": dict(repeat_with_prev),
            "tail_variety": dict(tail_variety),
            "prime_composite": dict(prime_composite),
            "route_012": dict(route_012),
            "sum_min": min(sums) if sums else 0,
            "sum_max": max(sums) if sums else 0,
            "sum_avg": round(sum(sums) / len(sums), 2) if sums else 0,
        }
