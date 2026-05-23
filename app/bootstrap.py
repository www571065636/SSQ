from __future__ import annotations

import time
from dataclasses import dataclass
from itertools import groupby
from statistics import mean

from app.analyzer.service import AnalysisService
from app.checker.prize_rules import PrizeRuleService
from app.checker.service import CheckService
from app.collector.official import OfficialDrawCollector
from app.config import ConfigService
from app.job_logger import JobLogger
from app.notifier.service import NotificationService
from app.recommender.service import RecommendationService
from app.repository.analysis_repository import AnalysisRepository
from app.repository.check_repository import CheckRepository
from app.repository.db import Database
from app.repository.draw_repository import DrawRepository
from app.repository.job_repository import JobRepository
from app.repository.push_repository import PushRepository
from app.repository.recommendation_repository import RecommendationRepository


@dataclass(slots=True)
class ServiceContainer:
    config: dict
    draw_repository: DrawRepository
    analysis_repository: AnalysisRepository
    recommendation_repository: RecommendationRepository
    check_repository: CheckRepository
    job_repository: JobRepository
    push_repository: PushRepository
    collector: OfficialDrawCollector
    analysis_service: AnalysisService
    recommendation_service: RecommendationService
    check_service: CheckService
    notification_service: NotificationService
    job_logger: JobLogger

    def init_db(self) -> None:
        self.draw_repository.init_table()
        self.analysis_repository.init_table()
        self.recommendation_repository.init_table()
        self.check_repository.init_table()
        self.job_repository.init_table()
        self.push_repository.init_table()

    def sync_history(self, start_date: str, end_date: str) -> int:
        draws = self.collector.fetch_history(start_date, end_date)
        return self.draw_repository.save_many(draws)

    def sync_latest(self) -> int:
        draw = self.collector.fetch_latest()
        if not draw:
            return 0
        return 1 if self.draw_repository.save_one(draw) else 0

    def run_generate_recommendation_job(self) -> list:
        items = self.recommendation_service.generate_daily(int(self.config["recommendation"]["daily_count"]))
        if items:
            self.notification_service.send_recommendations(items[0].batch_no, items)
        return items

    def run_sync_latest_job(self) -> int:
        return self.sync_latest()

    def run_check_latest_job(self) -> list:
        latest = self.draw_repository.get_latest()
        if not latest:
            return []
        results = self.check_service.check_issue(latest.issue_no)
        batch_no = f"check-{latest.issue_no}"
        self.notification_service.send_check_results(batch_no, latest.issue_no, results)
        return results

    def run_weekly_sync_job(self) -> dict:
        inserted = self.sync_history("2000-01-01", "2099-12-31")
        snapshot = self.analysis_service.build_snapshot()
        return {"inserted": inserted, "snapshot_id": snapshot.snapshot_id, "based_on_issue": snapshot.based_on_issue}

    def run_drawday_prepare_job(self) -> dict:
        inserted = self.sync_history("2000-01-01", "2099-12-31")
        snapshot = self.analysis_service.build_snapshot()
        recommendations = self.recommendation_service.generate_daily(int(self.config["recommendation"]["daily_count"]))
        payload = {
            "inserted": inserted,
            "snapshot_id": snapshot.snapshot_id,
            "based_on_issue": snapshot.based_on_issue,
            "target_issue_no": recommendations[0].target_issue_no if recommendations else None,
            "recommendations": [
                {
                    "recommendation_id": item.recommendation_id,
                    "strategy_name": item.strategy_name,
                    "target_issue_no": item.target_issue_no,
                    "red_numbers": item.red_numbers,
                    "blue_number": item.blue_number,
                    "score": item.feature_summary.get("score", 0),
                    "feature_alignment_score": item.feature_summary.get("feature_alignment_score", 0),
                }
                for item in recommendations
            ],
        }
        self.job_logger.write("drawday_prepare", payload)
        return payload

    def run_drawday_result_job(self) -> dict:
        inserted = self.sync_latest()
        latest = self.draw_repository.get_latest()
        if not latest:
            payload = {"inserted": inserted, "checked_issue": None, "message": "no draw data"}
            self.job_logger.write("drawday_result", payload)
            return payload
        results = self.check_service.check_issue(latest.issue_no)
        summary = self._summarize_check_results(results)
        payload = {
            "inserted": inserted,
            "checked_issue": latest.issue_no,
            "draw_date": latest.draw_date,
            "winning_numbers": {
                "red_numbers": latest.red_numbers,
                "blue_number": latest.blue_number,
            },
            "summary": summary,
            "results": [
                {
                    "recommendation_id": item.recommendation_id,
                    "red_hits": item.red_hits,
                    "blue_hit": item.blue_hit,
                    "prize_level": item.prize_level,
                    "prize_amount": item.prize_amount,
                }
                for item in results
            ],
        }
        self.job_logger.write("drawday_result", payload)
        return payload

    def get_dashboard_data(self, issue_from: str | None = None, issue_to: str | None = None) -> dict:
        latest_draw = self.draw_repository.get_latest()
        latest_snapshot = self.analysis_repository.get_latest_snapshot()
        recent_draws = self.draw_repository.list_recent(20)
        recommendation_pool = self._filter_recommendations(self.recommendation_repository.list_all(), issue_from, issue_to)
        recent_recommendations = self._sort_recommendations_by_score(recommendation_pool)[:20]
        recent_checks = self._filter_checks(self.check_repository.list_recent(50), issue_from, issue_to)[:20]
        recent_jobs = self.job_repository.list_recent(10)
        latest_sync_job = self.job_repository.get_latest_success("sync_history")
        recommendation_stats = self._build_recommendation_stats(issue_from, issue_to)
        check_stats = self._build_check_stats(issue_from, issue_to)
        return {
            "latest_draw": latest_draw,
            "latest_snapshot": latest_snapshot,
            "recent_draws": recent_draws,
            "recent_recommendations": recent_recommendations,
            "recent_checks": recent_checks,
            "recent_jobs": recent_jobs,
            "draw_count": self.draw_repository.count(),
            "latest_sync_job": latest_sync_job,
            "data_source_name": self.config["crawler"].get("source_name", "-"),
            "data_source_url": self.config["crawler"].get("source_url", "-"),
            "recommendation_stats": recommendation_stats,
            "check_stats": check_stats,
            "issue_filter": {"issue_from": issue_from or "", "issue_to": issue_to or ""},
        }

    def _build_recommendation_stats(self, issue_from: str | None = None, issue_to: str | None = None) -> dict:
        items = self._sort_recommendations_by_score(self._filter_recommendations(self.recommendation_repository.list_all(), issue_from, issue_to))[:30]
        if not items:
            return {
                "avg_score": 0.0,
                "top_score": 0.0,
                "avg_alignment_score": 0.0,
                "strategy_breakdown": [],
                "recent_score_cards": [],
            }

        strategy_map: dict[str, list[RecommendationDTO]] = {}
        for item in items:
            strategy_map.setdefault(item.strategy_name, []).append(item)

        strategy_breakdown = []
        for strategy_name, strategy_items in strategy_map.items():
            scores = [float(row.feature_summary.get("score", 0)) for row in strategy_items]
            strategy_breakdown.append(
                {
                    "strategy_name": strategy_name,
                    "count": len(strategy_items),
                    "avg_score": round(mean(scores), 4) if scores else 0.0,
                    "top_score": round(max(scores), 4) if scores else 0.0,
                }
            )
        strategy_breakdown.sort(key=lambda row: (row["avg_score"], row["count"]), reverse=True)

        score_ranked_items = self._sort_recommendations_by_score(items)

        recent_score_cards = []
        for item in score_ranked_items[:8]:
            summary = item.feature_summary
            recent_score_cards.append(
                {
                    "id": item.recommendation_id,
                    "issue_no": item.target_issue_no,
                    "strategy_name": item.strategy_name,
                    "score": round(float(summary.get("score", 0)), 4),
                    "alignment_score": round(float(summary.get("feature_alignment_score", 0)), 4),
                    "numbers": {
                        "reds": item.red_numbers,
                        "blue": item.blue_number,
                    },
                    "tags": [
                        f"和值 {summary.get('sum', '-')}",
                        f"三区 {summary.get('zones', '-')}",
                        f"012路 {summary.get('route_012', '-')}",
                    ],
                }
            )

        all_scores = [float(item.feature_summary.get("score", 0)) for item in items]
        all_alignment_scores = [float(item.feature_summary.get("feature_alignment_score", 0)) for item in items]
        return {
            "avg_score": round(mean(all_scores), 4) if all_scores else 0.0,
            "top_score": round(max(all_scores), 4) if all_scores else 0.0,
            "avg_alignment_score": round(mean(all_alignment_scores), 4) if all_alignment_scores else 0.0,
            "strategy_breakdown": strategy_breakdown,
            "recent_score_cards": recent_score_cards,
        }

    def _build_check_stats(self, issue_from: str | None = None, issue_to: str | None = None) -> dict:
        checks = self._filter_checks(self.check_repository.list_all(), issue_from, issue_to)
        recommendations = self._filter_recommendations(self.recommendation_repository.list_all(), issue_from, issue_to)
        if not checks or not recommendations:
            return {
                "checked_count": len(checks),
                "hit_rate": 0.0,
                "blue_hit_rate": 0.0,
                "avg_red_hits": 0.0,
                "strategy_hit_board": [],
                "issue_trend": [],
            }

        recommendation_map = {int(item.recommendation_id or 0): item for item in recommendations}
        strategy_bucket: dict[str, list[dict]] = {}
        for row in checks:
            item = recommendation_map.get(int(row["recommendation_id"]))
            if not item:
                continue
            strategy_bucket.setdefault(item.strategy_name, []).append(row)

        strategy_hit_board = []
        for strategy_name, rows in strategy_bucket.items():
            avg_red_hits = mean(int(row["red_hits"]) for row in rows)
            blue_hit_rate = mean(1 if int(row["blue_hit"]) else 0 for row in rows)
            hit_rate = mean(1 if int(row["red_hits"]) >= 4 or int(row["blue_hit"]) else 0 for row in rows)
            strategy_hit_board.append(
                {
                    "strategy_name": strategy_name,
                    "checked_count": len(rows),
                    "avg_red_hits": round(avg_red_hits, 4),
                    "blue_hit_rate": round(blue_hit_rate, 4),
                    "hit_rate": round(hit_rate, 4),
                }
            )
        strategy_hit_board.sort(key=lambda row: (row["hit_rate"], row["avg_red_hits"]), reverse=True)

        overall_avg_red_hits = mean(int(row["red_hits"]) for row in checks)
        overall_blue_hit_rate = mean(1 if int(row["blue_hit"]) else 0 for row in checks)
        overall_hit_rate = mean(1 if int(row["red_hits"]) >= 4 or int(row["blue_hit"]) else 0 for row in checks)
        return {
            "checked_count": len(checks),
            "hit_rate": round(overall_hit_rate, 4),
            "blue_hit_rate": round(overall_blue_hit_rate, 4),
            "avg_red_hits": round(overall_avg_red_hits, 4),
            "strategy_hit_board": strategy_hit_board,
            "issue_trend": self._build_issue_trend(checks),
        }

    def _build_issue_trend(self, checks: list[dict]) -> list[dict]:
        ordered = sorted(checks, key=lambda row: str(row["issue_no"]))
        trend = []
        for issue_no, rows_iter in groupby(ordered, key=lambda row: str(row["issue_no"])):
            rows = list(rows_iter)
            avg_red_hits = mean(int(row["red_hits"]) for row in rows)
            blue_hit_rate = mean(1 if int(row["blue_hit"]) else 0 for row in rows)
            hit_rate = mean(1 if int(row["red_hits"]) >= 4 or int(row["blue_hit"]) else 0 for row in rows)
            trend.append(
                {
                    "issue_no": issue_no,
                    "checked_count": len(rows),
                    "avg_red_hits": round(avg_red_hits, 4),
                    "blue_hit_rate": round(blue_hit_rate, 4),
                    "hit_rate": round(hit_rate, 4),
                }
            )
        return trend

    @staticmethod
    def _summarize_check_results(results) -> dict:
        if not results:
            return {
                "checked_count": 0,
                "avg_red_hits": 0.0,
                "blue_hit_rate": 0.0,
                "hit_rate": 0.0,
                "prize_counts": {},
            }
        avg_red_hits = mean(item.red_hits for item in results)
        blue_hit_rate = mean(1 if item.blue_hit else 0 for item in results)
        hit_rate = mean(1 if item.prize_level else 0 for item in results)
        prize_counts: dict[str, int] = {}
        for item in results:
            key = item.prize_level or "未中奖"
            prize_counts[key] = prize_counts.get(key, 0) + 1
        return {
            "checked_count": len(results),
            "avg_red_hits": round(avg_red_hits, 4),
            "blue_hit_rate": round(blue_hit_rate, 4),
            "hit_rate": round(hit_rate, 4),
            "prize_counts": prize_counts,
        }

    @staticmethod
    def _filter_recommendations(items: list[RecommendationDTO], issue_from: str | None, issue_to: str | None) -> list[RecommendationDTO]:
        if not issue_from and not issue_to:
            return items
        filtered = []
        for item in items:
            issue_no = item.target_issue_no or ""
            if issue_from and issue_no and issue_no < issue_from:
                continue
            if issue_to and issue_no and issue_no > issue_to:
                continue
            filtered.append(item)
        return filtered

    @staticmethod
    def _filter_checks(items: list[dict], issue_from: str | None, issue_to: str | None) -> list[dict]:
        if not issue_from and not issue_to:
            return items
        filtered = []
        for row in items:
            issue_no = str(row["issue_no"])
            if issue_from and issue_no < issue_from:
                continue
            if issue_to and issue_no > issue_to:
                continue
            filtered.append(row)
        return filtered

    @staticmethod
    def _sort_recommendations_by_score(items: list[RecommendationDTO]) -> list[RecommendationDTO]:
        return sorted(
            items,
            key=lambda row: (
                str(row.target_issue_no or ""),
                float(row.feature_summary.get("score", 0)),
                float(row.feature_summary.get("feature_alignment_score", 0)),
                int(row.recommendation_id or 0),
            ),
            reverse=True,
        )


def build_container(config_path: str = "config.json") -> ServiceContainer:
    config_service = ConfigService()
    config = config_service.load(config_path)
    database = Database(config["database"]["path"])
    draw_repository = DrawRepository(database)
    analysis_repository = AnalysisRepository(database)
    recommendation_repository = RecommendationRepository(database)
    check_repository = CheckRepository(database)
    job_repository = JobRepository(database)
    push_repository = PushRepository(database)
    collector = OfficialDrawCollector(config["crawler"])
    analysis_service = AnalysisService(draw_repository, analysis_repository, config)
    recommendation_service = RecommendationService(draw_repository, analysis_repository, recommendation_repository, config)
    prize_service = PrizeRuleService(config["prize_rules"])
    check_service = CheckService(draw_repository, recommendation_repository, check_repository, prize_service)
    notification_service = NotificationService(config, push_repository)
    job_logger = JobLogger(config.get("app", {}).get("scheduled_log_path", "logs/scheduled_jobs.log"))
    return ServiceContainer(
        config=config,
        draw_repository=draw_repository,
        analysis_repository=analysis_repository,
        recommendation_repository=recommendation_repository,
        check_repository=check_repository,
        job_repository=job_repository,
        push_repository=push_repository,
        collector=collector,
        analysis_service=analysis_service,
        recommendation_service=recommendation_service,
        check_service=check_service,
        notification_service=notification_service,
        job_logger=job_logger,
    )


def run_job(job_repository: JobRepository, job_name: str, func):
    started_at = time.perf_counter()
    run_id = job_repository.create_run(job_name)
    try:
        result = func()
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        job_repository.finish_run(run_id, "success", _message_for(result), duration_ms)
        return result
    except Exception as exc:
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        job_repository.finish_run(run_id, "failed", str(exc), duration_ms)
        raise


def _message_for(result) -> str:
    if isinstance(result, list):
        return f"items={len(result)}"
    return str(result)
