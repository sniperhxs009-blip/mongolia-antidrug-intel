"""基础单元测试：过滤、种子、报告结构"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.crawler.filters import content_hash, is_allowed_url, is_drug_related, classify_category
from config.sources import SOURCES, ALLOWED_DOMAINS


def test_sources_cover_seven_systems():
    ids = {s["system_id"] for s in SOURCES}
    assert {1, 2, 3, 4, 5, 6, 7}.issubset(ids)
    assert 8 in ids  # 媒体与公开资讯


def test_allowed_domains_not_empty():
    assert "police.gov.mn" in ALLOWED_DOMAINS or "www.police.gov.mn" in ALLOWED_DOMAINS
    assert any("unodc.org" in d for d in ALLOWED_DOMAINS)


def test_drug_filter():
    assert is_drug_related("Мансууруулах бодисын эсрэг ажиллагаа")
    assert is_drug_related("Customs seized narcotic drugs at border")
    assert not is_drug_related("Today weather is sunny in Ulaanbaatar city festival")


def test_url_allowlist():
    assert is_allowed_url("https://www.police.gov.mn/news/123")
    assert is_allowed_url("https://www.unodc.org/easternasiaandpacific/mongolia.html")
    assert not is_allowed_url("https://www.baidu.com/news")
    assert not is_allowed_url("https://weibo.com/xyz")


def test_hash_stable():
    a = content_hash("t", "http://x", "body")
    b = content_hash("t", "http://x", "body")
    assert a == b


def test_category():
    assert classify_category("border customs seizure") == "跨境毒情"
