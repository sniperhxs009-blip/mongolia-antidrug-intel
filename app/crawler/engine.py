"""全网增量爬虫引擎：仅蒙古国官方禁毒体系，低频率、断点续爬、自动发现下级栏目。"""
from __future__ import annotations

import json
import logging
import time
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional, Set, Tuple
from urllib.parse import urljoin, urldefrag, urlparse

import httpx
from bs4 import BeautifulSoup
from sqlalchemy.orm import Session
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.crawler.filters import (
    classify_category,
    content_hash,
    detect_lang,
    intel_level,
    is_allowed_url,
    is_critical,
    is_drug_related,
    is_stale,
    normalize_text,
    parse_date_guess,
    same_host_or_sub,
    translate_to_zh,
)
from app.db.models import CrawlJob, IntelItem, Source
from config.sources import SOURCES

logger = logging.getLogger(__name__)
settings = get_settings()

ProgressCallback = Optional[Callable[..., None]]


class CrawlEngine:
    def __init__(self, db: Session, on_event: ProgressCallback = None):
        self.db = db
        self.on_event = on_event
        self.headers = {
            "User-Agent": settings.crawl_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "mn,en;q=0.8,ru;q=0.6,zh;q=0.4",
        }
        self.stats = {
            "pages_fetched": 0,
            "items_new": 0,
            "items_updated": 0,
            "items_filtered": 0,
            "error_count": 0,
        }

    def _emit(self, event_type: str, **payload: Any) -> None:
        if not self.on_event:
            return
        try:
            self.on_event(event_type, **payload)
        except Exception:  # noqa: BLE001
            logger.debug("progress callback failed", exc_info=True)

    def seed_sources(self) -> int:
        """将七大体系种子写入数据库，并保留已发现下级页面。

        同一官网可归属多个机构（如警察总局门户同时服务统筹与缉毒体系），
        因此唯一键为 (org_name, page_url)。
        """
        created = 0
        seen: Set[Tuple[str, str]] = set()
        for s in SOURCES:
            for path in s.get("seed_paths") or ["/"]:
                page_url = urljoin(s["base_url"].rstrip("/") + "/", path.lstrip("/"))
                page_url = self._clean_url(page_url)
                key = (s["org_name"], page_url)
                if key in seen:
                    continue
                seen.add(key)
                exists = (
                    self.db.query(Source)
                    .filter(Source.org_name == s["org_name"], Source.page_url == page_url)
                    .first()
                )
                if exists:
                    continue
                row = Source(
                    system_id=s["system_id"],
                    system_name=s["system_name"],
                    org_name=s["org_name"],
                    org_name_mn=s.get("org_name_mn", ""),
                    base_url=s["base_url"],
                    page_url=page_url,
                    is_seed=True,
                    is_active=True,
                    lang=s.get("lang", "mn"),
                    discover_depth=0,
                    last_status="seeded",
                )
                self.db.add(row)
                created += 1
        self.db.commit()
        logger.info("种子数据源写入完成: +%s", created)
        return created

    def run_full_crawl(self, resume: bool = True) -> CrawlJob:
        job = CrawlJob(status="running", started_at=datetime.utcnow(), checkpoint="{}")
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)

        try:
            self._emit(
                "phase",
                status="running",
                phase="种子同步",
                message="正在同步七大体系官方数据源种子…",
            )
            seeded = self.seed_sources()
            self._emit("seeded", message=f"种子同步完成，新增 {seeded} 条", items_new=self.stats["items_new"])

            sources = (
                self.db.query(Source)
                .filter(Source.is_active.is_(True))
                .order_by(Source.system_id, Source.id)
                .all()
            )
            total = len(sources)
            self._emit(
                "phase",
                status="running",
                phase="全网巡检",
                message=f"开始巡检 {total} 个官方数据源",
                total_sources=total,
                current_index=0,
            )

            done_urls: Set[str] = set()
            if resume and job.checkpoint:
                try:
                    done_urls = set(json.loads(job.checkpoint or "{}").get("done", []))
                except Exception:
                    done_urls = set()

            fetched_pages: Set[str] = set()
            with httpx.Client(
                headers=self.headers,
                timeout=settings.crawl_timeout_sec,
                follow_redirects=True,
            ) as client:
                for idx, src in enumerate(sources, start=1):
                    checkpoint_key = f"{src.org_name}|{src.page_url}"
                    if checkpoint_key in done_urls:
                        self._emit(
                            "source_skip",
                            current_index=idx,
                            total_sources=total,
                            current_org=src.org_name,
                            current_url=src.page_url,
                            message=f"断点跳过：{src.org_name}",
                            pages_fetched=self.stats["pages_fetched"],
                            items_new=self.stats["items_new"],
                            items_updated=self.stats["items_updated"],
                            items_filtered=self.stats["items_filtered"],
                            error_count=self.stats["error_count"],
                        )
                        continue

                    self._emit(
                        "source_start",
                        current_index=idx,
                        total_sources=total,
                        current_org=src.org_name,
                        current_url=src.page_url,
                        phase="全网巡检",
                        message=f"[{idx}/{total}] 正在扫描：{src.org_name}",
                        system_name=src.system_name,
                        pages_fetched=self.stats["pages_fetched"],
                        items_new=self.stats["items_new"],
                        items_updated=self.stats["items_updated"],
                        items_filtered=self.stats["items_filtered"],
                        error_count=self.stats["error_count"],
                    )
                    try:
                        self._crawl_source(client, src, fetched_pages=fetched_pages)
                    except Exception as exc:  # noqa: BLE001
                        self.stats["error_count"] += 1
                        src.last_status = f"error:{exc}"[:60]
                        logger.exception("爬取失败 %s: %s", src.page_url, exc)
                        self._emit(
                            "source_error",
                            current_org=src.org_name,
                            current_url=src.page_url,
                            message=f"扫描失败：{src.org_name} — {exc}",
                            error_count=self.stats["error_count"],
                        )

                    done_urls.add(checkpoint_key)
                    job.checkpoint = json.dumps({"done": list(done_urls)[-500:]}, ensure_ascii=False)
                    job.pages_fetched = self.stats["pages_fetched"]
                    job.items_new = self.stats["items_new"]
                    job.items_updated = self.stats["items_updated"]
                    job.items_filtered = self.stats["items_filtered"]
                    job.error_count = self.stats["error_count"]
                    self.db.commit()

                    self._emit(
                        "source_done",
                        current_index=idx,
                        total_sources=total,
                        current_org=src.org_name,
                        current_url=src.page_url,
                        message=f"完成：{src.org_name}｜状态 {src.last_status}",
                        pages_fetched=self.stats["pages_fetched"],
                        items_new=self.stats["items_new"],
                        items_updated=self.stats["items_updated"],
                        items_filtered=self.stats["items_filtered"],
                        error_count=self.stats["error_count"],
                    )
                    time.sleep(settings.crawl_request_delay_sec)

            job.status = "success"
            job.message = "crawl completed"
            self._emit(
                "crawl_complete",
                phase="采集完成",
                message="全网巡检采集阶段完成，进入研判…",
                pages_fetched=self.stats["pages_fetched"],
                items_new=self.stats["items_new"],
                items_updated=self.stats["items_updated"],
                items_filtered=self.stats["items_filtered"],
                error_count=self.stats["error_count"],
            )
        except Exception as exc:  # noqa: BLE001
            job.status = "failed"
            job.message = str(exc)
            logger.exception("全量爬取失败")
            self._emit("error", status="failed", phase="失败", message=str(exc))
        finally:
            job.finished_at = datetime.utcnow()
            job.pages_fetched = self.stats["pages_fetched"]
            job.items_new = self.stats["items_new"]
            job.items_updated = self.stats["items_updated"]
            job.items_filtered = self.stats["items_filtered"]
            job.error_count = self.stats["error_count"]
            self.db.commit()
            self.db.refresh(job)
        return job

    def _crawl_source(
        self,
        client: httpx.Client,
        src: Source,
        fetched_pages: Optional[Set[str]] = None,
    ) -> None:
        fetched_pages = fetched_pages if fetched_pages is not None else set()
        html = None
        if src.page_url in fetched_pages:
            # 已抓过同 URL：仍尝试用缓存逻辑走发现；此处重新轻量请求会浪费，直接跳过列表发现
            html = self._fetch(client, src.page_url)
        else:
            html = self._fetch(client, src.page_url)
            if html is not None:
                fetched_pages.add(src.page_url)
                self.stats["pages_fetched"] += 1

        if html is None:
            src.last_status = "unreachable"
            src.last_crawled_at = datetime.utcnow()
            return

        soup = BeautifulSoup(html, "lxml")
        extra = []
        for s in SOURCES:
            if s["org_name"] == src.org_name:
                extra = s.get("keywords_extra") or []
                break

        # 列表页：抽取文章链接并递归发现下级栏目
        links = self._extract_links(soup, src.page_url, src.base_url)
        self._discover_child_sources(src, links)

        article_links = [u for u in links if self._looks_like_article(u)][: settings.crawl_max_pages_per_source]
        candidates = [src.page_url] + article_links

        for url in candidates:
            if not is_allowed_url(url):
                continue
            try:
                if url == src.page_url:
                    page_html = html
                elif url in fetched_pages:
                    page_html = self._fetch(client, url)
                else:
                    page_html = self._fetch(client, url)
                    if page_html:
                        fetched_pages.add(url)
                        self.stats["pages_fetched"] += 1
                        time.sleep(settings.crawl_request_delay_sec)
                if not page_html:
                    continue
                self._ingest_page(src, url, page_html, extra)
            except Exception as exc:  # noqa: BLE001
                self.stats["error_count"] += 1
                logger.warning("页面处理失败 %s: %s", url, exc)

        src.last_crawled_at = datetime.utcnow()
        src.last_status = "ok"

    def _ingest_page(self, src: Source, url: str, html: str, extra_keywords: list) -> None:
        soup = BeautifulSoup(html, "lxml")
        title = normalize_text(
            (soup.find("h1").get_text() if soup.find("h1") else None)
            or (soup.title.get_text() if soup.title else "")
            or src.org_name
        )
        # 去除脚本样式
        for tag in soup(["script", "style", "noscript", "nav", "footer", "header"]):
            tag.decompose()
        paragraphs = [normalize_text(p.get_text(" ", strip=True)) for p in soup.find_all(["p", "article", "li"])]
        paragraphs = [p for p in paragraphs if len(p) > 20]
        content = normalize_text("\n".join(paragraphs[:80]))
        summary = content[:400]
        blob = f"{title}\n{summary}\n{content}"

        if not is_drug_related(blob, extra_keywords):
            self.stats["items_filtered"] += 1
            return

        published = parse_date_guess(blob) or parse_date_guess(html[:5000])
        if is_stale(published, max_days=540):
            self.stats["items_filtered"] += 1
            return

        lang = detect_lang(blob) or src.lang or "mn"
        title_zh = translate_to_zh(title, lang, settings.enable_translation)
        summary_zh = translate_to_zh(summary, lang, settings.enable_translation)
        content_zh = translate_to_zh(content[:3000], lang, settings.enable_translation)

        ch = content_hash(title, url, content)
        existing = self.db.query(IntelItem).filter(
            (IntelItem.url == url) | (IntelItem.content_hash == ch)
        ).first()

        level = intel_level(blob)
        category = classify_category(blob)
        alert = is_critical(blob) or level == "紧急"

        if existing:
            changed = existing.content_hash != ch
            if changed:
                existing.title = title
                existing.title_zh = title_zh
                existing.summary = summary
                existing.summary_zh = summary_zh
                existing.content = content
                existing.content_zh = content_zh
                existing.content_hash = ch
                existing.intel_level = level
                existing.category = category
                existing.is_alert = alert
                existing.status = "updated"
                existing.crawled_at = datetime.utcnow()
                if published:
                    existing.published_at = published
                self.stats["items_updated"] += 1
                self.db.flush()
                self._emit(
                    "item",
                    item={
                        "id": existing.id,
                        "title": title_zh or title,
                        "org": src.org_name,
                        "system": src.system_name,
                        "level": level,
                        "category": category,
                        "url": url,
                        "status": "updated",
                        "is_alert": alert,
                    },
                    items_updated=self.stats["items_updated"],
                    items_new=self.stats["items_new"],
                    message=f"更新情报：{title_zh or title}",
                )
            else:
                existing.is_duplicate = True
            return

        item = IntelItem(
            source_id=src.id,
            system_id=src.system_id,
            system_name=src.system_name,
            org_name=src.org_name,
            url=url,
            title=title,
            title_zh=title_zh,
            summary=summary,
            summary_zh=summary_zh,
            content=content,
            content_zh=content_zh,
            lang=lang,
            published_at=published,
            crawled_at=datetime.utcnow(),
            content_hash=ch,
            intel_level=level,
            category=category,
            is_alert=alert,
            status="new",
            raw_meta=json.dumps({"source_page": src.page_url}, ensure_ascii=False),
        )
        self.db.add(item)
        self.db.flush()
        self.stats["items_new"] += 1
        self._emit(
            "item",
            item={
                "id": item.id,
                "title": title_zh or title,
                "org": src.org_name,
                "system": src.system_name,
                "level": level,
                "category": category,
                "url": url,
                "status": "new",
                "is_alert": alert,
            },
            items_new=self.stats["items_new"],
            items_updated=self.stats["items_updated"],
            message=f"新情报入库：{title_zh or title}",
        )

    def _discover_child_sources(self, src: Source, links: List[str]) -> None:
        if src.discover_depth >= settings.crawl_max_depth:
            return
        # 栏目型链接优先
        column_hints = [
            "news", "info", "press", "announcement", "legal", "prevention",
            "cooperation", "report", "мэдээ", "зарлал", "drug", "narcotic",
        ]
        added = 0
        for url in links:
            if added >= 15:
                break
            low = url.lower()
            if not any(h in low for h in column_hints):
                continue
            if not is_allowed_url(url):
                continue
            if not same_host_or_sub(url, src.base_url) and "unodc.org" not in urlparse(url).netloc:
                continue
            exists = (
                self.db.query(Source)
                .filter(Source.org_name == src.org_name, Source.page_url == url)
                .first()
            )
            if exists:
                continue
            child = Source(
                system_id=src.system_id,
                system_name=src.system_name,
                org_name=src.org_name,
                org_name_mn=src.org_name_mn,
                base_url=src.base_url,
                page_url=url,
                is_seed=False,
                is_active=True,
                lang=src.lang,
                discover_depth=src.discover_depth + 1,
                last_status="discovered",
            )
            self.db.add(child)
            added += 1
        if added:
            self.db.commit()
            logger.info("自动发现下级栏目 %s 条 @ %s", added, src.org_name)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=8), reraise=False)
    def _fetch(self, client: httpx.Client, url: str) -> Optional[str]:
        if not is_allowed_url(url):
            return None
        try:
            resp = client.get(url)
            if resp.status_code >= 400:
                logger.warning("HTTP %s %s", resp.status_code, url)
                return None
            ctype = resp.headers.get("content-type", "")
            if "html" not in ctype and "text" not in ctype and "xml" not in ctype:
                return None
            resp.encoding = resp.encoding or "utf-8"
            return resp.text
        except Exception as exc:  # noqa: BLE001
            logger.warning("请求失败 %s: %s", url, exc)
            return None

    def _extract_links(self, soup: BeautifulSoup, page_url: str, base_url: str) -> List[str]:
        out: List[str] = []
        seen: Set[str] = set()
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("#") or href.startswith("mailto:") or href.startswith("javascript:"):
                continue
            full = self._clean_url(urljoin(page_url, href))
            if full in seen:
                continue
            if not is_allowed_url(full):
                continue
            if not same_host_or_sub(full, base_url) and "unodc.org" not in urlparse(full).netloc:
                continue
            seen.add(full)
            out.append(full)
        return out

    @staticmethod
    def _clean_url(url: str) -> str:
        url, _ = urldefrag(url)
        return url.rstrip("/")

    @staticmethod
    def _looks_like_article(url: str) -> bool:
        low = url.lower()
        hints = [
            "news", "info", "press", "article", "detail", "view", "post",
            "announcement", "report", "мэдээ", "id=", "content",
        ]
        return any(h in low for h in hints)
