"""从新闻/PDF 文本中抽取涉毒统计数字"""
from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, List, Optional


# 指标类型
METRIC_CASE = "涉毒案件数"
METRIC_GROWTH = "同比增长率"
METRIC_PERSON = "涉案人数"
METRIC_CONVICT = "判决人数"
METRIC_SEIZURE = "查获次数"
METRIC_VIOLATION = "涉毒违法/违规"
METRIC_HIDDEN = "隐匿滥用人数估算"
METRIC_OTHER = "其他统计"


def _num(s: str) -> Optional[float]:
    if not s:
        return None
    s = s.replace(",", "").replace(" ", "").replace("，", "")
    s = s.replace("%", "")
    try:
        if "." in s:
            return float(s)
        return float(int(s))
    except ValueError:
        return None


def extract_stats_from_text(
    text: str,
    *,
    source_url: str = "",
    org_name: str = "",
    title: str = "",
) -> List[Dict[str, Any]]:
    """从蒙/中/英文本抽取可结构化的涉毒统计。"""
    blob = text or ""
    if not blob.strip():
        return []

    # 必须与毒品语境相关
    drug_ctx = re.search(
        r"мансууруулах|хар\s*тамхи|наркотик|narcotic|methamphetamine|fentanyl|"
        r"毒品|涉毒|缉毒|禁毒|贩毒|吸毒|冰毒|海洛因|大麻",
        blob,
        flags=re.IGNORECASE,
    )
    if not drug_ctx:
        return []

    out: List[Dict[str, Any]] = []
    seen = set()

    def add(metric: str, value: float, unit: str, period: str, raw: str, confidence: float = 0.7):
        key = f"{metric}|{value}|{period}|{raw[:40]}"
        if key in seen:
            return
        seen.add(key)
        out.append({
            "metric_name": metric,
            "metric_value": value,
            "unit": unit,
            "period": period,
            "raw_snippet": raw.strip()[:400],
            "confidence": confidence,
            "source_url": source_url,
            "org_name": org_name,
            "title": title[:300],
        })

    # 年份/时期
    year_m = re.search(r"(20[12]\d)\s*он", blob)
    year_en = re.search(r"\b(20[12]\d)\b", blob)
    q_m = re.search(r"(20[12]\d)\s*оны\s*(нэгдүгээр|хоёрдугаар|гуравдугаар|дөрөвдүгээр)\s*улирал", blob)
    period = ""
    if q_m:
        qmap = {"нэгдүгээр": "Q1", "хоёрдугаар": "Q2", "гуравдугаар": "Q3", "дөрөвдүгээр": "Q4"}
        period = f"{q_m.group(1)}-{qmap.get(q_m.group(2), 'Q?')}"
    elif year_m:
        period = year_m.group(1)
    elif year_en:
        period = year_en.group(1)

    # 1) 案件数：… 551 хэрэг / 192 гэмт хэрэг
    for m in re.finditer(
        r"(мансууруулах[^。\n]{0,80}?)(\d{1,5})\s*(гэмт\s*)?хэрэг",
        blob,
        flags=re.IGNORECASE,
    ):
        v = _num(m.group(2))
        if v and 1 <= v <= 100000:
            add(METRIC_CASE, v, "件", period, m.group(0), 0.85)

    for m in re.finditer(
        r"(\d{1,5})\s*(гэмт\s*)?хэрэгт\s*хяналт|"
        r"бүртгэгдсэн[^。\n]{0,40}?(\d{1,5})\s*(гэмт\s*)?хэрэг|"
        r"(\d{1,5})\s*drug[- ]related\s*cases?",
        blob,
        flags=re.IGNORECASE,
    ):
        raw = m.group(0)
        nums = re.findall(r"\d{1,5}", raw)
        for n in nums:
            v = _num(n)
            if v and 1 <= v <= 100000:
                add(METRIC_CASE, v, "件", period, raw, 0.75)

    # 中文：涉毒案件 551 起 / 增长 21.6%
    for m in re.finditer(r"(涉毒|毒品|缉毒)[^。\n]{0,30}?(\d{1,5})\s*(起|件|案)", blob):
        v = _num(m.group(2))
        if v:
            add(METRIC_CASE, v, "件", period, m.group(0), 0.8)

    # 2) 同比：21.6 хувиар өс / 57.2%
    for m in re.finditer(
        r"(\d{1,3}(?:[.,]\d+)?)\s*хув(?:иар)?\s*(өс|буур)|"
        r"(өс|буур)[^。\n]{0,20}?(\d{1,3}(?:[.,]\d+)?)\s*хув|"
        r"(增长|上升|下降|减少)\s*(\d{1,3}(?:[.,]\d+)?)\s*%|"
        r"(\d{1,3}(?:[.,]\d+)?)\s*%\s*(increase|decrease|rise|growth)",
        blob,
        flags=re.IGNORECASE,
    ):
        raw = m.group(0)
        nums = re.findall(r"\d{1,3}(?:[.,]\d+)?", raw)
        if not nums:
            continue
        v = _num(nums[0])
        if v is None or v > 500:
            continue
        sign = -1 if re.search(r"буур|下降|减少|decrease", raw, re.I) else 1
        add(METRIC_GROWTH, sign * v, "%", period, raw, 0.8)

    # 3) 涉案/判决人数
    for m in re.finditer(
        r"(\d{1,5})\s*хүн[^。\n]{0,40}?(яллагдагч|ял шийтгүүл|холбогдсон)|"
        r"(яллагдагч|ял шийтгүүл|холбогдсон)[^。\n]{0,40}?(\d{1,5})\s*хүн|"
        r"(\d{1,5})\s*(people|persons|suspects|convict)",
        blob,
        flags=re.IGNORECASE,
    ):
        raw = m.group(0)
        nums = re.findall(r"\d{1,5}", raw)
        for n in nums:
            v = _num(n)
            if not v or v > 100000:
                continue
            metric = METRIC_CONVICT if re.search(r"ял шийтгүүл|convict", raw, re.I) else METRIC_PERSON
            add(metric, v, "人", period, raw, 0.75)

    # 4) 隐匿滥用估算 30.000 / 30000
    for m in re.finditer(
        r"(\d{1,3}(?:[.,]\d{3})?|\d{4,6})\s*(далд\s*хэрэглэгч|hidden\s*user|隐匿)",
        blob,
        flags=re.IGNORECASE,
    ):
        v = _num(m.group(1))
        if v and v >= 100:
            add(METRIC_HIDDEN, v, "人", period, m.group(0), 0.7)

    # 5) 海关查获次数
    for m in re.finditer(
        r"(\d{1,5})\s*(удаа|times?).{0,40}?(мансууруулах|narcotic|drug)|"
        r"(мансууруулах|narcotic).{0,40}?(\d{1,5})\s*(удаа|seizure)",
        blob,
        flags=re.IGNORECASE,
    ):
        raw = m.group(0)
        nums = re.findall(r"\d{1,5}", raw)
        for n in nums:
            v = _num(n)
            if v and 1 <= v <= 10000:
                add(METRIC_SEIZURE, v, "次", period, raw, 0.7)

    return out[:40]


def stats_fingerprint(metric_name: str, value: float, period: str, url: str) -> str:
    raw = f"{metric_name}|{value}|{period}|{url}".encode("utf-8", errors="ignore")
    return hashlib.sha256(raw).hexdigest()[:40]
