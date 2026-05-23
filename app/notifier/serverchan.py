from __future__ import annotations

import json
from urllib.parse import urlencode
from urllib.request import Request, urlopen


class ServerChanNotifier:
    channel_name = "serverchan"

    def __init__(self, sendkey: str) -> None:
        self.sendkey = sendkey

    def send(self, title: str, content: str) -> tuple[bool, str]:
        if not self.sendkey:
            return False, "missing serverchan sendkey"
        body = urlencode({"title": title, "desp": content}).encode()
        request = Request(f"https://sctapi.ftqq.com/{self.sendkey}.send", data=body, method="POST")
        request.add_header("Content-Type", "application/x-www-form-urlencoded")
        with urlopen(request, timeout=10) as response:
            text = response.read().decode("utf-8", errors="ignore")
        payload = json.loads(text)
        success = int(payload.get("code", -1)) == 0
        return success, text

