"""核心数据源、黑白名单（合规修正版）。

修改原因：仅拦截直连 *.gov.mn 原生域名；放行 Google/RSS/site 快照中携带 gov.mn 的检索结果。
"""
from __future__ import annotations

from typing import Dict, List, Set
from urllib.parse import quote_plus, urlparse


# 永久黑名单：仅用于拦截「原生官网直链」HTTP，不用于过滤检索 query 字符串
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

# 搜索引擎 / 新闻聚合：即使 URL 文本含 gov.mn 也放行（不发起原生官网 HTTP）
SNAPSHOT_SAFE_HOSTS: Set[str] = {
    "news.google.com",
    "google.com",
    "www.google.com",
    "bing.com",
    "www.bing.com",
    "duckduckgo.com",
    "www.duckduckgo.com",
    "news.yahoo.com",
    "msn.com",
    "www.msn.com",
}

SEARCH_NEGATIVE_EXCLUDE = (
    ' -"内蒙古" -"Inner Mongolia" -乌兰乌德 -布里亚特 -赤塔 -恰克图 -后贝加尔 '
    '-乌兰乌德 -Ulan-Ude -Buryatia -Buryat -Chita -Kyakhta -Zabaikal -Забайкал '
    '-兴奋剂 -奥运会 -tobacco -cigarette -普通药品 -"medical care"'
)

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


def _url_host(url: str) -> str:
    low = (url or "").lower().strip()
    if not low:
        return ""
    try:
        host = urlparse(low if "://" in low else f"https://{low}").netloc.lower().split(":")[0]
        return host
    except Exception:
        return ""


def is_snapshot_safe_host(host: str) -> bool:
    h = (host or "").lower().replace("www.", "")
    if not h:
        return False
    if h in {x.replace("www.", "") for x in SNAPSHOT_SAFE_HOSTS}:
        return True
    return any(h.endswith("." + s.replace("www.", "")) for s in ("google.com", "bing.com", "duckduckgo.com"))


def is_direct_forbidden_host(host: str) -> bool:
    """仅判定原生官网域名（直连拦截）。"""
    h = (host or "").lower().split(":")[0]
    if not h:
        return False
    bare = h.replace("www.", "")
    if bare in {x.replace("www.", "") for x in FORBIDDEN_HOSTS}:
        return True
    if bare.endswith(".gov.mn") or bare == "gov.mn":
        return True
    if bare.endswith(".shturl.cc") or bare == "shturl.cc":
        return True
    return False


def is_forbidden_url(url: str) -> bool:
    """合规拦截：只拦原生 gov.mn/黑名单域名直链；放行搜索引擎快照 URL。

    修改原因：此前「含 gov.mn 字符串即丢」导致 Google News / site 快照官方情报全丢。
    """
    low = (url or "").lower().strip()
    if not low:
        return True
    host = _url_host(low)
    # 快照/聚合域名：即使 query 含 site:police.gov.mn 也放行
    if is_snapshot_safe_host(host):
        return False
    # 媒体域名上的文章链接放行（正文可能提及 gov.mn）
    media_ok = (
        "montsame.mn", "gogo.mn", "ikon.mn", "news.mn", "mongolnews.mn",
        "unodc.org", "nncc626.com", "news.cn", "xinhuanet.com", "cgtn.com",
    )
    bare = host.replace("www.", "")
    if any(bare == m or bare.endswith("." + m) for m in media_ok):
        # 媒体站本身不是 gov.mn，但仍拦截虚构专栏路径（如 unodc.org/mongolia）
        for frag in FORBIDDEN_PATH_FRAGMENTS:
            if frag in low:
                return True
        if not is_direct_forbidden_host(host):
            return False
    if is_direct_forbidden_host(host):
        return True
    # 虚构专栏路径：仅在非快照场景拦截（避免误采假路径）
    for frag in FORBIDDEN_PATH_FRAGMENTS:
        if frag in low and not is_snapshot_safe_host(host):
            # shturl 始终拦；anti-narcotics 等虚构路径拦
            return True
    return False


def sanitize_store_url(url: str, title: str = "") -> str:
    """若解析结果落在原生 gov.mn，改写为 Google News 快照检索链，禁止直链入库/请求。"""
    u = (url or "").strip()
    if not u:
        return u
    host = _url_host(u)
    if not is_direct_forbidden_host(host):
        return u
    # 包装为新闻检索快照（不直连 gov.mn）
    q = f'site:{host.replace("www.", "")} {title or "narcotic OR мансууруулах OR 禁毒"}'
    return (
        "https://news.google.com/rss/search?"
        f"q={quote_plus(q)}&hl=en-US&gl=US&ceid=US:en"
    )


def build_core_site_search_queries(
    time_range: str = "1y",
    when: str | None = None,
) -> List[dict]:
    """清单内每个官网：合并关键词的 site: 检索 + 少量站内搜（快、全覆盖）。"""
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
            prio = 20
        elif domain.endswith("nncc626.com") or "news.cn" in domain or "xinhuanet" in domain:
            q = f"site:{domain} (蒙古国 OR 中蒙 OR 扎门乌德 OR 甘其毛都) ({query_core}){when_suffix}"
            prio = 70  # 修改原因：国内中文媒体后置低优先级
        elif "cgtn.com" in domain or "akipress.com" in domain:
            q = f"site:{domain} Mongolia ({query_core}){when_suffix}"
            prio = 40
        else:
            q = f"site:{domain} ({query_core}){when_suffix}"
            prio = 10 if any(x in domain for x in ("montsame", "gogo", "ikon", "news.mn")) else 20
        q = (q + SEARCH_NEGATIVE_EXCLUDE).strip()
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
            "priority": prio,
        })

    # 修改原因：先生成蒙古本土/国际源，国内中文源最后生成避免额度耗尽
    cn_domains = ("nncc626.com", "news.cn", "xinhuanet.com")
    non_cn_sources = [s for s in CORE_OFFICIAL_SOURCES if not any(d in s["base_url"] for d in cn_domains)]
    cn_sources = [s for s in CORE_OFFICIAL_SOURCES if any(d in s["base_url"] for d in cn_domains)]

    for source in non_cn_sources:
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

    # 修改原因：恢复 site:*.gov.mn 快照检索（8组，仅走 Google News，不直连官网）
    gov_snapshot_hosts = [
        ("police.gov.mn", "баривчилгаа OR цагдаа OR мансууруулах OR narcotic", 2),
        ("police.gov.mn", "фентанил OR метамфетамин OR хар тамхи OR seizure", 2),
        ("customs.gov.mn", "гааль OR мансууруулах OR seizure OR smuggling", 4),
        ("customs.gov.mn", "хил OR прекурсор OR border OR trafficking", 4),
        ("health.gov.mn", "мансууруулах OR сэтгэц OR prescription OR narcotic", 3),
        ("mmra.gov.mn", "мансууруулах OR прекурсор OR pharmaceutical", 3),
        ("mongolia.gov.mn", "мансууруулах OR хар тамхи OR anti-drug", 1),
        ("bpo.gov.mn", "хил OR мансууруулах OR border OR narcotic", 4),
    ]
    for host, qcore, sys_id in gov_snapshot_hosts:
        sys_names = {1: "国家级禁毒统筹协调机构", 2: "执法缉毒与刑事司法体系", 3: "行业监管与麻精药品体系", 4: "边境口岸缉毒查验体系"}
        tasks.append({
            "system_id": sys_id,
            "system_name": sys_names.get(sys_id, "国家级禁毒统筹协调机构"),
            "org_name": f"快照·{host}",
            "query": f"site:{host} ({qcore}){when_suffix}{SEARCH_NEGATIVE_EXCLUDE}",
            "hl": "en",
            "gl": "us",
            "ceid": "US:en",
            "engine": "google_news",
            "require_mongolia": True,
            "tier": "primary",
            "source_kind": "gov_snapshot",
            "snapshot_only": True,
            "priority": 15,
        })

    # 站内搜索：蒙古本土媒体（最高优先级）
    site_kw_mn = KW_MN[:6]
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
                "priority": 5,
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
                "priority": 5,
            })

    # 蒙通社/GOGO/IKON 多语种补盲
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
            "query": f"site:{domain} ({qcore}){when_suffix}{SEARCH_NEGATIVE_EXCLUDE}",
            "hl": hl,
            "gl": gl,
            "ceid": ceid,
            "engine": "google_news",
            "require_mongolia": False,
            "tier": "primary",
            "source_kind": "keyword_search",
            "priority": 10,
        })

    # 国内中文媒体检索最后生成（低优先级）
    for source in cn_sources:
        domain = (
            source["base_url"]
            .replace("https://", "")
            .replace("http://", "")
            .rstrip("/")
        )
        domain_bare = domain[4:] if domain.startswith("www.") else domain
        _task(source, domain_bare, zh_or, "zh-CN", "cn", "CN:zh-Hans", "中文")

    tasks.sort(key=lambda x: x.get("priority", 50))
    return tasks
