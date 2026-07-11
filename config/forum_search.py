from __future__ import annotations

from typing import List, Tuple

from config.core_official import SEARCH_NEGATIVE_EXCLUDE

"""
论坛 / 社区 / 补充搜索引擎配置
覆盖：Reddit、知乎、贴吧、药物论坛、DuckDuckGo/Bing 新闻 RSS 等
"""

SYSTEM_ID = 11
SYSTEM_NAME = "全球论坛社区与补充搜索"


def _when_engine_params(when: str) -> Tuple[str, str, str]:
    """Map Google-style when -> (reddit t=, bing interval, ddg df)."""
    w = (when or "1y").strip().lower()
    if w in ("1d", "d"):
        return "day", "1", "d"
    if w in ("7d", "w", "week"):
        return "week", "7", "w"
    if w in ("30d", "m", "month"):
        return "month", "30", "m"
    if w in ("90d",):
        return "year", "30", "y"
    # 1y / default — 拉长窗口以覆盖稀疏信源
    return "year", "30", "y"

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
    "bluelight.org", "www.bluelight.org",
    "drugs-forum.com", "www.drugs-forum.com",
    "erowid.org", "www.erowid.org",
]

DRUG_CORE = (
    "drug OR narcotic OR methamphetamine OR meth OR heroin OR cannabis OR marijuana OR "
    "fentanyl OR ketamine OR \"drug trafficking\" OR \"drug smuggling\" OR NPS OR "
    "\"synthetic cannabinoid\" OR \"illicit drug\" OR nitazene OR \"crystal meth\" OR "
    "annaka OR \"caffeine sodium benzoate\" OR spice OR K2"
)


def build_forum_search_queries(mode: str = "full", when: str = "1y") -> List[dict]:
    """生成 Reddit/论坛/补充引擎搜索任务。when 必须带。"""
    tasks: List[dict] = []
    news_mode = mode == "news"
    when = when or "1y"
    when_suffix = f" when:{when}"
    reddit_t, bing_interval, ddg_df = _when_engine_params(when)

    # —— Reddit 定向（翻倍）——
    reddit_queries = [
        f'site:reddit.com Mongolia ({DRUG_CORE}){when_suffix}',
        f'site:reddit.com Ulaanbaatar (drug OR meth OR cannabis OR heroin OR fentanyl){when_suffix}',
        f'site:reddit.com Mongolia (methamphetamine OR "crystal meth" OR "drug bust"){when_suffix}',
        f'site:reddit.com Mongolia ("drug trafficking" OR smuggling OR narcotics){when_suffix}',
        f'site:reddit.com Mongolia (nitazene OR fentanyl OR NPS OR "synthetic cannabinoid"){when_suffix}',
        f'site:reddit.com (Zamyn-Uud OR "Gashuun Sukhait" OR Erenhot) (drug OR narcotic){when_suffix}',
        f'site:reddit.com r/mongolia (drug OR meth OR cannabis OR laws){when_suffix}',
        f'site:reddit.com Mongolia (annaka OR "caffeine sodium benzoate" OR "synthetic cannabinoid" OR spice){when_suffix}',
        f'site:zhihu.com 蒙古国 (安纳咖 OR 合成大麻素 OR 尼秦 OR 芬太尼){when_suffix}',
        f'site:bluelight.org Mongolia (meth OR fentanyl OR cannabis OR NPS){when_suffix}',
    ]
    if news_mode:
        # 修改原因：news 仅保留4组核心蒙语/口岸毒品词，削减闲聊噪音
        reddit_queries = [
            f'site:reddit.com (Ulaanbaatar OR Zamyn-Uud OR "Gashuun Sukhait") (мансууруулах OR фентанил OR метамфетамин OR "хар тамхи"){when_suffix}',
            f'site:reddit.com Mongolia (fentanyl OR nitazene OR methamphetamine) (Ulaanbaatar OR border){when_suffix}',
            f'site:zhihu.com 蒙古国 (芬太尼 OR 尼秦 OR 安纳咖 OR 冰毒){when_suffix}',
            f'site:reddit.com (扎门乌德 OR 甘其毛都 OR 乌兰巴托) (毒品 OR 缉毒 OR 查获){when_suffix}',
        ]
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

    # —— Reddit JSON 搜索 API ——
    reddit_api_qs = [
        "Mongolia drug OR meth OR heroin OR cannabis OR fentanyl",
        "Ulaanbaatar drug OR meth OR narcotic",
        "Mongolia \"drug trafficking\" OR smuggling narcotic",
        "Mongolia nitazene OR fentanyl OR NPS",
        "Mongolia customs OR border drug seizure",
        "r/mongolia cannabis OR meth OR drugs",
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
            "search_url": f"https://www.reddit.com/search.json?q={q}&sort=new&t={reddit_t}&limit=25",
            "require_mongolia": True,
            "tier": "forum",
            "source_kind": "forum",
        })

    # —— 其他论坛 / 社区（翻倍）——
    forum_sites = [
        ("Quora", "site:quora.com"),
        ("Bluelight", "site:bluelight.org"),
        ("DrugsForum", "site:drugs-forum.com"),
        ("Medium", "site:medium.com"),
        ("知乎", "site:zhihu.com"),
        ("贴吧", "site:tieba.baidu.com"),
        ("Erowid", "site:erowid.org"),
        ("豆瓣", "site:douban.com"),
    ]
    if news_mode:
        forum_sites = []  # news 模式不再批量刷论坛站
    for name, site in forum_sites:
        qs = [
            f"Mongolia ({DRUG_CORE}) {site}{when_suffix}",
            f"蒙古国 (毒品 OR 缉毒 OR 冰毒 OR 芬太尼) {site}{when_suffix}",
        ]
        if name in ("知乎", "贴吧", "豆瓣"):
            qs = [
                f"蒙古国 (毒品 OR 缉毒 OR 芬太尼 OR 安纳咖 OR 口岸) {site}{when_suffix}",
                f"乌兰巴托 OR 扎门乌德 (毒品 OR 缉毒 OR 走私) {site}{when_suffix}",
            ]
        for q in qs:
            tasks.append({
                "system_id": SYSTEM_ID,
                "system_name": SYSTEM_NAME,
                "org_name": f"论坛·{name}",
                "query": q,
                "hl": "en" if name not in ("知乎", "贴吧", "豆瓣") else "zh-CN",
                "gl": "us" if name not in ("知乎", "贴吧", "豆瓣") else "cn",
                "ceid": "US:en" if name not in ("知乎", "贴吧", "豆瓣") else "CN:zh-Hans",
                "engine": "web_search",
                "require_mongolia": True,
                "tier": "forum",
                "source_kind": "forum",
            })

    # —— 蒙古本地话题补盲 ——
    local_topics = [
        f'Монгол (мансууруулах OR "хар тамхи" OR фентанил) (reddit OR forum OR хэлэлцүүлэг){when_suffix}',
        f'Ulaanbaatar (\"drug laws\" OR \"is weed legal\" OR meth OR cannabis){when_suffix}',
        f'\"蒙古国\" (知乎 OR 贴吧 OR 论坛) (毒品 OR 缉毒 OR 安纳咖){when_suffix}',
    ]
    for q in local_topics:
        tasks.append({
            "system_id": SYSTEM_ID,
            "system_name": SYSTEM_NAME,
            "org_name": "论坛·蒙古本地话题",
            "query": q,
            "hl": "en",
            "gl": "us",
            "ceid": "US:en",
            "engine": "web_search",
            "require_mongolia": True,
            "tier": "forum",
            "source_kind": "forum",
        })

    # —— DuckDuckGo News RSS ——
    ddg_queries = [
        "Mongolia narcotic OR methamphetamine OR heroin OR cannabis",
        "Mongolia \"drug trafficking\" OR \"drug smuggling\" OR fentanyl",
        "Ulaanbaatar drug OR meth OR seizure",
        "Mongolia nitazene OR \"synthetic cannabinoid\" OR NPS",
        "Zamyn-Uud OR Erenhot drug OR narcotic seizure",
    ]
    if news_mode:
        ddg_queries = ddg_queries[:3]
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
            "search_url": f"https://duckduckgo.com/news.js?q={q}&o=json&df={ddg_df}",
            "require_mongolia": True,
            "tier": "forum",
            "source_kind": "search_engine",
        })
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

    # —— Bing News RSS ——
    bing_queries = [
        "Mongolia drug OR narcotic OR methamphetamine",
        "Mongolia heroin OR fentanyl OR cannabis trafficking",
        "Mongolia customs drug seizure OR border narcotic",
        "Ulaanbaatar meth OR fentanyl OR cannabis",
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
                + f"&qft=interval%3d%22{bing_interval}%22&format=RSS"
            ),
            "require_mongolia": True,
            "tier": "forum",
            "source_kind": "search_engine",
        })

    # —— Google News 讨论语义 ——
    discuss_qs = [
        f'Mongolia (reddit OR forum OR discussion) ({DRUG_CORE}){when_suffix}',
        f'"Mongolia" (\"I tried\" OR \"anyone know\" OR \"drug laws\") (cannabis OR meth OR drugs){when_suffix}',
        f'Mongolia (bluelight OR \"drugs forum\") (meth OR fentanyl OR cannabis){when_suffix}',
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

    for _task in tasks:
        q = _task.get("query") or ""
        if q and SEARCH_NEGATIVE_EXCLUDE.strip() not in q:
            # 修改原因：检索层降噪，统一负面排除
            _task["query"] = (q + SEARCH_NEGATIVE_EXCLUDE).strip()
        _task["priority"] = 90
        _task["source_kind"] = _task.get("source_kind") or "forum"
    if news_mode:
        tasks = tasks[:8]  # 硬顶：news 论坛任务极少
    return tasks
