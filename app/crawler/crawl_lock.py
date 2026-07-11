"""采集任务互斥锁：全量与新闻监测不可同时运行。

修改原因：性能/稳定性——防止并发采集打爆搜索引擎与 SQLite。
"""
from __future__ import annotations

import threading
import time
from typing import Optional

_lock = threading.Lock()
_holder: Optional[str] = None
_holder_since: Optional[float] = None
# 修改原因：任务崩溃后锁超时15分钟自动释放，避免永久占用
LOCK_TIMEOUT_SEC = 15 * 60


def is_lock_stale() -> bool:
    """判断当前锁是否已超时。"""
    if not _holder or _holder_since is None:
        return False
    return (time.time() - _holder_since) >= LOCK_TIMEOUT_SEC


def force_release_if_stale() -> bool:
    """超时则清空持有者，返回是否已释放。"""
    global _holder, _holder_since
    with _lock:
        if _holder and _holder_since and (time.time() - _holder_since) >= LOCK_TIMEOUT_SEC:
            _holder = None
            _holder_since = None
            return True
    return False


def try_acquire(owner: str) -> bool:
    global _holder, _holder_since
    with _lock:
        if _holder:
            if _holder_since and (time.time() - _holder_since) >= LOCK_TIMEOUT_SEC:
                _holder = None
                _holder_since = None
            else:
                return False
        _holder = owner
        _holder_since = time.time()
        return True


def release(owner: str) -> None:
    global _holder, _holder_since
    with _lock:
        if _holder == owner:
            _holder = None
            _holder_since = None


def current_owner() -> Optional[str]:
    force_release_if_stale()
    return _holder
