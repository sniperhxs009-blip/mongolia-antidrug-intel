# 全量修复版数据源：仅国内裸网可直连合法种子（禁止蒙古 .gov.mn）
# 关键词检索任务见 config/core_official.py / config/drug_lexicon.py

from config.core_official import CORE_OFFICIAL_SOURCES, build_core_site_search_queries
from config.drug_lexicon import (
    ALERT_KEYWORDS,
    all_drug_keywords,
    build_search_queries,
)

# 仅录入全量修复版合法种子；七大机构归类由研判引擎按内容自动完成
SOURCES = list(CORE_OFFICIAL_SOURCES)

# 检索任务以核心站内/site: 为主，辅以精简新闻检索
SEARCH_FEEDS = build_core_site_search_queries("30d") + build_search_queries(mode="news", when="30d")

DRUG_KEYWORDS = all_drug_keywords()
CRITICAL_KEYWORDS = ALERT_KEYWORDS

ALLOWED_DOMAINS = [
    "montsame.mn", "www.montsame.mn",
    "nncc626.com", "www.nncc626.com",
    "unodc.org", "www.unodc.org",
    "mongolia.un.org", "www.mongolia.un.org",
    "chinanews.com", "www.chinanews.com",
    "nmg.110.gov.cn", "gat.nmg.110.gov.cn",
    "odkb-csto.org", "www.odkb-csto.org",
    "scoec.gov.cn", "www.scoec.gov.cn",
    "mongolnews.mn", "ubpost.mongolnews.mn", "www.ubpost.mn", "ubpost.mn",
    "news.google.com",
]

ALLOW_ANY_MN_DOMAIN = False
ALLOW_GLOBAL_MEDIA = False
ALLOW_FORUM_DOMAINS = False

from config.global_media import GLOBAL_ALLOWED_DOMAINS  # noqa: E402
from config.forum_search import FORUM_ALLOWED_DOMAINS  # noqa: E402

if ALLOW_GLOBAL_MEDIA:
    ALLOWED_DOMAINS = list(dict.fromkeys(ALLOWED_DOMAINS + GLOBAL_ALLOWED_DOMAINS))
if ALLOW_FORUM_DOMAINS:
    ALLOWED_DOMAINS = list(dict.fromkeys(ALLOWED_DOMAINS + FORUM_ALLOWED_DOMAINS))
