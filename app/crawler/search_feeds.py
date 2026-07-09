"""谷歌新闻 RSS / 关键词搜索聚合采集 —— 保证海量涉毒资讯入库"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Callable, List, Optional
from urllib.parse import quote_plus, urlparse

import feedparser
import httpx
from sqlalchemy.orm import Session

from app.config import get_settings
from app.crawler.filters import (
    classify_category,
    content_hash,
    detect_lang,
    intel_level,
    is_allowed_url,
    is_critical,
    is_drug_related,
    normalize_text,
    translate_to_zh,
)
from app.db.models import IntelItem
from config.sources import SEARCH_FEEDS

logger = logging.getLogger(__name__)
settings = get_settings()

ProgressCallback = Optional[Callable[..., None]]


def _google_news_url(query: str, hl: str, gl: str, ceid: str) -> str:
    return (
        "https://news.google.com/rss/search?"
        f"q={quote_plus(query)}&hl={hl}&gl={gl}&ceid={quote_plus(ceid)}"
    )


class SearchFeedCollector:
    """从 Google News RSS 等搜索源批量拉取涉毒资讯。"""

    def __init__(self, db: Session, on_event: ProgressCallback = None):
        self.db = db
        self.on_event = on_event
        self.stats = {"feeds": 0, "items_new": 0, "items_updated": 0, "items_filtered": 0, "error_count": 0}

    def _emit(self, event_type: str, **payload: Any) -> None:
        if not self.on_event:
            return
        try:
            self.on_event(event_type, **payload)
        except Exception:  # noqa: BLE001
            logger.debug("search progress callback failed", exc_info=True)

    def run(self) -> dict:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "application/rss+xml, application/xml, text/xml, */*",
        }
        total = len(SEARCH_FEEDS)
        self._emit(
            "phase",
            status="running",
            phase="媒体搜索聚合",
            message=f"开始搜索聚合采集，共 {total} 路关键词源",
            total_sources=total,
            current_index=0,
        )

        with httpx.Client(headers=headers, timeout=30, follow_redirects=True, verify=False) as client:
            for idx, feed in enumerate(SEARCH_FEEDS, start=1):
                org = feed["org_name"]
                url = _google_news_url(feed["query"], feed["hl"], feed["gl"], feed["ceid"])
                self._emit(
                    "source_start",
                    current_index=idx,
                    total_sources=total,
                    current_org=org,
                    current_url=url,
                    phase="媒体搜索聚合",
                    message=f"[{idx}/{total}] 搜索：{org}（{feed['query']}）",
                )
                try:
                    self._ingest_feed(client, feed, url)
                    self.stats["feeds"] += 1
                except Exception as exc:  # noqa: BLE001
                    self.stats["error_count"] += 1
                    logger.warning("搜索源失败 %s: %s", org, exc)
                    self._emit("source_error", current_org=org, message=f"搜索失败：{org} — {exc}")
                self._emit(
                    "source_done",
                    current_index=idx,
                    total_sources=total,
                    current_org=org,
                    message=f"完成搜索：{org}｜新增 {self.stats['items_new']}",
                    items_new=self.stats["items_new"],
                    items_updated=self.stats["items_updated"],
                    items_filtered=self.stats["items_filtered"],
                    error_count=self.stats["error_count"],
                )

        self.db.commit()
        self._emit(
            "crawl_complete",
            phase="搜索聚合完成",
            message=f"搜索聚合完成：新增 {self.stats['items_new']}，更新 {self.stats['items_updated']}",
            items_new=self.stats["items_new"],
            items_updated=self.stats["items_updated"],
        )
        return self.stats

    def _ingest_feed(self, client: httpx.Client, feed: dict, url: str) -> None:
        resp = client.get(url)
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code}")
        parsed = feedparser.parse(resp.text)
        entries = parsed.entries or []
        for entry in entries[:40]:
            title = normalize_text(getattr(entry, "title", "") or "")
            link = getattr(entry, "link", "") or ""
            summary = normalize_text(
                getattr(entry, "summary", "")
                or getattr(entry, "description", "")
                or ""
            )
            if not title:
                continue

            body = f"{title}\n{summary}"
            body_l = body.lower()
            query_l = (feed.get("query") or "").lower()

            # 地域：仅看标题/摘要，不把查询词本身算进去
            mongolia_markers = [
                "mongolia", "mongolian", "улаанбаатар", "ulaanbaatar",
                "монгол", "蒙古", "乌兰巴托",
            ]
            has_mn = any(m in body_l for m in mongolia_markers)
            if feed.get("hl") == "mn":
                # 蒙语检索结果默认视为蒙古语境
                has_mn = True
            if feed.get("hl") in ("en", "zh-CN") and not has_mn:
                self.stats["items_filtered"] += 1
                continue

            # 排除中国内蒙古误匹配（除非同时出现蒙古国）
            if "内蒙古" in body and "蒙古国" not in body and "mongolia" not in body_l:
                self.stats["items_filtered"] += 1
                continue
            if "inner mongolia" in body_l and "mongolia" in body_l:
                # "Inner Mongolia" 单独出现时排除
                if "ulaanbaatar" not in body_l and "mongolian" not in body_l and "蒙古国" not in body:
                    # 若仅 Inner Mongolia，过滤
                    if re.search(r"\binner mongolia\b", body_l) and not re.search(
                        r"\bmongolia\b(?!\s*autonomous)", body_l.replace("inner mongolia", " ")
                    ):
                        self.stats["items_filtered"] += 1
                        continue

            lang = detect_lang(title + summary) or ("mn" if feed.get("hl") == "mn" else "en")
            # 翻译可关闭以加速；默认开
            title_zh = translate_to_zh(title, lang, settings.enable_translation)
            summary_zh = translate_to_zh(summary[:500], lang, settings.enable_translation)

            published = None
            if getattr(entry, "published_parsed", None):
                try:
                    published = datetime(*entry.published_parsed[:6])
                except Exception:
                    published = None

            item_url = link or f"search://{feed['org_name']}/{content_hash(title, feed['query'], summary)[:16]}"
            ch = content_hash(title, item_url, summary)
            existing = (
                self.db.query(IntelItem)
                .filter((IntelItem.url == item_url) | (IntelItem.content_hash == ch))
                .first()
            )
            level = intel_level(blob)
            category = classify_category(blob) if is_drug_related(blob, loose=True) else "媒体报道"
            alert = is_critical(blob) or level == "紧急"

            if existing:
                if existing.content_hash != ch:
                    existing.title = title
                    existing.title_zh = title_zh
                    existing.summary = summary
                    existing.summary_zh = summary_zh
                    existing.content_hash = ch
                    existing.intel_level = level
                    existing.category = category
                    existing.is_alert = alert
                    existing.status = "updated"
                    existing.crawled_at = datetime.utcnow()
                    self.stats["items_updated"] += 1
                    self.db.flush()
                    self._emit(
                        "item",
                        item={
                            "id": existing.id,
                            "title": title_zh or title,
                            "org": feed["org_name"],
                            "system": feed["system_name"],
                            "level": level,
                            "category": category,
                            "url": item_url,
                            "status": "updated",
                            "is_alert": alert,
                        },
                        items_updated=self.stats["items_updated"],
                        items_new=self.stats["items_new"],
                        message=f"更新：{title_zh or title}",
                    )
                continue

            row = IntelItem(
                source_id=None,
                system_id=feed["system_id"],
                system_name=feed["system_name"],
                org_name=feed["org_name"],
                url=item_url,
                title=title,
                title_zh=title_zh,
                summary=summary,
                summary_zh=summary_zh,
                content=summary,
                content_zh=summary_zh,
                lang=lang,
                published_at=published,
                crawled_at=datetime.utcnow(),
                content_hash=ch,
                intel_level=level,
                category=category,
                is_alert=alert,
                status="new",
                raw_meta='{"collector":"google_news_rss"}',
            )
            self.db.add(row)
            self.db.flush()
            self.stats["items_new"] += 1
            self._emit(
                "item",
                item={
                    "id": row.id,
                    "title": title_zh or title,
                    "org": feed["org_name"],
                    "system": feed["system_name"],
                    "level": level,
                    "category": category,
                    "url": item_url,
                    "status": "new",
                    "is_alert": alert,
                },
                items_new=self.stats["items_new"],
                items_updated=self.stats["items_updated"],
                message=f"新情报：{title_zh or title}",
            )
        self.db.commit()
