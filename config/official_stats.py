"""官方统计与 PDF 报表源配置（定稿合规版）。

修改原因：删除一切 site:*.gov.mn 快照检索；仅保留可直连公开源。
"""
from __future__ import annotations

from typing import List

from config.core_official import SEARCH_NEGATIVE_EXCLUDE

OFFICIAL_STAT_SOURCES = [
    {
        "system_id": 9,
        "system_name": "官方统计与年报体系",
        "org_name": "UNODC 世界毒品报告",
        "org_name_mn": "UNODC WDR",
        "base_url": "https://www.unodc.org",
        "seed_paths": [
            "/unodc/en/data-and-analysis/world-drug-report.html",
            "/unodc/en/data-and-analysis/wdr.html",
        ],
        "keywords_extra": ["Mongolia", "seizure", "narcotic"],
        "lang": "en",
        "source_type": "official_stats",
        "search_mode_only": True,
    },
    {
        "system_id": 9,
        "system_name": "官方统计与年报体系",
        "org_name": "联合国蒙古办事处",
        "org_name_mn": "UN Mongolia",
        "base_url": "https://mongolia.un.org",
        "seed_paths": ["/en/"],
        "keywords_extra": ["drug", "narcotic", "UNODC"],
        "lang": "en",
        "source_type": "official_stats",
        "search_mode_only": True,
    },
]

OFFICIAL_STAT_SEARCHES: List[dict] = [
    {
        "org_name": "统计搜索·中文官方数字",
        "query": (
            "\"蒙古国\" (检察院 OR 海关 OR 警察) (涉毒 OR 毒品 OR 芬太尼 OR 安纳咖) "
            "(案件 OR 查获 OR 同比 OR 统计)" + SEARCH_NEGATIVE_EXCLUDE
        ),
        "hl": "zh-CN", "gl": "cn", "ceid": "CN:zh-Hans",
        "engine": "google_news", "require_mongolia": True,
    },
    {
        "org_name": "统计搜索·海关查获",
        "query": (
            "Mongolia (Ulaanbaatar OR \"Zamyn-Uud\" OR customs) "
            "(narcotic OR fentanyl OR methamphetamine OR seizure)" + SEARCH_NEGATIVE_EXCLUDE
        ),
        "hl": "en", "gl": "us", "ceid": "US:en",
        "engine": "google_news", "require_mongolia": True,
    },
    {
        "org_name": "统计搜索·UNODC Mongolia",
        "query": (
            "UNODC Mongolia (drug OR narcotic OR seizure OR \"World Drug Report\")"
            + SEARCH_NEGATIVE_EXCLUDE
        ),
        "hl": "en", "gl": "us", "ceid": "US:en",
        "engine": "google_news", "require_mongolia": True,
    },
    {
        "org_name": "统计搜索·蒙通社缉毒数字",
        "query": (
            "site:montsame.mn (мансууруулах OR narcotic OR 缉毒 OR 芬太尼) "
            "(хувь OR percent OR 同比 OR 案件)" + SEARCH_NEGATIVE_EXCLUDE
        ),
        "hl": "en", "gl": "us", "ceid": "US:en",
        "engine": "google_news", "require_mongolia": False,
    },
    {
        "org_name": "统计搜索·检察院蒙语",
        "query": (
            "Монгол Улс (прокурор) (мансууруулах OR \"хар тамхи\") (хэрэг OR хувь)"
            + SEARCH_NEGATIVE_EXCLUDE
        ),
        "hl": "mn", "gl": "mn", "ceid": "MN:mn",
        "engine": "google_news", "require_mongolia": True,
    },
]

PDF_SEARCH_QUERIES: List[dict] = [
    {"org_name": "PDF·UNODC Mongolia", "query": 'site:unodc.org Mongolia (drug OR narcotic OR seizure) filetype:pdf'},
    {"org_name": "PDF·UNODC Cycle II Mongolia", "query": 'site:unodc.org Mongolia "Country Report" filetype:pdf'},
    {"org_name": "PDF·蒙古毒品国别公开", "query": '"Mongolia" (narcotic OR "drug trafficking" OR мансууруулах) filetype:pdf'},
    {"org_name": "PDF·蒙通社缉毒", "query": 'site:montsame.mn (мансууруулах OR narcotic OR 毒品) filetype:pdf'},
    {"org_name": "PDF·GOGO媒体", "query": 'site:gogo.mn (мансууруулах OR "хар тамхи") filetype:pdf'},
]

PDF_ALLOWED_DOMAINS = [
    "unodc.org", "www.unodc.org",
    "mongolia.un.org", "www.mongolia.un.org",
    "montsame.mn", "www.montsame.mn",
    "nncc626.com", "www.nncc626.com",
    "gogo.mn", "www.gogo.mn",
    "incb.org", "www.incb.org",
]

# PDF 安全上限（字节）
PDF_MAX_BYTES = 25 * 1024 * 1024
