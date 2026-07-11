"""过滤层定稿：严格蒙古国判定 + 强毒品词入库 + 噪音永久拦截。

修改原因：此前弱词/俄边境兜底导致内蒙古、布里亚特、烟草等无关内容入库。
"""
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

# 【强管制毒品词】仅此类可触发涉毒入库
STRONG_DRUG_TERMS = [
    "芬太尼", "尼秦", "异托尼他秦", "安纳咖", "甲基苯丙胺", "冰毒", "海洛因", "大麻",
    "可卡因", "氯胺酮", "鸦片", "合成大麻素", "易制毒", "麻精药品",
    "毒品", "禁毒", "缉毒", "贩毒", "吸毒", "涉毒", "制毒",
    "хар тамхи", "мансууруулах", "фентанил", "нитазен", "метамфетамин",
    "fentanyl", "nitazene", "isotonitazene", "methamphetamine", "crystal meth",
    "heroin", "cannabis", "marijuana", "cocaine", "ketamine", "narcotic",
    "anti-drug", "antidrug", "drug trafficking", "illicit drug", "illegal drug",
]
# 【弱执法词】单独命中不入库，须与强毒品词同现
WEAK_DRUG_TERMS = [
    "seizure", "seized", "seize", "trafficking", "smuggling", "smuggled",
    "查获", "走私", "口岸", "跨境", "баривчилгаа", "хураан", "гааль", "хил",
]
# 【烟草/普通医药/赛事】永久拦截
HARD_EXCLUDE_PATTERNS = [
    r"\bhuman trafficking\b",
    r"weight[- ]?loss",
    r"\bdiet pills?\b",
    r"\bcigarettes?\b",
    r"\bcigarette\b",
    r"\btobacco\b",
    r"烟草",
    r"香烟",
    r"\bammunition\b",
    r"rounds of ammunition",
    r"mongolian bbq",
    r"\bhepatitis\b",
    r"\banti-corruption\b",
    r"奥运会",
    r"兴奋剂",
    r"\bwada\b",
    r"\bdoping\b",
    r"普通药品",
    r"medical care",
    r"处方药",
    r"\bprescription\b",
    # 俄边境/布里亚特/内蒙古噪音（无蒙古国锚点时由地域函数丢弃；此处强化烟草等）
    r"分裂主义",
    r"地缘政治对抗",
]
# 负面地域：出现且无蒙古国正锚点 → 丢弃
NEGATIVE_GEO_MARKERS = [
    r"内蒙古", r"\binner mongolia\b", r"өvөр\s*монгол", r"ovorkh",
    r"乌兰乌德", r"ulan[- ]?ude", r"улан[- ]?удэ",
    r"布里亚特", r"buryat", r"бурят",
    r"赤塔", r"\bchita\b", r"чита",
    r"恰克图", r"kyakhta", r"кяхта",
    r"后贝加尔", r"забайкал", r"zabaikal",
    # 修改原因：过滤纯中国境内禁毒宣传/国内案件资讯
    r"中国禁毒", r"全国禁毒", r"公安部禁毒", r"国家禁毒委",
    r"境内管控", r"省内禁毒", r"全市禁毒宣传", r"禁毒宣传月",
    r"呼和浩特", r"二连浩特", r"满洲里", r"包头市", r"锡林郭勒",
]
# 修改原因：蒙语官方机构词汇，无中文「蒙古国」也判定有效
MN_OFFICIAL_GEO_MARKERS = (
    "цагдаа", "гааль", "монгол улс", "улаанбаатар", "хил",
    "баривчилгаа", "гаалийн", "цагдаагийн", "улсын", "засгийн газар",
)
GOV_WEAK_DRUG_MARKERS = (
    "цагдаа", "гааль", "баривчилгаа", "хил", "хураан", "customs", "police",
    "seizure", "smuggling", "border", "口岸", "海关", "警察", "缉毒", "查获",
)
# 国内口岸弱词：无蒙古锚点不得单独入库
DOMESTIC_CN_PORT_MARKERS = (
    "二连浩特", "满洲里", "二连", "呼和浩特", "包头", "锡林郭勒", "呼伦贝尔",
)

NEGATIVE_PATTERNS = HARD_EXCLUDE_PATTERNS

# 谷歌检索统一负面排除语法（修改原因：检索层降噪）
SEARCH_NEGATIVE_EXCLUDE = (
    ' -"内蒙古" -"Inner Mongolia" -乌兰乌德 -布里亚特 -赤塔 -恰克图 -后贝加尔 '
    "-兴奋剂 -奥运会 -tobacco -cigarette -普通药品 -\"medical care\""
)


def content_hash(
    title: str,
    url: str,
    body: str = "",
    *,
    org_name: str = "",
    published: Optional[datetime] = None,
) -> str:
    """去重：归一化标题+正文前缀，同源多语种通稿易合并；URL 仅作辅键。"""
    # 修改原因：不同媒体同案重复入库 → 归一化标题合并
    norm_title = re.sub(r"\s+", "", (title or "").lower())
    norm_title = re.sub(r"[^\w\u4e00-\u9fffа-яөүА-ЯӨҮ]", "", norm_title)[:120]
    body_key = re.sub(r"\s+", "", (body or "")[:800].lower())
    pub = published.strftime("%Y-%m-%d") if published else ""
    raw = f"{norm_title}|{pub}|{body_key}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def detect_lang(text: str) -> str:
    if re.search(r"[\u4e00-\u9fff]", text or ""):
        return "zh"
    if re.search(r"[а-яөүА-ЯӨҮ]", text or ""):
        return "mn"
    return "en"


_translate_fail_streak = 0
# 修改原因：翻译结果缓存 30 天 TTL，减少重复调用
_translate_cache: dict = {}  # key -> (ts, text)
_TRANSLATE_CACHE_TTL_SEC = 30 * 24 * 3600


def translate_to_zh(
    text: str,
    lang: str = None,
    enabled: bool = True,
    source_lang: str = None,
) -> str:
    """翻译熔断：连续5次失败切本地替换；结果缓存30天。"""
    global _translate_fail_streak
    if not enabled or not text:
        return text or ""
    key = hashlib.sha256((text[:2000] + (lang or "")).encode("utf-8", errors="ignore")).hexdigest()
    now = datetime.utcnow().timestamp()
    hit = _translate_cache.get(key)
    if hit and now - hit[0] < _TRANSLATE_CACHE_TTL_SEC:
        return hit[1]
    # 熔断
    if _translate_fail_streak >= 5:
        return _local_gloss(text)
    try:
        from deep_translator import GoogleTranslator
        src = source_lang or lang or "auto"
        if src in ("zh", "zh-CN"):
            _translate_cache[key] = (now, text)
            return text
        out = GoogleTranslator(source=src if src != "auto" else "auto", target="zh-CN").translate(text[:4500]) or text
        _translate_fail_streak = 0
        _translate_cache[key] = (now, out)
        if len(_translate_cache) > 5000:
            # 淘汰过期项
            expired = [k for k, v in _translate_cache.items() if now - v[0] >= _TRANSLATE_CACHE_TTL_SEC]
            for k in expired:
                _translate_cache.pop(k, None)
            if len(_translate_cache) > 5000:
                _translate_cache.clear()
        return out
    except Exception:
        _translate_fail_streak += 1
        return _local_gloss(text)


def _local_gloss(text: str) -> str:
    # 修改原因：翻译熔断后保留蒙古官方机构蒙英词汇锚点，避免地域判定误删
    rep = [
        ("Mongolia", "蒙古国"), ("Ulaanbaatar", "乌兰巴托"), ("drug", "毒品"),
        ("narcotic", "麻醉品"), ("fentanyl", "芬太尼"), ("methamphetamine", "冰毒"),
        ("heroin", "海洛因"), ("cannabis", "大麻"),
        ("цагдаа", "警察"), ("гааль", "海关"), ("монгол улс", "蒙古国"),
        ("баривчилгаа", "查获"), ("хил", "边境"), ("мансууруулах", "禁毒"),
        ("хар тамхи", "毒品"), ("улаанбаатар", "乌兰巴托"),
        ("immigration", "移民"), ("customs", "海关"), ("police", "警察"),
    ]
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


def has_strong_drug_term(text: str) -> bool:
    blob = (text or "").lower()
    return any(s.lower() in blob for s in STRONG_DRUG_TERMS)


def has_mongolia_port_anchor(text: str) -> bool:
    """蒙古口岸/核心城市锚点（用于弱词快讯兼容）。"""
    tl = (text or "").lower()
    t = text or ""
    # 修改原因：国内口岸（二连浩特等）无蒙古锚点不得视为蒙古口岸
    has_domestic = any(x in t for x in DOMESTIC_CN_PORT_MARKERS)
    anchors = [
        r"扎门乌德", r"zamyn[- ]?uud", r"zamiin[- ]?uud",
        r"甘其毛都", r"gashuun", r"gashuunsukhait",
        r"乌兰巴托", r"ulaanbaatar", r"улаанбаатар",
        r"蒙古国", r"монгол\s*улс", r"\bmongolia\b",
        r"中蒙口岸", r"гааль", r"цагдаа", r"гаальын",
    ]
    has_mn = any(re.search(p, tl, re.I) for p in anchors)
    if has_domestic and not has_mn:
        return False
    return has_mn


def _china_domestic_control_ratio(text: str) -> float:
    """中国境内管控/宣传句子占比（修改原因：纯国内资讯过滤）。"""
    t = text or ""
    parts = [p.strip() for p in re.split(r"[。！？!?\n；;]+", t) if p and len(p.strip()) >= 8]
    if not parts:
        return 0.0
    cn_markers = (
        "中国禁毒", "全国禁毒", "公安部", "国家禁毒", "境内", "我省", "我市",
        "全区禁毒", "禁毒宣传", "打防管控", "净边行动", "清源行动",
        "呼和浩特", "二连浩特", "满洲里", "内蒙古公安",
    )
    hit = sum(1 for s in parts if any(m in s for m in cn_markers))
    return hit / max(len(parts), 1)


def _body_has_mongolia_substance(text: str) -> bool:
    """正文须含口岸/城市/官方机构锚点，仅标题挂蒙古国不算。"""
    t = text or ""
    markers = [
        "扎门乌德", "甘其毛都", "中蒙口岸", "乌兰巴托", "Ulaanbaatar", "улаанбаатар",
        "蒙古国", "Монгол", "монгол улс", "海关", "警察", "检察院",
        "gaаль", "цагдаа", "гааль", "customs", "police", "Zamyn", "Gashuun",
        "蒙通社", "montsame", "gogo.mn", "ikon.mn",
    ]
    return any(m.lower() in t.lower() for m in markers)


def _title_only_mongolia_hook(text: str) -> bool:
    """仅标题含蒙古国、正文无实质蒙古内容 → 应过滤。"""
    parts = (text or "").split("\n", 1)
    title = parts[0] if parts else text or ""
    body = parts[1] if len(parts) > 1 else text or ""
    if "蒙古国" in title and not _body_has_mongolia_substance(body):
        return True
    return False


def _negative_geo_sentence_ratio(text: str) -> float:
    """负面地域句子占比：主体大段写内蒙古/俄边境则偏高。"""
    t = text or ""
    parts = [p.strip() for p in re.split(r"[。！？!?\n；;]+", t) if p and len(p.strip()) >= 8]
    if not parts:
        return 0.0
    neg_n = 0
    for s in parts:
        sl = s.lower()
        if any(re.search(p, sl, re.I) for p in NEGATIVE_GEO_MARKERS):
            neg_n += 1
            continue
        if any(x in s for x in ("内蒙古", "布里亚特", "乌兰乌德", "赤塔", "恰克图", "后贝加尔")):
            neg_n += 1
    return neg_n / max(len(parts), 1)


def is_mongolia_country_related(text: str) -> bool:
    """严格蒙古国判定（原文 + 主体占比 + 标题党过滤）。

    修改原因：纯国内资讯/仅标题挂蒙古国/主体≥70%中国境内管控则丢弃。
    """
    t = text or ""
    tl = t.lower()
    # 修改原因：仅蒙语官方词汇（цагдаа/гааль/монгол улс）无中文也判定蒙古相关
    if any(m in tl for m in MN_OFFICIAL_GEO_MARKERS):
        return True
    # 修改原因：仅标题含蒙古国、正文无口岸/城市/机构 → 丢弃
    if _title_only_mongolia_hook(t):
        return False
    if "内蒙古" in t or re.search(r"\binner mongolia\b", tl):
        if "蒙古国" not in t and not re.search(r"монгол\s*улс|\bmongolia\b|扎门乌德|甘其毛都|ulaanbaatar", tl):
            return False
    positive = [
        r"蒙古国", r"монгол\s*улс", r"\bmongolia\b", r"\bmongolian\b",
        r"ulaanbaatar", r"улаанбаатар", r"乌兰巴托",
        r"扎门乌德", r"zamyn[- ]?uud", r"zamiin[- ]?uud",
        r"甘其毛都", r"gashuun", r"gashuunsukhait",
    ]
    has_pos = any(re.search(p, tl, re.I) for p in positive)
    has_neg = any(re.search(p, tl, re.I) for p in NEGATIVE_GEO_MARKERS) or any(
        x in t for x in ("内蒙古", "布里亚特", "乌兰乌德", "赤塔", "恰克图")
    )
    # 修改原因：正文95%+纯国内管控才过滤，中蒙混合资讯放行
    if _china_domestic_control_ratio(t) >= 0.95:
        pos_hits = sum(1 for p in positive if re.search(p, tl, re.I))
        if pos_hits <= 1:
            return False
    if _negative_geo_sentence_ratio(t) >= 0.70:
        pos_hits = sum(1 for p in positive if re.search(p, tl, re.I))
        if pos_hits <= 1:
            return False
    if has_neg and not has_pos:
        return False
    if has_pos:
        return True
    if re.search(r"(?<!өвөр\s)монгол", tl) and not re.search(r"өvөр|ovorkh|inner", tl):
        if re.search(r"монгол", tl) and re.search(r"улс|улаанбаатар|гааль|цагдаа", tl):
            return True
    return False


def is_unodc_mongolia_signal(text: str) -> bool:
    """UNODC：全球禁毒报告/统计资讯正常入库，无需蒙古国字样。"""
    t = (text or "").lower()
    if "unodc" in t or "united nations office on drugs" in t:
        return True
    return is_mongolia_country_related(text or "")


def _has_hard_exclude(blob: str) -> bool:
    low = (blob or "").lower()
    for pat in HARD_EXCLUDE_PATTERNS:
        if re.search(pat, low, re.I):
            return True
    for t in TOPIC_BLACKLIST:
        if len(t) >= 4 and t.lower() in low:
            return True
    return False


def is_drug_related(text: str, extra=None, loose: bool = False, gov_snapshot: bool = False) -> bool:
    """涉毒判定：强词必入；弱词+蒙古地理锚点即可入库，无需强毒品词。"""
    blob = (text or "").lower()
    if not blob.strip():
        return False
    if _has_hard_exclude(blob):
        return False
    extras = [str(x).lower() for x in (extra or []) if x]
    if has_strong_drug_term(blob) or (extras and any(e in blob for e in extras if len(e) >= 3)):
        return True
    if any(x in (text or "") for x in DOMESTIC_CN_PORT_MARKERS) and not has_mongolia_port_anchor(text or ""):
        return False
    weak_terms = list(WEAK_DRUG_TERMS)
    if gov_snapshot:
        weak_terms = list(dict.fromkeys([*weak_terms, *GOV_WEAK_DRUG_MARKERS]))
    weak = any(w.lower() in blob for w in weak_terms)
    # 修改原因：废除弱词必须搭配强毒品词；口岸/查获弱词+蒙古锚点直接入库
    if weak and has_mongolia_port_anchor(blob):
        return True
    return False


def title_has_strong_drug(title: str) -> bool:
    """标题前置过滤：强毒品词，或弱词+蒙古口岸锚点。"""
    tt = title or ""
    if has_strong_drug_term(tt):
        return True
    return any(w.lower() in tt.lower() for w in WEAK_DRUG_TERMS) and has_mongolia_port_anchor(tt)


def credibility_label(org_name: str = "", system_id: int = 0, url: str = "") -> str:
    """可信度：官方高 / 地方媒体中 / 论坛低。"""
    o = (org_name or "").lower()
    u = (url or "").lower()
    blob = o + u
    # 修改原因：无蒙古锚点的 UNODC 全球报告标低可信仍入库
    if "unodc" in blob:
        if not any(x in blob for x in ("mongolia", "mongol", "蒙古", "монгол")):
            return "低"
        return "高"
    if system_id in (7, 9) or any(x in o for x in ("蒙通社", "montsame", "incb", "nncc", "禁毒网")):
        return "高"
    if system_id == 11 or any(x in o + u for x in ("reddit", "论坛", "zhihu", "贴吧", "bluelight", "forum")):
        return "低"
    return "中"


def alert_category(text: str) -> str:
    """告警细分：口岸大宗 / 新型毒品 / 跨境联合 / 禁毒新法。"""
    t = (text or "").lower()
    if any(x in t for x in ("新法", "列管", "立法", "law", "amendment")):
        return "禁毒新法"
    if any(x in t for x in ("芬太尼", "尼秦", "fentanyl", "nitazene", "nps", "合成")):
        return "芬太尼/尼秦新型毒品"
    if any(x in t for x in ("联合行动", "interpol", "csto", "跨境协作", "joint operation")):
        return "跨境联合行动"
    if any(x in t for x in ("口岸", "吨", "公斤", "大宗", "扎门", "甘其毛都", "customs", "seizure")):
        return "口岸大宗"
    return "综合告警"


def port_tag_from_text(text: str) -> str:
    """修改原因：分口岸趋势统计标签。"""
    t = (text or "").lower()
    if any(x in t for x in ("扎门乌德", "zamyn", "zamiin")):
        return "扎门乌德"
    if any(x in t for x in ("甘其毛都", "gashuun", "gashuunsukhait")):
        return "甘其毛都"
    if any(x in t for x in ("俄蒙", "俄蒙边境", "mongolia-russia", "хил")):
        return "俄蒙边境"
    if any(x in t for x in ("口岸", "customs", "гааль", "border")):
        return "其他口岸"
    return ""


def drug_type_from_text(text: str) -> str:
    """修改原因：毒品类型索引字段。"""
    t = (text or "").lower()
    if any(x in t for x in ("芬太尼", "fentanyl")):
        return "芬太尼"
    if any(x in t for x in ("尼秦", "nitazene")):
        return "尼秦"
    if any(x in t for x in ("甲基苯丙胺", "冰毒", "meth")):
        return "冰毒"
    if any(x in t for x in ("海洛因", "heroin")):
        return "海洛因"
    if any(x in t for x in ("大麻", "cannabis", "marijuana")):
        return "大麻"
    if any(x in t for x in ("安纳咖", "ephedrine")):
        return "安纳咖"
    if has_strong_drug_term(t):
        return "其他管制品"
    return ""


def sanitize_sensitive_text(text: str, hide_details: bool = False) -> str:
    """敏感叙事与涉密细节清洗（报告/邮件双重使用）。"""
    t = text or ""
    # 分裂/地缘负面粗过滤
    for pat in (r"分裂[^。\n]{0,20}", r"地缘政治对抗[^。\n]{0,30}"):
        t = re.sub(pat, "【已屏蔽】", t)
    if hide_details:
        t = re.sub(r"\d+(?:\.\d+)?\s*(?:公斤|千克|吨|kg|kilogram)", "【数量已隐藏】", t, flags=re.I)
        t = re.sub(r"(芬太尼|尼秦|fentanyl|nitazene)[^。\n]{0,40}", r"\1【细节已隐藏】", t, flags=re.I)
    return t


def is_allowed_url(url: str, extra_domains: Optional[list] = None) -> bool:
    # 修改原因：仅拦原生 gov.mn 直链；快照/媒体域名放行
    if is_forbidden_url(url):
        return False
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
    if host.endswith("unodc.org") or host.endswith("news.google.com") or "google.com" in host:
        return True
    if ALLOW_ANY_MN_DOMAIN and host.endswith(".mn") and not host.endswith(".gov.mn"):
        return True
    if ALLOW_GLOBAL_MEDIA:
        for suf in (
            "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk",
            "xinhuanet.com", "news.cn", "cgtn.com", "akipress.com",
            "tass.com", "ria.ru", "montsame.mn", "gogo.mn", "ikon.mn",
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
    if any(x in t for x in ["口岸", "гааль", "border", "customs", "边境", "跨境", "扎门", "甘其毛都"]):
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
