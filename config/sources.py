# 仅修改域名放行开关与时效窗口；其余结构/变量保留原始逻辑
from config.core_official import CORE_OFFICIAL_SOURCES, build_core_site_search_queries
from config.drug_lexicon import (
    ALERT_KEYWORDS,
    all_drug_keywords,
    build_search_queries,
)

# 种子来自核心官方配置（含蒙通社 + GOGO/IKON/News.mn/UB Post 等）
SOURCES = list(CORE_OFFICIAL_SOURCES)

# 检索窗口统一 1 年
SEARCH_FEEDS = build_core_site_search_queries("1y") + build_search_queries(mode="news", when="1y")

DRUG_KEYWORDS = all_drug_keywords()
CRITICAL_KEYWORDS = ALERT_KEYWORDS

# 放行开关：放开蒙古媒体 / 外媒 / 论坛补充源
ALLOW_ANY_MN_DOMAIN = True
ALLOW_GLOBAL_MEDIA = True
ALLOW_FORUM_DOMAINS = True

# 扩充合法白名单，新增蒙古4家民间媒体域名
ALLOWED_DOMAINS = [
    "montsame.mn", "www.montsame.mn",
    "gogo.mn", "www.gogo.mn",
    "ikon.mn", "www.ikon.mn",
    "news.mn", "www.news.mn",
    "ubpost.mongolnews.mn", "mongolnews.mn", "www.ubpost.mn", "ubpost.mn",
    "unodc.org", "www.unodc.org",
    "nncc626.com", "www.nncc626.com",
    "news.cn", "www.news.cn", "xinhuanet.com",
    "cgtn.com", "www.cgtn.com",
    "akipress.com", "www.akipress.com",
    "news.google.com",
]

# 封禁社交、视频、百科域名不变
BLOCKED_SUFFIXES = ["facebook.com", "twitter.com", "youtube.com", "wikipedia.org"]

from config.global_media import GLOBAL_ALLOWED_DOMAINS  # noqa: E402
from config.forum_search import FORUM_ALLOWED_DOMAINS  # noqa: E402

if ALLOW_GLOBAL_MEDIA:
    ALLOWED_DOMAINS = list(dict.fromkeys(ALLOWED_DOMAINS + GLOBAL_ALLOWED_DOMAINS))
if ALLOW_FORUM_DOMAINS:
    ALLOWED_DOMAINS = list(dict.fromkeys(ALLOWED_DOMAINS + FORUM_ALLOWED_DOMAINS))
