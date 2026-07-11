"""共享 HTTP 客户端：统一 UA 池/超时；永久禁止翻墙代理。"""
from __future__ import annotations

import itertools
import logging
import random
from typing import List, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_proxy_cycle = None

# 多套浏览器 UA，降低单一指纹被拦概率
USER_AGENT_POOL = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:122.0) Gecko/20100101 Firefox/122.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
    "Mozilla/5.0 (compatible; MN-AntiDrug-IntelBot/1.2; +https://github.com/mongolia-antidrug-intel)",
    # 修改原因：扩充移动端 UA，降低谷歌新闻 RSS 拦截概率
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) CriOS/122.0.6261.89 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.3 Mobile/15E148 Safari/604.1",
]


def pick_user_agent() -> str:
    """随机选取 UA；优先池内，回退配置项。"""
    try:
        return random.choice(USER_AGENT_POOL)
    except Exception:
        return getattr(settings, "crawl_user_agent", USER_AGENT_POOL[-1])


def _proxy_list() -> List[str]:
    # 硬性禁令：禁止翻墙代理
    if getattr(settings, "crawl_forbid_proxy", True):
        return []
    raw = (getattr(settings, "crawl_proxy_urls", "") or "").strip()
    if not raw:
        single = (getattr(settings, "crawl_proxy_url", "") or "").strip()
        return [single] if single else []
    return [p.strip() for p in raw.split(",") if p.strip()]


def next_proxy() -> Optional[str]:
    """轮换代理；未配置则返回 None（直连）。CRAWL_FORBID_PROXY=true 时恒为 None。"""
    global _proxy_cycle
    proxies = _proxy_list()
    if not proxies:
        return None
    if _proxy_cycle is None:
        random.shuffle(proxies)
        _proxy_cycle = itertools.cycle(proxies)
    return next(_proxy_cycle)


def build_httpx_client(**kwargs) -> httpx.Client:
    proxy = next_proxy()
    timeout = kwargs.pop("timeout", settings.crawl_timeout_sec)
    verify = kwargs.pop("verify", settings.crawl_ssl_verify)
    headers = kwargs.pop("headers", None) or {
        "User-Agent": pick_user_agent(),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "mn,en;q=0.9,zh-CN;q=0.8",
    }
    if "User-Agent" not in headers:
        headers["User-Agent"] = pick_user_agent()
    if proxy:
        logger.debug("httpx using proxy %s", proxy.split("@")[-1])
    return httpx.Client(
        headers=headers,
        timeout=timeout,
        follow_redirects=True,
        verify=verify,
        proxy=proxy,
        **kwargs,
    )
