"""定时调度，默认每小时执行"""
from apscheduler.schedulers.background import BackgroundScheduler

from app.pipeline import run_intel_cycle
from app.db import SessionLocal

scheduler = BackgroundScheduler(timezone="UTC")


def task_hourly():
    db = SessionLocal()
    try:
        run_intel_cycle(db, report_type="daily", send_email=True, mode="news")
    finally:
        db.close()


def reschedule_crawl(interval: str):
    scheduler.remove_all_jobs()
    mapping = {
        "every_30m": ("interval", {"minutes": 30}),
        "hourly": ("interval", {"hours": 1}),
        "every_6h": ("interval", {"hours": 6}),
        "every_12h": ("interval", {"hours": 12}),
        "daily": ("cron", {"hour": 8}),
    }
    kind, kwargs = mapping.get(interval or "hourly", ("interval", {"hours": 1}))
    scheduler.add_job(task_hourly, kind, id="crawl_job", replace_existing=True, **kwargs)


def start_scheduler():
    from app.config import get_settings

    try:
        s = get_settings()
        # Prefer configured timezone when tzdata is available
        try:
            scheduler.configure(timezone=s.timezone or "UTC")
        except Exception:
            scheduler.configure(timezone="UTC")
        reschedule_crawl(s.crawl_interval)
        if not scheduler.running:
            scheduler.start()
    except Exception as exc:  # noqa: BLE001
        print(f"scheduler start skipped: {exc}")
