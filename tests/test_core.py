"""全量修复版单元测试：黑名单、合法种子、过滤、检索任务"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.crawler.filters import content_hash, is_allowed_url, is_drug_related, classify_category
from app.crawler.stats_extract import extract_stats_from_text
from config.core_official import (
    CORE_OFFICIAL_SOURCES,
    build_core_site_search_queries,
    is_forbidden_url,
)
from config.sources import SOURCES, ALLOWED_DOMAINS, ALLOW_GLOBAL_MEDIA
from config.drug_lexicon import all_drug_keywords, build_search_queries
from config.official_stats import OFFICIAL_STAT_SOURCES, OFFICIAL_STAT_SEARCHES, PDF_SEARCH_QUERIES


def test_sources_are_core_only():
    assert SOURCES
    assert all(s.get("core_official") for s in SOURCES)
    assert len(SOURCES) == len(CORE_OFFICIAL_SOURCES)
    for s in SOURCES:
        assert not is_forbidden_url(s["base_url"])


def test_allowed_domains_no_gov_mn():
    assert not any(d.endswith(".gov.mn") or d == "gov.mn" for d in ALLOWED_DOMAINS)
    assert any("montsame.mn" in d for d in ALLOWED_DOMAINS)
    assert any("unodc.org" in d for d in ALLOWED_DOMAINS)


def test_forbidden_urls():
    assert is_forbidden_url("https://police.gov.mn/")
    assert is_forbidden_url("https://zasag.mn/anti-narcotics")
    assert is_forbidden_url("https://www.unodc.org/mongolia/")
    assert is_forbidden_url("https://shturl.cc/x")
    assert not is_forbidden_url("https://montsame.mn/cn")
    assert not is_forbidden_url(
        "https://www.unodc.org/unodc/en/data-and-analysis/world-drug-report.html"
    )


def test_drug_filter():
    assert is_drug_related("Мансууруулах бодисын эсрэг ажиллагаа")
    assert is_drug_related("Customs seized narcotic drugs at border")
    assert is_drug_related("Mongolian detectives seize drug smuggler")
    assert is_drug_related("中蒙口岸查获走私冰毒若干公斤")  # 正文强词
    assert is_drug_related("口岸查获走私货物")  # 弱词放行
    assert not is_drug_related("Today weather is sunny in Ulaanbaatar city festival")
    assert not is_drug_related("Two Seasons Dining Facility Mongolian BBQ")
    assert not is_drug_related("combat human trafficking in Mongolia")
    assert not is_drug_related("Russian medicine for hepatitis tax-free in Mongolia")
    assert not is_drug_related("Buryatia customs seized Mongolian cigarettes smuggling")
    assert not is_drug_related("2500 rounds of ammunition smuggled into Mongolia")
    assert not is_drug_related("Mongolian citizen detained for smuggling weight-loss pills")
    # 布里亚特+强毒词+蒙古锚点：跨境案应保留
    assert is_drug_related("Buryatia-Mongolia border narcotic trafficking case")


def test_mongolia_country():
    from app.crawler.filters import is_mongolia_country_related, is_unodc_mongolia_signal
    assert is_mongolia_country_related("Mongolia police seized methamphetamine in Ulaanbaatar")
    assert not is_mongolia_country_related("Ulan-Ude resident caught with cannabis in Buryatia")
    assert not is_mongolia_country_related("Afghanistan opium production down 93 percent UNODC")
    assert is_mongolia_country_related("蒙古国海关查获冰毒")
    assert is_mongolia_country_related("中蒙口岸扎门乌德缉毒专项")
    assert not is_mongolia_country_related("内蒙古呼和浩特市公安局破获贩毒案")
    assert is_mongolia_country_related("Chita-Kyakhta border narcotic smuggling to Mongolia")
    assert is_unodc_mongolia_signal("UNODC East Asia country data Mongolia cannabis seizure statistics")


def test_url_allowlist():
    assert not is_allowed_url("https://www.police.gov.mn/news/123")
    assert is_allowed_url("https://montsame.mn/cn/news/123")
    assert is_allowed_url("https://www.unodc.org/unodc/en/data-and-analysis/world-drug-report.html")
    assert not is_allowed_url("https://www.baidu.com/news")
    assert not is_allowed_url("https://weibo.com/xyz")
    # 全球媒体开关开启时路透等可入库；关闭则拒绝
    if ALLOW_GLOBAL_MEDIA:
        assert is_allowed_url("https://www.reuters.com/world/asia/")
    else:
        assert not is_allowed_url("https://www.reuters.com/world/asia/")


def test_hash_stable():
    a = content_hash("t", "http://x", "body")
    b = content_hash("t", "http://x", "body")
    assert a == b


def test_category():
    assert classify_category("border customs drug trafficking seizure") == "跨境毒情"
    assert classify_category("fentanyl nitazene NPS seizure") == "新型毒品"
    assert classify_category("涉毒案件同比统计 PDF") == "官方统计"


def test_lexicon_large():
    keys = all_drug_keywords()
    assert len(keys) >= 120
    assert any("芬太尼" in k or "fentanyl" in k.lower() for k in keys)
    assert any("мансууруулах" in k for k in keys)
    assert any("nitazene" in k.lower() or "硝基嗪" in k for k in keys)


def test_core_search_queries():
    qs = build_core_site_search_queries("30d")
    assert len(qs) >= 10
    assert any("montsame" in (q.get("query") or q.get("search_url") or "").lower() for q in qs)
    # 允许 Google 查询字符串含 site:*.gov.mn（快照检索）；禁止站内 search_url 直连 gov.mn
    assert any("site:police.gov.mn" in (q.get("query") or "").lower() for q in qs)
    assert not any(
        ".gov.mn" in (q.get("search_url") or "").lower()
        for q in qs
    )
    # 直连 URL 仍永久封禁；谷歌新闻包装链允许
    assert is_forbidden_url("https://police.gov.mn/news/1")
    from config.core_official import sanitize_store_url, is_google_snapshot_or_news_url
    wrapped = sanitize_store_url("https://police.gov.mn/news/1", "https://news.google.com/articles/abc")
    assert is_google_snapshot_or_news_url(wrapped) or "news.google.com" in wrapped
    assert not is_forbidden_url(wrapped)


def test_search_queries_built():
    qs = build_search_queries(mode="news", when="30d")
    assert len(qs) >= 10
    assert any(q.get("engine") == "google_news" for q in qs)
    assert any("when:30d" in (q.get("query") or "") for q in qs)


def test_official_stats_config():
    assert len(OFFICIAL_STAT_SOURCES) >= 1
    assert all(not is_forbidden_url(s["base_url"]) for s in OFFICIAL_STAT_SOURCES)
    assert len(OFFICIAL_STAT_SEARCHES) >= 3
    assert len(PDF_SEARCH_QUERIES) >= 2
    # PDF 查询禁止 site:police/customs.gov.mn（避免诱导直连下载）
    assert not any("site:police.gov.mn" in (q.get("query") or "") for q in PDF_SEARCH_QUERIES)
    assert not any("site:customs.gov.mn" in (q.get("query") or "") for q in PDF_SEARCH_QUERIES)
    # Google News 统计快照允许 query 含 site:*.gov.mn
    assert any("site:police.gov.mn" in (q.get("query") or "") for q in OFFICIAL_STAT_SEARCHES)


def test_stats_extract():
    text = (
        "Прокурорын байгууллагаас 2025 онд мансууруулах эм, сэтгэцэд нөлөөт бодисыг "
        "хууль бусаар ашиглах 551 хэрэгт хяналт тавьсан нь өмнөх оноос 21.6 хувиар өссөн."
    )
    rows = extract_stats_from_text(text, source_url="https://example.mn/x", org_name="总检察院")
    assert rows
    assert any(r["metric_name"] == "涉毒案件数" and r["metric_value"] == 551 for r in rows)
    assert any(r["metric_name"] == "同比增长率" for r in rows)
