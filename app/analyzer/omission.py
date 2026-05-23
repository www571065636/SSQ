from __future__ import annotations

from app.models.dto import DrawResultDTO


class OmissionAnalyzer:
    def calc_omission(self, draws: list[DrawResultDTO]) -> dict[str, int]:
        omission: dict[str, int] = {}
        latest_first = list(reversed(draws))
        for number in range(1, 34):
            omission[f"red_{number:02d}"] = self._distance(latest_first, number, is_blue=False)
        for number in range(1, 17):
            omission[f"blue_{number:02d}"] = self._distance(latest_first, number, is_blue=True)
        return omission

    @staticmethod
    def _distance(draws: list[DrawResultDTO], number: int, is_blue: bool) -> int:
        for index, draw in enumerate(draws):
            if is_blue and draw.blue_number == number:
                return index
            if not is_blue and number in draw.red_numbers:
                return index
        return len(draws)

