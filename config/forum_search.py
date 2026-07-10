"""
论坛 / 社区 / 补充搜索引擎配置
覆盖：Reddit、全球论坛讨论、DuckDuckGo/Bing 新闻 RSS 等
严格近期时效由调用方传入 when（如 7d / 30d）
"""
from __future__ import annotations

from typing import List

SYSTEM_ID = 11
SYSTEM_NAME = "全球论坛社区与补充搜索"

# 允许入库的论坛/社区域名
FORUM_ALLOWED_DOMAINS = [
    "reddit.com", "www.reddit.com", "old.reddit.com",
    "quora.com", "www.quora.com",
    "stackexchange.com", "stackoverflow.com",
    "medium.com", "www.medium.com",
    "substack.com",
    "discord.com", "www.discord.com",
    "telegram.org",
    "4chan.org",
    "disqus.com",
    "tieba.baidu.com",
    "zhihu.com", "www.zhihu.com",
    "douban.com", "www.douban.com",
    "v2ex.com", "www.v2ex.com",
    "hackernews.com", "news.ycombinator.com",
    "lesswrong.com",
    "bluelight.org", "www.bluelight.org",  # 药物讨论论坛（公开帖）
    "drugs-forum.com", "www.drugs-forum.com",
    "erowid.org", "www.erowid.org",
]

DRUG_CORE = (
    "drug OR narcotic OR methamphetamine OR meth OR heroin OR cannabis OR marijuana OR "
    "fentanyl OR ketamine OR \"drug trafficking\" OR \"drug smuggling\" OR NPS OR "
    "\"synthetic cannabinoid\" OR \"illicit drug\""
)


def build_forum_search_queries(mode: str = "full", when: str = "30d") -> List[dict]:
    """生成 Reddit/论坛/补充引擎搜索任务。when 必须带，保证近期。"""
    tasks: List[dict] = []
    news_mode = mode == "news"
    when = when or "30d"
    when_suffix = f" when:{when}"

    # —— Reddit 定向（Google News + 网页向查询）——
    reddit_queries = [
        f'site:reddit.com Mongolia ({DRUG_CORE}){when_suffix}',
        f'site:reddit.com Ulaanbaatar (drug OR meth OR cannabis OR heroin OR fentanyl){when_suffix}',
        f'site:reddit.com Mongolia (methamphetamine OR "crystal meth" OR "drug bust"){when_suffix}',
        f'site:reddit.com Mongolia ("drug trafficking" OR smuggling OR narcotics){when_suffix}',
    ]
    if news_mode:
        reddit_queries = reddit_queries[:3]
    for q in reddit_queries:
        tasks.append({
            "system_id": SYSTEM_ID,
            "system_name": SYSTEM_NAME,
            "org_name": "论坛·Reddit",
            "query": q,
            "hl": "en",
            "gl": "us",
            "ceid": "US:en",
            "engine": "google_news",
            "require_mongolia": True,
            "tier": "forum",
            "source_kind": "forum",
        })
        # 同步用 Google 网页搜索找帖子（News RSS 对 Reddit 覆盖不全）
        tasks.append({
            "system_id": SYSTEM_ID,
            "system_name": SYSTEM_NAME,
            "org_name": "论坛网页·Reddit",
            "query": q,
            "hl": "en",
            "gl": "us",
            "ceid": "US:en",
            "engine": "web_search",
            "require_mongolia": True,
            "tier": "forum",
            "source_kind": "forum",
        })

    # —— Reddit JSON 搜索 API（公开）——
    reddit_api_qs = [
        "Mongolia drug OR meth OR heroin OR cannabis OR fentanyl",
        "Ulaanbaatar drug OR meth OR narcotic",
        "Mongolia \"drug trafficking\" OR smuggling narcotic",
    ]
    if news_mode:
        reddit_api_qs = reddit_api_qs[:2]
    for q in reddit_api_qs:
        tasks.append({
            "system_id": SYSTEM_ID,
            "system_name": SYSTEM_NAME,
            "org_name": "Reddit接口搜索",
            "query": q,
            "hl": "en",
            "gl": "us",
            "ceid": "US:en",
            "engine": "reddit_search",
            "search_url": f"https://www.reddit.com/search.json?q={q}&sort=new&t=month&limit=25",
            "require_mongolia": True,
            "tier": "forum",
            "source_kind": "forum",
        })

    # —— 其他论坛 / 社区 ——
    forum_sites = [
        ("Quora", "site:quora.com"),
        ("Bluelight", "site:bluelight.org"),
        ("DrugsForum", "site:drugs-forum.com"),
        ("Medium", "site:medium.com"),
        ("知乎", "site:zhihu.com"),
        ("贴吧", "site:tieba.baidu.com"),
    ]
    if news_mode:
        forum_sites = forum_sites[:4]
    for name, site in forum_sites:
        q = f"Mongolia ({DRUG_CORE}) {site}{when_suffix}"
        tasks.append({
            "system_id": SYSTEM_ID,
            "system_name": SYSTEM_NAME,
            "org_name": f"论坛·{name}",
            "query": q,
            "hl": "en" if name not in ("知乎", "贴吧") else "zh-CN",
            "gl": "us" if name not in ("知乎", "贴吧") else "cn",
            "ceid": "US:en" if name not in ("知乎", "贴吧") else "CN:zh-Hans",
            "engine": "web_search",
            "require_mongolia": True,
            "tier": "forum",
            "source_kind": "forum",
        })

    # —— DuckDuckGo News RSS（补充引擎）——
    ddg_queries = [
        f"Mongolia narcotic OR methamphetamine OR heroin OR cannabis",
        f"Mongolia \"drug trafficking\" OR \"drug smuggling\" OR fentanyl",
        f"Ulaanbaatar drug OR meth OR seizure",
    ]
    if news_mode:
        ddg_queries = ddg_queries[:2]
    for q in ddg_queries:
        tasks.append({
            "system_id": SYSTEM_ID,
            "system_name": SYSTEM_NAME,
            "org_name": "DuckDuckGo新闻",
            "query": q,
            "hl": "en",
            "gl": "us",
            "ceid": "US:en",
            "engine": "ddg_news",
            "search_url": f"https://duckduckgo.com/news.js?q={q}&o=json&df=m",  # 近月
            "require_mongolia": True,
            "tier": "forum",
            "source_kind": "search_engine",
        })
        # DDG HTML 新闻页兜底
        tasks.append({
            "system_id": SYSTEM_ID,
            "system_name": SYSTEM_NAME,
            "org_name": "DuckDuckGo网页",
            "query": q,
            "hl": "en",
            "gl": "us",
            "ceid": "US:en",
            "engine": "web_search",
            "search_url": f"https://html.duckduckgo.com/html/?q={q}",
            "require_mongolia": True,
            "tier": "forum",
            "source_kind": "search_engine",
        })

    # —— Bing News RSS（补充）——
    bing_queries = [
        "Mongolia drug OR narcotic OR methamphetamine",
        "Mongolia heroin OR fentanyl OR cannabis trafficking",
    ]
    for q in bing_queries:
        tasks.append({
            "system_id": SYSTEM_ID,
            "system_name": SYSTEM_NAME,
            "org_name": "Bing新闻RSS",
            "query": q,
            "hl": "en",
            "gl": "us",
            "ceid": "US:en",
            "engine": "bing_news",
            "search_url": (
                "https://www.bing.com/news/search?q="
                + q.replace(" ", "+")
                + "&qft=interval%3d%227%22&format=RSS"  # 近7天
            ),
            "require_mongolia": True,
            "tier": "forum",
            "source_kind": "search_engine",
        })

    # —— Google News 再补一轮「论坛讨论」语义 ——
    discuss_qs = [
        f'Mongolia (reddit OR forum OR discussion) ({DRUG_CORE}){when_suffix}',
        f'"Mongolia" (\"I tried\" OR \"anyone know\" OR \"drug laws\") (cannabis OR meth OR drugs){when_suffix}',
    ]
    if not news_mode:
        for q in discuss_qs:
            tasks.append({
                "system_id": SYSTEM_ID,
                "system_name": SYSTEM_NAME,
                "org_name": "讨论帖·GoogleNews",
                "query": q,
                "hl": "en",
                "gl": "us",
                "ceid": "US:en",
                "engine": "google_news",
                "require_mongolia": True,
                "tier": "forum",
                "source_kind": "forum",
            })

    return tasks
