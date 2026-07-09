"""
官方统计与 PDF 报表源配置
覆盖：总检察院、海关、警察、统计局、UNODC、国家广播等
"""
from __future__ import annotations

from typing import List

# 官方统计门户（HTML 巡检种子）
OFFICIAL_STAT_SOURCES = [
    {
        "system_id": 9,
        "system_name": "官方统计与年报体系",
        "org_name": "总检察院",
        "org_name_mn": "Улсын ерөнхий прокурорын газар",
        "base_url": "https://www.prosecutor.mn",
        "seed_paths": ["/", "/mn", "/news", "/stat"],
        "keywords_extra": ["мансууруулах", "статистик", "тайлан"],
        "lang": "mn",
        "source_type": "official_stats",
    },
    {
        "system_id": 9,
        "system_name": "官方统计与年报体系",
        "org_name": "海关总局",
        "org_name_mn": "Гаалийн ерөнхий газар",
        "base_url": "https://www.customs.gov.mn",
        "seed_paths": ["/", "/mn", "/news"],
        "keywords_extra": ["мансууруулах", "хураан авсан", "контрабанд"],
        "lang": "mn",
        "source_type": "official_stats",
    },
    {
        "system_id": 9,
        "system_name": "官方统计与年报体系",
        "org_name": "国家警察总局",
        "org_name_mn": "Цагдаагийн ерөнхий газар",
        "base_url": "https://www.police.gov.mn",
        "seed_paths": ["/"],
        "keywords_extra": ["мансууруулах", "хар тамхи", "статистик"],
        "lang": "mn",
        "source_type": "official_stats",
    },
    {
        "system_id": 9,
        "system_name": "官方统计与年报体系",
        "org_name": "国家统计局 1212",
        "org_name_mn": "Үндэсний статистикийн хороо",
        "base_url": "https://www.1212.mn",
        "seed_paths": ["/"],
        "keywords_extra": ["гэмт хэрэг", "мансууруулах"],
        "lang": "mn",
        "source_type": "official_stats",
    },
    {
        "system_id": 9,
        "system_name": "官方统计与年报体系",
        "org_name": "法律信息中心",
        "org_name_mn": "Legalinfo",
        "base_url": "https://www.legalinfo.mn",
        "seed_paths": ["/"],
        "keywords_extra": ["мансууруулах", "сэтгэцэд"],
        "lang": "mn",
        "source_type": "official_stats",
    },
    {
        "system_id": 9,
        "system_name": "官方统计与年报体系",
        "org_name": "UNODC",
        "org_name_mn": "UNODC",
        "base_url": "https://www.unodc.org",
        "seed_paths": [
            "/unodc/en/data-and-analysis/wdr.html",
            "/easternasiaandpacific/index.html",
        ],
        "keywords_extra": ["Mongolia", "seizure", "narcotic"],
        "lang": "en",
        "source_type": "official_stats",
    },
    {
        "system_id": 9,
        "system_name": "官方统计与年报体系",
        "org_name": "蒙古国家广播 MNB",
        "org_name_mn": "МҮОНРТ",
        "base_url": "https://www.mnb.mn",
        "seed_paths": ["/"],
        "keywords_extra": ["мансууруулах", "прокурор", "статистик"],
        "lang": "mn",
        "source_type": "official_stats",
    },
]

# Google News / 网页搜索：专门追「官方统计数字」
OFFICIAL_STAT_SEARCHES: List[dict] = [
    {
        "org_name": "统计搜索·检察院涉毒案",
        "query": "Монгол прокурор мансууруулах бодис гэмт хэрэг статистик",
        "hl": "mn",
        "gl": "mn",
        "ceid": "MN:mn",
        "engine": "google_news",
        "require_mongolia": False,
    },
    {
        "org_name": "统计搜索·检察院同比",
        "query": "прокурорын байгууллага мансууруулах хэрэг хувь өс",
        "hl": "mn",
        "gl": "mn",
        "ceid": "MN:mn",
        "engine": "google_news",
        "require_mongolia": False,
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
        "org_name": "统计搜索·警察涉毒立案",
        "query": "ЦЕГ мансууруулах бодис гэмт хэрэг бүртгэгдсэн",
        "hl": "mn",
        "gl": "mn",
        "ceid": "MN:mn",
        "engine": "google_news",
        "require_mongolia": False,
    },
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
        "org_name": "统计搜索·UNODC Mongolia",
        "query": "UNODC Mongolia drug OR narcotic OR seizure OR \"World Drug Report\"",
        "hl": "en",
        "gl": "us",
        "ceid": "US:en",
        "engine": "google_news",
        "require_mongolia": True,
    },
]

# PDF 定向搜索（Google 网页结果页解析链接）
PDF_SEARCH_QUERIES: List[dict] = [
    {
        "org_name": "PDF·检察院统计",
        "query": 'site:prosecutor.mn мансууруулах filetype:pdf',
    },
    {
        "org_name": "PDF·海关年报",
        "query": 'site:customs.gov.mn (мансууруулах OR narcotic OR drug) filetype:pdf',
    },
    {
        "org_name": "PDF·警察毒情",
        "query": 'site:police.gov.mn (мансууруулах OR "хар тамхи") filetype:pdf',
    },
    {
        "org_name": "PDF·法律信息",
        "query": 'site:legalinfo.mn мансууруулах filetype:pdf',
    },
    {
        "org_name": "PDF·UNODC Mongolia",
        "query": 'site:unodc.org Mongolia (drug OR narcotic OR seizure) filetype:pdf',
    },
    {
        "org_name": "PDF·蒙古毒品国别",
        "query": '"Mongolia" (narcotic OR "drug trafficking" OR мансууруулах) filetype:pdf',
    },
    {
        "org_name": "PDF·OCIndex Mongolia",
        "query": 'site:ocindex.net Mongolia drug filetype:pdf',
    },
]

# 允许下载 PDF 的域名
PDF_ALLOWED_DOMAINS = [
    "prosecutor.mn", "www.prosecutor.mn",
    "customs.gov.mn", "www.customs.gov.mn",
    "police.gov.mn", "www.police.gov.mn",
    "legalinfo.mn", "www.legalinfo.mn",
    "unodc.org", "www.unodc.org",
    "gov.mn", "www.gov.mn",
    "1212.mn", "www.1212.mn",
    "ocindex.net", "www.ocindex.net",
    "mnb.mn", "www.mnb.mn", "news.mnb.mn",
    "parliament.mn", "www.parliament.mn",
]
