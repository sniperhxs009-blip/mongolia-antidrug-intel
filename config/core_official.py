"""
文档指定的核心官方种子站点（近30日禁毒情报归集）。
其他平台能拿到近期官方消息，主要靠直采这些域名，而不是只靠 Google News 泛搜。
"""
from __future__ import annotations

from typing import List

# 文档第九节 URL 清单 + 可解析的真实官网入口
CORE_OFFICIAL_SOURCES: List[dict] = [
    {
        "system_id": 8,
        "system_name": "全国媒体与公开资讯",
        "org_name": "蒙通社 MONTSAME（核心官方通讯社）",
        "org_name_mn": "МОНЦАМЭ",
        "base_url": "https://www.montsame.mn",
        "seed_paths": ["/", "/mn/news", "/en/news"],
        "keywords_extra": [
            "мансууруулах", "хар тамхи", "наркотик", "narcotic",
            "methamphetamine", "anti-drug",
        ],
        "lang": "mn",
        "source_type": "official",
        "core_official": True,
    },
    {
        "system_id": 2,
        "system_name": "刑事缉毒执法体系",
        "org_name": "国家警察总局独立缉毒局（核心）",
        "org_name_mn": "Цагдаагийн ерөнхий газар",
        "base_url": "https://www.police.gov.mn",
        "seed_paths": ["/", "/mn/news", "/en/news"],
        "keywords_extra": [
            "мансууруулах", "хар тамхи", "наркотик", "метамфетамин",
        ],
        "lang": "mn",
        "source_type": "official",
        "core_official": True,
    },
    {
        "system_id": 4,
        "system_name": "边境海关缉毒查验体系",
        "org_name": "海关边境管控总局（核心）",
        "org_name_mn": "Гаалийн ерөнхий газар",
        "base_url": "https://www.customs.gov.mn",
        "seed_paths": ["/", "/mn/news", "/en/news"],
        "keywords_extra": [
            "мансууруулах", "хар тамхи", "наркотик", "контрабанд",
        ],
        "lang": "mn",
        "source_type": "official",
        "core_official": True,
    },
    {
        "system_id": 7,
        "system_name": "国际禁毒协作机构",
        "org_name": "UNODC 蒙古国项目（核心）",
        "org_name_mn": "UNODC Mongolia",
        "base_url": "https://www.unodc.org",
        "seed_paths": [
            "/mongolia/",
            "/unodc/en/easternasiaandpacific/mongolia.html",
            "/easternasiaandpacific/mongolia.html",
        ],
        "keywords_extra": [
            "Mongolia", "narcotic", "methamphetamine", "illicit drug",
        ],
        "lang": "en",
        "source_type": "official",
        "core_official": True,
    },
    {
        "system_id": 3,
        "system_name": "麻精药品与制毒原料行业监管体系",
        "org_name": "卫生部麻精药品监管（核心）",
        "org_name_mn": "ЭМЯ",
        "base_url": "https://www.gov.mn",
        "seed_paths": [
            "/mn/organization/moh",
            "/en/organization/moh",
        ],
        "keywords_extra": [
            "мансууруулах", "хар тамхи", "наркотик",
        ],
        "lang": "mn",
        "source_type": "official",
        "core_official": True,
    },
    {
        "system_id": 3,
        "system_name": "麻精药品与制毒原料行业监管体系",
        "org_name": "卫生部官网（health/mohs）",
        "org_name_mn": "Эрүүл мэндийн яам",
        "base_url": "https://www.mohs.mn",
        "seed_paths": ["/", "/news"],
        "keywords_extra": ["мансууруулах", "хар тамхи", "донтсон"],
        "lang": "mn",
        "source_type": "official",
        "core_official": True,
    },
    {
        "system_id": 1,
        "system_name": "国家级禁毒统筹委员会体系",
        "org_name": "国家禁毒协调委员会政府公示（zasag）",
        "org_name_mn": "Засгийн газар",
        "base_url": "https://zasag.mn",
        "seed_paths": [
            "/anti-narcotics",
            "/news",
        ],
        "keywords_extra": [
            "мансууруулах", "хар тамхи", "наркотик",
        ],
        "lang": "mn",
        "source_type": "official",
        "core_official": True,
    },
    {
        "system_id": 1,
        "system_name": "国家级禁毒统筹委员会体系",
        "org_name": "蒙古国政府门户（禁毒相关）",
        "org_name_mn": "www.gov.mn",
        "base_url": "https://www.gov.mn",
        "seed_paths": ["/mn/news"],
        "keywords_extra": ["мансууруулах", "хар тамхи", "наркотик"],
        "lang": "mn",
        "source_type": "official",
        "core_official": True,
    },
]


def build_core_site_search_queries(when: str = "30d") -> List[dict]:
    """针对核心官方域名的 site: 搜索（补官网直采盲区）。"""
    when_suffix = f" when:{when}" if when else ""
    drug = (
        "мансууруулах OR \"хар тамхи\" OR narcotic OR methamphetamine "
        "OR \"illegal drug\" OR \"drug trafficking\""
    )
    sites = [
        ("蒙通社站内", "montsame.mn", 8, "mn", "mn", "MN:mn"),
        ("警察总局站内", "police.gov.mn", 2, "mn", "mn", "MN:mn"),
        ("海关总局站内", "customs.gov.mn", 4, "mn", "mn", "MN:mn"),
        ("UNODC蒙古站内", "unodc.org", 7, "en-US", "us", "US:en"),
        ("政府门户站内", "gov.mn", 1, "mn", "mn", "MN:mn"),
        ("zasag政府站内", "zasag.mn", 1, "mn", "mn", "MN:mn"),
        ("卫生部站内", "mohs.mn", 3, "mn", "mn", "MN:mn"),
        ("总检察院站内", "prosecutor.mn", 2, "mn", "mn", "MN:mn"),
    ]
    tasks: List[dict] = []
    for name, site, sid, hl, gl, ceid in sites:
        q = f"site:{site} ({drug}){when_suffix}"
        tasks.append({
            "system_id": sid,
            "system_name": {
                1: "国家级禁毒统筹委员会体系",
                2: "刑事缉毒执法体系",
                3: "麻精药品与制毒原料行业监管体系",
                4: "边境海关缉毒查验体系",
                7: "国际禁毒协作机构",
                8: "全国媒体与公开资讯",
            }.get(sid, "官方核心源"),
            "org_name": f"核心官网搜索·{name}",
            "query": q,
            "hl": hl,
            "gl": gl,
            "ceid": ceid,
            "engine": "google_news",
            "require_mongolia": sid != 7,  # UNODC 页可能不带国名，另用过滤器
            "tier": "core_official",
            "source_kind": "official_site",
        })
    return tasks
