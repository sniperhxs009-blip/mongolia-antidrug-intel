"""清理不符合「蒙古国 + 涉毒」双条件的脏数据。"""
from __future__ import annotations

import re
from typing import Dict

from sqlalchemy.orm import Session

from app.crawler.filters import is_drug_related
from app.db.models import IntelItem

MONGOLIA_MARKERS = [
    "mongolia", "mongolian", "улаанбаатар", "ulaanbaatar",
    "монгол", "蒙古国", "乌兰巴托",
]


def is_mongolia_related(text: str) -> bool:
    t = (text or "")
    tl = t.lower()
    if "内蒙古" in t and "蒙古国" not in t:
        return False
    if re.search(r"\binner mongolia\b", tl):
        return False
    if any(m in tl for m in MONGOLIA_MARKERS):
        return True
    if "蒙古国" in t:
        return True
    # 蒙古媒体域名文章：由调用方结合 org/url 判断
    return False


def is_from_mn_media(item: IntelItem) -> bool:
    url = (item.url or "").lower()
    org = (item.org_name or "")
    if any(d in url for d in ("gogo.mn", "montsame.mn", "ikon.mn", "news.mn", "police.gov.mn", "gov.mn")):
        return True
    if "站内搜索" in org:
        return True
    return False


def purge_irrelevant_items(db: Session) -> Dict[str, int]:
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
        drug_ok = is_drug_related(blob, loose=True)
        mn_ok = is_mongolia_related(blob) or is_from_mn_media(it)
        # 媒体站内也必须涉毒
        if is_from_mn_media(it) and not drug_ok:
            db.delete(it)
            deleted += 1
            continue
        if not drug_ok or not mn_ok:
            db.delete(it)
            deleted += 1
            continue
        kept += 1
    db.commit()
    return {"deleted": deleted, "kept": kept, "scanned": len(rows)}
