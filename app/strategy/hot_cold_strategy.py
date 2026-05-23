from __future__ import annotations

from app.models.dto import RecommendationDTO, StrategyContext
from app.utils.date import today_str
from app.utils.randomizer import create_rng


class HotColdStrategy:
    name = "hot_cold"

    def generate(self, context: StrategyContext) -> RecommendationDTO:
        rng = create_rng(context.rng_seed)
        hot_count = int(context.strategy_params.get("hot_count", 4))
        cold_count = int(context.strategy_params.get("cold_count", 2))
        if hot_count + cold_count != 6:
            hot_count, cold_count = 4, 2
        hot_pool = context.snapshot.hot_numbers or list(range(1, 34))
        cold_pool = [value for value in context.snapshot.cold_numbers if value not in hot_pool]
        if len(cold_pool) < cold_count:
            cold_pool = context.snapshot.cold_numbers or list(range(1, 34))
        if len(hot_pool) < hot_count:
            hot_pool = list(range(1, 34))
        selected = set(rng.sample(hot_pool, hot_count))
        remaining_cold_pool = [value for value in cold_pool if value not in selected]
        while len(remaining_cold_pool) < cold_count:
            candidate = rng.randint(1, 33)
            if candidate not in selected:
                remaining_cold_pool.append(candidate)
        selected.update(rng.sample(remaining_cold_pool, cold_count))
        while len(selected) < 6:
            selected.add(rng.randint(1, 33))
        blue_number = max(context.snapshot.blue_frequency, key=context.snapshot.blue_frequency.get)
        return RecommendationDTO(
            batch_no="",
            recommend_date=today_str(),
            target_issue_no=context.target_issue_no,
            strategy_name=self.name,
            red_numbers=sorted(selected),
            blue_number=blue_number,
        )

