"""情报流水线：采集 → 研判 → 告警邮件 → 报告落盘（支持实时进度回调）"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

from sqlalchemy.orm import Session

from app.analysis.engine import AnalysisEngine
from app.config import get_settings
from app.crawler.engine import CrawlEngine
from app.db.models import IntelItem
from app.emailer.service import EmailService

logger = logging.getLogger(__name__)
settings = get_settings()

ProgressCallback = Optional[Callable[..., None]]


def run_intel_cycle(
    db: Session,
    report_type: str = "daily",
    send_email: bool = True,
    skip_crawl: bool = False,
    on_event: ProgressCallback = None,
) -> Dict[str, Any]:
    def emit(event_type: str, **payload: Any) -> None:
        if on_event:
            try:
                on_event(event_type, **payload)
            except Exception:  # noqa: BLE001
                logger.debug("pipeline progress callback failed", exc_info=True)

    result: Dict[str, Any] = {
        "started_at": datetime.utcnow().isoformat(),
        "crawl": None,
        "report_id": None,
        "alerts_sent": False,
        "email_sent": False,
    }

    emit("phase", status="running", phase="启动", message="情报流水线已启动")

    if not skip_crawl:
        crawler = CrawlEngine(db, on_event=on_event)
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
        if job.status == "failed":
            emit("error", status="failed", phase="失败", message=job.message or "采集失败")
            result["finished_at"] = datetime.utcnow().isoformat()
            return result

    emit("phase", status="analyzing", phase="交叉研判", message="正在生成公安情报研判报告…")
    analyzer = AnalysisEngine(db)
    report = analyzer.generate_report(report_type=report_type)
    result["report_id"] = report.id
    emit(
        "report",
        status="analyzing",
        phase="报告已生成",
        report_id=report.id,
        message=f"研判报告已生成：#{report.id}",
    )

    mailer = EmailService(db)

    since = datetime.utcnow() - timedelta(hours=2)
    alert_items = (
        db.query(IntelItem)
        .filter(IntelItem.is_alert.is_(True))
        .filter(IntelItem.crawled_at >= since)
        .order_by(IntelItem.crawled_at.desc())
        .all()
    )
    if alert_items and send_email:
        emit("phase", status="emailing", phase="紧急告警", message=f"检测到 {len(alert_items)} 条告警，正在推送…")
        alert_report = analyzer.generate_report(report_type="alert", days=1)
        result["alerts_sent"] = mailer.send_alert(alert_items, alert_report)

    if send_email:
        emit("phase", status="emailing", phase="邮件推送", message="正在发送情报简报邮件…")
        if report_type == "daily":
            result["email_sent"] = mailer.send_daily_brief(report)
        else:
            result["email_sent"] = mailer.send_report(report, kind=report_type)

    result["finished_at"] = datetime.utcnow().isoformat()
    emit(
        "done",
        status="success",
        phase="完成",
        report_id=report.id,
        message="全网巡检与研判流程已完成",
        items_new=(result.get("crawl") or {}).get("items_new", 0),
        items_updated=(result.get("crawl") or {}).get("items_updated", 0),
        pages_fetched=(result.get("crawl") or {}).get("pages_fetched", 0),
        error_count=(result.get("crawl") or {}).get("error_count", 0),
    )
    return result
