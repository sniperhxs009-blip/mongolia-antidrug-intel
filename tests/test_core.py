"""定稿版单元测试：严格过滤、无 gov.mn 检索、黑名单、统计配置"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.crawler.filters import (
    content_hash,
    is_allowed_url,
    is_drug_related,
    is_mongolia_country_related,
    classify_category,
    title_has_strong_drug,
    credibility_label,
)
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


def test_forbidden_urls():
    assert is_forbidden_url("https://police.gov.mn/")
    assert is_forbidden_url("https://news.google.com/search?q=site:police.gov.mn")  # 含 gov.mn 即拦
    assert is_forbidden_url("https://zasag.mn/anti-narcotics")
    assert is_forbidden_url("https://www.unodc.org/mongolia/")
    assert not is_forbidden_url("https://montsame.mn/cn")


def test_drug_filter_strict():
    assert is_drug_related("Мансууруулах бодисын эсрэг ажиллагаа")
    assert is_drug_related("Customs seized narcotic drugs at border")
    assert is_drug_related("中蒙口岸查获走私冰毒若干公斤")
    # 仅弱词不入库
    assert not is_drug_related("口岸查获走私货物")
    assert not is_drug_related("Today weather is sunny in Ulaanbaatar city festival")
    assert not is_drug_related("Two Seasons Dining Facility Mongolian BBQ")
    assert not is_drug_related("combat human trafficking in Mongolia")
    assert not is_drug_related("Buryatia customs seized Mongolian cigarettes smuggling")
    assert not is_drug_related("2500 rounds of ammunition smuggled into Mongolia")
    assert not is_drug_related("Mongolian citizen detained for smuggling weight-loss pills")
    assert title_has_strong_drug("蒙古国警方查获芬太尼")
    assert not title_has_strong_drug("口岸查获走私货物")


def test_mongolia_country_strict():
    assert is_mongolia_country_related("Mongolia police seized methamphetamine in Ulaanbaatar")
    assert is_mongolia_country_related("蒙古国海关查获冰毒")
    assert is_mongolia_country_related("中蒙口岸扎门乌德缉毒专项")
    assert not is_mongolia_country_related("内蒙古呼和浩特市公安局破获贩毒案")
    assert not is_mongolia_country_related("Ulan-Ude resident caught with cannabis in Buryatia")
    assert not is_mongolia_country_related("Chita border tobacco smuggling")  # 无蒙古国锚点
    assert not is_mongolia_country_related("Afghanistan opium production down 93 percent UNODC")


def test_url_allowlist():
    assert not is_allowed_url("https://www.police.gov.mn/news/123")
    assert is_allowed_url("https://montsame.mn/cn/news/123")
    assert is_allowed_url("https://www.unodc.org/unodc/en/data-and-analysis/world-drug-report.html")
    assert not is_allowed_url("https://www.baidu.com/news")
    if ALLOW_GLOBAL_MEDIA:
        assert is_allowed_url("https://www.reuters.com/world/asia/")


def test_hash_stable():
    a = content_hash("t", "http://x", "body")
    b = content_hash("t", "http://y", "body")  # 同标题正文应合并倾向
    assert a == b


def test_category_and_credibility():
    assert classify_category("border customs drug trafficking seizure") == "跨境毒情"
    assert credibility_label("UNODC 世界毒品报告", 7) == "高"
    assert credibility_label("论坛·Reddit", 11) == "低"


def test_lexicon_large():
    keys = all_drug_keywords()
    assert len(keys) >= 120


def test_core_search_queries_no_gov():
    qs = build_core_site_search_queries("30d")
    assert len(qs) >= 10
    assert any("montsame" in (q.get("query") or q.get("search_url") or "").lower() for q in qs)
    # 定稿：禁止任何 site:*.gov.mn
    assert not any("gov.mn" in (q.get("query") or "").lower() for q in qs)
    assert not any("gov.mn" in (q.get("search_url") or "").lower() for q in qs)
    assert any("内蒙古" in (q.get("query") or "") or "Inner Mongolia" in (q.get("query") or "") for q in qs)  # 负面排除语法


def test_search_queries_built():
    qs = build_search_queries(mode="news", when="30d")
    assert len(qs) >= 10
    assert any("when:30d" in (q.get("query") or "") for q in qs)


def test_official_stats_config():
    assert len(OFFICIAL_STAT_SOURCES) >= 1
    assert all(not is_forbidden_url(s["base_url"]) for s in OFFICIAL_STAT_SOURCES)
    assert not any("gov.mn" in (q.get("query") or "") for q in OFFICIAL_STAT_SEARCHES)
    assert not any("gov.mn" in (q.get("query") or "") for q in PDF_SEARCH_QUERIES)


def test_stats_extract():
    text = (
        "Прокурорын байгууллагаас 2025 онд мансууруулах эм, сэтгэцэд нөлөөт бодисыг "
        "хууль бусаар ашиглах 551 хэрэгт хяналт тавьсан нь өмнөх оноос 21.6 хувиар өссөн."
    )
    rows = extract_stats_from_text(text, source_url="https://example.mn/x", org_name="总检察院")
    assert rows
    assert any(r["metric_name"] == "涉毒案件数" and r["metric_value"] == 551 for r in rows)


def test_alert_and_port_tags():
    from app.crawler.filters import alert_category, port_tag_from_text, drug_type_from_text, sanitize_sensitive_text

    assert alert_category("蒙古国通过禁毒新法列管尼秦") == "禁毒新法"
    assert "芬太尼" in alert_category("Ulaanbaatar fentanyl seizure")
    assert port_tag_from_text("扎门乌德口岸查获冰毒") == "扎门乌德"
    assert drug_type_from_text("甘其毛都查获芬太尼") == "芬太尼"
    hidden = sanitize_sensitive_text("查获12公斤芬太尼粉末一批", hide_details=True)
    assert "【数量已隐藏】" in hidden or "【细节已隐藏】" in hidden


def test_export_ledger_csv(tmp_path):
    from types import SimpleNamespace
    from app.export_ledger import export_intel_csv

    item = SimpleNamespace(
        id=1, title="t", title_zh="标题", org_name="蒙通社", category="综合",
        intel_level="重要", credibility="高", alert_kind="口岸大宗", port_tag="扎门乌德",
        drug_type="冰毒", published_at=None, url="https://montsame.mn/x",
        summary="摘要", summary_zh="摘要",
    )
    path = export_intel_csv([item], tmp_path / "t.csv", hide_details=False)
    assert Path(path).exists()
    text = Path(path).read_text(encoding="utf-8-sig")
    assert "蒙通社" in text
