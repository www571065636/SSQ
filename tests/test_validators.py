from app.models.dto import RecommendationDTO
from app.utils.validators import format_red_numbers, parse_red_numbers, validate_blue_number, validate_red_numbers


def test_validate_red_numbers_sorts_values():
    assert validate_red_numbers([33, 1, 5, 8, 20, 16]) == [1, 5, 8, 16, 20, 33]


def test_validate_blue_number_range():
    assert validate_blue_number(16) == 16


def test_red_numbers_format_and_parse():
    formatted = format_red_numbers([1, 5, 8, 16, 20, 33])
    assert formatted == "01,05,08,16,20,33"
    assert parse_red_numbers(formatted) == [1, 5, 8, 16, 20, 33]

