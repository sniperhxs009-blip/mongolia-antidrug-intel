"""情报流水线：采集 → 研判 → 告警邮件 → 报告落盘（支持实时进度回调）"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, Optional

from sqlalchemy.orm import Session

from app.analysis.engine import AnalysisEngine
from app.config import get_settings
from app.crawler.engine import CrawlEngine
from app.crawler.official_stats import OfficialStatsCollector
from app.crawler.search_feeds import SearchFeedCollector
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
    mode: str = "full",
) -> Dict[str, Any]:
    """mode=news：高频监测（仍含论坛+PDF）；mode=full：全量检索+研判+邮件。"""
    news_only = mode == "news"

    def emit(event_type: str, **payload: Any) -> None:
        if on_event:
            try:
                on_event(event_type, **payload)
            except Exception:  # noqa: BLE001
                logger.debug("pipeline progress callback failed", exc_info=True)

    result: Dict[str, Any] = {
        "started_at": datetime.utcnow().isoformat(),
        "mode": mode,
        "crawl": None,
        "search": None,
        "official_stats": None,
        "report_id": None,
        "alerts_sent": False,
        "email_sent": False,
    }

    emit(
        "phase",
        status="running",
        phase="启动",
        message="新闻监测已启动（含论坛/统计）" if news_only else "情报流水线已启动",
    )

    if not skip_crawl:
        # 修改原因：news/full 均执行脏数据清洗，防止俄/内蒙无关数据堆积
        try:
            from app.crawler.cleanup import purge_irrelevant_items, purge_noise_geo_items

            purged = purge_irrelevant_items(db)
            noise = purge_noise_geo_items(db)
            emit(
                "phase",
                status="running",
                phase="数据清洗",
                message=(
                    f"已清理无关 {purged.get('deleted', 0)} 条、"
                    f"噪音地域 {noise.get('deleted', 0) if isinstance(noise, dict) else noise} 条"
                ),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("cleanup failed: %s", exc)

        if settings.enable_search_feeds:
            emit(
                "phase",
                status="running",
                phase="最新新闻监测" if news_only else "关键词全量搜索",
                message=(
                    f"正在抓取涉毒新闻+论坛+快照（when:{getattr(settings,'news_when','1y')}）…"
                    if news_only
                    else f"正在全量词库+核心官网+论坛检索（when:{getattr(settings,'full_when','1y')}）…"
                ),
            )
            searcher = SearchFeedCollector(db, on_event=on_event)
            # news/full 均走完整检索通道（论坛 when 强制 1y；不再剔除 site:gov.mn 快照）
            result["search"] = searcher.run(mode="news" if news_only else "full")

        # news/full 均执行官方统计；full 额外含 PDF 发现
        if settings.enable_official_stats:
            emit(
                "phase",
                status="running",
                phase="官方统计采集",
                message="正在采集检察院/海关/UNODC 统计与 PDF 报表…",
            )
            stats_collector = OfficialStatsCollector(db, on_event=on_event)
            result["official_stats"] = stats_collector.run(mode="news" if news_only else "full")

        # 仅官网浅扫轻量化；页数上限放宽到 30 以配合 depth=2
        if settings.enable_official_crawl:
            old_max = settings.crawl_max_pages_per_source
            try:
                shallow = int(getattr(settings, "crawl_max_pages_core", 4) or 4)
                if shallow <= 0:
                    shallow = 4
                shallow = min(old_max if old_max > 0 else 30, max(4, min(max(shallow, 8), 30)))
                emit(
                    "phase",
                    status="running",
                    phase="核心官网浅扫",
                    message=f"检索完成后浅扫清单官网（每站最多 {shallow} 页，防漏）…",
                )
                settings.crawl_max_pages_per_source = shallow
                crawler = CrawlEngine(db, on_event=on_event)
                job = crawler.run_core_official_crawl(resume=False)
            finally:
                settings.crawl_max_pages_per_source = old_max

            if job is not None:
                result["crawl"] = {
                    "job_id": job.id,
                    "status": job.status,
                    "pages_fetched": job.pages_fetched,
                    "items_new": job.items_new,
                    "items_updated": job.items_updated,
                    "items_filtered": job.items_filtered,
                    "error_count": job.error_count,
                }
                if job.status == "failed" and not (result.get("search") or {}).get("items_new"):
                    emit("error", status="failed", phase="失败", message=job.message or "采集失败")
                    result["finished_at"] = datetime.utcnow().isoformat()
                    return result
            else:
                result["crawl"] = {"status": "skipped"}
        else:
            result["crawl"] = {"status": "skipped"}

    new_count = (
        (result.get("search") or {}).get("items_new", 0)
        + (result.get("crawl") or {}).get("items_new", 0)
        + (result.get("official_stats") or {}).get("items_new", 0)
    )
    upd_count = (result.get("search") or {}).get("items_updated", 0) + (result.get("crawl") or {}).get("items_updated", 0)

    # 新闻快扫：不生成报告、不发日简报；仅对新告警发邮件
    if news_only:
        mailer = EmailService(db)
        since = datetime.utcnow() - timedelta(hours=3)
        alert_items = (
            db.query(IntelItem)
            .filter(IntelItem.is_alert.is_(True))
            .filter(IntelItem.crawled_at >= since)
            .filter(IntelItem.status == "new")
            .order_by(IntelItem.crawled_at.desc())
            .all()
        )
        if alert_items and settings.enable_alert_email and send_email:
            emit("phase", status="emailing", phase="紧急告警", message=f"新告警 {len(alert_items)} 条，正在推送…")
            analyzer = AnalysisEngine(db)
            alert_report = analyzer.generate_report(report_type="alert", days=1)
            result["alerts_sent"] = mailer.send_alert(alert_items, alert_report)
            result["report_id"] = alert_report.id

        result["finished_at"] = datetime.utcnow().isoformat()
        emit(
            "done",
            status="success",
            phase="完成",
            report_id=result.get("report_id"),
            message=f"新闻监测完成：新增 {new_count}，更新 {upd_count}",
            items_new=new_count,
            items_updated=upd_count,
            pages_fetched=0,
            error_count=(result.get("search") or {}).get("error_count", 0),
        )
        return result

    emit("phase", status="analyzing", phase="交叉研判", message="正在生成情报研判报告…")
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
        message=f"全网巡检完成：新增 {new_count}，更新 {upd_count}",
        items_new=new_count,
        items_updated=upd_count,
        pages_fetched=(result.get("crawl") or {}).get("pages_fetched", 0),
        error_count=(result.get("crawl") or {}).get("error_count", 0),
    )
    return result
