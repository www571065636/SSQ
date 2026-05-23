from __future__ import annotations

from typing import Protocol

from app.models.dto import DrawResultDTO


class DrawCollectorProtocol(Protocol):
    def fetch_history(self, start_date: str, end_date: str) -> list[DrawResultDTO]:
        ...

    def fetch_latest(self) -> DrawResultDTO | None:
        ...

