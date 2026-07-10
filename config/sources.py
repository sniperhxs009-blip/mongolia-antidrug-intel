ALLOW_ANY_MN_DOMAIN = True
ALLOW_GLOBAL_MEDIA = True
ALLOW_FORUM_DOMAINS = True
ALLOWED_DOMAINS = [
    "montsame.mn", "www.montsame.mn",
    "gogo.mn", "www.gogo.mn",
    "ikon.mn", "www.ikon.mn",
    "news.mn", "www.news.mn",
    "ubpost.mongolnews.mn", "mongolnews.mn",
    "unodc.org", "www.unodc.org",
    "nncc626.com", "www.nncc626.com",
    "news.cn", "www.news.cn", "xinhuanet.com",
    "cgtn.com", "www.cgtn.com",
    "akipress.com", "www.akipress.com",
    "news.google.com",
]
BLOCKED_SUFFIXES = ["facebook.com","twitter.com","youtube.com","wikipedia.org"]

from config.core_official import CORE_OFFICIAL_SOURCES
from config.drug_lexicon import all_drug_keywords
SOURCES = list(CORE_OFFICIAL_SOURCES)
DRUG_KEYWORDS = all_drug_keywords()
CRITICAL_KEYWORDS = ["芬太尼", "尼秦", "吨", "公斤", "专项行动", "fentanyl", "nitazene"]
