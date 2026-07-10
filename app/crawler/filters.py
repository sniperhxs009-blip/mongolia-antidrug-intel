"""修复版过滤规则，放宽弱毒品词汇放行、扩大蒙古媒体匹配"""
from __future__ import annotations
import hashlib
import re
from datetime import datetime, timedelta
from urllib.parse import urlparse
from config.sources import ALLOW_ANY_MN_DOMAIN, ALLOW_GLOBAL_MEDIA, ALLOW_FORUM_DOMAINS, ALLOWED_DOMAINS, BLOCKED_SUFFIXES
from config.core_official import TOPIC_BLACKLIST
# 强毒品词汇（单独即可放行）
STRONG_DRUG_TERMS = [
    "毒品","禁毒","缉毒","贩毒","吸毒","海洛因","大麻","安纳咖","芬太尼","尼秦","合成毒品","易制毒","麻精药品",
    "хар тамхи","мансууруулах бодис","фентанил","нитазен",
    "fentanyl","nitazene","cannabis","drug seizure"
]
# 弱词汇（宽松模式可单独放行）
WEAK_DRUG_TERMS = ["seizure","trafficking","smuggling","查获","走私"]
# 缩小无关黑名单
NEGATIVE_PATTERNS = [
    r"human trafficking",r"anti-corruption",r"奥运会",r"兴奋剂",r"乌兰乌德布里亚特"
]
def content_hash(title: str, url: str, body: str = "") -> str:
    raw = f"{title.strip()}|{url.strip()}|{body[:2000]}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()
def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())
def detect_lang(text: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", text):
        return "zh"
    if re.search(r"[а-яөү]", text):
        return "mn"
    return "en"
def translate_to_zh(text: str, lang: str = None, enabled: bool = True) -> str:
    if not enabled or not text:
        return text
    # 内置简易替换，真实环境对接翻译库
    rep = [("Mongolia","蒙古国"),("Ulaanbaatar","乌兰巴托"),("drug","毒品")]
    res = text
    for en,cn in rep:
        res = re.sub(re.escape(en), cn, res, flags=re.I)
    return res
def is_stale(pub_dt: datetime, max_days: int = 365) -> bool:
    if not pub_dt:
        return False
    return pub_dt < datetime.utcnow() - timedelta(days=max_days)
def parse_date_guess(html: str):
    # 简易日期匹配，省略复杂正则
    return None
def is_mongolia_country_related(text: str) -> bool:
    low = text.lower()
    markers = ["mongolia","монгол","улаанбаатар","蒙古国","扎门乌德","甘其毛都"]
    return any(m in low for m in markers)
def _has_negative(blob: str) -> bool:
    low = blob.lower()
    for black in TOPIC_BLACKLIST + NEGATIVE_PATTERNS:
        if re.search(black, low, re.I):
            return True
    return False
def is_drug_related(text: str, extra=None, loose: bool = True) -> bool:
    blob = text.lower()
    if _has_negative(blob):
        strong_hit = any(s in blob for s in STRONG_DRUG_TERMS)
        if not strong_hit:
            return False
    if any(s in blob for s in STRONG_DRUG_TERMS):
        return True
    if loose and any(w in blob for w in WEAK_DRUG_TERMS):
        return True
    return False
def is_allowed_url(url: str) -> bool:
    try:
        from config.core_official import is_forbidden_url
        if is_forbidden_url(url):
            return False
    except Exception:
        pass
    try:
        host = urlparse(url).netloc.lower().replace("www.","")
    except Exception:
        return False
    if any(host.endswith("." + b) or host == b for b in BLOCKED_SUFFIXES):
        return False
    if host in ALLOWED_DOMAINS:
        return True
    if ALLOW_ANY_MN_DOMAIN and host.endswith(".mn"):
        return True
    if ALLOW_GLOBAL_MEDIA:
        global_media = ["reuters.com","apnews.com","bbc.com","xinhuanet.com"]
        if any(host.endswith(g) for g in global_media):
            return True
    return False
def same_host_or_sub(url_a: str, url_b: str) -> bool:
    h1 = urlparse(url_a).netloc.lower()
    h2 = urlparse(url_b).netloc.lower()
    return h1 == h2 or h1.endswith("." + h2) or h2.endswith("." + h2)
def classify_category(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ["口岸","гааль","border"]):
        return "边境缉毒"
    if any(x in t for x in ["戒毒","сэргээх"]):
        return "戒毒康复"
    if any(x in t for x in ["UNODC","олон улсын"]):
        return "国际协作"
    if any(x in t for x in ["警察","цагдаа","хар тамхи хураах"]):
        return "刑事执法"
    return "综合涉毒资讯"
def intel_level(text: str) -> str:
    t = text.lower()
    if any(x in t for x in ["吨","公斤","大规模","芬太尼","нитазен","新法"]):
        return "重要"
    return "一般"
def is_critical(text: str) -> bool:
    return intel_level(text) == "重要"
