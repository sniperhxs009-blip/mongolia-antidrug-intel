"""文本过滤、去重、翻译与情报等级判定工具"""
from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Tuple
from urllib.parse import urlparse

from config.sources import ALLOWED_DOMAINS, CRITICAL_KEYWORDS, DRUG_KEYWORDS

logger = logging.getLogger(__name__)


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
    allow = set(ALLOWED_DOMAINS)
    if extra_domains:
        allow.update(extra_domains)
    if host in allow:
        return True
    # 允许同主域下级子域名（仅 .gov.mn / ulaanbaatar.mn / unodc.org）
    for d in allow:
        if host.endswith("." + d) or host == d:
            return True
    # 严格：仅蒙古官方与 UNODC
    if host.endswith(".gov.mn") or host.endswith(".mn"):
        # 仍需在白名单主域内
        for d in allow:
            base = d.replace("www.", "")
            if host.endswith(base):
                return True
    return host.endswith("unodc.org")


def is_drug_related(text: str, extra_keywords: Optional[list] = None) -> bool:
    blob = (text or "").lower()
    keys = list(DRUG_KEYWORDS)
    if extra_keywords:
        keys.extend(extra_keywords)
    for kw in keys:
        if kw.lower() in blob:
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
        ("新型毒品", ["合成", "芬太尼", "冰毒", "синтетик", "synthetic", "meth", "fentanyl", "NPS"]),
        ("制毒原料", ["易制毒", "麻精", "precursor", "controlled", "зохицуулалт", "эм"]),
        ("戒毒康复", ["戒毒", "康复", "成瘾", "нөхөн сэргээх", "донтсон", "rehab", "addiction"]),
        ("国际协作", ["UNODC", "国际", "олон улсын", "cooperation", "外交"]),
        ("执法行动", ["缉毒", "查获", "专项", "баривчилгаа", "seizure", "operation", "цагдаа"]),
        ("政策法规", ["立法", "法规", "新法", "хууль", "legal", "regulation", "policy"]),
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
    important = ["查获", "逮捕", "管制", "专项", "seizure", "arrest", "баривчилгаа", "тусгай"]
    watch = ["会议", "培训", "宣传", "урьдчилан", "prevention", "meeting"]
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
    if re.search(r"[а-яА-ЯёЁөүӨҮ]", t):
        # 蒙语西里尔与俄语共用字母，优先看蒙语特有字母
        if re.search(r"[өүӨҮ]", t):
            return "mn"
        return "ru"
    return "en"


def translate_to_zh(text: str, source_lang: Optional[str] = None, enabled: bool = True) -> str:
    """将蒙/英/俄文本翻译为中文；失败时返回原文。"""
    text = normalize_text(text)
    if not text or not enabled:
        return text
    lang = source_lang or detect_lang(text)
    if lang == "zh":
        return text
    try:
        from deep_translator import GoogleTranslator

        src = {"mn": "mn", "en": "en", "ru": "ru"}.get(lang, "auto")
        # 长文本分段
        chunks = [text[i : i + 4500] for i in range(0, len(text), 4500)]
        out = []
        for c in chunks:
            out.append(GoogleTranslator(source=src, target="zh-CN").translate(c))
        return "\n".join(out)
    except Exception as exc:  # noqa: BLE001
        logger.warning("翻译失败，保留原文: %s", exc)
        return text


def parse_date_guess(text: str) -> Optional[datetime]:
    """从页面文本中粗略提取日期。"""
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


def is_stale(published_at: Optional[datetime], max_days: int = 365) -> bool:
    if not published_at:
        return False
    return published_at < datetime.utcnow() - timedelta(days=max_days)


def same_host_or_sub(url: str, base_url: str) -> bool:
    try:
        h1 = urlparse(url).netloc.lower().split(":")[0]
        h2 = urlparse(base_url).netloc.lower().split(":")[0]
        return h1 == h2 or h1.endswith("." + h2.replace("www.", "")) or h2.endswith("." + h1.replace("www.", ""))
    except Exception:
        return False
