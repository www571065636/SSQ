from __future__ import annotations

from typing import Protocol

from app.models.dto import RecommendationDTO, StrategyContext


class BaseStrategy(Protocol):
    name: str

    def generate(self, context: StrategyContext) -> RecommendationDTO:
        ...

