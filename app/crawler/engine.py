"""全网增量爬虫引擎：仅蒙古国官方禁毒体系，低频率、断点续爬、自动发现下级栏目。"""
from __future__ import annotations

import json
import logging
import random
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
    is_mongolia_country_related,
    is_stale,
    is_unodc_mongolia_signal,
    normalize_text,
    parse_date_guess,
    same_host_or_sub,
    translate_to_zh,
)
from app.crawler.http_client import build_httpx_client, pick_user_agent
from app.crawler.rate_limit import can_crawl_host, mark_host_crawled
from app.db.models import CrawlJob, IntelItem, Source
from config.core_official import is_forbidden_url
from config.sources import SOURCES
from config.official_stats import OFFICIAL_STAT_SOURCES
from config.global_media import GLOBAL_COVERAGE_SOURCES

logger = logging.getLogger(__name__)
settings = get_settings()

ProgressCallback = Optional[Callable[..., None]]


class CrawlEngine:
    def __init__(self, db: Session, on_event: ProgressCallback = None):
        self.db = db
        self.on_event = on_event
        # 原缺陷：固定 UA 易被反爬；现用 UA 池随机
        self.headers = {
            "User-Agent": pick_user_agent(),
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
        from config.core_official import CORE_OFFICIAL_SOURCES

        all_sources = (
            list(CORE_OFFICIAL_SOURCES)
            + list(SOURCES)
            + list(OFFICIAL_STAT_SOURCES)
            + list(GLOBAL_COVERAGE_SOURCES)
        )
        for s in all_sources:
            for path in s.get("seed_paths") or ["/"]:
                page_url = urljoin(s["base_url"].rstrip("/") + "/", path.lstrip("/"))
                page_url = self._clean_url(page_url)
                if is_forbidden_url(page_url):
                    continue
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

    def run_core_official_crawl(self, resume: bool = False) -> CrawlJob:
        """仅巡检文档指定的核心官方种子（适合新闻监测轮增量）。"""
        from config.core_official import CORE_OFFICIAL_SOURCES

        core_orgs = {s["org_name"] for s in CORE_OFFICIAL_SOURCES}
        core_hosts = {
            (s["base_url"].replace("https://", "").replace("http://", "").split("/")[0]).lower()
            for s in CORE_OFFICIAL_SOURCES
        }
        job = CrawlJob(status="running", started_at=datetime.utcnow(), checkpoint="{}")
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        try:
            self.seed_sources()
            # 浅扫：每个 base_url 只保留 1 个入口（优先 /cn、/mn、/en），避免多语言入口深翻页
            path_score = {"/cn": 0, "/mn": 1, "/en": 2, "/": 3}

            def _score(url: str) -> int:
                u = (url or "").rstrip("/")
                for p, sc in path_score.items():
                    if u.endswith(p):
                        return sc
                return 9

            raw_sources = []
            for s in CORE_OFFICIAL_SOURCES:
                from urllib.parse import urljoin

                paths = s.get("seed_paths") or ["/"]
                best_path = sorted(paths, key=lambda p: path_score.get(p, 5))[0]
                page = urljoin(s["base_url"].rstrip("/") + "/", best_path.lstrip("/")).rstrip("/")
                raw_sources.append((s["org_name"], s["base_url"], page))

            sources = (
                self.db.query(Source)
                .filter(Source.is_active.is_(True))
                .filter(Source.is_seed.is_(True))
                .order_by(Source.system_id, Source.id)
                .all()
            )
            by_org: Dict[str, list] = {}
            for s in sources:
                if s.org_name in core_orgs:
                    by_org.setdefault(s.org_name, []).append(s)
            seen_host: Set[str] = set()
            uniq = []
            for org_name, base, page in raw_sources:
                host = urlparse(base).netloc.lower().replace("www.", "")
                if host in seen_host:
                    continue
                seen_host.add(host)
                matched = None
                for cand in by_org.get(org_name, []):
                    if (cand.page_url or "").rstrip("/") == page.rstrip("/"):
                        matched = cand
                        break
                if matched is None and by_org.get(org_name):
                    matched = sorted(by_org[org_name], key=lambda x: _score(x.page_url or ""))[0]
                if matched is not None:
                    uniq.append(matched)
            sources = uniq
            total = len(sources)
            self._emit(
                "phase",
                status="running",
                phase="核心官网浅扫",
                message=f"浅扫清单官网 {total} 站（每站1入口，少翻页防漏）…",
                total_sources=total,
                current_index=0,
            )
            old_max = settings.crawl_max_pages_per_source
            shallow = int(getattr(settings, "crawl_max_pages_core", 4) or 4)
            if shallow <= 0:
                shallow = 4
            settings.crawl_max_pages_per_source = min(old_max if old_max > 0 else 4, max(2, min(shallow, 6)))
            try:
                self._crawl_source_list(job, sources, resume=resume, phase="核心官网浅扫")
            finally:
                settings.crawl_max_pages_per_source = old_max
            job.status = "success"
            job.finished_at = datetime.utcnow()
            job.pages_fetched = self.stats["pages_fetched"]
            job.items_new = self.stats["items_new"]
            job.items_updated = self.stats["items_updated"]
            job.items_filtered = self.stats["items_filtered"]
            job.error_count = self.stats["error_count"]
            job.message = (
                f"核心官网浅扫完成：新{self.stats['items_new']} "
                f"更新{self.stats['items_updated']} 过滤{self.stats['items_filtered']}"
            )
            self.db.commit()
            self._emit("phase", status="success", phase="核心官网浅扫完成", message=job.message)
            return job
        except Exception as exc:  # noqa: BLE001
            logger.exception("core official crawl failed")
            job.status = "failed"
            job.message = str(exc)
            job.finished_at = datetime.utcnow()
            self.db.commit()
            self._emit("error", status="failed", phase="核心官网失败", message=str(exc))
            return job

    def _crawl_source_list(
        self,
        job: CrawlJob,
        sources: list,
        resume: bool = True,
        phase: str = "全网巡检",
    ) -> None:
        total = len(sources)
        done_urls: Set[str] = set()
        if resume and job.checkpoint:
            try:
                done_urls = set(json.loads(job.checkpoint or "{}").get("done", []))
            except Exception:
                done_urls = set()

        fetched_pages: Set[str] = set()
        with build_httpx_client(headers=self.headers) as client:
            for idx, src in enumerate(sources, start=1):
                checkpoint_key = f"{src.org_name}|{src.page_url}"
                if is_forbidden_url(src.page_url or ""):
                    self.stats["items_filtered"] += 1
                    continue
                if not can_crawl_host(self.db, src.page_url or src.base_url or ""):
                    self._emit(
                        "source_skip",
                        current_index=idx,
                        total_sources=total,
                        current_org=src.org_name,
                        current_url=src.page_url,
                        message=f"日频次已满，跳过：{src.org_name}",
                    )
                    continue
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
                    phase=phase,
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
                    mark_host_crawled(self.db, src.page_url or src.base_url or "")
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
                import random

                jitter = float(getattr(settings, "crawl_delay_jitter_sec", 0.8) or 0)
                time.sleep(settings.crawl_request_delay_sec + random.uniform(0, max(0.0, jitter)))

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
            self._crawl_source_list(job, sources, resume=resume, phase="全网巡检")

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
        try:
            from config.core_official import CORE_OFFICIAL_SOURCES
        except Exception:
            CORE_OFFICIAL_SOURCES = []
        for s in list(CORE_OFFICIAL_SOURCES) + list(SOURCES) + list(OFFICIAL_STAT_SOURCES) + list(GLOBAL_COVERAGE_SOURCES):
            if s["org_name"] == src.org_name:
                extra = s.get("keywords_extra") or []
                break

        # 列表页：抽取文章链接并递归发现下级栏目
        links = self._extract_links(soup, src.page_url, src.base_url)
        self._discover_child_sources(src, links)

        article_links = [u for u in links if self._looks_like_article(u)]
        if self._is_media_source(src) and len(article_links) < 15:
            # 媒体站文章 URL 不规则时，扩大候选
            article_links = links[: settings.crawl_max_pages_per_source]
        # 去重保序
        seen_c: Set[str] = set()
        ordered: List[str] = []
        for u in [src.page_url] + article_links:
            if u not in seen_c:
                seen_c.add(u)
                ordered.append(u)
        candidates = ordered[: settings.crawl_max_pages_per_source]

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
                        time.sleep(
                            settings.crawl_request_delay_sec
                            + random.uniform(0, float(getattr(settings, "crawl_delay_jitter_sec", 2.0) or 0))
                        )
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
        # 去除脚本样式与站点导航，避免侧栏/相关推荐把毒品词污染进正文
        for tag in soup(["script", "style", "noscript", "nav", "footer", "header", "aside", "form"]):
            tag.decompose()
        # 优先正文容器，避免全站 li/菜单误伤
        main = (
            soup.find("article")
            or soup.find(attrs={"class": lambda c: c and any(x in str(c).lower() for x in ("content", "article", "news-body", "post"))})
            or soup.find("main")
            or soup
        )
        paragraphs = [
            normalize_text(p.get_text(" ", strip=True))
            for p in main.find_all(["p", "h2", "h3"])
        ]
        paragraphs = [p for p in paragraphs if len(p) > 25]
        content = normalize_text("\n".join(paragraphs[:40]))
        summary = content[:400]
        # 原缺陷：仅用标题+摘要且蒙通社强制标题含毒词 → 深度专题被误删
        # 优化：标题/摘要/正文任一命中强毒词即可；取消蒙通社标题强制
        gate_blob = f"{title}\n{summary}\n{content[:2500]}"
        if not is_drug_related(gate_blob, extra_keywords, loose=True):
            self.stats["items_filtered"] += 1
            return
        # UNODC：放宽为分栏/统计信号即可，不必全文强调 Mongolia
        host = (url or "").lower()
        if "unodc.org" in host and not is_unodc_mongolia_signal(gate_blob):
            self.stats["items_filtered"] += 1
            return

        blob = f"{title}\n{summary}\n{content}"

        published = parse_date_guess(blob) or parse_date_guess(html[:5000])
        # 无发布时间：is_stale 返回 False，保留入库
        if is_stale(published, max_days=settings.crawl_max_age_days):
            self.stats["items_filtered"] += 1
            return

        # 短快讯：内容过短但标题涉毒仍保留（取消 250 字门槛）
        if len(title) + len(content) < 100 and not is_drug_related(title, loose=True):
            if len(title) < 12:
                self.stats["items_filtered"] += 1
                return

        lang = detect_lang(blob) or src.lang or "mn"
        title_zh = translate_to_zh(title, lang, settings.enable_translation)
        summary_zh = translate_to_zh(summary, lang, settings.enable_translation)
        content_zh = translate_to_zh(content[:3000], lang, settings.enable_translation)

        ch = content_hash(
            title, url, content,
            org_name=src.org_name or "",
            published=published,
        )
        # 仅同 URL 或同 hash（含机构+日期）合并；不同媒体同案分别入库
        existing = self.db.query(IntelItem).filter(
            (IntelItem.url == url) | (IntelItem.content_hash == ch)
        ).first()

        level = intel_level(gate_blob)
        category = classify_category(gate_blob)
        alert = is_critical(gate_blob) or level == "紧急"

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
        # 递归深度完整生效（原 min(depth,1) 导致 depth=2 失效）
        if src.discover_depth >= int(getattr(settings, "crawl_max_depth", 2) or 2):
            return
        column_hints = [
            "narcotic", "anti-drug", "antidrug", "drug-control", "drug",
            "мансууруулах", "хар-тамхи", "хар тамхи", "anti-narcotics",
            "мансууруулах-хэсэг", "мансууруулах хэсэг", "хар тамхи мэдээ",
            "баривчилгаа", "гааль", "фентанил", "метамфетамин",
            "缉毒", "禁毒", "毒品", "seizure", "trafficking",
        ]
        added = 0
        for url in links:
            if added >= 30:  # 子栏目上限 30
                break
            if is_forbidden_url(url):
                continue
            low = url.lower()
            # 路径或锚文本关键词（links 仅为 URL，用路径匹配）
            if not any(h.replace(" ", "-") in low or h.replace(" ", "") in low or h in low for h in column_hints):
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
        if not is_allowed_url(url) or is_forbidden_url(url):
            return None
        try:
            # 每次请求轮换 UA，降低反爬拦截
            client.headers["User-Agent"] = pick_user_agent()
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
            # 媒体/搜索落地允许跨站；官网优先同域
            host = urlparse(full).netloc.lower()
            if not same_host_or_sub(full, base_url):
                if not (host.endswith(".mn") or "unodc.org" in host or "news.google.com" in host):
                    continue
            seen.add(full)
            out.append(full)
        return out

    @staticmethod
    def _clean_url(url: str) -> str:
        url, _ = urldefrag(url)
        return url.rstrip("/")

    @staticmethod
    def _is_media_source(src: Source) -> bool:
        return (src.system_id == 8) or ("媒体" in (src.system_name or ""))

    @staticmethod
    def _looks_like_article(url: str) -> bool:
        low = url.lower()
        hints = [
            "news", "info", "press", "article", "detail", "view", "post",
            "announcement", "report", "мэдээ", "id=", "content", "/n/",
            "story", "media", "zar", "p/", "a/",
        ]
        return any(h in low for h in hints)
