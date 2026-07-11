"""官方统计采集：新闻统计抽取 + PDF 发现/下载/文本解析"""
from __future__ import annotations

import logging
import os
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
    content_hash,
    detect_lang,
    intel_level,
    is_drug_related,
    normalize_text,
    translate_to_zh,
)
from app.crawler.stats_extract import extract_stats_from_text, stats_fingerprint
from app.db.models import IntelItem, StatRecord
from config.official_stats import (
    OFFICIAL_STAT_SEARCHES,
    PDF_ALLOWED_DOMAINS,
    PDF_SEARCH_QUERIES,
)

logger = logging.getLogger(__name__)
settings = get_settings()
ProgressCallback = Optional[Callable[..., None]]


def _google_news_url(query: str, hl: str, gl: str, ceid: str) -> str:
    return (
        "https://news.google.com/rss/search?"
        f"q={quote_plus(query)}&hl={hl}&gl={gl}&ceid={quote_plus(ceid)}"
    )


def _google_web_url(query: str) -> str:
    return f"https://www.google.com/search?q={quote_plus(query)}&num=20&hl=en"


def _host_allowed(url: str) -> bool:
    host = urlparse(url).netloc.lower().replace("www.", "")
    for d in PDF_ALLOWED_DOMAINS:
        base = d.replace("www.", "")
        if host == base or host.endswith("." + base):
            return True
    return False


def _extract_pdf_text(data: bytes) -> str:
    """尽量抽取 PDF 文本；超大分片；恶意脚本特征直接跳过。

    修改原因：PDF 安全改造——体积上限已在调用方；此处增加恶意文本检测与分片读取。
    """
    # 恶意/脚本载荷粗检
    head = data[:8000].lower()
    if b"/javascript" in head or b"/js" in head and b"action" in head or b"app:javascript" in head:
        logger.warning("PDF malicious script marker detected, skip")
        return ""
    try:
        from pypdf import PdfReader  # type: ignore
        import io

        reader = PdfReader(io.BytesIO(data))
        parts = []
        # 分片：每批最多 20 页，累计字符上限 200000
        max_chars = 200000
        for i, page in enumerate(reader.pages[:80]):
            try:
                chunk = page.extract_text() or ""
            except Exception:
                continue
            parts.append(chunk)
            if sum(len(p) for p in parts) >= max_chars:
                break
            if i > 0 and i % 20 == 0 and not "".join(parts).strip():
                # 连续空白页过多则提前结束，避免阻塞
                break
        text = "\n".join(parts)
        if text.strip():
            return text[:20000]  # 下游再截断
    except Exception as exc:  # noqa: BLE001
        logger.debug("pypdf extract failed: %s", exc)

    # 回退：从二进制里捞可打印片段
    try:
        raw = data.decode("latin-1", errors="ignore")
        chunks = re.findall(r"[\x20-\x7E\u0400-\u04FF\u4e00-\u9fff]{8,}", raw)
        return "\n".join(chunks[:2000])[:20000]
    except Exception:
        return ""


class OfficialStatsCollector:
    def __init__(self, db: Session, on_event: ProgressCallback = None):
        self.db = db
        self.on_event = on_event
        self.stats = {
            "feeds": 0,
            "items_new": 0,
            "items_updated": 0,
            "stats_new": 0,
            "pdfs": 0,
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
            logger.debug("stats progress callback failed", exc_info=True)

    def run(self, mode: str = "full") -> dict:
        headers = {
            "User-Agent": settings.crawl_user_agent,
            "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
            "Accept-Language": "mn,en;q=0.9,zh-CN;q=0.8",
        }
        # 新闻快扫：只跑统计新闻搜索；全量：再加 PDF 发现
        if mode == "news":
            tasks = list(OFFICIAL_STAT_SEARCHES)
        else:
            tasks = list(OFFICIAL_STAT_SEARCHES) + list(PDF_SEARCH_QUERIES)
        total = len(tasks)
        self._emit(
            "phase",
            status="running",
            phase="官方统计采集",
            message=f"启动官方统计采集（{mode}），共 {total} 路任务",
            total_sources=total,
            current_index=0,
        )

        pdf_dir = os.path.join(settings.resolved_data_dir, "raw", "pdfs")
        os.makedirs(pdf_dir, exist_ok=True)

        with httpx.Client(
            headers=headers,
            timeout=httpx.Timeout(35.0, connect=10.0),
            follow_redirects=True,
            verify=False,
        ) as client:
            for idx, task in enumerate(tasks, start=1):
                org = task["org_name"]
                self._emit(
                    "source_start",
                    current_index=idx,
                    total_sources=total,
                    current_org=org,
                    current_url=task.get("query", ""),
                    phase="官方统计采集",
                    message=f"[{idx}/{total}] {org}",
                    items_new=self.stats["items_new"],
                    items_updated=self.stats["items_updated"],
                    items_filtered=self.stats["items_filtered"],
                    error_count=self.stats["error_count"],
                )
                try:
                    if task.get("engine") == "google_news":
                        url = _google_news_url(
                            task["query"], task["hl"], task["gl"], task["ceid"]
                        )
                        self._ingest_news(client, task, url)
                    else:
                        self._ingest_pdf_search(client, task, pdf_dir)
                    self.stats["feeds"] += 1
                    self.db.commit()
                except Exception as exc:  # noqa: BLE001
                    self.stats["error_count"] += 1
                    try:
                        self.db.rollback()
                    except Exception:
                        pass
                    logger.warning("官方统计任务失败 %s: %s", org, exc)
                    self._emit("source_error", current_org=org, message=f"失败：{org} — {exc}")
                self._emit(
                    "source_done",
                    current_index=idx,
                    total_sources=total,
                    current_org=org,
                    message=f"完成：{org}｜统计新增 {self.stats['stats_new']}",
                    items_new=self.stats["items_new"],
                    items_updated=self.stats["items_updated"],
                    items_filtered=self.stats["items_filtered"],
                    error_count=self.stats["error_count"],
                )

        self.db.commit()
        self._emit(
            "crawl_complete",
            phase="官方统计完成",
            message=(
                f"官方统计完成：情报+{self.stats['items_new']}，"
                f"统计点+{self.stats['stats_new']}，PDF {self.stats['pdfs']}"
            ),
            items_new=self.stats["items_new"],
            items_updated=self.stats["items_updated"],
        )
        return self.stats

    def _ingest_news(self, client: httpx.Client, feed: dict, url: str) -> None:
        resp = client.get(url)
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code}")
        parsed = feedparser.parse(resp.text)
        for entry in (parsed.entries or [])[:25]:
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
            body = f"{title}\n{summary}"
            if not is_drug_related(body, loose=False):
                self.stats["items_filtered"] += 1
                continue
            from app.crawler.filters import is_mongolia_country_related, is_unodc_mongolia_signal

            if not is_mongolia_country_related(body) and not is_unodc_mongolia_signal(body):
                self.stats["items_filtered"] += 1
                continue
            # 无发布时间不丢弃；统计类优先含数字，但口岸快讯无数字也放行
            if not re.search(
                r"\d|статистик|хувь|өс|бүртгэгд|хэрэг|seizure|percent|%|案件|同比|查获|мансууруулах|narcotic|毒品",
                body,
                flags=re.I,
            ):
                self.stats["items_filtered"] += 1
                continue
            item = self._save_intel(
                org_name=feed["org_name"],
                title=title,
                summary=summary,
                url=link,
                published=published,  # None 也可入库
                category="官方统计",
            )
            if item:
                self._save_stats_from_text(
                    body,
                    source_url=link,
                    org_name=feed["org_name"],
                    title=title,
                    intel_id=item.id,
                    source_type="news_stat",
                )

    def _ingest_pdf_search(self, client: httpx.Client, task: dict, pdf_dir: str) -> None:
        # 用 Google 网页搜索找 PDF；失败则跳过
        search_url = _google_web_url(task["query"])
        resp = client.get(search_url)
        if resp.status_code >= 400:
            raise RuntimeError(f"HTTP {resp.status_code}")
        soup = BeautifulSoup(resp.text, "lxml")
        pdf_urls: List[str] = []
        for a in soup.find_all("a", href=True):
            href = a["href"]
            # Google 包装链
            if href.startswith("/url?"):
                qs = parse_qs(urlparse(href).query)
                cand = unquote((qs.get("q") or qs.get("url") or [""])[0])
            else:
                cand = href
            if not cand.lower().endswith(".pdf"):
                # 有些结果是 /url?q=...pdf
                if ".pdf" not in cand.lower():
                    continue
                m = re.search(r"(https?://[^\s\"'<>]+\.pdf)", cand, flags=re.I)
                if not m:
                    continue
                cand = m.group(1)
            if not cand.startswith("http"):
                continue
            # 硬性：禁止下载蒙古 .gov.mn PDF（即使搜索结果出现）
            from config.core_official import is_forbidden_url
            if is_forbidden_url(cand) or ".gov.mn" in cand.lower():
                continue
            if not _host_allowed(cand) and "unodc.org" not in cand and "ocindex.net" not in cand:
                host = urlparse(cand).netloc.lower()
                # 原缺陷：含 "gov." 即放行 → 可能直连 gov.mn；现明确排除
                if host.endswith(".gov.mn") or host == "gov.mn":
                    continue
                if not any(x in host for x in (".mn", "unodc.org", "ocindex.net", "incb.org")):
                    continue
                if host.endswith(".gov.mn"):
                    continue
            if cand not in pdf_urls:
                pdf_urls.append(cand)
            if len(pdf_urls) >= 6:
                break

        for pdf_url in pdf_urls:
            self._download_and_parse_pdf(client, pdf_url, task["org_name"], pdf_dir)

    def _download_and_parse_pdf(
        self, client: httpx.Client, pdf_url: str, org_name: str, pdf_dir: str
    ) -> None:
        if pdf_url in self._seen_urls:
            return
        self._seen_urls.add(pdf_url)
        try:
            resp = client.get(pdf_url)
            if resp.status_code >= 400 or not resp.content:
                return
            ctype = (resp.headers.get("content-type") or "").lower()
            if "pdf" not in ctype and not pdf_url.lower().endswith(".pdf"):
                return
            data = resp.content
            from config.official_stats import PDF_MAX_BYTES
            if len(data) > int(PDF_MAX_BYTES or 25 * 1024 * 1024):
                # 修改原因：超大 PDF 跳过，防内存溢出
                return
            if len(data) < 500:
                return
            fname = hashlib_name(pdf_url) + ".pdf"
            path = os.path.join(pdf_dir, fname)
            with open(path, "wb") as f:
                f.write(data)
            text = _extract_pdf_text(data)
            if not text or len(text) < 20:
                # 短 PDF：若含毒品统计关键词仍保留
                if not text or not re.search(
                    r"мансууруулах|narcotic|drug|毒品|涉毒|seizure",
                    text or "",
                    flags=re.I,
                ):
                    return
            # 入库判定复用宽松规则；扫描前 20000 字符
            sample = text[:20000]
            if not is_drug_related(sample, loose=False):
                if not re.search(
                    r"мансууруулах|хар\s*тамхи|narcotic|methamphetamine|fentanyl|毒品|涉毒|seizure",
                    text,
                    flags=re.I,
                ):
                    return
            title = f"PDF报表：{urlparse(pdf_url).path.split('/')[-1][:80]}"
            summary = normalize_text(text[:1200])
            item = self._save_intel(
                org_name=org_name,
                title=title,
                summary=summary,
                url=pdf_url,
                published=None,
                category="PDF报表",
                content=text[:20000],
            )
            self.stats["pdfs"] += 1
            self._save_stats_from_text(
                text[:30000],
                source_url=pdf_url,
                org_name=org_name,
                title=title,
                intel_id=item.id if item else None,
                source_type="pdf",
            )
            self._emit(
                "item",
                item={
                    "id": item.id if item else 0,
                    "title": title,
                    "org": org_name,
                    "system": "官方统计与年报体系",
                    "level": "关注",
                    "category": "PDF报表",
                    "url": pdf_url,
                    "status": "new",
                    "is_alert": False,
                },
                message=f"PDF入库：{title}",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("PDF 处理失败 %s: %s", pdf_url, exc)
            self.stats["error_count"] += 1

    def _save_intel(
        self,
        org_name: str,
        title: str,
        summary: str,
        url: str,
        published: Optional[datetime],
        category: str,
        content: str = "",
    ) -> Optional[IntelItem]:
        title = normalize_text(title)
        summary = normalize_text(summary)
        if not title or not url:
            return None
        if url in self._seen_urls:
            existing = self.db.query(IntelItem).filter(IntelItem.url == url).first()
            return existing
        self._seen_urls.add(url)

        lang = detect_lang(title + summary) or "mn"
        title_zh = translate_to_zh(title, lang, settings.enable_translation)
        body = content or summary
        ch = content_hash(title, url, summary)
        existing = (
            self.db.query(IntelItem)
            .filter((IntelItem.url == url) | (IntelItem.content_hash == ch))
            .first()
        )
        level = intel_level(f"{title}\n{summary}")
        if existing:
            if existing.content_hash != ch:
                existing.title = title
                existing.title_zh = title_zh
                existing.summary = summary
                existing.summary_zh = summary
                existing.content = body[:20000]
                existing.content_hash = ch
                existing.category = category
                existing.intel_level = level
                existing.status = "updated"
                existing.crawled_at = datetime.utcnow()
                self.stats["items_updated"] += 1
                self.db.flush()
            return existing

        row = IntelItem(
            source_id=None,
            system_id=9,
            system_name="官方统计与年报体系",
            org_name=org_name,
            url=url,
            title=title,
            title_zh=title_zh,
            summary=summary,
            summary_zh=summary,
            content=body[:20000],
            content_zh="",
            lang=lang,
            published_at=published,
            crawled_at=datetime.utcnow(),
            content_hash=ch,
            intel_level=level,
            category=category,
            is_alert=level in ("重要", "紧急"),
            status="new",
            raw_meta='{"collector":"official_stats"}',
        )
        self.db.add(row)
        self.db.flush()
        self.stats["items_new"] += 1
        return row

    def _save_stats_from_text(
        self,
        text: str,
        *,
        source_url: str,
        org_name: str,
        title: str,
        intel_id: Optional[int],
        source_type: str,
    ) -> None:
        extracted = extract_stats_from_text(
            text, source_url=source_url, org_name=org_name, title=title
        )
        for st in extracted:
            fp = stats_fingerprint(
                st["metric_name"], st["metric_value"], st.get("period") or "", source_url
            )
            exists = self.db.query(StatRecord).filter(StatRecord.fingerprint == fp).first()
            if exists:
                continue
            row = StatRecord(
                intel_id=intel_id,
                system_id=9,
                system_name="官方统计与年报体系",
                org_name=org_name,
                source_url=source_url,
                source_type=source_type,
                title=title[:500],
                metric_name=st["metric_name"],
                metric_value=st["metric_value"],
                unit=st.get("unit") or "",
                period=st.get("period") or "",
                raw_snippet=st.get("raw_snippet") or "",
                confidence=st.get("confidence") or 0.7,
                fingerprint=fp,
                crawled_at=datetime.utcnow(),
            )
            self.db.add(row)
            self.stats["stats_new"] += 1
        if extracted:
            self.db.flush()


def hashlib_name(url: str) -> str:
    import hashlib

    return hashlib.sha1(url.encode("utf-8", errors="ignore")).hexdigest()[:20]
