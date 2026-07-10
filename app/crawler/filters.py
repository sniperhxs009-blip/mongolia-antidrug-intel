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

BLOCKED_SUFFIXES = (
    "facebook.com", "twitter.com", "x.com", "instagram.com", "tiktok.com",
    "youtube.com", "linkedin.com", "wikipedia.org", "pinterest.com",
)

# 强涉毒词：单独出现即可认定（排除过于宽泛的 drug/trafficking）
STRONG_DRUG_TERMS = [
    # 中文
    "毒品", "禁毒", "缉毒", "贩毒", "吸毒", "涉毒", "制毒", "运毒", "戒毒",
    "海洛因", "可卡因", "冰毒", "冰块", "大麻", "黑烟草", "哈希什", "鸦片", "罂粟",
    "安纳咖", "苯甲酸钠咖啡因", "曲马多", "羟考酮", "可待因",
    "芬太尼", "尼秦", "异托尼他秦", "甲托尼他秦", "奥芬", "氯胺酮",
    "合成大麻素", "香料毒", "裸盖菇素", "迷幻蘑菇", "卡西酮", "浴盐",
    "快乐水", "派对毒品", "液态新型精神药物", "情绪舒缓液",
    "安定", "阿普唑仑", "苯二氮卓",
    "摇头丸", "K粉", "麻古", "易制毒", "麻精药品", "合成毒品", "新型毒品",
    "毒枭", "毒贩", "查获毒品", "走私毒品",
    # 蒙语
    "мансууруулах", "хар тамхи", "наркотик", "героин", "кокаин", "каннабис",
    "метамфетамин", "амфетамин", "кетамин", "фентанил", "экстази", "прекурсор",
    "донтсон", "марихуан", "гашиш", "опиум", "нитазен", "изотонитазен",
    "трамадол", "псилоцибин", "катинон",
    "мансууруулах бодис", "тэмцэх хар тамхи", "сэргээх төв",
    "синтетик мансууруулах бодис", "газар хил худалдаа",
    # 英语强词
    "narcotic", "narcotics", "heroin", "cocaine", "methamphetamine", "meth ",
    " cannabis", "marijuana", "hashish", "fentanyl", "ketamine", "mdma",
    "ecstasy", "opium", "opioid", "precursor", "anti-drug", "antidrug",
    "drug bust", "drug raid", "drug smugg", "drug traffick", "drug seizure",
    "seized drug", "illegal drug", "illicit drug", "controlled substance",
    "synthetic cannabinoid", "synthetic cannabis", "cross-border trafficking",
    "drug rehabilitation", "unodc mongolia",
    "nitazene", "isotonitazene", "metonitazene",
    "xylazine", "bath salt", "psilocybin", "tramadol", "oxycodone",
    "hhc", "delta-8", "mdpv", "annaka", "caffeine sodium benzoate",
    "psychotropic",
]

# 弱词：必须与强语境组合，不能单独入库
WEAK_DRUG_TERMS = [
    "drug", "drugs", "trafficking", "trafficker", "smuggling", "smuggler",
    "seizure", "seized", "addiction", "addict", "rehab", "rehabilitation",
    "overdose", "баривчилгаа", "хураан авсан",
]

# 明确排除：香烟/弹药/减肥药/人口贩运/医药/餐饮/文体等（非毒品）
NEGATIVE_PATTERNS = [
    r"\bmongolia\s*grill\b",
    r"\bmongolian\s*bbq\b",
    r"\bmongolian\s*barbecue\b",
    r"\bmongolian\s*beef\b",
    r"\brestaurant\b",
    r"\bdining\b",
    r"\bmenu\b",
    r"\bbbq\b",
    r"\bbarbecue\b",
    r"\bolympic",
    r"\bgold\s*medal\b",
    r"\bpainting\b",
    r"\bcaravaggio\b",
    r"\bart\s*exhibit",
    r"\bmuseum\b",
    r"\bhepatitis\b",
    r"\bpharma",
    r"\bmedicine\b",
    r"\bmedication\b",
    r"\bvaccine\b",
    r"\btreatment\s+for\b",
    r"human\s+traffick",
    r"sex\s+traffick",
    r"people\s+traffick",
    r"illegal\s+trafficking\s+of\s+people",
    r"anti[- ]?corruption",
    r"orphanage",
    r"asset\s+recover",
    r"low[- ]priced\s+stock",
    r"stock\s+market",
    r"coal\s+mine",
    r"煤矿",
    r"低价股",
    r"股票",
    r"股市",
    r"financial\s+post",
    r"rape\b",
    # 香烟 / 烟草（非毒品）
    r"\bcigarette",
    r"\btobacco\b",
    r"\bsmokes?\b",
    r"сигарет",
    r"табак",
    r"香烟",
    r"卷烟",
    r"烟草",
    # 普通烟草（排除 хар тамхи 毒品义）
    r"(?<!хар )тамхи",
    r"(?<!хар\u00a0)тамхи",
    # 弹药 / 武器走私
    r"\bammunition\b",
    r"\bammo\b",
    r"\bcartridge",
    r"патрон",
    r"боеприпас",
    r"弹药",
    r"子弹",
    # 减肥药 / 普通药品走私
    r"weight[- ]?loss",
    r"diet\s+pill",
    r"slim(ming)?\s+pill",
    r"减肥药",
    r"похуден",
    # 人口贩运 / 无关社会
    r"人口贩运",
    r"拐卖",
    r"反腐败",
    r"unesco",
    r"kindergarten",
    r"early\s+screening",
    r"preventive\s+check",
    r"abortion",
    r"pregnancy\s+aid",
    r"奥运会",
    r"金牌",
    r"烤肉",
    r"餐厅",
    r"画作",
    r"肝炎",
    r"药品免税",
    r"хүн\s*худалдах",
    # 非毒品「查获/走私」噪声：化石、恐龙、土拨鼠鼠疫、雪豹皮、游艇
    r"\bfossil\b",
    r"\bdinosaur\b",
    r"\btyrannosaur",
    r"恐龙",
    r"化石",
    r"\bmarmot\b",
    r"土拨鼠",
    r"\bplague\b",
    r"鼠疫",
    r"\bsnow\s*leopard\b",
    r"雪豹",
    r"\bluxury\s+good",
    r"奢侈品",
    r"\byacht\b",
    r"游艇",
    # 俄罗斯布里亚特/乌兰乌德本地案（非蒙古国）
    r"улан[- ]?удэ",
    r"ulan[- ]?ude",
    r"buryat",
    r"бурят",
    r"乌兰乌德",
    r"布里亚特",
    # 体育兴奋剂 / 非管制医药噪声（文档要求剔除）
    r"\bdoping\b",
    r"\bwada\b",
    r"\banti[- ]?doping\b",
    r"兴奋剂",
    r"反兴奋剂",
    r"\bsteroide?s?\b",
    r"анаболик",
    r"допинг",
    r"军事演习",
    r"联合军演",
    r"military\s+exercise",
    r"joint\s+exercise",
    r"版画",
    r"画展",
    r"exhibition",
    r"printmaking",
    r"马背射箭",
    r"世界马日",
    r"horse\s+archery",
    r"股市",
    r"股票",
    r"stock\s+market",
    r"暴跌",
    r"地震",
    r"earthquake",
    r"委内瑞拉",
    r"venezuela",
    r"anti[- ]?corruption",
    r"煤炭盗窃",
    r"资源盗窃",
    r"railway",
    r"data\s+center",
    r"数字化转型",
    r"зохицуулах\s+хороо",  # 泛「监管委员会」含金融监管，勿当禁毒词
    r"санхүүгийн\s+зохицуулах",  # 金融监管委员会
    r"strategic\s+plan",
    r"стратеги\s+төлөвлөгөө",
]


def content_hash(title: str, url: str, body: str = "") -> str:
    raw = f"{title.strip()}|{url.strip()}|{body[:2000].strip()}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()


def normalize_text(text: str) -> str:
    text = text or ""
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_allowed_url(url: str, extra_domains: Optional[list] = None) -> bool:
    try:
        from config.core_official import is_forbidden_url

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
    # 国际主流媒体 / 禁毒机构常见后缀放行（已在 GLOBAL_ALLOWED_DOMAINS 白名单为主）
    intl_suffixes = (
        "reuters.com", "apnews.com", "bbc.com", "bbc.co.uk", "theguardian.com",
        "cnn.com", "aljazeera.com", "thediplomat.com", "rfa.org", "voanews.com",
        "scmp.com", "nikkei.com", "news.cn", "xinhuanet.com", "cgtn.com",
        "tass.com", "ria.ru", "akipress.com", "vice.com", "bloomberg.com",
        "nytimes.com", "washingtonpost.com", "wsj.com", "ft.com", "dw.com",
        "incb.org", "who.int", "wcoomd.org", "interpol.int", "state.gov",
        "dea.gov", "euda.europa.eu", "emcdda.europa.eu", "ocindex.net",
        "eurasianet.org", "france24.com", "japantimes.co.jp", "yna.co.kr",
        "reddit.com", "quora.com", "zhihu.com", "tieba.baidu.com",
        "bluelight.org", "drugs-forum.com", "medium.com", "substack.com",
        "news.ycombinator.com", "duckduckgo.com", "bing.com",
    )
    for suf in intl_suffixes:
        if host == suf or host.endswith("." + suf):
            return True
    if ALLOW_ANY_MN_DOMAIN and host.endswith(".mn"):
        return True
    return False


def _has_negative(blob: str) -> bool:
    try:
        from config.core_official import TOPIC_BLACKLIST

        low = blob.lower()
        for t in TOPIC_BLACKLIST:
            if t.lower() in low:
                return True
    except Exception:
        pass
    for pat in NEGATIVE_PATTERNS:
        if re.search(pat, blob, flags=re.IGNORECASE):
            return True
    return False


def is_drug_related(text: str, extra_keywords: Optional[list] = None, loose: bool = False) -> bool:
    """严格涉毒判定：强词命中，或弱词+强语境；并排除医药/人口贩运/餐饮等。"""
    blob = (text or "").lower()
    if not blob:
        return False

    # 先排除明显无关
    if _has_negative(blob):
        # 若同时有非常明确的毒品强词，仍可放行（如“毒贩在餐厅落网”）
        strong_override = any(
            k in blob
            for k in [
                "наркотик", "мансууруулах", "хар тамхи", "heroin", "cocaine",
                "methamphetamine", "fentanyl", "ketamine", "毒品", "毒贩", "缉毒",
                "illegal drug", "illicit drug", "drug smugg", "drug traffick",
            ]
        )
        if not strong_override:
            return False

    # 1) 强词
    for kw in STRONG_DRUG_TERMS:
        if kw.lower().strip() in blob:
            return True

    # 2) 词库中的具体品名（跳过过于宽泛的执法/走私通用词）
    skip_broad = {
        "drug", "drugs", "trafficking", "trafficker", "smuggling", "smuggler",
        "seizure", "seized", "addiction", "addict", "rehab", "rehabilitation",
        "overdose", "контрабанда", "контрабанд", "баривчилгаа", "хураан авсан",
        "цагдаа", "гааль", "гэмт хэрэг", "урьдчилан сэргийлэх", "нөхөн сэргээх",
        "эмчилгээ", "хилээр нэвтрүүлэх", "донтсон", "донтлох", "донтлол",
        "зохицуулалттай эм", "тамхины бодис",
        # 极宽词：军演/反腐/海关日常/联合国首页都会误伤
        "тэмцэх", "газар хил", "хилээр", "зохицуулах", "сэргээх төв",
        "mongolia", "unodc", "united nations", "联合国",
    }
    keys = list(DRUG_KEYWORDS)
    if extra_keywords:
        keys.extend(extra_keywords)
    for kw in sorted(set(keys), key=len, reverse=True):
        k = kw.lower().strip()
        if not k or k in skip_broad or len(k) < 4:
            continue
        if k in blob:
            return True

    # 3) 弱词必须搭配明确毒品语境
    has_weak = any(w in blob for w in WEAK_DRUG_TERMS)
    narcotic_context = any(
        x in blob
        for x in [
            "narcotic", "heroin", "cocaine", "methamphetamine", "cannabis", "marijuana",
            "opium", "fentanyl", "ketamine", "мансууруулах", "хар тамхи",
            "наркотик", "毒品", "毒贩", "缉毒", "illegal drug", "illicit drug",
            "drug traffick", "drug smugg",
        ]
    )
    if has_weak and narcotic_context:
        return True

    # loose 不再用“警察+抓捕”这种过宽组合
    if loose:
        return False
    return False


def is_critical(text: str, extra: Optional[list] = None) -> bool:
    blob = (text or "").lower()
    if not is_drug_related(blob):
        return False
    keys = list(CRITICAL_KEYWORDS)
    if extra:
        keys.extend(extra)
    for kw in keys:
        if kw.lower() in blob:
            return True
    return False


def is_mongolia_country_related(text: str) -> bool:
    """判定是否指向蒙古国（排除内蒙古、乌兰乌德/布里亚特等）。"""
    t = text or ""
    tl = t.lower()
    if "内蒙古" in t and "蒙古国" not in t:
        if not any(x in t for x in ("中蒙", "扎门", "甘其毛都", "二连", "口岸缉毒")):
            return False
    if re.search(r"\binner mongolia\b", tl):
        return False
    # 俄罗斯乌兰乌德 / 布里亚特本地新闻
    if re.search(
        r"улан[- ]?удэ|ulan[- ]?ude|buryat|бурят|乌兰乌德|布里亚特",
        tl,
        flags=re.I,
    ):
        if not re.search(
            r"улаанбаатар|ulaanbaatar|蒙古国|монгол\s*улс|mongolia\s+police|mongolia\s+customs",
            tl,
            flags=re.I,
        ):
            return False
    markers = [
        "mongolia", "mongolian", "улаанбаатар", "ulaanbaatar",
        "монгол улс", "蒙古国", "乌兰巴托",
        "扎门乌德", "甘其毛都", "二连浩特", "中蒙口岸", "中蒙边境",
        "zamyn-uud", "gashuun", "erenhot",
    ]
    if any(m in tl for m in markers) or "蒙古国" in t:
        return True
    if re.search(r"(?<!内)蒙古", t):
        return True
    if "内蒙古" in t and any(x in t for x in ("蒙古国", "中蒙", "扎门", "甘其毛都", "二连")):
        return True
    # 单独「монгол」过宽，需搭配毒品语境
    if "монгол" in tl and re.search(
        r"мансууруулах|хар\s*тамхи|наркотик|метамфетамин|фентанил|героин",
        tl,
        flags=re.I,
    ):
        return True
    return False


def classify_category(text: str) -> str:
    t = (text or "").lower()
    if not is_drug_related(t, loose=False):
        return "综合"
    rules = [
        ("跨境毒情", ["跨境贩毒", "口岸缉毒", "边境走私", "drug traffick", "drug smugg"]),
        ("新型毒品", ["合成毒品", "芬太尼", "冰毒", "synthetic cannabinoid", "methamphetamine", "fentanyl", "метамфетамин", "нитазен"]),
        ("制毒原料", ["易制毒", "麻精", "precursor", "прекурсор", "controlled substance"]),
        ("戒毒康复", ["戒毒", "康复", "成瘾", "нөхөн сэргээх", "донтсон", "rehab"]),
        ("国际协作", ["UNODC", "国际禁毒", "anti-drug cooperation"]),
        ("执法行动", ["缉毒", "查获毒品", "drug seizure", "drug bust", "баривчилгаа"]),
        ("政策法规", ["立法", "法规", "管制目录", "regulation"]),
        ("媒体报道", ["news", "мэдээ", "报道"]),
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
    if not is_drug_related(t):
        return "一般"
    important = ["查获", "逮捕", "管制", "专项", "seizure", "seized", "arrest", "баривчилгаа", "тусгай", "smuggl"]
    watch = ["会议", "培训", "宣传", "урьдчилан", "prevention", "meeting", "мэдээ", "UNODC"]
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
