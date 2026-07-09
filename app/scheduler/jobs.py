"""定时任务：高频新闻监测 + 每日全量研判 + 周报"""
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
    "every_30m": IntervalTrigger(minutes=30),
    "hourly": IntervalTrigger(hours=1),
    "every_6h": IntervalTrigger(hours=6),
    "every_12h": IntervalTrigger(hours=12),
    "daily": IntervalTrigger(hours=24),
}


def _job_news_monitor() -> None:
    """高频：只抓最新涉毒新闻，不生成完整日报告。"""
    logger.info("定时任务触发：新闻监测")
    db = SessionLocal()
    try:
        result = run_intel_cycle(db, report_type="daily", send_email=True, mode="news")
        logger.info("新闻监测完成: %s", result)
    except Exception:
        logger.exception("新闻监测失败")
    finally:
        db.close()


def _job_full_daily() -> None:
    """每日：全量搜索 + 研判报告 + 邮件简报。"""
    logger.info("定时任务触发：全量日研判")
    db = SessionLocal()
    try:
        result = run_intel_cycle(db, report_type="daily", send_email=True, mode="full")
        logger.info("全量日研判完成: %s", result)
    except Exception:
        logger.exception("全量日研判失败")
    finally:
        db.close()


def _job_weekly_report() -> None:
    logger.info("定时任务触发：周度研判报告")
    db = SessionLocal()
    try:
        result = run_intel_cycle(db, report_type="weekly", send_email=True, skip_crawl=True, mode="full")
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
    trigger = INTERVAL_MAP.get(settings.crawl_interval, INTERVAL_MAP["hourly"])
    # 高频新闻监测（默认每小时）
    sched.add_job(
        _job_news_monitor,
        trigger=trigger,
        id="news_monitor",
        replace_existing=True,
        max_instances=1,
        coalesce=True,
        next_run_time=datetime.now(),  # 启动后尽快跑一轮新闻
    )
    # 每天固定时刻全量研判 + 日简报
    sched.add_job(
        _job_full_daily,
        CronTrigger(
            hour=settings.email_daily_brief_hour,
            minute=settings.email_daily_brief_minute,
            timezone=settings.timezone,
        ),
        id="daily_full",
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
    logger.info(
        "调度器已启动：新闻监测=%s，每日全量=%02d:%02d",
        settings.crawl_interval,
        settings.email_daily_brief_hour,
        settings.email_daily_brief_minute,
    )
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
    trigger = INTERVAL_MAP.get(interval_key, INTERVAL_MAP["hourly"])
    try:
        sched.reschedule_job("news_monitor", trigger=trigger)
    except Exception:
        # 兼容旧 job id
        try:
            sched.reschedule_job("crawl_analyze", trigger=trigger)
        except Exception:
            logger.exception("重设巡检间隔失败")
            return
    logger.info("已重设新闻监测间隔: %s", interval_key)
