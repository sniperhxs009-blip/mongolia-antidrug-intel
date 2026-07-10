"""
修正后核心官方种子：仅真实挂靠站点，禁止虚构专栏路径。

已剔除：shturl.cc、zasag.mn/anti-narcotics、health.gov.mn/drug-control、
unodc.org/mongolia/、customs.gov.mn（国内 IP 常 SSL 超时）。
"""
from __future__ import annotations

from typing import List

# 禁止程序自动拼接的虚构路径片段
FORBIDDEN_PATH_FRAGMENTS = (
    "/anti-narcotics",
    "/drug-control",
    "/antidrug",
    "/anti_drug",
    "shturl.cc",
)

# 蒙/英双语言入库白名单（命中才可入库；与 filters 强词对齐）
CORE_DRUG_WHITELIST_MN = [
    "хар тамхи",
    "мансууруулах бодис",
    "мансууруулах",
    "тэмцэх хар тамхи",
    "газар хил худалдаа",
    "сэргээх төв",
    "синтетик мансууруулах бодис",
    "наркотик",
]
CORE_DRUG_WHITELIST_EN = [
    "narcotics",
    "narcotic",
    "drug seizure",
    "fentanyl",
    "synthetic cannabis",
    "cross-border trafficking",
    "drug rehabilitation",
    "UNODC Mongolia",
    "methamphetamine",
    "illicit drug",
    "anti-drug",
]

CORE_OFFICIAL_SOURCES: List[dict] = [
    # 1) 蒙通社 — 唯一高频综合涉毒新闻源
    {
        "system_id": 8,
        "system_name": "全国媒体与公开资讯",
        "org_name": "蒙通社 MONTSAME",
        "org_name_mn": "МОНЦАМЭ",
        "base_url": "https://montsame.mn",
        "seed_paths": ["/", "/mn", "/en"],
        "keywords_extra": CORE_DRUG_WHITELIST_MN + CORE_DRUG_WHITELIST_EN,
        "lang": "mn",
        "source_type": "official",
        "core_official": True,
        "priority": 1,
    },
    # 2) 警察总局 — 缉毒局通报挂靠主站（无独立缉毒局官网）
    {
        "system_id": 2,
        "system_name": "刑事缉毒执法体系",
        "org_name": "国家警察总局",
        "org_name_mn": "Цагдаагийн ерөнхий газар",
        "base_url": "https://www.police.gov.mn",
        "seed_paths": ["/", "/mn", "/en"],
        "keywords_extra": CORE_DRUG_WHITELIST_MN + ["баривчилгаа", "метамфетамин"],
        "lang": "mn",
        "source_type": "official",
        "core_official": True,
        "priority": 1,
    },
    # 3) 政府主站 — 禁毒委员会会议/顶层政策挂靠
    {
        "system_id": 1,
        "system_name": "国家级禁毒统筹委员会体系",
        "org_name": "蒙古国政府主站",
        "org_name_mn": "mongolia.gov.mn",
        "base_url": "https://mongolia.gov.mn",
        "seed_paths": ["/", "/news"],
        "keywords_extra": CORE_DRUG_WHITELIST_MN + ["мансууруулах бодисын эсрэг"],
        "lang": "mn",
        "source_type": "official",
        "core_official": True,
        "priority": 1,
    },
    # 4) 药品器械监管局 — 麻精药品管控
    {
        "system_id": 3,
        "system_name": "麻精药品与制毒原料行业监管体系",
        "org_name": "药品医疗器械监管局 MMRA",
        "org_name_mn": "MMRA",
        "base_url": "https://mmra.gov.mn",
        "seed_paths": ["/"],
        "keywords_extra": CORE_DRUG_WHITELIST_MN + ["зохицуулалттай эм", "прекурсор"],
        "lang": "mn",
        "source_type": "official",
        "core_official": True,
        "priority": 2,
    },
    # 5) 卫生部主站
    {
        "system_id": 3,
        "system_name": "麻精药品与制毒原料行业监管体系",
        "org_name": "卫生部 MOHS",
        "org_name_mn": "Эрүүл мэндийн яам",
        "base_url": "https://www.mohs.mn",
        "seed_paths": ["/"],
        "keywords_extra": CORE_DRUG_WHITELIST_MN + ["донтсон", "сэргээх төв"],
        "lang": "mn",
        "source_type": "official",
        "core_official": True,
        "priority": 2,
    },
    # 6) UNODC 全球站 — 禁止 /mongolia/ 虚构子站，靠内容筛 Mongolia
    {
        "system_id": 7,
        "system_name": "国际禁毒协作机构",
        "org_name": "UNODC 全球站（筛 Mongolia）",
        "org_name_mn": "UNODC",
        "base_url": "https://www.unodc.org",
        "seed_paths": [
            "/easternasiaandpacific/index.html",
            "/unodc/en/easternasiaandpacific/index.html",
            "/unodc/en/drug-trafficking/index.html",
        ],
        "keywords_extra": ["Mongolia", "UNODC Mongolia"] + CORE_DRUG_WHITELIST_EN,
        "lang": "en",
        "source_type": "official",
        "core_official": True,
        "require_mongolia": True,
        "priority": 2,
    },
    # 7) 边防总局
    {
        "system_id": 4,
        "system_name": "边境海关缉毒查验体系",
        "org_name": "边防总局 BPO",
        "org_name_mn": "Хилийн цэргийн ерөнхий газар",
        "base_url": "https://bpo.gov.mn",
        "seed_paths": ["/"],
        "keywords_extra": CORE_DRUG_WHITELIST_MN + ["хил", "контрабанд"],
        "lang": "mn",
        "source_type": "official",
        "core_official": True,
        "priority": 2,
    },
    # 8) 海关电子服务站（替代 customs.gov.mn）
    {
        "system_id": 4,
        "system_name": "边境海关缉毒查验体系",
        "org_name": "海关电子服务站 eCustoms",
        "org_name_mn": "eCustoms",
        "base_url": "https://ecustoms.mn",
        "seed_paths": ["/"],
        "keywords_extra": CORE_DRUG_WHITELIST_MN + ["гааль", "контрабанд"],
        "lang": "mn",
        "source_type": "official",
        "core_official": True,
        "priority": 2,
    },
    # 9) 外交部 — 国际禁毒协作
    {
        "system_id": 7,
        "system_name": "国际禁毒协作机构",
        "org_name": "外交部 MOFA",
        "org_name_mn": "ГХЯ",
        "base_url": "https://mofa.gov.mn",
        "seed_paths": ["/"],
        "keywords_extra": CORE_DRUG_WHITELIST_MN + CORE_DRUG_WHITELIST_EN,
        "lang": "mn",
        "source_type": "official",
        "core_official": True,
        "priority": 3,
    },
    # 10) 国家情报局
    {
        "system_id": 2,
        "system_name": "刑事缉毒执法体系",
        "org_name": "国家情报局 GIA",
        "org_name_mn": "Тагнуулын ерөнхий газар",
        "base_url": "https://gia.gov.mn",
        "seed_paths": ["/"],
        "keywords_extra": CORE_DRUG_WHITELIST_MN,
        "lang": "mn",
        "source_type": "official",
        "core_official": True,
        "priority": 3,
    },
]


def is_forbidden_url(url: str) -> bool:
    low = (url or "").lower()
    return any(f in low for f in FORBIDDEN_PATH_FRAGMENTS)


def build_core_site_search_queries(when: str = "30d") -> List[dict]:
    """针对真实挂靠域名的 site: 搜索（补官网直采盲区）。"""
    when_suffix = f" when:{when}" if when else ""
    drug = (
        '"хар тамхи" OR "мансууруулах бодис" OR мансууруулах OR narcotics OR '
        '"drug seizure" OR fentanyl OR methamphetamine OR "illicit drug"'
    )
    sites = [
        ("蒙通社", "montsame.mn", 8, "mn", "mn", "MN:mn"),
        ("警察总局", "police.gov.mn", 2, "mn", "mn", "MN:mn"),
        ("政府主站", "mongolia.gov.mn", 1, "mn", "mn", "MN:mn"),
        ("药品监管局", "mmra.gov.mn", 3, "mn", "mn", "MN:mn"),
        ("卫生部", "mohs.mn", 3, "mn", "mn", "MN:mn"),
        ("UNODC", "unodc.org", 7, "en-US", "us", "US:en"),
        ("边防总局", "bpo.gov.mn", 4, "mn", "mn", "MN:mn"),
        ("海关电子站", "ecustoms.mn", 4, "mn", "mn", "MN:mn"),
        ("外交部", "mofa.gov.mn", 7, "mn", "mn", "MN:mn"),
        ("情报局", "gia.gov.mn", 2, "mn", "mn", "MN:mn"),
    ]
    names = {
        1: "国家级禁毒统筹委员会体系",
        2: "刑事缉毒执法体系",
        3: "麻精药品与制毒原料行业监管体系",
        4: "边境海关缉毒查验体系",
        7: "国际禁毒协作机构",
        8: "全国媒体与公开资讯",
    }
    tasks: List[dict] = []
    for name, site, sid, hl, gl, ceid in sites:
        q = f"site:{site} ({drug}){when_suffix}"
        if site == "unodc.org":
            q = f"site:unodc.org Mongolia ({drug}){when_suffix}"
        tasks.append({
            "system_id": sid,
            "system_name": names.get(sid, "官方核心源"),
            "org_name": f"核心官网搜索·{name}",
            "query": q,
            "hl": hl,
            "gl": gl,
            "ceid": ceid,
            "engine": "google_news",
            "require_mongolia": True,
            "tier": "core_official",
            "source_kind": "official_site",
        })
    return tasks
