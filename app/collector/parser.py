from __future__ import annotations

import csv
import json
import re
from pathlib import Path

from app.models.dto import DrawResultDTO
from app.utils.validators import validate_draw


class DrawParser:
    def parse_json_text(self, text: str, source_name: str, source_url: str) -> list[DrawResultDTO]:
        payload = json.loads(text)
        if not isinstance(payload, list):
            raise ValueError("json source must be a list")
        return [self._from_mapping(item, source_name, source_url) for item in payload]

    def parse_csv_text(self, text: str, source_name: str, source_url: str) -> list[DrawResultDTO]:
        rows = csv.DictReader(text.splitlines())
        return [self._from_mapping(row, source_name, source_url) for row in rows]

    def parse_html_text(self, text: str, source_name: str, source_url: str) -> list[DrawResultDTO]:
        pattern = re.compile(
            r"(?P<issue>\d{5,})\D+(?P<date>\d{4}-\d{2}-\d{2})\D+"
            r"(?P<r1>\d{1,2})\D+(?P<r2>\d{1,2})\D+(?P<r3>\d{1,2})\D+"
            r"(?P<r4>\d{1,2})\D+(?P<r5>\d{1,2})\D+(?P<r6>\d{1,2})\D+(?P<blue>\d{1,2})"
        )
        draws = []
        for match in pattern.finditer(text):
            draws.append(
                validate_draw(
                    DrawResultDTO(
                        issue_no=match.group("issue"),
                        draw_date=match.group("date"),
                        red_numbers=[int(match.group(f"r{i}")) for i in range(1, 7)],
                        blue_number=int(match.group("blue")),
                        source_name=source_name,
                        source_url=source_url,
                        raw_payload=match.group(0),
                    )
                )
            )
        return draws

    def parse_path(self, path: Path, source_name: str, source_url: str) -> list[DrawResultDTO]:
        text = path.read_text(encoding="utf-8")
        suffix = path.suffix.lower()
        if suffix == ".json":
            return self.parse_json_text(text, source_name, source_url)
        if suffix == ".csv":
            return self.parse_csv_text(text, source_name, source_url)
        return self.parse_html_text(text, source_name, source_url)

    def _from_mapping(self, item: dict, source_name: str, source_url: str) -> DrawResultDTO:
        red_values = item.get("red_numbers")
        if isinstance(red_values, str):
            red_numbers = [int(part) for part in red_values.split(",")]
        else:
            red_numbers = [int(part) for part in red_values]
        draw = DrawResultDTO(
            issue_no=str(item["issue_no"]),
            draw_date=str(item["draw_date"]),
            red_numbers=red_numbers,
            blue_number=int(item["blue_number"]),
            source_name=source_name,
            source_url=source_url,
            raw_payload=json.dumps(item, ensure_ascii=False),
        )
        return validate_draw(draw)

