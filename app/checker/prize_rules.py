from __future__ import annotations


class PrizeRuleService:
    def __init__(self, prize_config: dict) -> None:
        self.prize_config = prize_config

    def resolve_prize(self, red_hits: int, blue_hit: bool) -> tuple[str | None, float | None]:
        if red_hits == 6 and blue_hit:
            return "first", self.prize_config.get("first")
        if red_hits == 6 and not blue_hit:
            return "second", self.prize_config.get("second")
        if red_hits == 5 and blue_hit:
            return "third", self.prize_config.get("third")
        if (red_hits == 5 and not blue_hit) or (red_hits == 4 and blue_hit):
            return "fourth", self.prize_config.get("fourth")
        if (red_hits == 4 and not blue_hit) or (red_hits == 3 and blue_hit):
            return "fifth", self.prize_config.get("fifth")
        if blue_hit and red_hits in {0, 1, 2}:
            return "sixth", self.prize_config.get("sixth")
        return None, None

