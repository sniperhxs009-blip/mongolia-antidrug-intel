"""合规修正版单元测试：直连拦 gov.mn、快照放行、过滤降噪、口岸弱词兼容"""
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
    sanitize_store_url,
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


def test_forbidden_urls_direct_only():
    # 直连原生官网必须拦
    assert is_forbidden_url("https://police.gov.mn/")
    assert is_forbidden_url("https://customs.gov.mn/news")
    assert is_forbidden_url("https://zasag.mn/anti-narcotics")
    assert is_forbidden_url("https://www.unodc.org/mongolia/")
    # 修改原因：搜索引擎/快照携带 gov.mn 必须放行
    assert not is_forbidden_url("https://news.google.com/search?q=site:police.gov.mn+narcotic")
    assert not is_forbidden_url(
        "https://news.google.com/rss/search?q=site:customs.gov.mn+мансууруулах&hl=en-US&gl=US&ceid=US:en"
    )
    assert not is_forbidden_url("https://montsame.mn/cn")
    # 包装后不为直连
    wrapped = sanitize_store_url("https://police.gov.mn/news/123", title="мансууруулах")
    assert "news.google.com" in wrapped
    assert not is_forbidden_url(wrapped)


def test_drug_filter_strict_and_port_weak():
    assert is_drug_related("Мансууруулах бодисын эсрэг ажиллагаа")
    assert is_drug_related("Customs seized narcotic drugs at border")
    assert is_drug_related("中蒙口岸查获走私冰毒若干公斤")
    # 仅弱词、无蒙古口岸 → 不入库
    assert not is_drug_related("口岸查获走私货物")
    assert not is_drug_related("Today weather is sunny in Ulaanbaatar city festival")
    assert not is_drug_related("Buryatia customs seized Mongolian cigarettes smuggling")
    # 弱词 + 蒙古口岸锚点 → 允许（小型缉毒快讯）
    assert is_drug_related("扎门乌德口岸查获走私货物一批")
    assert title_has_strong_drug("蒙古国警方查获芬太尼")
    assert title_has_strong_drug("甘其毛都口岸查获走私")
    assert not title_has_strong_drug("口岸查获走私货物")


def test_mongolia_country_strict():
    assert is_mongolia_country_related("Mongolia police seized methamphetamine in Ulaanbaatar")
    assert is_mongolia_country_related("蒙古国海关查获冰毒")
    assert is_mongolia_country_related("中蒙口岸扎门乌德缉毒专项")
    assert not is_mongolia_country_related("内蒙古呼和浩特市公安局破获贩毒案")
    assert not is_mongolia_country_related("Ulan-Ude resident caught with cannabis in Buryatia")
    assert not is_mongolia_country_related("Chita border tobacco smuggling")
    # 主体大段俄边境，仅顺带提蒙古 → 过滤
    long_ru = (
        "赤塔海关查获烟草。布里亚特警方在乌兰乌德行动。恰克图边境检查站加强巡查。"
        "后贝加尔地区走私案件上升。赤塔法院审理走私案。乌兰乌德仓库被查。"
        "布里亚特媒体报道边境动态。赤塔口岸通关量上升。恰克图贸易区扩建。"
        "顺带提及 Mongolia 一词。"
    )
    assert not is_mongolia_country_related(long_ru)


def test_url_allowlist():
    assert not is_allowed_url("https://www.police.gov.mn/news/123")
    assert is_allowed_url("https://montsame.mn/cn/news/123")
    assert is_allowed_url("https://www.unodc.org/unodc/en/data-and-analysis/world-drug-report.html")
    assert is_allowed_url("https://news.google.com/rss/search?q=site:police.gov.mn")
    assert not is_allowed_url("https://www.baidu.com/news")
    if ALLOW_GLOBAL_MEDIA:
        assert is_allowed_url("https://www.reuters.com/world/asia/")


def test_hash_stable():
    a = content_hash("t", "http://x", "body")
    b = content_hash("t", "http://y", "body")
    assert a == b


def test_regulatory_and_port_seizure_news():
    from app.crawler.filters import (
        has_regulatory_drug_term,
        is_drug_related,
        is_nav_or_index_page,
        passes_news_ingest_gate,
        title_has_strong_drug,
    )

    assert title_has_strong_drug("蒙古国成立国家级药品质量检测实验室")
    assert has_regulatory_drug_term("National drug quality laboratory controlled substance")
    assert is_drug_related("全国口岸今年累计缴获毒品4.07吨 扎门乌德")
    assert is_drug_related("那达慕摔跤选手检出违禁兴奋剂 蒙古国", loose=False)
    assert passes_news_ingest_gate("美国毒品邮寄到蒙古！三人被捕", url="https://news.mn/n/12345")
    assert passes_news_ingest_gate("蒙古海关查获6克麻醉药品", url="https://news.mn/n/99999")
    assert not passes_news_ingest_gate("边境口岸缉毒查验体系")
    assert not passes_news_ingest_gate("国际禁毒协作机构")
    assert not passes_news_ingest_gate("蒙古节拍")
    assert not passes_news_ingest_gate("每日简报")
    assert is_nav_or_index_page("关于蒙古节拍", "https://mongolia.robertritz.com/")
    assert not passes_news_ingest_gate(
        "联邦调查局寻求扣押纽约公寓与蒙古前领导人采矿计划有关",
        url="https://www.cnbc.com/2024/01/test.html",
    )

    assert classify_category("border customs drug trafficking seizure") == "跨境毒情"
    assert credibility_label("UNODC 世界毒品报告", 7) == "低"
    assert credibility_label("UNODC Mongolia report", 7) == "高"
    assert credibility_label("论坛·Reddit", 11) == "低"


def test_lexicon_large():
    keys = all_drug_keywords()
    assert len(keys) >= 120


def test_core_search_queries_snapshot_ok():
    qs = build_core_site_search_queries("30d")
    assert len(qs) >= 10
    assert any("montsame" in (q.get("query") or q.get("search_url") or "").lower() for q in qs)
    # 修改原因：允许 site:*.gov.mn 快照检索 query
    assert any("site:police.gov.mn" in (q.get("query") or "") for q in qs)
    # 但 search_url 不得直连 gov.mn
    assert not any(
        (q.get("search_url") or "").lower().find("police.gov.mn") >= 0
        and "google" not in (q.get("search_url") or "").lower()
        for q in qs
        if q.get("search_url")
    )
    assert any("内蒙古" in (q.get("query") or "") or "Inner Mongolia" in (q.get("query") or "") for q in qs)


def test_search_queries_built():
    qs = build_search_queries(mode="news", when="30d")
    assert len(qs) >= 10
    assert any("when:30d" in (q.get("query") or "") for q in qs)
    # 论坛不应默认混入 lexicon 批量任务
    assert not any((q.get("source_kind") == "forum") for q in qs)


def test_official_stats_config():
    assert len(OFFICIAL_STAT_SOURCES) >= 1
    assert all(not is_forbidden_url(s["base_url"]) for s in OFFICIAL_STAT_SOURCES)
    # PDF 搜索仍不直连 gov.mn 域名作为 search_url
    assert not any(
        is_forbidden_url(q.get("search_url") or "https://example.com")
        for q in PDF_SEARCH_QUERIES
        if q.get("search_url")
    )


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
