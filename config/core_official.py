"""
全量修复版种子与黑名单。

硬性禁令：
- 禁止访问全部蒙古本土 .gov.mn 及虚构专栏路径
- 禁止翻墙代理；仅国内裸网可直连公开域名
- 禁止自动拼接 /anti-narcotics、/drug-control 等后缀
- 采集模式：关键词检索式增量，不做全站递归
"""
from __future__ import annotations

from typing import List
from urllib.parse import quote_plus, urlparse

# —— 永久黑名单（命中即跳过，不探测、不拼接）——
FORBIDDEN_HOST_SUFFIXES = (
    ".gov.mn",
    "gov.mn",
)
FORBIDDEN_HOSTS = {
    "shturl.cc",
    "www.shturl.cc",
    "customs.gov.mn",
    "www.customs.gov.mn",
    "police.gov.mn",
    "www.police.gov.mn",
    "bpo.gov.mn",
    "www.bpo.gov.mn",
    "gia.gov.mn",
    "www.gia.gov.mn",
    "ecustoms.mn",
    "www.ecustoms.mn",
    "mohs.mn",
    "www.mohs.mn",
    "mmra.gov.mn",
    "www.mmra.gov.mn",
    "mofa.gov.mn",
    "www.mofa.gov.mn",
    "zasag.mn",
    "www.zasag.mn",
    "health.gov.mn",
    "www.health.gov.mn",
}
# 仅屏蔽虚构专栏路径；勿用裸 /narcotics（会误伤合法文章 URL）
FORBIDDEN_PATH_FRAGMENTS = (
    "/anti-narcotics",
    "/drug-control",
    "/antidrug",
    "/anti_drug",
    "shturl.cc",
    "unodc.org/mongolia",
    "unodc.org/unodc/mongolia",
)

# 三语检索词
KW_ZH = [
    "毒品", "缉毒", "禁毒", "贩毒", "戒毒", "芬太尼", "合成大麻素",
    "安纳咖", "新型毒品", "毒情", "麻醉药品",
]
KW_EN = [
    "narcotics", "drug seizure", "trafficking", "fentanyl",
    "synthetic cannabis", "anaga", "rehabilitation",
    "new psychoactive substance", "methamphetamine",
]
KW_MN = [
    "хар тамхи", "мансууруулах бодис", "хар тамхитай тэмцэх",
    "газар хил худалдаа", "сэргээх төв", "синтетик мансууруулах бодис",
]

# 黑名单主题（误入库顽疾）
TOPIC_BLACKLIST = [
    "军演", "国防", "画展", "文娱", "股市", "金融监管", "市政", "基建",
    "民生", "福利", "体育", "赛事", "宗教", "畜牧", "military exercise",
    "exhibition", "stock market", "зохицуулах хороо", "санхүүгийн",
]


def is_forbidden_url(url: str) -> bool:
    low = (url or "").lower().strip()
    if not low:
        return True
    try:
        host = urlparse(low if "://" in low else f"https://{low}").netloc.lower().split(":")[0]
    except Exception:
        host = ""
    if host in FORBIDDEN_HOSTS:
        return True
    # 全部蒙古本土 .gov.mn
    if host.endswith(".gov.mn") or host == "gov.mn":
        return True
    if any(f in low for f in FORBIDDEN_PATH_FRAGMENTS):
        return True
    return False


# —— 一级核心：检索式种子（非递归全站）——
CORE_OFFICIAL_SOURCES: List[dict] = [
    {
        "system_id": 8,
        "system_name": "全国媒体与公开资讯",
        "org_name": "蒙通社中文站",
        "org_name_mn": "МОНЦАМЭ CN",
        "base_url": "https://montsame.mn",
        "seed_paths": ["/cn"],
        "lang": "zh",
        "source_type": "media",
        "core_official": True,
        "priority": 1,
        "tier": "primary",
        "search_mode_only": True,
    },
    {
        "system_id": 8,
        "system_name": "全国媒体与公开资讯",
        "org_name": "蒙通社英文站",
        "org_name_mn": "МОНЦАМЭ EN",
        "base_url": "https://montsame.mn",
        "seed_paths": ["/en"],
        "lang": "en",
        "source_type": "media",
        "core_official": True,
        "priority": 1,
        "tier": "primary",
        "search_mode_only": True,
    },
    {
        "system_id": 8,
        "system_name": "全国媒体与公开资讯",
        "org_name": "蒙通社蒙语站",
        "org_name_mn": "МОНЦАМЭ MN",
        "base_url": "https://montsame.mn",
        "seed_paths": ["/mn"],
        "lang": "mn",
        "source_type": "media",
        "core_official": True,
        "priority": 1,
        "tier": "primary",
        "search_mode_only": True,
    },
    {
        "system_id": 4,
        "system_name": "边境海关缉毒查验体系",
        "org_name": "中国禁毒网",
        "org_name_mn": "NNCC",
        "base_url": "http://www.nncc626.com",
        "seed_paths": ["/"],
        "lang": "zh",
        "source_type": "official",
        "core_official": True,
        "priority": 1,
        "tier": "primary",
        "search_mode_only": True,
    },
    {
        "system_id": 7,
        "system_name": "国际禁毒协作机构",
        "org_name": "UNODC 全球站（筛 Mongolia）",
        "org_name_mn": "UNODC",
        "base_url": "https://www.unodc.org",
        "seed_paths": [
            "/unodc/en/data-and-analysis/world-drug-report.html",
        ],
        "lang": "en",
        "source_type": "official",
        "core_official": True,
        "priority": 1,
        "tier": "primary",
        "require_mongolia": True,
        "search_mode_only": True,
    },
    # —— 二级补充 ——
    {
        "system_id": 7,
        "system_name": "国际禁毒协作机构",
        "org_name": "联合国蒙古国办事处",
        "org_name_mn": "UN Mongolia",
        "base_url": "https://mongolia.un.org",
        "seed_paths": ["/en"],
        "lang": "en",
        "source_type": "official",
        "core_official": True,
        "priority": 2,
        "tier": "secondary",
        "search_mode_only": True,
    },
    {
        "system_id": 8,
        "system_name": "全国媒体与公开资讯",
        "org_name": "中新网",
        "org_name_mn": "China News",
        "base_url": "https://www.chinanews.com",
        "seed_paths": ["/"],
        "lang": "zh",
        "source_type": "media",
        "core_official": True,
        "priority": 2,
        "tier": "secondary",
        "search_mode_only": True,
    },
    {
        "system_id": 4,
        "system_name": "边境海关缉毒查验体系",
        "org_name": "内蒙古公安",
        "org_name_mn": "NMG GAT",
        "base_url": "http://gat.nmg.110.gov.cn",
        "seed_paths": ["/"],
        "lang": "zh",
        "source_type": "official",
        "core_official": True,
        "priority": 2,
        "tier": "secondary",
        "search_mode_only": True,
    },
    {
        "system_id": 7,
        "system_name": "国际禁毒协作机构",
        "org_name": "集安组织 CSTO",
        "org_name_mn": "CSTO",
        "base_url": "https://www.odkb-csto.org",
        "seed_paths": ["/"],
        "lang": "en",
        "source_type": "official",
        "core_official": True,
        "priority": 2,
        "tier": "secondary",
        "search_mode_only": True,
    },
    {
        "system_id": 7,
        "system_name": "国际禁毒协作机构",
        "org_name": "上合组织经合",
        "org_name_mn": "SCO",
        "base_url": "https://www.scoec.gov.cn",
        "seed_paths": ["/"],
        "lang": "zh",
        "source_type": "official",
        "core_official": True,
        "priority": 2,
        "tier": "secondary",
        "search_mode_only": True,
    },
    {
        "system_id": 8,
        "system_name": "全国媒体与公开资讯",
        "org_name": "UB Post",
        "org_name_mn": "UB Post",
        "base_url": "https://ubpost.mongolnews.mn",
        "seed_paths": ["/"],
        "lang": "en",
        "source_type": "media",
        "core_official": True,
        "priority": 2,
        "tier": "secondary",
        "search_mode_only": True,
    },
]

# 研判备注用 PDF（不爬取）
REFERENCE_PDFS = [
    {
        "title": "UNODC Mongolia Cycle II Country Report",
        "url": "https://www.unodc.org/documents/treaties/UNCAC/CountryVisitFinalReports/2023_10_26_Mongolia_Cycle_II_Country_Report_EN.pdf",
    }
]


def build_core_site_search_queries(when: str = "30d") -> List[dict]:
    """关键词检索式任务（Google News site: + 站内搜），仅合法可直连域名。"""
    when_suffix = f" when:{when}" if when else ""
    tasks: List[dict] = []

    def add_google(name: str, site: str, sid: int, sname: str, query_core: str, hl: str, gl: str, ceid: str, tier: str) -> None:
        q = f"site:{site} ({query_core}){when_suffix}"
        if "unodc.org" in site:
            q = f"site:unodc.org Mongolia ({query_core}){when_suffix}"
        tasks.append({
            "system_id": sid,
            "system_name": sname,
            "org_name": f"检索·{name}",
            "query": q,
            "hl": hl,
            "gl": gl,
            "ceid": ceid,
            "engine": "google_news",
            "require_mongolia": "unodc" not in site.lower() or True,
            "tier": tier,
            "source_kind": "keyword_search",
        })

    # 蒙通社三语
    zh_or = " OR ".join(f'"{k}"' if " " in k else k for k in KW_ZH[:8])
    en_or = " OR ".join(f'"{k}"' if " " in k else k for k in KW_EN[:8])
    mn_or = " OR ".join(f'"{k}"' for k in KW_MN[:5])
    add_google("蒙通社中文", "montsame.mn", 8, "全国媒体与公开资讯", zh_or, "zh-CN", "cn", "CN:zh-Hans", "primary")
    add_google("蒙通社英文", "montsame.mn", 8, "全国媒体与公开资讯", en_or, "en-US", "us", "US:en", "primary")
    add_google("蒙通社蒙语", "montsame.mn", 8, "全国媒体与公开资讯", mn_or, "mn", "mn", "MN:mn", "primary")

    # 中国禁毒网 / 中新网 / 内蒙古公安 — 用主题检索（无 site 时也带蒙古）
    cn_border = '"蒙古国" OR 扎门乌德 OR 甘其毛都 OR 二连浩特 OR "中蒙口岸"'
    drug_zh = "毒品 OR 缉毒 OR 贩毒 OR 安纳咖 OR 芬太尼"
    for name, site, sid, sname in [
        ("中国禁毒网", "nncc626.com", 4, "边境海关缉毒查验体系"),
        ("中新网", "chinanews.com", 8, "全国媒体与公开资讯"),
        ("内蒙古公安", "nmg.110.gov.cn", 4, "边境海关缉毒查验体系"),
    ]:
        add_google(name, site, sid, sname, f"({cn_border}) ({drug_zh})", "zh-CN", "cn", "CN:zh-Hans", "primary" if "nncc" in site else "secondary")

    add_google("UNODC", "unodc.org", 7, "国际禁毒协作机构", en_or, "en-US", "us", "US:en", "primary")
    add_google("联合国蒙古办事处", "mongolia.un.org", 7, "国际禁毒协作机构", en_or + " OR drug OR narcotic", "en-US", "us", "US:en", "secondary")
    add_google("CSTO", "odkb-csto.org", 7, "国际禁毒协作机构", "Mongolia (narcotics OR drug OR operation)", "en-US", "us", "US:en", "secondary")
    add_google("上合经合", "scoec.gov.cn", 7, "国际禁毒协作机构", "禁毒 OR 毒品 OR Mongolia narcotic", "zh-CN", "cn", "CN:zh-Hans", "secondary")
    add_google("UB Post", "mongolnews.mn", 8, "全国媒体与公开资讯", en_or, "en-US", "us", "US:en", "secondary")

    # 蒙通社站内搜索（可打开原文）
    for lang, path, kws in (
        ("zh", "/cn/search?q={q}", KW_ZH[:6]),
        ("en", "/en/search?q={q}", KW_EN[:6]),
        ("mn", "/mn/search?q={q}", KW_MN[:4]),
    ):
        for kw in kws:
            tasks.append({
                "system_id": 8,
                "system_name": "全国媒体与公开资讯",
                "org_name": f"蒙通社站内·{lang}",
                "query": kw,
                "hl": lang,
                "gl": "mn" if lang == "mn" else ("cn" if lang == "zh" else "us"),
                "ceid": "MN:mn" if lang == "mn" else ("CN:zh-Hans" if lang == "zh" else "US:en"),
                "engine": "site_search",
                "search_url": f"https://montsame.mn{path.format(q=quote_plus(kw))}",
                "require_mongolia": False,
                "tier": "primary",
                "source_kind": "site_search",
            })

    return tasks
