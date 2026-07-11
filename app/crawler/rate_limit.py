"""单站日抓取频次限制。

原缺陷：全球统一低限额，蒙古本土媒体很快触顶导致漏采。
优化：对 montsame/gogo/ikon/news.mn/ubpost 等本土媒体放宽日限额；
国际小众高危站维持默认限制。
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime
from typing import Dict
from urllib.parse import urlparse

from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import SystemSetting

logger = logging.getLogger(__name__)
settings = get_settings()

KEY = "host_crawl_quota"

# 蒙古本土媒体：放宽日限额（相对默认值放大）
MN_MEDIA_HOST_SUFFIXES = (
    "montsame.mn",
    "gogo.mn",
    "ikon.mn",
    "news.mn",
    "mongolnews.mn",
    "ubpost.mn",
)


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().split(":")[0]
    except Exception:
        return ""


def _is_mn_media(host: str) -> bool:
    h = (host or "").replace("www.", "")
    return any(h == s or h.endswith("." + s) for s in MN_MEDIA_HOST_SUFFIXES)


def _limit_for_host(host: str) -> int:
    base = int(getattr(settings, "crawl_max_per_host_per_day", 10) or 10)
    if _is_mn_media(host):
        # 修改原因：蒙古本土媒体单日上限 50（单独豁免扩容）
        return 50
    h = (host or "").replace("www.", "")
    # 修改原因：国内新华网/禁毒网等单日上限降至 5
    domestic_cn = (
        "news.cn", "xinhuanet.com", "nncc626.com", "nmg.110.gov.cn",
    )
    if any(h == s or h.endswith("." + s) for s in domestic_cn):
        return 5
    noisy = (
        "reddit.com", "zhihu.com", "tieba.baidu.com", "bluelight.org",
        "reuters.com", "bbc.com", "apnews.com", "tass.com", "ria.ru",
    )
    if any(h == s or h.endswith("." + s) for s in noisy):
        return 10
    return min(base, 10)


def _load(db: Session) -> Dict[str, dict]:
    row = db.query(SystemSetting).filter(SystemSetting.key == KEY).first()
    if not row or not row.value:
        return {}
    try:
        return json.loads(row.value)
    except Exception:
        return {}


def _save(db: Session, data: Dict[str, dict]) -> None:
    row = db.query(SystemSetting).filter(SystemSetting.key == KEY).first()
    payload = json.dumps(data, ensure_ascii=False)
    if row:
        row.value = payload
    else:
        db.add(SystemSetting(key=KEY, value=payload))
    db.commit()


def can_crawl_host(db: Session, url_or_host: str) -> bool:
    host = _host(url_or_host) if "://" in (url_or_host or "") else (url_or_host or "").lower()
    if not host:
        return True
    limit = _limit_for_host(host)
    data = _load(db)
    today = date.today().isoformat()
    rec = data.get(host) or {}
    if rec.get("day") != today:
        return True
    return int(rec.get("count") or 0) < limit


def mark_host_crawled(db: Session, url_or_host: str) -> None:
    host = _host(url_or_host) if "://" in (url_or_host or "") else (url_or_host or "").lower()
    if not host:
        return
    data = _load(db)
    today = date.today().isoformat()
    rec = data.get(host) or {}
    if rec.get("day") != today:
        rec = {"day": today, "count": 0}
    rec["count"] = int(rec.get("count") or 0) + 1
    rec["last"] = datetime.utcnow().isoformat()
    data[host] = rec
    _save(db, data)
    logger.debug(
        "host quota %s -> %s/%s",
        host,
        rec["count"],
        _limit_for_host(host),
    )
