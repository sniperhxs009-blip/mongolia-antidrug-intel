ALLOW_GLOBAL_MEDIA = True
GLOBAL_COVERAGE_SOURCES = [
    {"org_name": "新华社", "base_url": "https://news.cn", "system_id": 10, "system_name": "全球媒体与国际禁毒机构"},
    {"org_name": "CGTN", "base_url": "https://cgtn.com", "system_id": 10, "system_name": "全球媒体与国际禁毒机构"},
    {"org_name": "AKIpress中亚通讯社", "base_url": "https://akipress.com", "system_id": 10, "system_name": "全球媒体与国际禁毒机构"},
]
GLOBAL_ALLOWED_DOMAINS = ["news.cn", "xinhuanet.com", "cgtn.com", "akipress.com"]


def build_global_search_queries(mode: str = "news", when: str = "1y"):
    when_suffix = f" when:{when}" if when else ""
    out = []
    for src in GLOBAL_COVERAGE_SOURCES:
        host = src["base_url"].replace("https://", "").replace("http://", "")
        out.append({
            "system_id": 10,
            "system_name": "全球媒体与国际禁毒机构",
            "org_name": f"全球·{src['org_name']}",
            "query": f"site:{host} Mongolia (drug OR narcotic OR 毒品){when_suffix}",
            "hl": "en",
            "gl": "us",
            "ceid": "US:en",
            "engine": "google_news",
            "require_mongolia": True,
            "tier": mode,
        })
    return out
