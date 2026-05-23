from __future__ import annotations


class SchedulerService:
    def __init__(self, app_services) -> None:
        self.app_services = app_services
        self._scheduler = None

    def register_jobs(self) -> None:
        try:
            from apscheduler.schedulers.background import BackgroundScheduler
        except ImportError as exc:
            raise RuntimeError("APScheduler is not installed. Please install requirements.txt first.") from exc
        if self._scheduler:
            return
        scheduler = BackgroundScheduler(timezone=self.app_services.config.get("app", {}).get("timezone", "Asia/Shanghai"))
        scheduler.add_job(
            self.app_services.run_drawday_prepare_job,
            "cron",
            day_of_week="tue,thu,sun",
            hour=20,
            minute=0,
            id="drawday_prepare",
            replace_existing=True,
        )
        scheduler.add_job(
            self.app_services.run_drawday_result_job,
            "cron",
            day_of_week="tue,thu,sun",
            hour=21,
            minute=30,
            id="drawday_result",
            replace_existing=True,
        )
        self._scheduler = scheduler

    def run_forever(self) -> None:
        if not hasattr(self, "_scheduler"):
            self.register_jobs()
        if self._scheduler and not self._scheduler.running:
            self._scheduler.start()

    def start(self) -> None:
        if not self._scheduler:
            self.register_jobs()
        if self._scheduler and not self._scheduler.running:
            self._scheduler.start()
