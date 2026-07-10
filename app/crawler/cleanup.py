"""清理不符合「蒙古国 + 真正涉毒」双条件的脏数据。"""
from __future__ import annotations

import re
from typing import Dict

from sqlalchemy.orm import Session

from app.crawler.filters import is_drug_related, is_mongolia_country_related
from app.db.models import IntelItem, StatRecord


def is_from_mn_media(item: IntelItem) -> bool:
    url = (item.url or "").lower()
    org = item.org_name or ""
    if any(
        d in url
        for d in (
            "gogo.mn", "montsame.mn", "ikon.mn", "news.mn",
            "police.gov.mn", "gov.mn", "prosecutor.mn", "customs.gov.mn",
        )
    ):
        return True
    return "站内搜索" in org


def purge_irrelevant_items(db: Session) -> Dict[str, int]:
    from datetime import datetime, timedelta

    from app.config import get_settings

    settings = get_settings()
    max_days = int(getattr(settings, "crawl_max_age_days", 30) or 30)
    cutoff = datetime.utcnow() - timedelta(days=max_days)

    rows = db.query(IntelItem).all()
    deleted = 0
    kept = 0
    for it in rows:
        blob = " ".join(
            [
                it.title or "",
                it.title_zh or "",
                it.summary or "",
                it.summary_zh or "",
                it.content or "",
                it.content_zh or "",
            ]
        )
        # 过期旧闻（有发布时间）一律清理
        pub = it.published_at
        if pub and pub < cutoff:
            db.delete(it)
            deleted += 1
            continue
        drug_ok = is_drug_related(blob, loose=True)
        mn_ok = is_mongolia_country_related(blob) or is_from_mn_media(it)
        if is_from_mn_media(it) and not drug_ok:
            db.delete(it)
            deleted += 1
            continue
        if not drug_ok or not mn_ok:
            db.delete(it)
            deleted += 1
            continue
        kept += 1

    for st in db.query(StatRecord).all():
        blob = " ".join([st.title or "", st.raw_snippet or "", st.org_name or ""])
        if not is_mongolia_country_related(blob) and "蒙古" not in (st.org_name or ""):
            if "mongolia" not in blob.lower() and "монгол" not in blob.lower() and "蒙古" not in blob:
                db.delete(st)
                deleted += 1

    db.commit()
    return {"deleted": deleted, "kept": kept, "scanned": len(rows)}
