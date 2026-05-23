from __future__ import annotations

import json
from urllib.request import Request, urlopen


class WeComBotNotifier:
    channel_name = "wecom_bot"

    def __init__(self, webhook: str) -> None:
        self.webhook = webhook

    def send(self, title: str, content: str) -> tuple[bool, str]:
        if not self.webhook:
            return False, "missing wecom webhook"
        payload = json.dumps({"msgtype": "text", "text": {"content": f"{title}\n{content}"}}).encode("utf-8")
        request = Request(self.webhook, data=payload, method="POST")
        request.add_header("Content-Type", "application/json")
        with urlopen(request, timeout=10) as response:
            text = response.read().decode("utf-8", errors="ignore")
        result = json.loads(text)
        success = int(result.get("errcode", -1)) == 0
        return success, text

