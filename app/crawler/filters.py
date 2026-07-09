"""文本过滤、去重、翻译与情报等级判定工具"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlparse

from config.sources import ALLOW_ANY_MN_DOMAIN, ALLOWED_DOMAINS, CRITICAL_KEYWORDS, DRUG_KEYWORDS

logger = logging.getLogger(__name__)

# 明确排除的非目标域名
BLOCKED_SUFFIXES = (
    "facebook.com", "twitter.com", "x.com", "instagram.com", "tiktok.com",
    "youtube.com", "linkedin.com", "wikipedia.org", "pinterest.com",
)


def content_hash(title: str, url: str, body: str = "") -> str:
    raw = f"{title.strip()}|{url.strip()}|{body[:2000].strip()}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()


def normalize_text(text: str) -> str:
    text = text or ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_allowed_url(url: str, extra_domains: Optional[list] = None) -> bool:
    try:
        host = urlparse(url).netloc.lower().split(":")[0]
    except Exception:
        return False
    if not host:
        return False
    if any(host == b or host.endswith("." + b) for b in BLOCKED_SUFFIXES):
        return False

    allow = set(ALLOWED_DOMAINS)
    if extra_domains:
        allow.update(extra_domains)
    if host in allow:
        return True
    for d in allow:
        base = d.replace("www.", "")
        if host == base or host.endswith("." + base):
            return True
    if host.endswith("unodc.org") or host.endswith("news.google.com"):
        return True
    # 海量采集：允许蒙古国域名公开资讯
    if ALLOW_ANY_MN_DOMAIN and host.endswith(".mn"):
        return True
    return False


def is_drug_related(text: str, extra_keywords: Optional[list] = None, loose: bool = False) -> bool:
    blob = (text or "").lower()
    if not blob:
        return False
    keys = list(DRUG_KEYWORDS)
    if extra_keywords:
        keys.extend(extra_keywords)
    # 去重并按长度降序，优先长词
    keys = sorted(set(keys), key=len, reverse=True)
    for kw in keys:
        k = kw.lower().strip()
        if not k:
            continue
        if k in blob:
            return True
    if loose:
        # 宽松模式：执法/海关/边境 + 查获类组合
        combo_a = any(x in blob for x in ["баривчилгаа", "seizure", "seized", "查获", "缴获", "arrest"])
        combo_b = any(x in blob for x in ["хил", "гааль", "цагдаа", "border", "customs", "police", "口岸", "海关", "警察"])
        if combo_a and combo_b:
            return True
    return False


def is_critical(text: str, extra: Optional[list] = None) -> bool:
    blob = (text or "").lower()
    keys = list(CRITICAL_KEYWORDS)
    if extra:
        keys.extend(extra)
    for kw in keys:
        if kw.lower() in blob:
            return True
    return False


def classify_category(text: str) -> str:
    t = (text or "").lower()
    rules = [
        ("跨境毒情", ["跨境", "口岸", "边境", "хил", "гааль", "border", "customs", "trafficking"]),
        ("新型毒品", ["合成", "芬太尼", "冰毒", "синтетик", "synthetic", "meth", "fentanyl", "NPS", "метамфетамин"]),
        ("制毒原料", ["易制毒", "麻精", "precursor", "прекурсор", "controlled"]),
        ("戒毒康复", ["戒毒", "康复", "成瘾", "нөхөн сэргээх", "донтсон", "rehab", "addiction"]),
        ("国际协作", ["UNODC", "国际", "олон улсын", "cooperation", "外交"]),
        ("执法行动", ["缉毒", "查获", "专项", "баривчилгаа", "seizure", "operation", "цагдаа"]),
        ("政策法规", ["立法", "法规", "新法", "хууль", "legal", "regulation", "policy"]),
        ("媒体报道", ["news", "мэдээ", "报道", "通讯"]),
    ]
    for name, kws in rules:
        for kw in kws:
            if kw.lower() in t:
                return name
    return "综合"


def intel_level(text: str) -> str:
    if is_critical(text):
        return "紧急"
    t = (text or "").lower()
    important = ["查获", "逮捕", "管制", "专项", "seizure", "seized", "arrest", "баривчилгаа", "тусгай"]
    watch = ["会议", "培训", "宣传", "урьдчилан", "prevention", "meeting", "мэдээ"]
    for kw in important:
        if kw.lower() in t:
            return "重要"
    for kw in watch:
        if kw.lower() in t:
            return "关注"
    return "一般"


def detect_lang(text: str) -> str:
    t = text or ""
    if re.search(r"[\u4e00-\u9fff]", t):
        return "zh"
    if re.search(r"[өүӨҮ]", t):
        return "mn"
    if re.search(r"[а-яА-ЯёЁ]", t):
        return "ru"
    return "en"


def translate_to_zh(text: str, source_lang: Optional[str] = None, enabled: bool = True) -> str:
    text = normalize_text(text)
    if not text or not enabled:
        return text
    lang = source_lang or detect_lang(text)
    if lang == "zh":
        return text
    try:
        from deep_translator import GoogleTranslator

        src = {"mn": "mn", "en": "en", "ru": "ru"}.get(lang, "auto")
        chunks = [text[i : i + 4500] for i in range(0, len(text), 4500)]
        out = []
        for c in chunks:
            out.append(GoogleTranslator(source=src, target="zh-CN").translate(c))
        return "\n".join(out)
    except Exception as exc:  # noqa: BLE001
        logger.warning("翻译失败，保留原文: %s", exc)
        return text


def parse_date_guess(text: str) -> Optional[datetime]:
    if not text:
        return None
    patterns = [
        r"(20\d{2})[./\-](\d{1,2})[./\-](\d{1,2})",
        r"(\d{1,2})[./\-](\d{1,2})[./\-](20\d{2})",
    ]
    for i, pat in enumerate(patterns):
        m = re.search(pat, text)
        if not m:
            continue
        try:
            if i == 0:
                y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
            else:
                d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
            return datetime(y, mo, d)
        except ValueError:
            continue
    return None


def is_stale(published_at: Optional[datetime], max_days: int = 3650) -> bool:
    """默认保留近10年公开资讯，避免误杀历史通报。"""
    if not published_at:
        return False
    return published_at < datetime.utcnow() - timedelta(days=max_days)


def same_host_or_sub(url: str, base_url: str) -> bool:
    try:
        h1 = urlparse(url).netloc.lower().split(":")[0]
        h2 = urlparse(base_url).netloc.lower().split(":")[0]
        b1 = h1.replace("www.", "")
        b2 = h2.replace("www.", "")
        return h1 == h2 or h1.endswith("." + b2) or h2.endswith("." + b1) or b1 == b2
    except Exception:
        return False
