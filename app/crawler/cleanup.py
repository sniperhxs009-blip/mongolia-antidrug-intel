"""修复版数据清理逻辑，放宽蒙古媒体域名判定，不再强制文本带蒙古关键词"""
from __future__ import annotations
import re
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from app.config import get_settings
from app.crawler.filters import is_drug_related, is_mongolia_country_related
from app.db.models import IntelItem, StatRecord
def purge_irrelevant_items(db: Session) -> dict:
    settings = get_settings()
    max_days = int(getattr(settings, "crawl_max_age_days", 365) or 365)
    cutoff = datetime.utcnow() - timedelta(days=max_days)
    rows = db.query(IntelItem).all()
    deleted = 0
    kept = 0
    for it in rows:
        pub = it.published_at
        if pub and pub < cutoff:
            db.delete(it)
            deleted += 1
            continue
        blob = " ".join([it.title or "",it.title_zh or "",it.summary or "",it.summary_zh or ""]).lower()
        drug_ok = is_drug_related(blob, loose=True)
        url_low = (it.url or "").lower()
        mn_media_domain = any(d in url_low for d in ["gogo.mn","ikon.mn","news.mn","montsame.mn","mongolnews.mn"])
        mn_ok = is_mongolia_country_related(blob) or mn_media_domain
        if not drug_ok:
            db.delete(it)
            deleted += 1
            continue
        if not mn_ok and not any(k in blob for k in ["芬太尼","fentanyl","安纳咖","анарга"]):
            db.delete(it)
            deleted += 1
            continue
        kept += 1
    for st in db.query(StatRecord).all():
        st_blob = f"{st.title}{st.raw_snippet}{st.org_name}".lower()
        if not is_drug_related(st_blob, loose=True):
            db.delete(st)
            deleted += 1
    db.commit()
    return {"deleted": deleted, "kept": kept, "scanned": len(rows)}
