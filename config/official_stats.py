"""
官方统计与 PDF 报表源配置（全量修复版）

禁止蒙古本土 .gov.mn / customs.gov.mn / police.gov.mn 等直连探测。
统计数字仅从国内可直连公开源与 Google News 检索间接获取。
"""
from __future__ import annotations

from typing import List

# 官方统计门户（仅合法可直连）
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

# Google News：追「官方统计数字」公开报道（结果再经域名白名单过滤）
OFFICIAL_STAT_SEARCHES: List[dict] = [
    {
        "org_name": "统计搜索·中文官方数字",
        "query": "\"蒙古国\" (检察院 OR 海关 OR 警察) (涉毒 OR 毒品) (案件 OR 查获 OR 同比 OR 统计)",
        "hl": "zh-CN",
        "gl": "cn",
        "ceid": "CN:zh-Hans",
        "engine": "google_news",
        "require_mongolia": True,
    },
    {
        "org_name": "统计搜索·海关查获",
        "query": "Mongolia customs narcotic OR drug seizure OR мансууруулах гааль",
        "hl": "en",
        "gl": "us",
        "ceid": "US:en",
        "engine": "google_news",
        "require_mongolia": True,
    },
    {
        "org_name": "统计搜索·UNODC Mongolia",
        "query": "UNODC Mongolia drug OR narcotic OR seizure OR \"World Drug Report\"",
        "hl": "en",
        "gl": "us",
        "ceid": "US:en",
        "engine": "google_news",
        "require_mongolia": True,
    },
    {
        "org_name": "统计搜索·蒙通社缉毒数字",
        "query": "site:montsame.mn (наркотик OR narcotic OR мансууруулах OR 缉毒 OR 毒品)",
        "hl": "en",
        "gl": "us",
        "ceid": "US:en",
        "engine": "google_news",
        "require_mongolia": False,
    },
]

# PDF 定向搜索（禁止 site:*.gov.mn）
PDF_SEARCH_QUERIES: List[dict] = [
    {
        "org_name": "PDF·UNODC Mongolia",
        "query": 'site:unodc.org Mongolia (drug OR narcotic OR seizure) filetype:pdf',
    },
    {
        "org_name": "PDF·UNODC Cycle II Mongolia",
        "query": 'site:unodc.org Mongolia "Country Report" filetype:pdf',
    },
    {
        "org_name": "PDF·蒙古毒品国别公开",
        "query": '"Mongolia" (narcotic OR "drug trafficking" OR мансууруулах) filetype:pdf',
    },
]

# 允许下载 PDF 的域名（不含蒙古 .gov.mn）
PDF_ALLOWED_DOMAINS = [
    "unodc.org", "www.unodc.org",
    "mongolia.un.org", "www.mongolia.un.org",
    "montsame.mn", "www.montsame.mn",
    "nncc626.com", "www.nncc626.com",
]
