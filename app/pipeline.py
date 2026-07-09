"""情报流水线：采集 → 研判 → 告警邮件 → 报告落盘"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.analysis.engine import AnalysisEngine
from app.config import get_settings
from app.crawler.engine import CrawlEngine
from app.db.models import IntelItem
from app.emailer.service import EmailService

logger = logging.getLogger(__name__)
settings = get_settings()


def run_intel_cycle(
    db: Session,
    report_type: str = "daily",
    send_email: bool = True,
    skip_crawl: bool = False,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "started_at": datetime.utcnow().isoformat(),
        "crawl": None,
        "report_id": None,
        "alerts_sent": False,
        "email_sent": False,
    }

    if not skip_crawl:
        crawler = CrawlEngine(db)
        job = crawler.run_full_crawl(resume=True)
        result["crawl"] = {
            "job_id": job.id,
            "status": job.status,
            "pages_fetched": job.pages_fetched,
            "items_new": job.items_new,
            "items_updated": job.items_updated,
            "items_filtered": job.items_filtered,
            "error_count": job.error_count,
        }

    analyzer = AnalysisEngine(db)
    report = analyzer.generate_report(report_type=report_type)
    result["report_id"] = report.id

    mailer = EmailService(db)

    # 重大突发：最近 2 小时内新增告警条目即时推送
    since = datetime.utcnow() - timedelta(hours=2)
    alert_items = (
        db.query(IntelItem)
        .filter(IntelItem.is_alert.is_(True))
        .filter(IntelItem.crawled_at >= since)
        .order_by(IntelItem.crawled_at.desc())
        .all()
    )
    if alert_items and send_email:
        alert_report = analyzer.generate_report(report_type="alert", days=1)
        result["alerts_sent"] = mailer.send_alert(alert_items, alert_report)

    if send_email:
        if report_type == "daily":
            result["email_sent"] = mailer.send_daily_brief(report)
        else:
            result["email_sent"] = mailer.send_report(report, kind=report_type)

    result["finished_at"] = datetime.utcnow().isoformat()
    return result
