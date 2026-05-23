from __future__ import annotations

from app.models.dto import PushResultDTO
from app.notifier.formatter import MessageFormatter
from app.notifier.serverchan import ServerChanNotifier
from app.notifier.wecom_bot import WeComBotNotifier
from app.repository.push_repository import PushRepository


class ConsoleNotifier:
    channel_name = "console"

    def send(self, title: str, content: str) -> tuple[bool, str]:
        print(title)
        print(content)
        return True, "printed to console"


class NotificationService:
    def __init__(self, config: dict, push_repository: PushRepository) -> None:
        self.config = config
        self.push_repository = push_repository
        self.formatter = MessageFormatter()

    def send_recommendations(self, batch_no: str, items) -> None:
        title, content = self.formatter.format_recommendation(items)
        self._send(batch_no, "recommend", title, content)

    def send_check_results(self, batch_no: str, issue_no: str, results) -> None:
        title, content = self.formatter.format_check_result(issue_no, results)
        self._send(batch_no, "check_result", title, content)

    def _send(self, batch_no: str, message_type: str, title: str, content: str) -> None:
        notifier = self._build_notifier()
        success, response = notifier.send(title, content)
        target = self.config["notifier"].get("target", "")
        self.push_repository.save(
            PushResultDTO(
                batch_no=batch_no,
                channel=notifier.channel_name,
                target=target,
                message_type=message_type,
                payload=f"{title}\n{content}",
                response_body=response,
                status="success" if success else "failed",
            )
        )

    def _build_notifier(self):
        if not self.config["notifier"].get("enabled", False):
            return ConsoleNotifier()
        channel = self.config["notifier"].get("default_channel", "console")
        if channel == "serverchan":
            return ServerChanNotifier(self.config["notifier"].get("serverchan_sendkey", ""))
        if channel == "wecom_bot":
            return WeComBotNotifier(self.config["notifier"].get("wecom_webhook", ""))
        return ConsoleNotifier()

