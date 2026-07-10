ALLOW_FORUM_DOMAINS = True
FORUM_WHITELIST = ["bluelight.org", "drugs-forum.com"]
FORUM_BLACKLIST = []
FORUM_ALLOWED_DOMAINS = list(FORUM_WHITELIST)


def build_forum_search_queries(mode: str = "news", when: str = "1y"):
    """论坛补充检索（精简版）。"""
    return [
        {
            "system_id": 11,
            "system_name": "全球论坛社区与补充搜索",
            "org_name": "Reddit·Mongolia drugs",
            "query": f"Mongolia (narcotic OR fentanyl OR meth) when:{when}",
            "hl": "en",
            "gl": "us",
            "ceid": "US:en",
            "engine": "reddit_search",
            "source_kind": "forum",
            "require_mongolia": True,
            "tier": mode,
        }
    ]
