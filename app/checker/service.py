from __future__ import annotations

from app.checker.prize_rules import PrizeRuleService
from app.models.dto import CheckResultDTO, DrawResultDTO, RecommendationDTO
from app.repository.check_repository import CheckRepository
from app.repository.draw_repository import DrawRepository
from app.repository.recommendation_repository import RecommendationRepository


class CheckService:
    def __init__(
        self,
        draw_repository: DrawRepository,
        recommendation_repository: RecommendationRepository,
        check_repository: CheckRepository,
        prize_service: PrizeRuleService,
    ) -> None:
        self.draw_repository = draw_repository
        self.recommendation_repository = recommendation_repository
        self.check_repository = check_repository
        self.prize_service = prize_service

    def check_issue(self, issue_no: str) -> list[CheckResultDTO]:
        draw = self.draw_repository.get_by_issue(issue_no)
        if not draw:
            raise ValueError(f"draw issue not found: {issue_no}")
        recommendations = self.recommendation_repository.list_by_issue(issue_no)
        results = [self.compare_numbers(item, draw) for item in recommendations]
        self.check_repository.save_results(results)
        return results

    def compare_numbers(self, recommendation: RecommendationDTO, draw: DrawResultDTO) -> CheckResultDTO:
        red_hits = len(set(recommendation.red_numbers) & set(draw.red_numbers))
        blue_hit = recommendation.blue_number == draw.blue_number
        prize_level, prize_amount = self.prize_service.resolve_prize(red_hits, blue_hit)
        return CheckResultDTO(
            recommendation_id=int(recommendation.recommendation_id or 0),
            issue_no=draw.issue_no,
            red_hits=red_hits,
            blue_hit=blue_hit,
            prize_level=prize_level,
            prize_amount=prize_amount,
        )

