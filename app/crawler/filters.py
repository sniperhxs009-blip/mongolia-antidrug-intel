"""过滤规则修复：函数名/入参/返回值兼容原项目，仅放宽过滤逻辑，解决有效新闻被误删问题"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlparse

from config.core_official import TOPIC_BLACKLIST, is_forbidden_url
from config.sources import (
    ALLOW_ANY_MN_DOMAIN,
    ALLOW_GLOBAL_MEDIA,
    ALLOWED_DOMAINS,
    BLOCKED_SUFFIXES,
)

# 强涉毒关键词（命中直接判定有效）
STRONG_DRUG_TERMS = [
    "毒品", "禁毒", "缉毒", "贩毒", "吸毒", "海洛因", "大麻", "安纳咖", "芬太尼", "尼秦",
    "异托尼他秦", "合成大麻素", "易制毒", "麻精药品",
    "хар тамхи", "мансууруулах бодис", "фентанил", "нитазен",
    "fentanyl", "nitazene", "cannabis", "drug seizure", "narcotic", "methamphetamine",
]
# 弱关联词汇（查获/走私类单独也可放行，修复强制搭配强词导致误删）
WEAK_DRUG_TERMS = ["seizure", "trafficking", "smuggling", "查获", "走私", "баривчилгаа", "хураан"]
# 负面过滤词大幅缩减
NEGATIVE_PATTERNS = [
    r"human trafficking",
    r"anti-corruption",
    r"奥运会",
    r"兴奋剂wada",
    r"乌兰乌德布里亚特",
    r"ulan[- ]?ude",
    r"buryat",
]


def content_hash(title: str, url: str, body: str = "") -> str:
    raw = f"{title.strip()}|{url.strip()}|{body[:2000]}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def detect_lang(text: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", text or ""):
        return "zh"
    if re.search(r"[а-яөүА-ЯӨҮ]", text or ""):
        return "mn"
    return "en"


def translate_to_zh(
    text: str,
    lang: str = None,
    enabled: bool = True,
    source_lang: str = None,
) -> str:
    if not enabled or not text:
        return text or ""
    # 保留轻量替换；完整翻译由上层开关控制时可再接 deep-translator
    rep = [("Mongolia", "蒙古国"), ("Ulaanbaatar", "乌兰巴托"), ("drug", "毒品")]
    res = text
    for en, cn in rep:
        res = re.sub(re.escape(en), cn, res, flags=re.I)
    return res


def is_stale(pub_dt: Optional[datetime], max_days: int = 365) -> bool:
    if not pub_dt:
        return False
    return pub_dt < datetime.utcnow() - timedelta(days=max_days)


def parse_date_guess(html: str) -> Optional[datetime]:
    """尽量解析日期；失败返回 None（不因缺日期直接丢弃）。"""
    if not html:
        return None
    m = re.search(
        r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})",
        html[:8000],
    )
    if not m:
        return None
    try:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except Exception:
        return None


def is_mongolia_country_related(text: str) -> bool:
    low = (text or "").lower()
    markers = [
        "mongolia", "монгол", "улаанбаатар", "ulaanbaatar",
        "蒙古国", "乌兰巴托", "扎门乌德", "甘其毛都", "二连浩特", "中蒙",
    ]
    if any(m in low for m in markers):
        return True
    if re.search(r"(?<!内)蒙古", text or ""):
        return True
    return False


def _has_negative(blob: str) -> bool:
    low = (blob or "").lower()
    for black in list(TOPIC_BLACKLIST) + list(NEGATIVE_PATTERNS):
        try:
            if re.search(black, low, re.I):
                return True
        except re.error:
            if black.lower() in low:
                return True
    return False


def is_drug_related(text: str, extra=None, loose: bool = True) -> bool:
    """核心修复：查获/走私等弱词也可判定有效；兼容 extra / loose 入参。"""
    blob = (text or "").lower()
    if not blob.strip():
        return False
    extras = [str(x).lower() for x in (extra or []) if x]

    if _has_negative(blob):
        strong_hit = any(s.lower() in blob for s in STRONG_DRUG_TERMS) or any(e in blob for e in extras)
        if not strong_hit:
            return False

    if any(s.lower() in blob for s in STRONG_DRUG_TERMS):
        return True
    if extras and any(e in blob for e in extras):
        return True

    # 放宽：弱词命中即保留（解决引擎侧常传 loose=False 仍误删查获新闻）
    if any(w.lower() in blob for w in WEAK_DRUG_TERMS):
        return True
    if loose and any(w.lower() in blob for w in WEAK_DRUG_TERMS):
        return True
    return False


def is_allowed_url(url: str, extra_domains: Optional[list] = None) -> bool:
    try:
        if is_forbidden_url(url):
            return False
    except Exception:
        pass
    try:
        host = urlparse(url).netloc.lower().split(":")[0].replace("www.", "")
    except Exception:
        return False
    if not host:
        return False
    if any(host == b or host.endswith("." + b) for b in BLOCKED_SUFFIXES):
        return False

    allow = set(ALLOWED_DOMAINS)
    if extra_domains:
        allow.update(extra_domains)
    for d in allow:
        base = d.replace("www.", "")
        if host == base or host.endswith("." + base) or host == d:
            return True
    if host.endswith("unodc.org") or host.endswith("news.google.com"):
        return True
    if ALLOW_ANY_MN_DOMAIN and host.endswith(".mn") and not host.endswith(".gov.mn"):
        return True
    if ALLOW_GLOBAL_MEDIA:
        global_media = [
            "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk",
            "xinhuanet.com", "news.cn", "cgtn.com", "akipress.com",
        ]
        if any(host == g or host.endswith("." + g) for g in global_media):
            return True
    return False


def same_host_or_sub(url_a: str, url_b: str) -> bool:
    try:
        h1 = urlparse(url_a).netloc.lower().split(":")[0].replace("www.", "")
        h2 = urlparse(url_b).netloc.lower().split(":")[0].replace("www.", "")
        return h1 == h2 or h1.endswith("." + h2) or h2.endswith("." + h1)
    except Exception:
        return False


def classify_category(text: str) -> str:
    t = (text or "").lower()
    if any(x in t for x in ["口岸", "гааль", "border", "customs", "边境", "跨境"]):
        return "跨境毒情"
    if any(x in t for x in ["戒毒", "сэргээх", "rehab", "成瘾"]):
        return "戒毒康复"
    if any(x in t for x in ["unodc", "олон улсын", "国际"]):
        return "国际协作"
    if any(x in t for x in ["警察", "цагдаа", "баривчилгаа", "缉毒"]):
        return "执法行动"
    if any(x in t for x in ["芬太尼", "尼秦", "fentanyl", "nitazene", "合成"]):
        return "新型毒品"
    return "综合"


def intel_level(text: str) -> str:
    t = (text or "").lower()
    if any(x in t for x in ["吨", "公斤", "大规模", "芬太尼", "尼秦", "新法", "fentanyl", "nitazene"]):
        return "重要"
    return "一般"


def is_critical(text: str, extra: Optional[list] = None) -> bool:
    return intel_level(text) == "重要" or is_drug_related(text, extra=extra, loose=True)
