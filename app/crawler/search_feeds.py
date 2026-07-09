"""全量关键词搜索采集：谷歌新闻 + 蒙古媒体站内搜索，并解析可打开原文链接。"""
from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any, Callable, List, Optional, Set
from urllib.parse import parse_qs, quote_plus, unquote, urljoin, urlparse

import feedparser
import httpx
from bs4 import BeautifulSoup
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


def _resolve_google_article_url(link: str, client: httpx.Client) -> str:
    """尽量把 Google News 跳转链解析为可打开的原文 URL（快速、失败则保留原链）。"""
    if not link:
        return link
    host = urlparse(link).netloc.lower()
    if "news.google.com" not in host:
        return link
    qs = parse_qs(urlparse(link).query)
    for key in ("url", "q"):
        if key in qs and qs[key]:
            cand = unquote(qs[key][0])
            if cand.startswith("http") and "news.google.com" not in cand:
                return cand
    # 不做二次 HTTP 解析（太慢）；保留 Google 链，前端仍可点开
    return link


class SearchFeedCollector:
    def __init__(self, db: Session, on_event: ProgressCallback = None):
        self.db = db
        self.on_event = on_event
        self.stats = {
            "feeds": 0,
            "items_new": 0,
            "items_updated": 0,
            "items_filtered": 0,
            "error_count": 0,
        }
        self._seen_urls: Set[str] = set()

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
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "mn,en;q=0.9,zh-CN;q=0.8",
        }
        feeds = SEARCH_FEEDS
        total = len(feeds)
        self._emit(
            "phase",
            status="running",
            phase="关键词全量搜索",
            message=f"启动全量毒品关键词搜索，共 {total} 路任务",
            total_sources=total,
            current_index=0,
        )

        with httpx.Client(
            headers=headers,
            timeout=httpx.Timeout(20.0, connect=8.0),
            follow_redirects=True,
            verify=False,
        ) as client:
            for idx, feed in enumerate(feeds, start=1):
                org = feed["org_name"]
                engine = feed.get("engine") or "google_news"
                self._emit(
                    "source_start",
                    current_index=idx,
                    total_sources=total,
                    current_org=org,
                    current_url=feed.get("search_url") or feed.get("query", ""),
                    phase="关键词全量搜索",
                    message=f"[{idx}/{total}] {org}",
                    items_new=self.stats["items_new"],
                    items_updated=self.stats["items_updated"],
                    items_filtered=self.stats["items_filtered"],
                    error_count=self.stats["error_count"],
                )
                try:
                    if engine == "site_search":
                        self._ingest_site_search(client, feed)
                    else:
                        url = _google_news_url(feed["query"], feed["hl"], feed["gl"], feed["ceid"])
                        self._ingest_google_feed(client, feed, url)
                    self.stats["feeds"] += 1
                    self.db.commit()
                except Exception as exc:  # noqa: BLE001
                    self.stats["error_count"] += 1
                    try:
                        self.db.rollback()
                    except Exception:
                        pass
                    logger.warning("搜索失败 %s: %s", org, exc)
                    self._emit("source_error", current_org=org, message=f"失败：{org} — {exc}")
                self._emit(
                    "source_done",
                    current_index=idx,
                    total_sources=total,
                    current_org=org,
                    message=f"完成：{org}｜累计新增 {self.stats['items_new']}",
                    items_new=self.stats["items_new"],
                    items_updated=self.stats["items_updated"],
                    items_filtered=self.stats["items_filtered"],
                    error_count=self.stats["error_count"],
                )

        self.db.commit()
        self._emit(
            "crawl_complete",
            phase="关键词搜索完成",
            message=f"关键词搜索完成：新增 {self.stats['items_new']}，过滤 {self.stats['items_filtered']}",
            items_new=self.stats["items_new"],
            items_updated=self.stats["items_updated"],
        )
        return self.stats

    def _ingest_google_feed(self, client: httpx.Client, feed: dict, url: str) -> None:
        resp = client.get(url)
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code}")
        parsed = feedparser.parse(resp.text)
        for entry in (parsed.entries or [])[:35]:
            title = normalize_text(getattr(entry, "title", "") or "")
            link = getattr(entry, "link", "") or ""
            raw_sum = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
            # 去掉 RSS HTML
            summary = normalize_text(BeautifulSoup(raw_sum, "lxml").get_text(" ", strip=True))
            if not title:
                continue
            real_url = _resolve_google_article_url(link, client)
            published = None
            if getattr(entry, "published_parsed", None):
                try:
                    published = datetime(*entry.published_parsed[:6])
                except Exception:
                    published = None
            self._save_item(
                feed=feed,
                title=title,
                summary=summary,
                url=real_url or link,
                published=published,
                require_mongolia=bool(feed.get("require_mongolia", True)),
                force_drug=False,
            )

    def _ingest_site_search(self, client: httpx.Client, feed: dict) -> None:
        search_url = feed.get("search_url")
        if not search_url:
            return
        resp = client.get(search_url)
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code}")
        soup = BeautifulSoup(resp.text, "lxml")
        for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
            tag.decompose()

        query = (feed.get("query") or "").lower()
        candidates = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            text = normalize_text(a.get_text(" ", strip=True))
            if not text or len(text) < 12:
                continue
            full = urljoin(search_url, href)
            host = urlparse(full).netloc.lower()
            if not any(x in host for x in ("gogo.mn", "montsame.mn", "ikon.mn", "news.mn")):
                continue
            path = urlparse(full).path.lower()
            if path in ("/", "") or "search" in path:
                continue
            if any(x in path for x in ("/login", "/tag", "/category", "/corner", "/topic", "/author", "/#")):
                continue
            # 只要文章型路径
            article_ok = any(
                x in path
                for x in ("/n/", "/r/", "/a/", "/news/", "/post/", "/article/", "/mn/", "/en/")
            )
            if not article_ok:
                continue
            # 标题必须涉毒，或明确包含本轮搜索词 —— 禁止把侧边栏热搜一并入库
            title_blob = text.lower()
            if not is_drug_related(text, loose=True) and query not in title_blob:
                continue
            candidates.append((text, full))

        seen = set()
        uniq = []
        for title, url in candidates:
            if url in seen:
                continue
            seen.add(url)
            uniq.append((title, url))

        for title, url in uniq[:30]:
            self._save_item(
                feed=feed,
                title=title,
                summary=f"{title}（关键词：{feed.get('query','')}）",
                url=url,
                published=None,
                require_mongolia=False,  # 蒙古媒体站，地域默认成立
                force_drug=False,  # 仍要过涉毒校验
            )

    def _save_item(
        self,
        feed: dict,
        title: str,
        summary: str,
        url: str,
        published: Optional[datetime],
        require_mongolia: bool,
        force_drug: bool = False,
    ) -> None:
        title = normalize_text(title)
        summary = normalize_text(summary)
        if not title:
            return
        body = f"{title}\n{summary}"
        body_l = body.lower()

        # —— 排除中国内蒙古等误伤 ——
        if "内蒙古" in body and "蒙古国" not in body:
            self.stats["items_filtered"] += 1
            return
        if re.search(r"\binner mongolia\b", body_l):
            self.stats["items_filtered"] += 1
            return

        mongolia_markers = [
            "mongolia", "mongolian", "улаанбаатар", "ulaanbaatar",
            "монгол улс", "монгол", "蒙古国", "乌兰巴托",
        ]
        has_mn = any(m in body_l for m in mongolia_markers) or ("蒙古国" in body)

        # 明显他国稿且无蒙古标记 → 丢弃
        foreign_hits = [
            "cyprus", "uzbekistan", "tajikistan", "vanuatu", "yunnan",
            "kazakhstan", "kyrgyz", "afghanistan only",
        ]
        if any(f in body_l for f in foreign_hits) and not has_mn:
            self.stats["items_filtered"] += 1
            return

        # require_mongolia：英/中谷歌源强制；蒙语谷歌源不强制标题含“蒙古”
        # （蒙文国内稿标题常不写国名）
        req_mn = feed.get("require_mongolia")
        if req_mn is None:
            req_mn = require_mongolia
        if req_mn and not has_mn:
            self.stats["items_filtered"] += 1
            return

        # 涉毒：标题/摘要必须命中词库（不允许仅因查询词放行）
        if not force_drug:
            if not is_drug_related(body, loose=True):
                self.stats["items_filtered"] += 1
                return
        elif not is_drug_related(body, loose=True) and not is_drug_related(feed.get("query", ""), loose=True):
            self.stats["items_filtered"] += 1
            return

        item_url = url or f"search://{feed['org_name']}/{content_hash(title, feed.get('query',''), summary)[:16]}"
        if item_url in self._seen_urls:
            return
        self._seen_urls.add(item_url)

        lang = detect_lang(title + summary) or ("mn" if feed.get("hl") == "mn" else "en")
        # 为提速：搜索阶段默认不翻译长文，只译标题
        title_zh = translate_to_zh(title, lang, settings.enable_translation)
        summary_zh = summary if lang == "zh" else (title_zh if not summary else summary)

        ch = content_hash(title, item_url, summary)
        existing = (
            self.db.query(IntelItem)
            .filter((IntelItem.url == item_url) | (IntelItem.content_hash == ch))
            .first()
        )
        blob = f"{body}\n{feed.get('query','')}"
        level = intel_level(blob)
        category = classify_category(blob)
        alert = is_critical(blob) or level == "紧急"

        if existing:
            if existing.content_hash != ch:
                existing.title = title
                existing.title_zh = title_zh
                existing.summary = summary
                existing.summary_zh = summary_zh
                existing.url = item_url
                existing.content_hash = ch
                existing.intel_level = level
                existing.category = category
                existing.is_alert = alert
                existing.status = "updated"
                existing.crawled_at = datetime.utcnow()
                self.stats["items_updated"] += 1
                self.db.flush()
                self._emit_item(existing, feed, "updated", alert, category, level, title_zh or title, item_url)
            return

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
            raw_meta='{"collector":"keyword_search"}',
        )
        self.db.add(row)
        self.db.flush()
        self.stats["items_new"] += 1
        self._emit_item(row, feed, "new", alert, category, level, title_zh or title, item_url)

    def _emit_item(self, row, feed, status, alert, category, level, title, url):
        self._emit(
            "item",
            item={
                "id": row.id,
                "title": title,
                "org": feed["org_name"],
                "system": feed["system_name"],
                "level": level,
                "category": category,
                "url": url,
                "status": status,
                "is_alert": alert,
            },
            items_new=self.stats["items_new"],
            items_updated=self.stats["items_updated"],
            message=f"{'新情报' if status=='new' else '更新'}：{title}",
        )
