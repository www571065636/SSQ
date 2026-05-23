from __future__ import annotations

from typing import Protocol


class BaseNotifier(Protocol):
    channel_name: str

    def send(self, title: str, content: str) -> tuple[bool, str]:
        ...

