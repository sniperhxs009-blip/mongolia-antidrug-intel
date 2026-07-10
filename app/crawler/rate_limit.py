"""单站日抓取频次限制（默认每日 ≤3 次）。"""
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


def _host(url: str) -> str:
    try:
        return urlparse(url).netloc.lower().split(":")[0]
    except Exception:
        return ""


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
    limit = int(getattr(settings, "crawl_max_per_host_per_day", 3) or 3)
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
    logger.debug("host quota %s -> %s/%s", host, rec["count"], getattr(settings, "crawl_max_per_host_per_day", 3))
