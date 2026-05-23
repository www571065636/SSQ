from __future__ import annotations

from app.models.dto import RecommendationDTO, StrategyContext
from app.utils.date import today_str
from app.utils.randomizer import create_rng


class RandomStrategy:
    name = "random"

    def generate(self, context: StrategyContext) -> RecommendationDTO:
        rng = create_rng(context.rng_seed)
        red_numbers = sorted(rng.sample(range(1, 34), 6))
        blue_number = rng.randint(1, 16)
        return RecommendationDTO(
            batch_no="",
            recommend_date=today_str(),
            target_issue_no=context.target_issue_no,
            strategy_name=self.name,
            red_numbers=red_numbers,
            blue_number=blue_number,
        )

