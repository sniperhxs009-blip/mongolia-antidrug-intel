"""官方统计配置（对齐完整代码.txt，并补齐采集器所需字段）"""
OFFICIAL_STAT_SOURCES = [
    {
        "system_id": 9,
        "system_name": "官方统计与年报体系",
        "org_name": "UNODC 世界毒品报告",
        "org_name_mn": "UNODC WDR",
        "base_url": "https://www.unodc.org",
        "seed_paths": ["/unodc/en/data-and-analysis/world-drug-report.html"],
        "keywords_extra": ["Mongolia", "seizure", "narcotic"],
        "lang": "en",
        "source_type": "official_stats",
    },
]

OFFICIAL_STAT_SEARCHES = [
    {
        "org_name": "UNODC年度报告",
        "query": "Mongolia drug statistics when:1y",
        "hl": "en",
        "gl": "us",
        "ceid": "US:en",
        "engine": "google_news",
        "require_mongolia": True,
    },
    {
        "org_name": "蒙通社缉毒统计",
        "query": "site:montsame.mn (мансууруулах OR narcotic OR 缉毒) when:1y",
        "hl": "en",
        "gl": "us",
        "ceid": "US:en",
        "engine": "google_news",
        "require_mongolia": False,
    },
]

PDF_ALLOWED_DOMAINS = ["unodc.org", "www.unodc.org", "montsame.mn", "www.montsame.mn"]

PDF_SEARCH_QUERIES = [
    {
        "org_name": "PDF·Mongolia narcotics",
        "query": "Mongolia narcotics report filetype:pdf",
    },
    {
        "org_name": "PDF·UNODC Mongolia",
        "query": "site:unodc.org Mongolia (drug OR narcotic) filetype:pdf",
    },
]
