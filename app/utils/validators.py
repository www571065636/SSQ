from __future__ import annotations

from app.models.dto import DrawResultDTO, RecommendationDTO


def validate_red_numbers(numbers: list[int]) -> list[int]:
    if len(numbers) != 6:
        raise ValueError("red_numbers must contain exactly 6 values")
    if len(set(numbers)) != 6:
        raise ValueError("red_numbers must be unique")
    if any(number < 1 or number > 33 for number in numbers):
        raise ValueError("red_numbers must be within 1-33")
    return sorted(numbers)


def validate_blue_number(number: int) -> int:
    if number < 1 or number > 16:
        raise ValueError("blue_number must be within 1-16")
    return number


def validate_draw(draw: DrawResultDTO) -> DrawResultDTO:
    draw.red_numbers = validate_red_numbers(draw.red_numbers)
    draw.blue_number = validate_blue_number(draw.blue_number)
    if not draw.issue_no:
        raise ValueError("issue_no is required")
    if not draw.draw_date:
        raise ValueError("draw_date is required")
    return draw


def validate_recommendation(recommendation: RecommendationDTO) -> RecommendationDTO:
    recommendation.red_numbers = validate_red_numbers(recommendation.red_numbers)
    recommendation.blue_number = validate_blue_number(recommendation.blue_number)
    return recommendation


def format_red_numbers(numbers: list[int]) -> str:
    return ",".join(f"{number:02d}" for number in sorted(numbers))


def parse_red_numbers(value: str) -> list[int]:
    return [int(item) for item in value.split(",") if item]

