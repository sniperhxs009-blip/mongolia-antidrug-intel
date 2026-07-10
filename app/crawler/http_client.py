"""共享 HTTP 客户端：境外代理池 + 统一 UA/超时。"""
from __future__ import annotations

import itertools
import logging
import random
from typing import Iterable, List, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

_proxy_cycle = None


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
    """轮换代理；未配置则返回 None（直连）。"""
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
        "User-Agent": settings.crawl_user_agent,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "mn,en;q=0.9,zh-CN;q=0.8",
    }
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
