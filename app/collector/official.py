from __future__ import annotations

from pathlib import Path
import time
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import requests

from app.collector.parser import DrawParser
from app.models.dto import DrawResultDTO
from app.utils.validators import validate_draw


class OfficialDrawCollector:
    def __init__(self, crawler_config: dict) -> None:
        self.crawler_config = crawler_config
        self.parser = DrawParser()

    def fetch_history(self, start_date: str, end_date: str) -> list[DrawResultDTO]:
        draws = self._load_source()
        return [draw for draw in draws if start_date <= draw.draw_date <= end_date]

    def fetch_latest(self) -> DrawResultDTO | None:
        draws = self._load_source()
        if not draws:
            return None
        return sorted(draws, key=lambda item: item.issue_no)[-1]

    def _load_source(self) -> list[DrawResultDTO]:
        source_type = self.crawler_config.get("source_type", "json_file")
        source_name = self.crawler_config.get("source_name", "unknown")
        source_url = self.crawler_config.get("source_url", "")
        if source_type == "cwl_api":
            return self._load_cwl_api(source_name, source_url)
        if source_type in {"json_file", "csv_file", "html_file"}:
            return self.parser.parse_path(Path(source_url), source_name, source_url)
        request = Request(source_url, headers={"User-Agent": "Mozilla/5.0"})
        timeout = int(self.crawler_config.get("timeout_seconds", 10))
        with urlopen(request, timeout=timeout) as response:
            text = response.read().decode("utf-8", errors="ignore")
        if source_type == "json_url":
            return self.parser.parse_json_text(text, source_name, source_url)
        if source_type == "csv_url":
            return self.parser.parse_csv_text(text, source_name, source_url)
        return self.parser.parse_html_text(text, source_name, source_url)

    def _load_cwl_api(self, source_name: str, source_url: str) -> list[DrawResultDTO]:
        payload = self._request_cwl_100(source_url)
        result = payload.get("result") or []
        draws: list[DrawResultDTO] = []
        for item in result:
            red_numbers = [int(part) for part in str(item["red"]).split(",") if part]
            blue_values = [int(part) for part in str(item["blue"]).split(",") if part]
            draw = DrawResultDTO(
                issue_no=str(item["code"]),
                draw_date=self._normalize_draw_date(str(item["date"])),
                red_numbers=red_numbers,
                blue_number=blue_values[0] if blue_values else 0,
                source_name=source_name,
                source_url=source_url,
                raw_payload=str(item),
            )
            draws.append(validate_draw(draw))
        draws.sort(key=lambda item: item.issue_no)
        return draws

    def _request_cwl_100(self, source_url: str) -> dict:
        params = {
            "name": "ssq",
            "issueCount": int(self.crawler_config.get("issue_count", 100)),
        }
        timeout = int(self.crawler_config.get("timeout_seconds", 10))
        headers = {"User-Agent": "Mozilla/5.0"}
        response = requests.get(source_url, params=params, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _normalize_draw_date(value: str) -> str:
        return value.split("(")[0].strip()
