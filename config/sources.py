# 国内裸网直连完整官网清单放行；黑名单由 core_official.is_forbidden_url 强制拦截
from config.core_official import CORE_OFFICIAL_SOURCES, build_core_site_search_queries
from config.drug_lexicon import (
    ALERT_KEYWORDS,
    all_drug_keywords,
    build_search_queries,
)

# 种子 = 完整可直连官网清单
SOURCES = list(CORE_OFFICIAL_SOURCES)

# 1年窗口：核心 site:/站内检索 + 新闻补盲
SEARCH_FEEDS = build_core_site_search_queries("30d") + build_search_queries(mode="news", when="30d")

DRUG_KEYWORDS = all_drug_keywords()
CRITICAL_KEYWORDS = ALERT_KEYWORDS

ALLOW_ANY_MN_DOMAIN = True
ALLOW_GLOBAL_MEDIA = True
ALLOW_FORUM_DOMAINS = True

# 完整放行域名（与官网清单一致）
ALLOWED_DOMAINS = [
    # 蒙古本土媒体
    "montsame.mn", "www.montsame.mn",
    "gogo.mn", "www.gogo.mn",
    "ikon.mn", "www.ikon.mn",
    "news.mn", "www.news.mn",
    "ubpost.mongolnews.mn", "mongolnews.mn", "www.ubpost.mn", "ubpost.mn",
    # 国际禁毒权威
    "unodc.org", "www.unodc.org",
    # 国内官方禁毒
    "nncc626.com", "www.nncc626.com",
    # 补充国际合规媒体
    "news.cn", "www.news.cn", "xinhuanet.com", "www.xinhuanet.com",
    "cgtn.com", "www.cgtn.com",
    "akipress.com", "www.akipress.com",
    # 检索入口
    "news.google.com",
]

BLOCKED_SUFFIXES = [
    "facebook.com", "twitter.com", "youtube.com", "wikipedia.org",
    "shturl.cc",
]

from config.global_media import GLOBAL_ALLOWED_DOMAINS  # noqa: E402
from config.forum_search import FORUM_ALLOWED_DOMAINS  # noqa: E402

if ALLOW_GLOBAL_MEDIA:
    ALLOWED_DOMAINS = list(dict.fromkeys(ALLOWED_DOMAINS + GLOBAL_ALLOWED_DOMAINS))
if ALLOW_FORUM_DOMAINS:
    ALLOWED_DOMAINS = list(dict.fromkeys(ALLOWED_DOMAINS + FORUM_ALLOWED_DOMAINS))
