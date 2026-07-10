"""核心数据源、黑白名单修复脚本，兼容项目全部原有调用逻辑，仅新增蒙古民间媒体、缩小黑名单"""
from __future__ import annotations

from typing import Dict, List, Union
from urllib.parse import urlparse

# 永久封禁国内无法访问的蒙古gov官方站点
FORBIDDEN_HOSTS = {
    "police.gov.mn",
    "customs.gov.mn",
    "health.gov.mn",
    "zasag.mn",
    "mohs.mn",
    "mmra.gov.mn",
    "mofa.gov.mn",
    "ecustoms.mn",
    "gia.gov.mn",
    "bpo.gov.mn",
    "gov.mn",
    "mongolia.gov.mn",
    "immigration.gov.mn",
}
# 封禁无效404专栏路径
FORBIDDEN_PATH_FRAGMENTS = ("/anti-narcotics", "/drug-control", "unodc.org/mongolia")
# 关键开关：放行全部.mn后缀蒙古媒体域名
ALLOW_ANY_MN_DOMAIN = True
# 大幅缩减无关内容黑名单，删除股市、画展等宽泛误过滤词汇
TOPIC_BLACKLIST = [
    "human trafficking",
    "anti-corruption",
    "奥运会",
    "兴奋剂wada",
    "乌兰乌德布里亚特",
]

# 核心合法数据源：保留原有渠道，新增4家蒙古本土民间媒体
CORE_OFFICIAL_SOURCES: List[Dict] = [
    {
        "system_id": 8,
        "system_name": "全国媒体与公开资讯",
        "org_name": "蒙通社 MONTSAME",
        "base_url": "https://montsame.mn",
        "seed_paths": ["/cn", "/en", "/mn"],
        "lang": "zh,en,mn",
        "search_mode_only": True,
        "core_official": True,
        "keywords_extra": ["хар тамхи", "毒品", "narcotics"],
    },
    {
        "system_id": 8,
        "system_name": "全国媒体与公开资讯",
        "org_name": "GOGO.MN蒙古媒体",
        "base_url": "https://gogo.mn",
        "seed_paths": ["/mn"],
        "lang": "mn",
        "search_mode_only": True,
        "core_official": True,
    },
    {
        "system_id": 8,
        "system_name": "全国媒体与公开资讯",
        "org_name": "IKON.MN",
        "base_url": "https://ikon.mn",
        "seed_paths": ["/mn"],
        "lang": "mn",
        "core_official": True,
    },
    {
        "system_id": 8,
        "system_name": "全国媒体与公开资讯",
        "org_name": "News.mn",
        "base_url": "https://news.mn",
        "seed_paths": ["/mn"],
        "lang": "mn",
        "core_official": True,
    },
    {
        "system_id": 8,
        "system_name": "全国媒体与公开资讯",
        "org_name": "UB Post",
        "base_url": "https://ubpost.mongolnews.mn",
        "seed_paths": ["/en"],
        "lang": "en",
        "core_official": True,
    },
    {
        "system_id": 7,
        "system_name": "国际禁毒协作机构",
        "org_name": "UNODC 联合国毒罪办",
        "base_url": "https://www.unodc.org",
        "seed_paths": ["/unodc/en/data-and-analysis/world-drug-report.html"],
        "lang": "en",
        "core_official": True,
        "keywords_extra": ["Mongolia", "narcotics"],
    },
    {
        "system_id": 4,
        "system_name": "边境口岸缉毒查验体系",
        "org_name": "中国禁毒网",
        "base_url": "http://www.nncc626.com",
        "seed_paths": ["/"],
        "lang": "zh",
        "core_official": True,
        "keywords_extra": ["蒙古国", "中蒙口岸", "扎门乌德", "甘其毛都"],
    },
]

# 中英蒙三语检索关键词库，扩充新型毒品词汇
KW_ZH = ["毒品", "禁毒", "缉毒", "贩毒", "芬太尼", "尼秦", "安纳咖", "合成毒品", "口岸走私", "易制毒"]
KW_EN = ["narcotics", "drug seizure", "fentanyl", "nitazene", "trafficking", "Mongolia"]
KW_MN = ["хар тамхи", "мансууруулах бодис", "фентанил", "нитазен", "газар хил худалдаа"]


def is_forbidden_url(url: str) -> bool:
    """判断黑名单封禁链接，函数名、入参、返回值完全兼容旧代码"""
    low = (url or "").lower().strip()
    if not low:
        return True
    try:
        host = urlparse(low if "://" in low else f"https://{low}").netloc.lower().split(":")[0]
        host = host.replace("www.", "")
    except Exception:
        host = ""
    if host in FORBIDDEN_HOSTS:
        return True
    # 永久屏蔽全部蒙古本土 .gov.mn
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
    """统一使用1年检索窗口生成检索任务（dict），兼容 search_feeds / self-check 原有调用。"""
    tr = (when or time_range or "1y").strip()
    when_suffix = f" when:{tr}" if tr and not tr.startswith("when:") else (f" {tr}" if tr else "")
    tasks: List[dict] = []
    for source in CORE_OFFICIAL_SOURCES:
        domain = (
            source["base_url"]
            .replace("https://", "")
            .replace("http://", "")
            .rstrip("/")
        )
        sid = int(source.get("system_id") or 8)
        sname = source.get("system_name") or "全国媒体与公开资讯"
        org = source.get("org_name") or domain
        lang = str(source.get("lang") or "en")
        if "zh" in lang:
            hl, gl, ceid = "zh-CN", "cn", "CN:zh-Hans"
        elif "mn" in lang and "en" not in lang and "zh" not in lang:
            hl, gl, ceid = "mn", "mn", "MN:mn"
        else:
            hl, gl, ceid = "en", "us", "US:en"
        for kw in KW_ZH + KW_EN + KW_MN:
            q = f"site:{domain} ({kw}){when_suffix}"
            if "unodc.org" in domain:
                q = f"site:unodc.org Mongolia ({kw}){when_suffix}"
            tasks.append({
                "system_id": sid,
                "system_name": sname,
                "org_name": f"检索·{org}·{kw[:12]}",
                "query": q,
                "hl": hl,
                "gl": gl,
                "ceid": ceid,
                "engine": "google_news",
                "require_mongolia": "unodc" not in domain,
                "tier": "primary",
                "source_kind": "keyword_search",
            })
    return tasks
