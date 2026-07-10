"""核心数据源、黑白名单：国内裸网可直连完整官网清单 + 永久黑名单

【本次全链路增产修复】
缺陷：site:*.gov.mn 快照检索生成后，采集端曾整段剔除；直连.gov.mn仍须永久禁止。
修改范围：扩充蒙语海关/警察专项 query；明确 is_forbidden_url 仅拦直链；
          快照/缓存域名判定辅助函数供 filters/search_feeds 放行入库（不发起 HTTP 到 gov.mn）。
"""
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

KW_ZH = [
    "毒品", "禁毒", "缉毒", "贩毒", "芬太尼", "尼秦", "安纳咖", "合成毒品",
    "口岸走私", "易制毒", "冰毒", "海洛因", "查获", "跨境",
]
KW_EN = [
    "narcotics", "drug seizure", "fentanyl", "nitazene", "trafficking",
    "methamphetamine", "heroin", "cannabis", "smuggling",
]
KW_MN = [
    "хар тамхи", "мансууруулах бодис", "фентанил", "нитазен",
    "метамфетамин", "баривчилгаа", "гааль мансууруулах",
]

# 仅用于 Google News/网页检索的 site:*.gov.mn 快照词（禁止直连这些域名）
# 原缺陷：完全不检索官方公开通稿 → 统计/执法数字缺失；现仅搜索引擎快照，不发起 HTTP 到 gov.mn
GOV_MN_SEARCH_SITES = [
    "police.gov.mn",
    "customs.gov.mn",
    "gia.gov.mn",
    "bpo.gov.mn",
    "immigration.gov.mn",
]


def is_google_snapshot_or_news_url(url: str) -> bool:
    """谷歌新闻/网页缓存/搜索结果页：可入库展示，不构成对 gov.mn 的直连。"""
    low = (url or "").lower()
    if not low.startswith("http"):
        return False
    try:
        host = urlparse(low).netloc.lower().replace("www.", "")
    except Exception:
        return False
    return (
        host.endswith("news.google.com")
        or host.endswith("google.com")
        or host.endswith("googleusercontent.com")
        or "webcache.googleusercontent.com" in host
        or host.endswith("bing.com")
        or host.endswith("duckduckgo.com")
    )


def is_gov_mn_direct_url(url: str) -> bool:
    """是否为蒙古 .gov.mn 原始直链（禁止 HTTP 抓取）。"""
    low = (url or "").lower().strip()
    if not low or is_google_snapshot_or_news_url(low):
        return False
    try:
        host = urlparse(low if "://" in low else f"https://{low}").netloc.lower().split(":")[0]
        host = host.replace("www.", "")
    except Exception:
        return False
    return host.endswith(".gov.mn") or host == "gov.mn"


def sanitize_store_url(url: str, google_link: str = "") -> str:
    """入库 URL：gov.mn 直链改写为谷歌新闻检索/原 RSS 链，永不保存可直连抓取的 gov.mn。"""
    from urllib.parse import quote_plus

    u = (url or "").strip()
    g = (google_link or "").strip()
    if g and is_google_snapshot_or_news_url(g):
        if not u or is_gov_mn_direct_url(u) or is_forbidden_url(u):
            return g
    if u and is_gov_mn_direct_url(u):
        # 用谷歌新闻搜索包装，前端可点开快照结果，程序不 GET gov.mn
        return f"https://news.google.com/search?q={quote_plus(u)}&hl=en-US&gl=US&ceid=US:en"
    return u or g


def is_forbidden_url(url: str) -> bool:
    """判断黑名单封禁链接：永久拦截 .gov.mn 直链与虚构路径；谷歌快照域名不在此列。"""
    low = (url or "").lower().strip()
    if not low:
        return True
    # 谷歌/必应快照与新闻聚合页允许（非 gov.mn 直连）
    if is_google_snapshot_or_news_url(low):
        return False
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
    """清单内每个官网：合并关键词的 site: 检索 + 少量站内搜（快、全覆盖）。"""
    from urllib.parse import quote_plus

    tr = (when or time_range or "1y").strip()
    when_suffix = f" when:{tr}" if tr and not str(tr).startswith("when:") else (f" {tr}" if tr else "")
    tasks: List[dict] = []

    zh_or = " OR ".join(KW_ZH[:7])
    en_or = " OR ".join(f'"{k}"' if " " in k else k for k in KW_EN[:5])
    mn_or = " OR ".join(f'"{k}"' for k in KW_MN[:4])

    def _task(source: dict, domain: str, query_core: str, hl: str, gl: str, ceid: str, tag: str) -> None:
        sid = int(source.get("system_id") or 8)
        sname = source.get("system_name") or "全国媒体与公开资讯"
        org = source.get("org_name") or domain
        if "unodc.org" in domain:
            q = f"site:unodc.org Mongolia ({query_core}){when_suffix}"
        elif domain.endswith("nncc626.com") or "news.cn" in domain or "xinhuanet" in domain:
            q = f"site:{domain} (蒙古国 OR 中蒙 OR 扎门乌德 OR 甘其毛都) ({query_core}){when_suffix}"
        elif "cgtn.com" in domain or "akipress.com" in domain:
            q = f"site:{domain} Mongolia ({query_core}){when_suffix}"
        else:
            q = f"site:{domain} ({query_core}){when_suffix}"
        tasks.append({
            "system_id": sid,
            "system_name": sname,
            "org_name": f"检索·{org}·{tag}",
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
        domain_bare = domain[4:] if domain.startswith("www.") else domain
        lang = str(source.get("lang") or "en")
        # 蒙通社三语各一路；其余站点按主语言 1～2 路
        if "montsame.mn" in domain_bare:
            _task(source, domain_bare, zh_or, "zh-CN", "cn", "CN:zh-Hans", "中文")
            _task(source, domain_bare, en_or, "en", "us", "US:en", "英文")
            _task(source, domain_bare, mn_or, "mn", "mn", "MN:mn", "蒙语")
        elif "zh" in lang:
            _task(source, domain_bare, zh_or, "zh-CN", "cn", "CN:zh-Hans", "中文")
        elif lang == "mn" or lang.startswith("mn"):
            _task(source, domain_bare, mn_or, "mn", "mn", "MN:mn", "蒙语")
            _task(source, domain_bare, en_or, "en", "us", "US:en", "英文补")
        else:
            _task(source, domain_bare, en_or, "en", "us", "US:en", "英文")

    # 站内搜索：覆盖清单内蒙古媒体（每站少量高价值词）
    site_kw_mn = KW_MN[:3]
    site_kw_zh = KW_ZH[:3]
    site_kw_en = ["narcotics", "fentanyl", "drug seizure"]
    for path, kws, lang in (
        ("/cn/search?q={q}", site_kw_zh, "zh"),
        ("/en/search?q={q}", site_kw_en, "en"),
        ("/mn/search?q={q}", site_kw_mn, "mn"),
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
    for name, tmpl, kws in (
        ("GOGO站内", "https://gogo.mn/search?q={q}", site_kw_mn + ["метамфетамин", "фентанил"]),
        ("IKON站内", "https://ikon.mn/search?q={q}", site_kw_mn + ["метамфетамин", "фентанил"]),
        ("News.mn站内", "https://news.mn/search?q={q}", site_kw_mn + ["баривчилгаа"]),
        ("UB Post站内", "https://ubpost.mongolnews.mn/?s={q}", site_kw_en + ["methamphetamine", "trafficking"]),
    ):
        for kw in kws:
            tasks.append({
                "system_id": 8,
                "system_name": "全国媒体与公开资讯",
                "org_name": f"{name}·{kw[:10]}",
                "query": kw,
                "hl": "en" if "UB" in name else "mn",
                "gl": "us" if "UB" in name else "mn",
                "ceid": "US:en" if "UB" in name else "MN:mn",
                "engine": "site_search",
                "search_url": tmpl.format(q=quote_plus(kw)),
                "require_mongolia": False,
                "tier": "primary",
                "source_kind": "site_search",
            })

    # Google 快照检索蒙古 .gov.mn（仅 query 含 site:，程序不直连；入库用谷歌包装链）
    gov_drug_en = "(narcotic OR drug OR methamphetamine OR fentanyl OR seizure OR trafficking)"
    gov_drug_mn = "(мансууруулах OR \"хар тамхи\" OR фентанил OR баривчилгаа OR метамфетамин)"
    gov_drug_zh = "(毒品 OR 缉毒 OR 查获 OR 芬太尼 OR 安纳咖)"
    for host in GOV_MN_SEARCH_SITES:
        for tag, qcore, hl, gl, ceid, eng in (
            ("英", gov_drug_en, "en", "us", "US:en", "google_news"),
            ("蒙", gov_drug_mn, "mn", "mn", "MN:mn", "google_news"),
            ("中", gov_drug_zh, "zh-CN", "cn", "CN:zh-Hans", "google_news"),
            ("网页蒙", gov_drug_mn, "mn", "mn", "MN:mn", "web_search"),
        ):
            tasks.append({
                "system_id": 8,
                "system_name": "全国媒体与公开资讯",
                "org_name": f"检索快照·{host}·{tag}",
                "query": f"site:{host} {qcore}{when_suffix}",
                "hl": hl,
                "gl": gl,
                "ceid": ceid,
                "engine": eng,
                "require_mongolia": True,
                "tier": "primary",
                "source_kind": "keyword_search",
                "snapshot_only": True,
            })
    # 蒙语海关/警察专项（拆短句，避免谷歌截断）
    for q, tag in (
        (f"site:customs.gov.mn гааль мансууруулах{when_suffix}", "海关蒙语"),
        (f"site:customs.gov.mn баривчилгаа хар тамхи{when_suffix}", "海关查获"),
        (f"site:police.gov.mn цагдаа мансууруулах{when_suffix}", "警察蒙语"),
        (f"site:police.gov.mn баривчилгаа фентанил{when_suffix}", "警察芬太尼"),
        (f"site:bpo.gov.mn прокурор мансууруулах{when_suffix}", "检察蒙语"),
    ):
        tasks.append({
            "system_id": 8,
            "system_name": "全国媒体与公开资讯",
            "org_name": f"检索快照·{tag}",
            "query": q,
            "hl": "mn",
            "gl": "mn",
            "ceid": "MN:mn",
            "engine": "google_news",
            "require_mongolia": True,
            "tier": "primary",
            "source_kind": "keyword_search",
            "snapshot_only": True,
        })

    # 蒙通社/GOGO/IKON 多语种补盲（扩大媒体检索任务量）
    media_extra = [
        ("montsame.mn", "毒品 OR 缉毒 OR 芬太尼 OR 安纳咖", "zh-CN", "cn", "CN:zh-Hans"),
        ("montsame.mn", "narcotic OR fentanyl OR methamphetamine OR seizure", "en", "us", "US:en"),
        ("gogo.mn", "мансууруулах OR \"хар тамхи\" OR фентанил", "mn", "mn", "MN:mn"),
        ("ikon.mn", "мансууруулах OR метамфетамин OR баривчилгаа", "mn", "mn", "MN:mn"),
        ("news.mn", "мансууруулах OR гааль OR хил", "mn", "mn", "MN:mn"),
        ("ubpost.mongolnews.mn", "drug OR narcotic OR trafficking OR seizure", "en", "us", "US:en"),
    ]
    for domain, qcore, hl, gl, ceid in media_extra:
        tasks.append({
            "system_id": 8,
            "system_name": "全国媒体与公开资讯",
            "org_name": f"媒体补盲·{domain}",
            "query": f"site:{domain} ({qcore}){when_suffix}",
            "hl": hl,
            "gl": gl,
            "ceid": ceid,
            "engine": "google_news",
            "require_mongolia": False,
            "tier": "primary",
            "source_kind": "keyword_search",
        })

    return tasks
