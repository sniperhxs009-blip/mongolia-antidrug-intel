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
    credibility_label,
    detect_lang,
    intel_level,
    is_allowed_url,
    is_critical,
    is_drug_related,
    is_mongolia_country_related,
    is_unodc_mongolia_signal,
    normalize_text,
    title_has_strong_drug,
    translate_to_zh,
)
from app.crawler.http_client import build_httpx_client, pick_user_agent
from app.db.models import IntelItem
from config.drug_lexicon import build_search_queries
from config.core_official import is_forbidden_url, sanitize_store_url

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
                # 修改原因：解析出原生 gov.mn 时改写为快照链，禁止后续直连
                return sanitize_store_url(cand)
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

    def run(self, mode: str = "full") -> dict:
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/json,*/*;q=0.8",
            "Accept-Language": "mn,en;q=0.9,zh-CN;q=0.8",
        }
        when = (
            (getattr(settings, "news_when", "1y") if mode == "news" else getattr(settings, "full_when", "1y"))
            or "1y"
        )
        # 【增产修复】原缺陷：news 只取极少补盲、剔除 site:gov.mn、论坛几乎不跑
        from config.core_official import build_core_site_search_queries

        core_feeds = build_core_site_search_queries(when=when)
        lex_mode = "full" if mode == "full" else "news"
        lexicon_feeds = build_search_queries(mode=lex_mode, when=when)
        feeds = list(core_feeds) + list(lexicon_feeds)
        forum_when = getattr(settings, "forum_when", None) or "30d"
        # 修改原因：论坛默认关闭，仅手动开启
        if getattr(settings, "enable_forum_search", False):
            from config.forum_search import build_forum_search_queries

            feeds.extend(build_forum_search_queries(mode=lex_mode, when=forum_when))
        # 去重
        seen_keys: Set[str] = set()
        uniq_feeds = []
        for f in feeds:
            key = f"{f.get('engine')}|{f.get('query')}|{f.get('search_url')}"
            if key in seen_keys:
                continue
            seen_keys.add(key)
            uniq_feeds.append(f)
        feeds = uniq_feeds
        phase = "关键词全渠道检索"
        msg = f"检索任务 {len(feeds)} 路（when:{when}，含快照/论坛/媒体）"
        # 仅剔除 search_url 直连 gov.mn；保留 query 内 site:*.gov.mn 快照检索
        try:
            def _feed_ok(f: dict) -> bool:
                # 修改原因：仅拦 search_url 直连 gov.mn；放行 query 内 site:*.gov.mn 快照
                if "shturl" in " ".join(str(f.get(k) or "") for k in ("search_url", "org_name")).lower():
                    return False
                su = f.get("search_url") or ""
                if su and is_forbidden_url(su):
                    return False
                return True

            feeds = [f for f in feeds if _feed_ok(f)]
            # 修改原因：任务权重 本土站内 > UNODC > 外媒 > 论坛
            def _prio(f: dict) -> int:
                if f.get("priority") is not None:
                    return int(f["priority"])
                eng = f.get("engine") or ""
                kind = f.get("source_kind") or ""
                org = (f.get("org_name") or "").lower()
                if eng == "site_search" or kind == "site_search":
                    return 5
                if "unodc" in org or "unodc" in (f.get("query") or "").lower():
                    return 20
                if kind == "forum" or "论坛" in org or "reddit" in org:
                    return 90
                if kind == "gov_snapshot" or f.get("snapshot_only"):
                    return 15
                return 40

            feeds.sort(key=_prio)
        except Exception:
            pass

        total = len(feeds)
        self._emit(
            "phase",
            status="running",
            phase=phase,
            message=msg,
            total_sources=total,
            current_index=0,
        )

        with build_httpx_client(
            headers=headers,
            timeout=httpx.Timeout(20.0, connect=8.0),
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
                    phase=phase,
                    message=f"[{idx}/{total}] {org}",
                    items_new=self.stats["items_new"],
                    items_updated=self.stats["items_updated"],
                    items_filtered=self.stats["items_filtered"],
                    error_count=self.stats["error_count"],
                )
                try:
                    if engine == "site_search":
                        self._ingest_site_search(client, feed)
                    elif engine == "reddit_search":
                        self._ingest_reddit(client, feed)
                    elif engine == "bing_news":
                        self._ingest_rss_url(client, feed, feed.get("search_url") or "")
                    elif engine == "ddg_news":
                        self._ingest_ddg_news(client, feed)
                    elif engine == "web_search":
                        self._ingest_web_search(client, feed)
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

    def _too_old(self, published: Optional[datetime]) -> bool:
        """严格近期：有发布时间且超过 crawl_max_age_days 则丢弃。"""
        if not published:
            return False  # 无日期时靠 when: 查询约束；不因缺日期全丢
        max_days = int(getattr(settings, "crawl_max_age_days", 30) or 30)
        from datetime import timedelta

        return published < datetime.utcnow() - timedelta(days=max_days)

    def _ingest_google_feed(self, client: httpx.Client, feed: dict, url: str) -> None:
        # 取消 18/30 硬截断；尝试最多 8 轮（RSS 主结果 + start 偏移）
        import random
        import time

        seen_links: Set[str] = set()
        for page in range(8):
            page_url = url
            if page > 0:
                page_url = (
                    "https://news.google.com/rss/search?"
                    f"q={quote_plus(feed['query'])}&hl={feed['hl']}&gl={feed['gl']}"
                    f"&ceid={quote_plus(feed['ceid'])}&start={page * 10}"
                )
            client.headers["User-Agent"] = pick_user_agent()
            try:
                resp = client.get(page_url)
            except Exception:
                break
            if resp.status_code >= 400:
                break
            parsed = feedparser.parse(resp.text)
            entries = list(parsed.entries or [])
            if not entries:
                break
            new_on_page = 0
            for entry in entries:
                title = normalize_text(getattr(entry, "title", "") or "")
                link = getattr(entry, "link", "") or ""
                raw_sum = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
                summary = normalize_text(BeautifulSoup(raw_sum, "lxml").get_text(" ", strip=True))
                if not title:
                    continue
                # 修改原因：标题无强毒品词则跳过页面解析/下载，降噪减请求
                if not title_has_strong_drug(title) and not title_has_strong_drug(summary):
                    self.stats["items_filtered"] += 1
                    continue
                real_url = _resolve_google_article_url(link, client)
                store_url = sanitize_store_url(real_url or link, title=title)
                # 修改原因：原生 gov.mn 直链改写为快照链后入库；禁止丢弃官方快照情报
                if is_forbidden_url(store_url):
                    self.stats["items_filtered"] += 1
                    continue
                if store_url in seen_links:
                    continue
                seen_links.add(store_url)
                new_on_page += 1
                published = None
                if getattr(entry, "published_parsed", None):
                    try:
                        published = datetime(*entry.published_parsed[:6])
                    except Exception:
                        published = None
                # 无日期不丢弃
                if published is not None and self._too_old(published):
                    self.stats["items_filtered"] += 1
                    continue
                self._save_item(
                    feed=feed,
                    title=title,
                    summary=summary or title,
                    url=store_url,
                    published=published,
                    require_mongolia=bool(feed.get("require_mongolia", True)),
                    force_drug=False,
                )
            if page > 0 and new_on_page == 0:
                break
            time.sleep(random.uniform(0.08, 0.35))

    def _ingest_rss_url(self, client: httpx.Client, feed: dict, url: str) -> None:
        if not url:
            return
        client.headers["User-Agent"] = pick_user_agent()
        resp = client.get(url)
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code}")
        parsed = feedparser.parse(resp.text)
        for entry in (parsed.entries or []):
            title = normalize_text(getattr(entry, "title", "") or "")
            link = getattr(entry, "link", "") or ""
            raw_sum = getattr(entry, "summary", "") or getattr(entry, "description", "") or ""
            summary = normalize_text(BeautifulSoup(raw_sum, "lxml").get_text(" ", strip=True))
            if not title:
                continue
            published = None
            if getattr(entry, "published_parsed", None):
                try:
                    published = datetime(*entry.published_parsed[:6])
                except Exception:
                    published = None
            if published is not None and self._too_old(published):
                self.stats["items_filtered"] += 1
                continue
            self._save_item(
                feed=feed,
                title=title,
                summary=summary or title,
                url=link,
                published=published,
                require_mongolia=bool(feed.get("require_mongolia", True)),
            )

    def _ingest_reddit(self, client: httpx.Client, feed: dict) -> None:
        url = feed.get("search_url")
        if not url:
            from urllib.parse import quote

            # 与 NEWS_WHEN/FULL_WHEN 对齐：默认近一年
            t = "year"
            w = (getattr(settings, "forum_when", None) or getattr(settings, "full_when", "1y") or "1y").lower()
            if w in ("1d", "d"):
                t = "day"
            elif w in ("7d", "w", "week"):
                t = "week"
            elif w in ("30d", "m", "month"):
                t = "month"
            url = (
                "https://www.reddit.com/search.json?"
                f"q={quote(feed.get('query') or '')}&sort=new&t={t}&limit=25"
            )
        headers = {"User-Agent": pick_user_agent()}
        last_err = None
        resp = None
        for attempt in range(3):
            try:
                headers = {"User-Agent": pick_user_agent()}
                resp = client.get(url, headers=headers)
                if resp.status_code < 500:
                    break
                last_err = RuntimeError(f"HTTP {resp.status_code}")
            except Exception as exc:  # noqa: BLE001
                last_err = exc
            import time
            time.sleep(0.5 * (2 ** attempt))
        if resp is None or resp.status_code >= 400:
            raise last_err or RuntimeError("reddit failed")
        data = resp.json()
        children = ((data.get("data") or {}).get("children")) or []
        for child in children[:40]:
            d = child.get("data") or {}
            title = normalize_text(d.get("title") or "")
            permalink = d.get("permalink") or ""
            link = ("https://www.reddit.com" + permalink) if permalink.startswith("/") else (d.get("url") or "")
            summary = normalize_text((d.get("selftext") or "")[:500])
            if not title:
                continue
            # 短快讯：≥100 字符或标题涉毒即保留（取消过严长度限制）
            if len(title) + len(summary) < 20:
                continue
            published = None
            created = d.get("created_utc")
            if created:
                try:
                    published = datetime.utcfromtimestamp(float(created))
                except Exception:
                    published = None
            if published is not None and self._too_old(published):
                self.stats["items_filtered"] += 1
                continue
            self._save_item(
                feed=feed,
                title=title,
                summary=summary or title,
                url=link,
                published=published,
                require_mongolia=True,
            )

    def _ingest_ddg_news(self, client: httpx.Client, feed: dict) -> None:
        # DuckDuckGo news JSON 常不稳定，失败则走 HTML 搜索
        url = feed.get("search_url") or ""
        try:
            if url:
                resp = client.get(url)
                if resp.status_code < 400:
                    data = resp.json()
                    results = data if isinstance(data, list) else (data.get("results") or data.get("items") or [])
                    for it in results[:20]:
                        title = normalize_text(it.get("title") or it.get("heading") or "")
                        link = it.get("url") or it.get("link") or ""
                        summary = normalize_text(it.get("excerpt") or it.get("body") or "")
                        if title and link:
                            self._save_item(
                                feed=feed,
                                title=title,
                                summary=summary,
                                url=link,
                                published=None,
                                require_mongolia=True,
                            )
                    return
        except Exception as exc:  # noqa: BLE001
            logger.debug("ddg json failed: %s", exc)
        # 兜底 HTML
        q = feed.get("query") or ""
        self._ingest_web_search(
            client,
            {**feed, "search_url": f"https://html.duckduckgo.com/html/?q={quote_plus(q)}"},
        )

    def _ingest_web_search(self, client: httpx.Client, feed: dict) -> None:
        """解析 Google/DuckDuckGo HTML 搜索结果中的链接（偏 Reddit/论坛）。"""
        url = feed.get("search_url")
        if not url:
            q = feed.get("query") or ""
            w = (getattr(settings, "forum_when", None) or getattr(settings, "full_when", "1y") or "1y").lower()
            qdr = "y"
            if w in ("1d", "d"):
                qdr = "d"
            elif w in ("7d", "w", "week"):
                qdr = "w"
            elif w in ("30d", "m", "month", "90d"):
                qdr = "m"
            url = f"https://www.google.com/search?q={quote_plus(q)}&num=20&hl=en&tbs=qdr:{qdr}"
        resp = client.get(url)
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code}")
        soup = BeautifulSoup(resp.text, "lxml")
        seen = set()
        count = 0
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            text = normalize_text(a.get_text(" ", strip=True))
            cand = href
            if href.startswith("/url?"):
                qs = parse_qs(urlparse(href).query)
                cand = unquote((qs.get("q") or qs.get("url") or [""])[0])
            if "uddg=" in href:
                qs = parse_qs(urlparse("http://x/?" + href.split("?", 1)[-1]).query)
                cand = unquote((qs.get("uddg") or [""])[0])
            if not cand.startswith("http"):
                continue
            host = urlparse(cand).netloc.lower()
            # 优先论坛/社区；也允许新闻域
            forum_ok = any(
                x in host
                for x in (
                    "reddit.com", "quora.com", "zhihu.com", "tieba.baidu.com",
                    "bluelight.org", "drugs-forum.com", "medium.com", "substack.com",
                    "news.ycombinator.com",
                )
            )
            news_ok = any(
                x in host
                for x in (
                    "reuters.com", "bbc.", "theguardian.", "apnews.", "vice.com",
                    "thediplomat.com", "news.mn", "gogo.mn", "montsame.mn",
                )
            )
            if not (forum_ok or news_ok):
                continue
            if cand in seen or len(text) < 8:
                continue
            seen.add(cand)
            self._save_item(
                feed=feed,
                title=text[:300],
                summary=f"{text}（来源：{host}）",
                url=cand,
                published=None,
                require_mongolia=True,
            )
            count += 1
            if count >= 15:
                break

    def _site_search_next_urls(self, soup: BeautifulSoup, current_url: str) -> list:
        """解析站内搜索分页链接（page=/p=/offset= 等）。"""
        nexts = []
        for a in soup.find_all("a", href=True):
            href = (a.get("href") or "").strip()
            label = normalize_text(a.get_text(" ", strip=True)).lower()
            full = urljoin(current_url, href)
            if full == current_url:
                continue
            q = (urlparse(full).query or "").lower()
            path = (urlparse(full).path or "").lower()
            if any(x in q for x in ("page=", "p=", "offset=", "start=", "paged=")):
                nexts.append(full)
            elif re.search(r"/page/\d+", path) or label in (
                "next", "›", "»", "дараах", "下一页", "дараагийн", "хуудас",
                "мэдээ", "older", "more",
            ):
                nexts.append(full)
            # 蒙语分页常见：?page= / хуудас=
            if "хуудас" in q or "хуудас" in path or "мэдээ" in label and any(c.isdigit() for c in label):
                nexts.append(full)
        # 去重保序
        seen = set()
        out = []
        for u in nexts:
            if u in seen:
                continue
            seen.add(u)
            out.append(u)
        return out[:8]

    def _collect_site_search_candidates(self, soup: BeautifulSoup, search_url: str, query: str) -> list:
        candidates = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            text = normalize_text(a.get_text(" ", strip=True))
            if not text or len(text) < 12:
                continue
            full = urljoin(search_url, href)
            host = urlparse(full).netloc.lower()
            if not any(x in host for x in (
                "montsame.mn", "gogo.mn", "ikon.mn", "news.mn",
                "nncc626.com", "chinanews.com", "unodc.org",
                "mongolia.un.org", "nmg.110.gov.cn", "odkb-csto.org",
                "scoec.gov.cn", "mongolnews.mn", "ubpost",
            )):
                continue
            if is_forbidden_url(full):
                continue
            path = urlparse(full).path.lower()
            if path in ("/", "") or "search" in path:
                continue
            if any(x in path for x in ("/login", "/tag", "/category", "/corner", "/topic", "/author", "/#")):
                continue
            article_ok = any(
                x in path
                for x in ("/n/", "/r/", "/a/", "/news/", "/post/", "/article/", "/mn/", "/en/", "/cn/")
            )
            if not article_ok:
                continue
            # 修改原因：站内候选必须标题含强毒品词，弱词/检索词 alone 不触发下载
            if not title_has_strong_drug(text):
                continue
            candidates.append((text, full))
        return candidates

    def _ingest_site_search(self, client: httpx.Client, feed: dict) -> None:
        """站内搜索：自动翻页最多 10 页，每页候选汇总后取 30×页 上限。"""
        search_url = feed.get("search_url")
        if not search_url:
            return
        query = (feed.get("query") or "").lower()
        pages_to_visit = [search_url]
        visited = set()
        all_candidates = []
        max_pages = 10  # 原 5 → 10

        while pages_to_visit and len(visited) < max_pages:
            page_url = pages_to_visit.pop(0)
            if page_url in visited:
                continue
            visited.add(page_url)
            client.headers["User-Agent"] = pick_user_agent()
            try:
                resp = client.get(page_url)
            except Exception:
                continue
            if resp.status_code >= 400:
                if page_url == search_url:
                    raise RuntimeError(f"HTTP {resp.status_code}")
                continue
            soup = BeautifulSoup(resp.text, "lxml")
            for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
                tag.decompose()
            page_cands = self._collect_site_search_candidates(soup, page_url, query)
            all_candidates.extend(page_cands[:30])  # 每页最多 30 条
            for nxt in self._site_search_next_urls(soup, page_url):
                if nxt not in visited and nxt not in pages_to_visit:
                    pages_to_visit.append(nxt)

        seen = set()
        uniq = []
        for title, url in all_candidates:
            # 仅完全相同 URL 去重；同案不同链接保留
            if url in seen:
                continue
            seen.add(url)
            uniq.append((title, url))

        for title, url in uniq[:300]:
            self._save_item(
                feed=feed,
                title=title,
                summary=title,
                url=url,
                published=None,
                require_mongolia=False,
                force_drug=False,
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
        # 短快讯：标题+摘要 ≥100 或标题本身涉毒即可（取消 250 字符门槛）
        if len(title) + len(summary) < 100 and not is_drug_related(title, loose=False):
            if len(title) < 12:
                self.stats["items_filtered"] += 1
                return
        if is_forbidden_url(url or ""):
            # 修改原因：仅拦原生直链；快照包装链可入库
            self.stats["items_filtered"] += 1
            return
        url = sanitize_store_url(url or "", title=title)
        if is_forbidden_url(url):
            self.stats["items_filtered"] += 1
            return
        if not is_allowed_url(url) and not (url or "").startswith("search://"):
            self.stats["items_filtered"] += 1
            return
        body = f"{title}\n{summary}"
        body_l = body.lower()

        # 修改原因：内蒙古/俄边境无蒙古国正锚点一律丢弃，禁止毒品词兜底
        if "内蒙古" in body or re.search(r"\binner mongolia\b", body_l):
            if not is_mongolia_country_related(body):
                self.stats["items_filtered"] += 1
                return
        if re.search(
            r"улан[- ]?удэ|ulan[- ]?ude|buryat|бурят|乌兰乌德|布里亚特|"
            r"chita|чита|kyakhta|кяхта|забайкал|zabaikal|后贝加尔|恰克图|赤塔",
            body_l,
            flags=re.I,
        ):
            if not is_mongolia_country_related(body):
                self.stats["items_filtered"] += 1
                return

        has_mn = is_mongolia_country_related(body)

        foreign_hits = [
            "cyprus", "uzbekistan", "tajikistan", "vanuatu", "yunnan",
            "kazakhstan", "kyrgyz", "afghanistan", "china/afghanistan",
            "афганистан",
        ]
        if any(f in body_l for f in foreign_hits) and not has_mn:
            self.stats["items_filtered"] += 1
            return

        req_mn = feed.get("require_mongolia")
        if req_mn is None:
            req_mn = require_mongolia
        # UNODC / 快照任务：放宽蒙古信号
        if req_mn and not is_mongolia_country_related(body):
            if feed.get("snapshot_only") or "unodc" in body_l:
                if not is_unodc_mongolia_signal(body):
                    self.stats["items_filtered"] += 1
                    return
            else:
                self.stats["items_filtered"] += 1
                return

        gate = body
        if not force_drug and not is_drug_related(gate, loose=False):
            self.stats["items_filtered"] += 1
            return

        if published is not None and self._too_old(published):
            self.stats["items_filtered"] += 1
            return

        item_url = url or f"search://{feed['org_name']}/{content_hash(title, feed.get('query',''), summary, org_name=feed.get('org_name',''))[:16]}"
        if item_url in self._seen_urls:
            return
        self._seen_urls.add(item_url)

        lang = detect_lang(title + summary) or ("mn" if feed.get("hl") == "mn" else "en")
        title_zh = translate_to_zh(title, lang, settings.enable_translation)
        summary_zh = summary if lang == "zh" else (title_zh if not summary else summary)

        # 去重：hash 含机构+日期，不同媒体同案分别入库；仅同 URL 或同 hash 合并
        ch = content_hash(
            title, item_url, summary,
            org_name=feed.get("org_name") or "",
            published=published,
        )
        existing = (
            self.db.query(IntelItem)
            .filter((IntelItem.url == item_url) | (IntelItem.content_hash == ch))
            .first()
        )
        blob = f"{body}\n{feed.get('query','')}"
        level = intel_level(blob)
        if published is None:
            # 无发布时间：降低展示优先级（一般），仍入库
            level = level if level == "重要" else "一般"
        category = classify_category(blob)
        alert = is_critical(blob) or level == "紧急"
        # 修改原因：入库即标注可信度/告警类别/口岸/毒品类型
        from app.crawler.filters import alert_category, credibility_label, drug_type_from_text, port_tag_from_text

        cred = credibility_label(feed.get("org_name") or "", int(feed.get("system_id") or 0), item_url)
        akind = alert_category(blob) if alert else ""
        ptag = port_tag_from_text(blob)
        dtype = drug_type_from_text(blob)

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
                existing.credibility = cred
                existing.alert_kind = akind
                existing.port_tag = ptag
                existing.drug_type = dtype
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
            credibility=cred,
            alert_kind=akind,
            port_tag=ptag,
            drug_type=dtype,
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
