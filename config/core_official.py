"""核心数据源、黑白名单：国内裸网可直连完整官网清单 + 永久黑名单"""
from __future__ import annotations

from typing import Dict, List
from urllib.parse import urlparse

# 永久黑名单（国内无法访问 / 无效短链，强制拦截）
FORBIDDEN_HOSTS = {
    "shturl.cc",
    "www.shturl.cc",
    "customs.gov.mn",
    "www.customs.gov.mn",
    "health.gov.mn",
    "www.health.gov.mn",
    "zasag.mn",
    "www.zasag.mn",
    "mohs.mn",
    "www.mohs.mn",
    "mmra.gov.mn",
    "www.mmra.gov.mn",
    "mofa.gov.mn",
    "www.mofa.gov.mn",
    "ecustoms.mn",
    "www.ecustoms.mn",
    "police.gov.mn",
    "gia.gov.mn",
    "bpo.gov.mn",
    "gov.mn",
    "mongolia.gov.mn",
    "immigration.gov.mn",
}
FORBIDDEN_PATH_FRAGMENTS = (
    "/anti-narcotics",
    "/drug-control",
    "unodc.org/mongolia",
    "shturl.cc",
)

ALLOW_ANY_MN_DOMAIN = True

TOPIC_BLACKLIST = [
    "human trafficking",
    "anti-corruption",
    "奥运会",
    "兴奋剂wada",
    "乌兰乌德布里亚特",
]

# —— 国内裸网直连完整官网清单（全部放行并作为采集种子）——
CORE_OFFICIAL_SOURCES: List[Dict] = [
    # 一、蒙古本土正规媒体
    {
        "system_id": 8,
        "system_name": "全国媒体与公开资讯",
        "org_name": "蒙通社 MONTSAME",
        "base_url": "https://montsame.mn",
        "seed_paths": ["/", "/cn", "/en", "/mn"],
        "lang": "zh,en,mn",
        "search_mode_only": False,
        "core_official": True,
        "tier": "primary",
        "keywords_extra": ["хар тамхи", "毒品", "narcotics", "мансууруулах"],
    },
    {
        "system_id": 8,
        "system_name": "全国媒体与公开资讯",
        "org_name": "GOGO.MN蒙古媒体",
        "base_url": "https://gogo.mn",
        "seed_paths": ["/", "/mn"],
        "lang": "mn",
        "search_mode_only": False,
        "core_official": True,
        "tier": "primary",
        "keywords_extra": ["хар тамхи", "мансууруулах"],
    },
    {
        "system_id": 8,
        "system_name": "全国媒体与公开资讯",
        "org_name": "IKON.MN",
        "base_url": "https://ikon.mn",
        "seed_paths": ["/", "/mn"],
        "lang": "mn",
        "search_mode_only": False,
        "core_official": True,
        "tier": "primary",
        "keywords_extra": ["хар тамхи", "мансууруулах"],
    },
    {
        "system_id": 8,
        "system_name": "全国媒体与公开资讯",
        "org_name": "News.mn",
        "base_url": "https://news.mn",
        "seed_paths": ["/", "/mn"],
        "lang": "mn",
        "search_mode_only": False,
        "core_official": True,
        "tier": "primary",
        "keywords_extra": ["хар тамхи", "мансууруулах"],
    },
    {
        "system_id": 8,
        "system_name": "全国媒体与公开资讯",
        "org_name": "UB Post",
        "base_url": "https://ubpost.mongolnews.mn",
        "seed_paths": ["/", "/en"],
        "lang": "en",
        "search_mode_only": False,
        "core_official": True,
        "tier": "primary",
        "keywords_extra": ["narcotics", "drug", "fentanyl"],
    },
    # 二、国际禁毒权威
    {
        "system_id": 7,
        "system_name": "国际禁毒协作机构",
        "org_name": "UNODC 联合国毒罪办",
        "base_url": "https://www.unodc.org",
        "seed_paths": [
            "/",
            "/unodc/en/data-and-analysis/world-drug-report.html",
        ],
        "lang": "en",
        "search_mode_only": False,
        "core_official": True,
        "tier": "primary",
        "keywords_extra": ["Mongolia", "narcotics", "drug"],
    },
    # 三、国内官方禁毒
    {
        "system_id": 4,
        "system_name": "边境口岸缉毒查验体系",
        "org_name": "中国禁毒网",
        "base_url": "http://www.nncc626.com",
        "seed_paths": ["/"],
        "lang": "zh",
        "search_mode_only": False,
        "core_official": True,
        "tier": "primary",
        "keywords_extra": ["蒙古国", "中蒙口岸", "扎门乌德", "甘其毛都", "缉毒"],
    },
    # 四、补充国际合规媒体
    {
        "system_id": 10,
        "system_name": "全球媒体与国际禁毒机构",
        "org_name": "新华网国际",
        "base_url": "https://www.news.cn",
        "seed_paths": ["/"],
        "lang": "zh",
        "search_mode_only": False,
        "core_official": True,
        "tier": "secondary",
        "keywords_extra": ["蒙古国", "毒品", "缉毒", "贩毒"],
    },
    {
        "system_id": 10,
        "system_name": "全球媒体与国际禁毒机构",
        "org_name": "CGTN",
        "base_url": "https://www.cgtn.com",
        "seed_paths": ["/"],
        "lang": "en",
        "search_mode_only": False,
        "core_official": True,
        "tier": "secondary",
        "keywords_extra": ["Mongolia", "narcotics", "drug"],
    },
    {
        "system_id": 10,
        "system_name": "全球媒体与国际禁毒机构",
        "org_name": "AKIpress 中亚通讯社",
        "base_url": "https://akipress.com",
        "seed_paths": ["/"],
        "lang": "en",
        "search_mode_only": False,
        "core_official": True,
        "tier": "secondary",
        "keywords_extra": ["Mongolia", "narcotics", "drug"],
    },
]

KW_ZH = ["毒品", "禁毒", "缉毒", "贩毒", "芬太尼", "尼秦", "安纳咖", "合成毒品", "口岸走私", "易制毒"]
KW_EN = ["narcotics", "drug seizure", "fentanyl", "nitazene", "trafficking", "Mongolia"]
KW_MN = ["хар тамхи", "мансууруулах бодис", "фентанил", "нитазен", "газар хил худалдаа"]


def is_forbidden_url(url: str) -> bool:
    """判断黑名单封禁链接，兼容旧代码调用。"""
    low = (url or "").lower().strip()
    if not low:
        return True
    try:
        host = urlparse(low if "://" in low else f"https://{low}").netloc.lower().split(":")[0]
        host = host.replace("www.", "")
    except Exception:
        host = ""
    if host in FORBIDDEN_HOSTS or host.endswith(".shturl.cc"):
        return True
    if host.endswith(".gov.mn") or host == "gov.mn":
        return True
    for frag in FORBIDDEN_PATH_FRAGMENTS:
        if frag in low:
            return True
    return False


def build_core_site_search_queries(
    time_range: str = "1y",
    when: str | None = None,
) -> List[dict]:
    """为清单内每个官网生成 site: 关键词检索任务（1年窗口）。"""
    tr = (when or time_range or "1y").strip()
    when_suffix = f" when:{tr}" if tr and not str(tr).startswith("when:") else (f" {tr}" if tr else "")
    tasks: List[dict] = []

    def _add(source: dict, domain: str, kw: str, hl: str, gl: str, ceid: str) -> None:
        sid = int(source.get("system_id") or 8)
        sname = source.get("system_name") or "全国媒体与公开资讯"
        org = source.get("org_name") or domain
        if "unodc.org" in domain:
            q = f"site:unodc.org Mongolia ({kw}){when_suffix}"
        elif domain.endswith("nncc626.com") or "news.cn" in domain or "xinhuanet" in domain:
            q = f"site:{domain} (蒙古国 OR 中蒙) ({kw}){when_suffix}"
        elif "cgtn.com" in domain or "akipress.com" in domain:
            q = f"site:{domain} Mongolia ({kw}){when_suffix}"
        else:
            q = f"site:{domain} ({kw}){when_suffix}"
        tasks.append({
            "system_id": sid,
            "system_name": sname,
            "org_name": f"检索·{org}·{kw[:12]}",
            "query": q,
            "hl": hl,
            "gl": gl,
            "ceid": ceid,
            "engine": "google_news",
            "require_mongolia": True,
            "tier": source.get("tier") or "primary",
            "source_kind": "keyword_search",
        })

    for source in CORE_OFFICIAL_SOURCES:
        domain = (
            source["base_url"]
            .replace("https://", "")
            .replace("http://", "")
            .rstrip("/")
        )
        # 去掉 www. 便于 site: 匹配
        domain_bare = domain[4:] if domain.startswith("www.") else domain
        lang = str(source.get("lang") or "en")
        if "zh" in lang:
            hl, gl, ceid = "zh-CN", "cn", "CN:zh-Hans"
            kws = KW_ZH
        elif lang == "mn" or (lang.startswith("mn") and "en" not in lang and "zh" not in lang):
            hl, gl, ceid = "mn", "mn", "MN:mn"
            kws = KW_MN + ["мансууруулах", "хар тамхи"]
        else:
            hl, gl, ceid = "en", "us", "US:en"
            kws = KW_EN
        # 去重关键词，控制单站任务量
        seen = set()
        for kw in kws:
            if kw in seen:
                continue
            seen.add(kw)
            _add(source, domain_bare, kw, hl, gl, ceid)

    # 蒙通社站内搜索（可打开原文）
    from urllib.parse import quote_plus

    for path, kws, lang in (
        ("/cn/search?q={q}", KW_ZH[:6], "zh"),
        ("/en/search?q={q}", KW_EN[:5], "en"),
        ("/mn/search?q={q}", KW_MN[:4], "mn"),
    ):
        for kw in kws:
            tasks.append({
                "system_id": 8,
                "system_name": "全国媒体与公开资讯",
                "org_name": f"蒙通社站内·{lang}",
                "query": kw,
                "hl": lang,
                "gl": "cn" if lang == "zh" else ("mn" if lang == "mn" else "us"),
                "ceid": "CN:zh-Hans" if lang == "zh" else ("MN:mn" if lang == "mn" else "US:en"),
                "engine": "site_search",
                "search_url": f"https://montsame.mn{path.format(q=quote_plus(kw))}",
                "require_mongolia": False,
                "tier": "primary",
                "source_kind": "site_search",
            })

    # GOGO / IKON / News.mn 站内检索补盲
    for name, tmpl, kws in (
        ("GOGO站内", "https://gogo.mn/search?q={q}", KW_MN[:4]),
        ("IKON站内", "https://ikon.mn/search?q={q}", KW_MN[:4]),
        ("News.mn站内", "https://news.mn/search?q={q}", KW_MN[:4]),
    ):
        for kw in kws:
            tasks.append({
                "system_id": 8,
                "system_name": "全国媒体与公开资讯",
                "org_name": f"{name}·{kw[:10]}",
                "query": kw,
                "hl": "mn",
                "gl": "mn",
                "ceid": "MN:mn",
                "engine": "site_search",
                "search_url": tmpl.format(q=quote_plus(kw)),
                "require_mongolia": False,
                "tier": "primary",
                "source_kind": "site_search",
            })

    return tasks
