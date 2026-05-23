from __future__ import annotations

from datetime import datetime, timedelta


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")


def today_str() -> str:
    return datetime.now().date().isoformat()


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%Y-%m-%d")


def next_issue_no(issue_no: str) -> str:
    width = len(issue_no)
    return str(int(issue_no) + 1).zfill(width)


def date_range_days(start_date: str, end_date: str) -> int:
    start = parse_date(start_date)
    end = parse_date(end_date)
    return (end - start).days


def shift_days(date_str: str, days: int) -> str:
    return (parse_date(date_str) + timedelta(days=days)).date().isoformat()

