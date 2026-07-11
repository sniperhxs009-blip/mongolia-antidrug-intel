"""采集任务互斥锁：全量与新闻监测不可同时运行。

修改原因：性能/稳定性——防止并发采集打爆搜索引擎与 SQLite。
"""
from __future__ import annotations

import threading
from typing import Optional

_lock = threading.Lock()
_holder: Optional[str] = None


def try_acquire(owner: str) -> bool:
    global _holder
    with _lock:
        if _holder:
            return False
        _holder = owner
        return True


def release(owner: str) -> None:
    global _holder
    with _lock:
        if _holder == owner:
            _holder = None


def current_owner() -> Optional[str]:
    return _holder
