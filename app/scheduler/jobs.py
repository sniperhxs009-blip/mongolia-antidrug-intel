"""定时调度，默认每小时执行"""
from apscheduler.schedulers.background import BackgroundScheduler
from app.pipeline import run_intel_cycle
from app.db import SessionLocal
scheduler = BackgroundScheduler(timezone="Asia/Ulaanbaatar")
def task_hourly():
    db = SessionLocal()
    run_intel_cycle(db, report_type="daily", send_email=True, mode="news")
    db.close()
def reschedule_crawl(interval: str):
    global scheduler
    scheduler.remove_all_jobs()
    match interval:
        case "every_30m":
            scheduler.add_job(task_hourly, "interval", minutes=30)
        case "hourly":
            scheduler.add_job(task_hourly, "interval", hours=1)
        case "every_6h":
            scheduler.add_job(task_hourly, "interval", hours=6)
        case "every_12h":
            scheduler.add_job(task_hourly, "interval", hours=12)
        case "daily":
            scheduler.add_job(task_hourly, "cron", hour=8)
def start_scheduler():
    from app.config import get_settings
    s = get_settings()
    reschedule_crawl(s.crawl_interval)
    scheduler.start()
