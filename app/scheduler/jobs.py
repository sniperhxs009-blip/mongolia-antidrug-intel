"""定时任务系统：每日/12小时/6小时/每小时巡检 + 日简报推送"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from app.config import get_settings
from app.db.models import SessionLocal
from app.pipeline import run_intel_cycle

logger = logging.getLogger(__name__)
settings = get_settings()

_scheduler: Optional[BackgroundScheduler] = None


INTERVAL_MAP = {
    "hourly": IntervalTrigger(hours=1),
    "every_6h": IntervalTrigger(hours=6),
    "every_12h": IntervalTrigger(hours=12),
    "daily": IntervalTrigger(hours=24),
}


def _job_crawl_and_analyze() -> None:
    logger.info("定时任务触发：全网巡检抓取 + 研判")
    db = SessionLocal()
    try:
        result = run_intel_cycle(db, report_type="daily", send_email=True)
        logger.info("定时任务完成: %s", result)
    except Exception:
        logger.exception("定时任务失败")
    finally:
        db.close()


def _job_weekly_report() -> None:
    logger.info("定时任务触发：周度研判报告")
    db = SessionLocal()
    try:
        result = run_intel_cycle(db, report_type="weekly", send_email=True, skip_crawl=True)
        logger.info("周报完成: %s", result)
    except Exception:
        logger.exception("周报任务失败")
    finally:
        db.close()


def start_scheduler() -> BackgroundScheduler:
    global _scheduler
    if _scheduler and _scheduler.running:
        return _scheduler

    sched = BackgroundScheduler(timezone=settings.timezone)
    trigger = INTERVAL_MAP.get(settings.crawl_interval, INTERVAL_MAP["daily"])
    sched.add_job(
        _job_crawl_and_analyze,
        trigger=trigger,
        id="crawl_analyze",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(),  # 启动后尽快跑一轮
    )
    sched.add_job(
        _job_crawl_and_analyze,
        CronTrigger(
            hour=settings.email_daily_brief_hour,
            minute=settings.email_daily_brief_minute,
            timezone=settings.timezone,
        ),
        id="daily_brief",
        replace_existing=True,
        max_instances=1,
    )
    sched.add_job(
        _job_weekly_report,
        CronTrigger(day_of_week="mon", hour=9, minute=0, timezone=settings.timezone),
        id="weekly_report",
        replace_existing=True,
        max_instances=1,
    )
    sched.start()
    _scheduler = sched
    logger.info("调度器已启动，巡检间隔=%s", settings.crawl_interval)
    return sched


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        _scheduler = None


def get_scheduler() -> Optional[BackgroundScheduler]:
    return _scheduler


def reschedule_crawl(interval_key: str) -> None:
    settings.crawl_interval = interval_key
    sched = get_scheduler()
    if not sched:
        return
    trigger = INTERVAL_MAP.get(interval_key, INTERVAL_MAP["daily"])
    sched.reschedule_job("crawl_analyze", trigger=trigger)
    logger.info("已重设巡检间隔: %s", interval_key)
