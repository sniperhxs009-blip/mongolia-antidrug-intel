"""过滤规则优化：正文强词可入库；弱化标题强制；精准蒙古国匹配；无日期不直接丢弃。

【本次全链路增产修复】
缺陷：UNODC 过严、短讯误删、布里亚特/俄边境误删、gov.mn 快照无法入库、去重过激。
修改：UNODC 分栏信号放宽；俄边境城市列表；≥100字快讯保留；content_hash 含机构+日期；
      负面词完整匹配；is_allowed_url 放行谷歌快照；统一 loose 判定入口。
"""
from __future__ import annotations

import hashlib
import re
from datetime import datetime, timedelta
from typing import Optional
from urllib.parse import urlparse

from config.core_official import (
    TOPIC_BLACKLIST,
    is_forbidden_url,
    is_google_snapshot_or_news_url,
)
from config.sources import (
    ALLOW_ANY_MN_DOMAIN,
    ALLOW_GLOBAL_MEDIA,
    ALLOWED_DOMAINS,
    BLOCKED_SUFFIXES,
)

STRONG_DRUG_TERMS = [
    "毒品", "禁毒", "缉毒", "贩毒", "吸毒", "涉毒", "制毒", "运毒", "戒毒",
    "海洛因", "大麻", "安纳咖", "芬太尼", "尼秦", "异托尼他秦", "合成大麻素",
    "易制毒", "麻精药品", "冰毒", "氯胺酮", "可卡因", "鸦片",
    "хар тамхи", "мансууруулах", "фентанил", "нитазен", "метамфетамин",
    "fentanyl", "nitazene", "cannabis", "narcotic", "methamphetamine",
    "heroin", "cocaine", "ketamine", "drug seizure", "anti-drug", "antidrug",
]
WEAK_DRUG_TERMS = [
    "seizure", "seized", "seize", "trafficking", "smuggling", "smuggled", "smuggler", "smuggle",
    "查获", "走私", "口岸", "跨境", "баривчилгаа", "хураан", "гааль", "хил",
]
STRONG_DRUG_EXTRA = [
    "drug smuggl", "drug bust", "drug traffick", "illegal drug", "illicit drug",
    "anti-drug", "antidrug", "narcotics",
]
HARD_EXCLUDE_PATTERNS = [
    r"\bhuman trafficking\b",
    r"weight[- ]?loss",
    r"\bdiet pills?\b",
    r"\bcigarettes?\b",
    r"\bammunition\b",
    r"rounds of ammunition",
    r"mongolian bbq",
    r"\bhepatitis\b",
    r"\banti-corruption\b",
    r"奥运会",
    r"兴奋剂\s*wada",
    r"\bwada\b.*(?:doping|兴奋剂|athlete)",
]
BURYAT_MARKERS = [
    r"buryat", r"бурят", r"ulan[- ]?ude", r"улан[- ]?удэ", r"乌兰乌德", r"布里亚特",
]
RU_BORDER_MARKERS = [
    r"\bchita\b", r"чита", r"kyakhta", r"кяхта", r"забайкал", r"zabaikal",
    r"后贝加尔", r"恰克图", r"赤塔", r"манчжур", r"manzhouli",
]
NEGATIVE_PATTERNS = HARD_EXCLUDE_PATTERNS + [r"奥运会"]


def content_hash(
    title: str,
    url: str,
    body: str = "",
    *,
    org_name: str = "",
    published: Optional[datetime] = None,
) -> str:
    pub = published.strftime("%Y-%m-%d") if published else ""
    org = (org_name or "").strip()
    raw = f"{org}|{pub}|{title.strip()}|{url.strip()}|{body[:2000]}".encode("utf-8", errors="ignore")
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
    try:
        from deep_translator import GoogleTranslator
        src = source_lang or lang or "auto"
        if src in ("zh", "zh-CN"):
            return text
        return GoogleTranslator(source=src if src != "auto" else "auto", target="zh-CN").translate(text[:4500]) or text
    except Exception:
        rep = [("Mongolia", "蒙古国"), ("Ulaanbaatar", "乌兰巴托"), ("drug", "毒品"), ("narcotic", "麻醉品")]
        res = text
        for en, cn in rep:
            res = re.sub(re.escape(en), cn, res, flags=re.I)
        return res


def is_stale(pub_dt: Optional[datetime], max_days: int = 365) -> bool:
    if not pub_dt:
        return False
    try:
        return pub_dt < datetime.utcnow() - timedelta(days=max_days)
    except Exception:
        return False


def parse_date_guess(html: str) -> Optional[datetime]:
    if not html:
        return None
    m = re.search(r"(20\d{2})[-/.年](\d{1,2})[-/.月](\d{1,2})", html[:8000])
    if not m:
        return None
    try:
        return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except Exception:
        return None


def is_mongolia_country_related(text: str) -> bool:
    t = text or ""
    tl = t.lower()
    if "内蒙古" in t and "蒙古国" not in t:
        if not any(x in t for x in ("中蒙", "扎门乌德", "甘其毛都", "二连", "口岸缉毒")):
            return False
    if re.search(r"\binner mongolia\b", tl):
        return False
    if any(re.search(p, tl, re.I) for p in BURYAT_MARKERS):
        if not re.search(
            r"улаанбаатар|ulaanbaatar|蒙古国|монгол\s*улс|mongolia\s+(police|customs)|中蒙",
            tl, re.I,
        ):
            if not any(s.lower() in tl for s in STRONG_DRUG_TERMS + STRONG_DRUG_EXTRA):
                return False
    markers = [
        "mongolia", "mongolian", "улаанбаатар", "ulaanbaatar", "монгол улс",
        "蒙古国", "乌兰巴托", "扎门乌德", "甘其毛都", "二连浩特",
        "中蒙口岸", "中蒙边境", "中蒙", "zamyn-uud", "gashuun", "erenhot",
        "chita", "чита", "kyakhta", "кяхта", "赤塔", "恰克图", "后贝加尔", "zabaikal",
    ]
    if any(m in tl for m in markers) or "蒙古国" in t:
        return True
    if re.search(r"(?<!内)蒙古", t):
        return True
    return False


def is_unodc_mongolia_signal(text: str) -> bool:
    t = text or ""
    tl = t.lower()
    if is_mongolia_country_related(t):
        return True
    if re.search(r"\bmongolia\b|\bmng\b|монгол", tl) and re.search(
        r"seizure|narcotic|drug|traffick|cannabis|meth|opioid|мансууруулах|毒品", tl,
    ):
        return True
    if re.search(r"country\s*(profile|report|data).*mongolia|mongolia.*country\s*(profile|report)", tl):
        return True
    if re.search(r"east(ern)?\s*asia.*mongolia|mongolia.*east(ern)?\s*asia", tl):
        return True
    return False


def _has_hard_exclude(blob: str) -> bool:
    low = (blob or "").lower()
    for pat in HARD_EXCLUDE_PATTERNS:
        if re.search(pat, low, re.I):
            return True
    for t in TOPIC_BLACKLIST:
        if len(t) >= 4 and t.lower() in low:
            return True
    return False


def _has_negative(blob: str) -> bool:
    if _has_hard_exclude(blob):
        return True
    low = (blob or "").lower()
    if any(re.search(p, low, re.I) for p in BURYAT_MARKERS + RU_BORDER_MARKERS):
        if not any(s.lower() in low for s in STRONG_DRUG_TERMS + STRONG_DRUG_EXTRA):
            return True
    return False


def is_drug_related(text: str, extra=None, loose: bool = True) -> bool:
    blob = (text or "").lower()
    if not blob.strip():
        return False
    if _has_hard_exclude(blob):
        return False
    extras = [str(x).lower() for x in (extra or []) if x]
    if any(s.lower() in blob for s in STRONG_DRUG_TERMS):
        return True
    if any(s.lower() in blob for s in STRONG_DRUG_EXTRA):
        return True
    if extras and any(e in blob for e in extras):
        return True
    if any(w.lower() in blob for w in WEAK_DRUG_TERMS):
        if _has_negative(blob) and not any(s.lower() in blob for s in STRONG_DRUG_TERMS + STRONG_DRUG_EXTRA):
            return False
        return True
    return False


def is_allowed_url(url: str, extra_domains: Optional[list] = None) -> bool:
    try:
        if is_google_snapshot_or_news_url(url):
            return True
        if is_forbidden_url(url):
            return False
    except Exception:
        pass
    try:
        host = urlparse(url).netloc.lower().split(":")[0]
    except Exception:
        return False
    if not host:
        return False
    host_bare = host.replace("www.", "")
    if any(host_bare == b or host.endswith("." + b) for b in BLOCKED_SUFFIXES):
        return False
    allow = set(ALLOWED_DOMAINS)
    if extra_domains:
        allow.update(extra_domains)
    for d in allow:
        base = d.replace("www.", "")
        if host == d or host_bare == base or host.endswith("." + base):
            return True
    if host.endswith("unodc.org") or host.endswith("news.google.com"):
        return True
    if ALLOW_ANY_MN_DOMAIN and host.endswith(".mn") and not host.endswith(".gov.mn"):
        return True
    if ALLOW_GLOBAL_MEDIA:
        for suf in (
            "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk",
            "xinhuanet.com", "news.cn", "cgtn.com", "akipress.com",
            "tass.com", "ria.ru",
        ):
            if host_bare == suf or host.endswith("." + suf):
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
    if any(x in t for x in ["口岸", "гааль", "border", "customs", "边境", "跨境", "扎门", "甘其毛都", "赤塔", "恰克图"]):
        return "跨境毒情"
    if any(x in t for x in ["戒毒", "сэргээх", "rehab", "成瘾", "青少年"]):
        return "戒毒康复"
    if any(x in t for x in ["unodc", "олон улсын", "国际", "reddit", "论坛"]):
        return "国际协作"
    if any(x in t for x in ["统计", "同比", "pdf", "статистик", "案件数"]):
        return "官方统计"
    if any(x in t for x in ["警察", "цагдаа", "баривчилгаа", "缉毒", "查获"]):
        return "执法行动"
    if any(x in t for x in ["芬太尼", "尼秦", "fentanyl", "nitazene", "合成", "nps", "安纳咖"]):
        return "新型毒品"
    return "综合"


def intel_level(text: str) -> str:
    t = (text or "").lower()
    if any(x in t for x in ["吨", "公斤", "大规模", "芬太尼", "尼秦", "新法", "fentanyl", "nitazene", "专项"]):
        return "重要"
    return "一般"


def is_critical(text: str, extra: Optional[list] = None) -> bool:
    return intel_level(text) == "重要"
