from __future__ import annotations

import argparse
import json

from app.bootstrap import build_container, run_job
from app.scheduler import SchedulerService


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="双色球数据分析与智能推送系统")
    parser.add_argument("--config", default="config.json", help="配置文件路径")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="初始化数据库")

    history = subparsers.add_parser("sync-history", help="同步历史开奖数据")
    history.add_argument("--start", required=True, help="开始日期 YYYY-MM-DD")
    history.add_argument("--end", required=True, help="结束日期 YYYY-MM-DD")

    subparsers.add_parser("sync-latest", help="同步最新开奖数据")

    analyze = subparsers.add_parser("analyze", help="生成统计快照")
    analyze.add_argument("--window", type=int, default=None, help="统计窗口期数")

    recommend = subparsers.add_parser("recommend", help="生成推荐号码")
    recommend.add_argument("--count", type=int, default=None, help="推荐组数")

    check = subparsers.add_parser("check", help="核对开奖")
    check.add_argument("--issue", required=True, help="待核对期号")

    subparsers.add_parser("run-scheduler", help="启动调度器")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    container = build_container(args.config)

    if args.command == "init-db":
        container.init_db()
        print("数据库初始化完成")
        return 0

    container.init_db()

    if args.command == "sync-history":
        result = run_job(container.job_repository, "sync_history", lambda: container.sync_history(args.start, args.end))
        print(json.dumps({"status": "success", "inserted": result}, ensure_ascii=False))
        return 0

    if args.command == "sync-latest":
        result = run_job(container.job_repository, "sync_latest", container.sync_latest)
        print(json.dumps({"status": "success", "inserted": result}, ensure_ascii=False))
        return 0

    if args.command == "analyze":
        result = run_job(
            container.job_repository,
            "analyze",
            lambda: container.analysis_service.build_snapshot(args.window),
        )
        print(
            json.dumps(
                {
                    "status": "success",
                    "based_on_issue": result.based_on_issue,
                    "snapshot_id": result.snapshot_id,
                    "window_size": result.window_size,
                },
                ensure_ascii=False,
            )
        )
        return 0

    if args.command == "recommend":
        count = args.count or int(container.config["recommendation"]["daily_count"])
        items = run_job(
            container.job_repository,
            "recommend",
            lambda: container.recommendation_service.generate_daily(count),
        )
        payload = [
            {
                "strategy": item.strategy_name,
                "red_numbers": item.red_numbers,
                "blue_number": item.blue_number,
                "target_issue_no": item.target_issue_no,
            }
            for item in items
        ]
        print(json.dumps({"status": "success", "count": len(items), "items": payload}, ensure_ascii=False))
        return 0

    if args.command == "check":
        items = run_job(
            container.job_repository,
            "check",
            lambda: container.check_service.check_issue(args.issue),
        )
        payload = [
            {
                "recommendation_id": item.recommendation_id,
                "red_hits": item.red_hits,
                "blue_hit": item.blue_hit,
                "prize_level": item.prize_level,
                "prize_amount": item.prize_amount,
            }
            for item in items
        ]
        print(json.dumps({"status": "success", "count": len(items), "items": payload}, ensure_ascii=False))
        return 0

    if args.command == "run-scheduler":
        scheduler = SchedulerService(container)
        scheduler.register_jobs()
        scheduler.run_forever()
        return 0

    parser.print_help()
    return 1

