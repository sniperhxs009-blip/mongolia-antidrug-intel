"""
全球主流媒体 + 国际禁毒组织/机构
专门捕捉「境外报道蒙古国毒情」的新闻、报告与通稿
"""
from __future__ import annotations

from typing import List

SYSTEM_ID = 10
SYSTEM_NAME = "全球媒体与国际禁毒机构"

# —— 国际禁毒组织 / 执法协作机构（官网种子）——
INTL_ORG_SOURCES = [
    {
        "system_id": SYSTEM_ID,
        "system_name": SYSTEM_NAME,
        "org_name": "UNODC 联合国毒品和犯罪问题办公室",
        "base_url": "https://www.unodc.org",
        "seed_paths": [
            "/unodc/en/frontpage.html",
            "/easternasiaandpacific/index.html",
            "/unodc/en/data-and-analysis/wdr.html",
        ],
        "keywords_extra": ["Mongolia", "narcotic", "trafficking"],
        "lang": "en",
        "source_type": "intl_org",
    },
    {
        "system_id": SYSTEM_ID,
        "system_name": SYSTEM_NAME,
        "org_name": "INCB 国际麻醉品管制局",
        "base_url": "https://www.incb.org",
        "seed_paths": ["/", "/incb/en/news.html"],
        "keywords_extra": ["Mongolia", "narcotic"],
        "lang": "en",
        "source_type": "intl_org",
    },
    {
        "system_id": SYSTEM_ID,
        "system_name": SYSTEM_NAME,
        "org_name": "WHO 世界卫生组织",
        "base_url": "https://www.who.int",
        "seed_paths": ["/"],
        "keywords_extra": ["Mongolia", "substance", "drug"],
        "lang": "en",
        "source_type": "intl_org",
    },
    {
        "system_id": SYSTEM_ID,
        "system_name": SYSTEM_NAME,
        "org_name": "WCO 世界海关组织",
        "base_url": "https://www.wcoomd.org",
        "seed_paths": ["/en/media/newsroom.aspx"],
        "keywords_extra": ["Mongolia", "drug", "synthetic"],
        "lang": "en",
        "source_type": "intl_org",
    },
    {
        "system_id": SYSTEM_ID,
        "system_name": SYSTEM_NAME,
        "org_name": "INTERPOL 国际刑警组织",
        "base_url": "https://www.interpol.int",
        "seed_paths": ["/en/News-and-Events/News"],
        "keywords_extra": ["Mongolia", "drug", "trafficking"],
        "lang": "en",
        "source_type": "intl_org",
    },
    {
        "system_id": SYSTEM_ID,
        "system_name": SYSTEM_NAME,
        "org_name": "EMCDDA / EUDA 欧盟毒品署",
        "base_url": "https://www.euda.europa.eu",
        "seed_paths": ["/"],
        "keywords_extra": ["Mongolia", "NPS", "drug"],
        "lang": "en",
        "source_type": "intl_org",
    },
    {
        "system_id": SYSTEM_ID,
        "system_name": SYSTEM_NAME,
        "org_name": "US INL 国际禁毒执法事务局",
        "base_url": "https://www.state.gov",
        "seed_paths": ["/inl/", "/reports/2025-international-narcotics-control-strategy-report/"],
        "keywords_extra": ["Mongolia", "narcotics"],
        "lang": "en",
        "source_type": "intl_org",
    },
    {
        "system_id": SYSTEM_ID,
        "system_name": SYSTEM_NAME,
        "org_name": "DEA 美国缉毒署",
        "base_url": "https://www.dea.gov",
        "seed_paths": ["/"],
        "keywords_extra": ["Mongolia", "trafficking"],
        "lang": "en",
        "source_type": "intl_org",
    },
    {
        "system_id": SYSTEM_ID,
        "system_name": SYSTEM_NAME,
        "org_name": "Global Initiative / OC-Index",
        "base_url": "https://ocindex.net",
        "seed_paths": ["/country/mongolia"],
        "keywords_extra": ["Mongolia", "drug"],
        "lang": "en",
        "source_type": "intl_org",
    },
]

# —— 全球主流媒体（官网种子，配合搜索）——
GLOBAL_MEDIA_SOURCES = [
    {"org_name": "Reuters", "base_url": "https://www.reuters.com", "seed_paths": ["/"]},
    {"org_name": "AP News", "base_url": "https://apnews.com", "seed_paths": ["/"]},
    {"org_name": "AFP / France24", "base_url": "https://www.france24.com", "seed_paths": ["/"]},
    {"org_name": "BBC", "base_url": "https://www.bbc.com", "seed_paths": ["/"]},
    {"org_name": "The Guardian", "base_url": "https://www.theguardian.com", "seed_paths": ["/"]},
    {"org_name": "CNN", "base_url": "https://edition.cnn.com", "seed_paths": ["/"]},
    {"org_name": "Al Jazeera", "base_url": "https://www.aljazeera.com", "seed_paths": ["/"]},
    {"org_name": "The Diplomat", "base_url": "https://thediplomat.com", "seed_paths": ["/"]},
    {"org_name": "Radio Free Asia", "base_url": "https://www.rfa.org", "seed_paths": ["/"]},
    {"org_name": "VOA", "base_url": "https://www.voanews.com", "seed_paths": ["/"]},
    {"org_name": "Nikkei Asia", "base_url": "https://asia.nikkei.com", "seed_paths": ["/"]},
    {"org_name": "South China Morning Post", "base_url": "https://www.scmp.com", "seed_paths": ["/"]},
    {"org_name": "Xinhua 新华社", "base_url": "https://english.news.cn", "seed_paths": ["/"]},
    {"org_name": "CGTN", "base_url": "https://www.cgtn.com", "seed_paths": ["/"]},
    {"org_name": "TASS", "base_url": "https://tass.com", "seed_paths": ["/"]},
    {"org_name": "RIA Novosti", "base_url": "https://ria.ru", "seed_paths": ["/"]},
    {"org_name": "Kyodo / Japan Times", "base_url": "https://www.japantimes.co.jp", "seed_paths": ["/"]},
    {"org_name": "Yonhap", "base_url": "https://en.yna.co.kr", "seed_paths": ["/"]},
    {"org_name": "AKIpress", "base_url": "https://akipress.com", "seed_paths": ["/"]},
    {"org_name": "VICE", "base_url": "https://www.vice.com", "seed_paths": ["/"]},
]

def _media_as_sources() -> List[dict]:
    out = []
    for m in GLOBAL_MEDIA_SOURCES:
        out.append({
            "system_id": SYSTEM_ID,
            "system_name": SYSTEM_NAME,
            "org_name": m["org_name"],
            "org_name_mn": "",
            "base_url": m["base_url"],
            "seed_paths": m.get("seed_paths") or ["/"],
            "keywords_extra": ["Mongolia", "drug", "narcotic", "methamphetamine"],
            "lang": "en",
            "source_type": "global_media",
        })
    return out


GLOBAL_COVERAGE_SOURCES = INTL_ORG_SOURCES + _media_as_sources()

# 域名白名单补充
GLOBAL_ALLOWED_DOMAINS = [
    # 国际组织
    "unodc.org", "www.unodc.org",
    "incb.org", "www.incb.org",
    "who.int", "www.who.int",
    "wcoomd.org", "www.wcoomd.org",
    "interpol.int", "www.interpol.int",
    "euda.europa.eu", "www.euda.europa.eu", "emcdda.europa.eu", "www.emcdda.europa.eu",
    "state.gov", "www.state.gov",
    "dea.gov", "www.dea.gov",
    "ocindex.net", "www.ocindex.net",
    "globalinitiative.net", "www.globalinitiative.net",
    "incb.org",
    # 通讯社 / 主流媒体
    "reuters.com", "www.reuters.com",
    "apnews.com", "www.apnews.com",
    "afp.com", "www.afp.com",
    "france24.com", "www.france24.com",
    "bbc.com", "www.bbc.com", "bbc.co.uk", "www.bbc.co.uk",
    "theguardian.com", "www.theguardian.com",
    "cnn.com", "edition.cnn.com", "www.cnn.com",
    "aljazeera.com", "www.aljazeera.com",
    "thediplomat.com", "www.thediplomat.com",
    "rfa.org", "www.rfa.org",
    "voanews.com", "www.voanews.com",
    "asia.nikkei.com", "nikkei.com",
    "scmp.com", "www.scmp.com",
    "news.cn", "english.news.cn", "www.news.cn", "xinhuanet.com", "www.xinhuanet.com",
    "cgtn.com", "www.cgtn.com",
    "tass.com", "www.tass.com", "tass.ru",
    "ria.ru", "www.ria.ru",
    "japantimes.co.jp", "www.japantimes.co.jp",
    "yna.co.kr", "en.yna.co.kr",
    "akipress.com", "www.akipress.com",
    "vice.com", "www.vice.com",
    "bloomberg.com", "www.bloomberg.com",
    "ft.com", "www.ft.com",
    "nytimes.com", "www.nytimes.com",
    "washingtonpost.com", "www.washingtonpost.com",
    "wsj.com", "www.wsj.com",
    "economist.com", "www.economist.com",
    "time.com", "www.time.com",
    "newsweek.com", "www.newsweek.com",
    "dw.com", "www.dw.com",
    "euronews.com", "www.euronews.com",
    "politico.com", "www.politico.eu",
    "foreignpolicy.com", "www.foreignpolicy.com",
    "cfr.org", "www.cfr.org",
    "brookings.edu", "www.brookings.edu",
    "rand.org", "www.rand.org",
    "crisisgroup.org", "www.crisisgroup.org",
    # 区域
    "asiatimes.com", "www.asiatimes.com",
    "eurasianet.org", "www.eurasianet.org",
    "themoscowtimes.com", "www.themoscowtimes.com",
    "scmp.com",
    "koreaherald.com", "www.koreaherald.com",
    "stripes.com", "www.stripes.com",
]


def build_global_search_queries(mode: str = "full", when: str = "") -> List[dict]:
    """生成全球媒体 + 国际机构对蒙古毒情的搜索任务。"""
    tasks: List[dict] = []
    news_mode = mode == "news"
    when_suffix = f" when:{when}" if when else ""

    # 核心毒品语境（强制与 Mongolia 同现）
    drug_core = (
        "drug OR narcotic OR methamphetamine OR fentanyl OR heroin OR cannabis OR "
        "\"drug trafficking\" OR \"drug smuggling\" OR \"synthetic drug\" OR NPS OR "
        "\"illicit drug\" OR \"controlled substance\""
    )

    # —— 国际组织定向 ——
    org_sites_full = [
        ("UNODC", "site:unodc.org"),
        ("INCB", "site:incb.org"),
        ("WCO", "site:wcoomd.org"),
        ("INTERPOL", "site:interpol.int"),
        ("WHO", "site:who.int"),
        ("EUDA", "site:euda.europa.eu OR site:emcdda.europa.eu"),
        ("US-State-INL", "site:state.gov"),
        ("OCIndex", "site:ocindex.net OR site:globalinitiative.net"),
    ]
    org_sites_news = [
        ("UNODC", "site:unodc.org"),
        ("INCB", "site:incb.org"),
        ("WCO", "site:wcoomd.org"),
        ("INTERPOL", "site:interpol.int"),
        ("US-State-INL", "site:state.gov"),
    ]
    for name, site in (org_sites_news if news_mode else org_sites_full):
        tasks.append({
            "system_id": SYSTEM_ID,
            "system_name": SYSTEM_NAME,
            "org_name": f"国际机构·{name}",
            "query": f"Mongolia ({drug_core}) {site}{when_suffix}",
            "hl": "en",
            "gl": "us",
            "ceid": "US:en",
            "engine": "google_news",
            "require_mongolia": True,
            "tier": "news" if news_mode else "full",
        })

    # —— 全球主流媒体定向 ——
    media_sites_full = [
        ("Reuters", "site:reuters.com"),
        ("AP", "site:apnews.com"),
        ("BBC", "site:bbc.com OR site:bbc.co.uk"),
        ("Guardian", "site:theguardian.com"),
        ("CNN", "site:cnn.com"),
        ("AlJazeera", "site:aljazeera.com"),
        ("Diplomat", "site:thediplomat.com"),
        ("RFA", "site:rfa.org"),
        ("VOA", "site:voanews.com"),
        ("Nikkei", "site:asia.nikkei.com"),
        ("SCMP", "site:scmp.com"),
        ("Xinhua", "site:news.cn OR site:xinhuanet.com"),
        ("CGTN", "site:cgtn.com"),
        ("TASS", "site:tass.com"),
        ("RIA", "site:ria.ru"),
        ("JapanTimes", "site:japantimes.co.jp"),
        ("Yonhap", "site:yna.co.kr"),
        ("AKIpress", "site:akipress.com"),
        ("VICE", "site:vice.com"),
        ("Bloomberg", "site:bloomberg.com"),
        ("NYT", "site:nytimes.com"),
        ("DW", "site:dw.com"),
        ("Eurasianet", "site:eurasianet.org"),
        ("France24", "site:france24.com"),
    ]
    media_sites_news = [
        ("Reuters", "site:reuters.com"),
        ("AP", "site:apnews.com"),
        ("BBC", "site:bbc.com OR site:bbc.co.uk"),
        ("Diplomat", "site:thediplomat.com"),
        ("RFA", "site:rfa.org"),
        ("SCMP", "site:scmp.com"),
        ("Xinhua", "site:news.cn OR site:xinhuanet.com"),
        ("TASS", "site:tass.com"),
        ("AKIpress", "site:akipress.com"),
        ("VICE", "site:vice.com"),
        ("Bloomberg", "site:bloomberg.com"),
        ("Eurasianet", "site:eurasianet.org"),
    ]
    for name, site in (media_sites_news if news_mode else media_sites_full):
        tasks.append({
            "system_id": SYSTEM_ID,
            "system_name": SYSTEM_NAME,
            "org_name": f"全球媒体·{name}",
            "query": f"Mongolia ({drug_core}) {site}{when_suffix}",
            "hl": "en",
            "gl": "us",
            "ceid": "US:en",
            "engine": "google_news",
            "require_mongolia": True,
            "tier": "news" if news_mode else "full",
        })

    # —— 综合国际英语（不限站点，靠 Mongolia+毒品强约束）——
    intl_en = [
        "Mongolia (\"drug trafficking\" OR \"drug smuggling\" OR \"narcotics\" OR methamphetamine)",
        "Mongolia (fentanyl OR nitazene OR \"synthetic cannabinoid\" OR NPS)",
        "\"Ulaanbaatar\" (drug OR narcotic OR methamphetamine OR heroin)",
        "Mongolia (\"World Drug Report\" OR UNODC OR INCB OR INTERPOL)",
        "Mongolia (\"customs seizure\" OR \"drug bust\" OR \"anti-drug\")",
    ]
    if news_mode:
        intl_en = intl_en[:3]
    for q in intl_en:
        tasks.append({
            "system_id": SYSTEM_ID,
            "system_name": SYSTEM_NAME,
            "org_name": f"国际综合·{q.split('(')[0].strip()[:14]}",
            "query": f"{q}{when_suffix}",
            "hl": "en",
            "gl": "us",
            "ceid": "US:en",
            "engine": "google_news",
            "require_mongolia": True,
            "tier": "news" if news_mode else "full",
        })

    # —— 中文国际报道 ——
    zh_intl = [
        "\"蒙古国\" (毒品 OR 缉毒 OR 贩毒 OR 冰毒 OR 芬太尼) (路透 OR 美联社 OR 新华社 OR 法新社 OR 联合国)",
        "\"蒙古国\" (UNODC OR 国际刑警 OR 世界海关) (毒品 OR 缉毒 OR 走私)",
        "\"乌兰巴托\" (毒品 OR 冰毒 OR 海洛因 OR 缉毒)",
    ]
    if news_mode:
        zh_intl = zh_intl[:2]
    for g in zh_intl:
        tasks.append({
            "system_id": SYSTEM_ID,
            "system_name": SYSTEM_NAME,
            "org_name": f"国际中文·{g.split('(')[0].replace(chr(34),'')[:12]}",
            "query": f"{g}{when_suffix}",
            "hl": "zh-CN",
            "gl": "cn",
            "ceid": "CN:zh-Hans",
            "engine": "google_news",
            "require_mongolia": True,
            "tier": "news" if news_mode else "full",
        })

    # —— 俄语国际（俄媒常报蒙俄口岸）——
    ru_intl = [
        "Монголия (наркотик OR метамфетамин OR фентанил OR контрабанда)",
        "Улан-Батор (наркотик OR метамфетамин)",
    ]
    if not news_mode:
        for q in ru_intl:
            tasks.append({
                "system_id": SYSTEM_ID,
                "system_name": SYSTEM_NAME,
                "org_name": f"国际俄语·{q[:16]}",
                "query": f"{q}{when_suffix}",
                "hl": "ru",
                "gl": "ru",
                "ceid": "RU:ru",
                "engine": "google_news",
                "require_mongolia": True,
                "tier": "full",
            })

    return tasks
