from __future__ import annotations

from collections import Counter

from app.models.dto import DrawResultDTO


class FrequencyAnalyzer:
    def calc_red_frequency(self, draws: list[DrawResultDTO]) -> dict[int, float]:
        counter: Counter[int] = Counter()
        for draw in draws:
            counter.update(draw.red_numbers)
        total = len(draws) * 6 if draws else 1
        return {number: round(counter.get(number, 0) / total, 6) for number in range(1, 34)}

    def calc_blue_frequency(self, draws: list[DrawResultDTO]) -> dict[int, float]:
        counter: Counter[int] = Counter(draw.blue_number for draw in draws)
        total = len(draws) if draws else 1
        return {number: round(counter.get(number, 0) / total, 6) for number in range(1, 17)}

    def calc_weighted_red_frequency(self, draws: list[DrawResultDTO], weights: list[float]) -> dict[int, float]:
        total_weight = sum(weights) * 6 if draws and weights else 1
        weighted_counter: dict[int, float] = {number: 0.0 for number in range(1, 34)}
        for draw, weight in zip(draws, weights):
            for number in draw.red_numbers:
                weighted_counter[number] += weight
        return {number: round(weighted_counter[number] / total_weight, 6) for number in range(1, 34)}

    def calc_weighted_blue_frequency(self, draws: list[DrawResultDTO], weights: list[float]) -> dict[int, float]:
        total_weight = sum(weights) if draws and weights else 1
        weighted_counter: dict[int, float] = {number: 0.0 for number in range(1, 17)}
        for draw, weight in zip(draws, weights):
            weighted_counter[draw.blue_number] += weight
        return {number: round(weighted_counter[number] / total_weight, 6) for number in range(1, 17)}
