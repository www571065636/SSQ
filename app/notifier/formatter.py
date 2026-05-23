from __future__ import annotations

from app.models.dto import CheckResultDTO, RecommendationDTO


class MessageFormatter:
    def format_recommendation(self, items: list[RecommendationDTO]) -> tuple[str, str]:
        title = f"双色球推荐 {items[0].recommend_date}" if items else "双色球推荐"
        lines = []
        for index, item in enumerate(items, start=1):
            red = " ".join(f"{value:02d}" for value in item.red_numbers)
            lines.append(f"{index}. {red} + {item.blue_number:02d} [{item.strategy_name}]")
        return title, "\n".join(lines)

    def format_check_result(self, issue_no: str, results: list[CheckResultDTO]) -> tuple[str, str]:
        title = f"双色球核对结果 {issue_no}"
        if not results:
            return title, "没有找到需要核对的推荐记录。"
        lines = []
        for index, item in enumerate(results, start=1):
            prize = item.prize_level or "未中奖"
            lines.append(f"{index}. 命中{item.red_hits}红+{int(item.blue_hit)}蓝，结果：{prize}")
        return title, "\n".join(lines)

    def format_system_alert(self, message: str) -> tuple[str, str]:
        return "双色球系统告警", message

