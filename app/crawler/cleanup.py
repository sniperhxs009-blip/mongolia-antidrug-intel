"""批量清洗无关情报；支持一键清理内蒙古/俄边境脏数据。

修改原因：历史噪音入库后需可追溯清理。
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.audit import audit_log
from app.crawler.filters import is_drug_related, is_mongolia_country_related
from app.db.models import IntelItem, StatRecord
from config.core_official import is_forbidden_url

logger = logging.getLogger(__name__)

NOISE_GEO = ("内蒙古", "Inner Mongolia", "乌兰乌德", "布里亚特", "赤塔", "恰克图", "后贝加尔", "Buryat", "Chita", "Kyakhta")


def purge_irrelevant_items(db: Session) -> dict:
    deleted = 0
    kept = 0
    items = db.query(IntelItem).all()
    for it in items:
        blob = " ".join(
            [
                it.title or "",
                it.title_zh or "",
                it.summary or "",
                it.summary_zh or "",
                it.content or "",
                it.content_zh or "",
                it.url or "",
            ]
        )
        if is_forbidden_url(it.url or "") or "gov.mn" in (it.url or "").lower():
            db.delete(it)
            deleted += 1
            continue
        # 地域：必须蒙古国相关
        if not is_mongolia_country_related(blob):
            db.delete(it)
            deleted += 1
            continue
        # 涉毒：严格强词
        if not is_drug_related(blob, loose=False):
            db.delete(it)
            deleted += 1
            continue
        kept += 1
    db.commit()
    audit_log("purge_irrelevant", detail={"deleted": deleted, "kept": kept})
    return {"deleted": deleted, "kept": kept}


def purge_noise_geo_items(db: Session) -> dict:
    """一键清理内蒙古、俄边境无关历史脏数据。"""
    deleted = 0
    items = db.query(IntelItem).all()
    for it in items:
        blob = " ".join([it.title or "", it.summary or "", it.content or "", it.title_zh or "", it.summary_zh or ""])
        if any(n in blob for n in NOISE_GEO) and not is_mongolia_country_related(blob):
            db.delete(it)
            deleted += 1
    db.commit()
    audit_log("purge_noise_geo", detail={"deleted": deleted})
    return {"deleted": deleted}


def archive_old_non_critical(db: Session, days: int = 30) -> dict:
    """归档/删除超 N 天非重要、非告警情报，控制库体积。"""
    cutoff = datetime.utcnow() - timedelta(days=days)
    q = (
        db.query(IntelItem)
        .filter(IntelItem.crawled_at < cutoff)
        .filter(IntelItem.is_alert.is_(False))
        .filter(IntelItem.intel_level.notin_(["重要", "紧急"]))
    )
    n = q.count()
    for it in q.limit(5000).all():
        db.delete(it)
    db.commit()
    audit_log("archive_old_intel", detail={"deleted": n, "days": days})
    return {"deleted": n, "days": days}
