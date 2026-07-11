"""巡检任务实时进度总线（内存态，供 SSE 推送）"""
from __future__ import annotations

import threading
import time
import uuid
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Deque, Dict, List, Optional


@dataclass
class CrawlProgress:
    run_id: str
    report_type: str = "daily"
    status: str = "queued"  # queued | running | analyzing | emailing | success | failed
    phase: str = "初始化"
    message: str = ""
    total_sources: int = 0
    current_index: int = 0
    pages_fetched: int = 0
    items_new: int = 0
    items_updated: int = 0
    items_filtered: int = 0
    error_count: int = 0
    current_org: str = ""
    current_url: str = ""
    report_id: Optional[int] = None
    started_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    finished_at: Optional[str] = None
    events: Deque[Dict[str, Any]] = field(default_factory=lambda: deque(maxlen=200))  # 修改原因：限制 SSE 缓存防泄漏
    lock: threading.Lock = field(default_factory=threading.Lock)

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            pct = 0
            if self.total_sources:
                pct = min(99, int(self.current_index * 100 / self.total_sources))
            if self.status in ("analyzing", "emailing"):
                pct = 92
            if self.status == "success":
                pct = 100
            if self.status == "failed":
                pct = max(pct, 100)
            return {
                "run_id": self.run_id,
                "report_type": self.report_type,
                "status": self.status,
                "phase": self.phase,
                "message": self.message,
                "percent": pct,
                "total_sources": self.total_sources,
                "current_index": self.current_index,
                "pages_fetched": self.pages_fetched,
                "items_new": self.items_new,
                "items_updated": self.items_updated,
                "items_filtered": self.items_filtered,
                "error_count": self.error_count,
                "current_org": self.current_org,
                "current_url": self.current_url,
                "report_id": self.report_id,
                "started_at": self.started_at,
                "finished_at": self.finished_at,
                "events": list(self.events)[-80:],
            }

    def emit(self, event_type: str, **payload: Any) -> None:
        evt = {
            "id": str(uuid.uuid4())[:8],
            "ts": datetime.utcnow().isoformat(),
            "type": event_type,
            **payload,
        }
        with self.lock:
            self.events.append(evt)
            # 同步统计字段
            for k in (
                "phase",
                "message",
                "status",
                "total_sources",
                "current_index",
                "pages_fetched",
                "items_new",
                "items_updated",
                "items_filtered",
                "error_count",
                "current_org",
                "current_url",
                "report_id",
            ):
                if k in payload and payload[k] is not None:
                    setattr(self, k, payload[k])
            if event_type in ("done", "error"):
                self.finished_at = datetime.utcnow().isoformat()


class ProgressHub:
    def __init__(self) -> None:
        self._runs: Dict[str, CrawlProgress] = {}
        self._current_id: Optional[str] = None
        self._lock = threading.Lock()

    def create(self, report_type: str = "daily") -> CrawlProgress:
        run_id = uuid.uuid4().hex[:12]
        prog = CrawlProgress(run_id=run_id, report_type=report_type, status="queued", phase="排队中")
        with self._lock:
            self._runs[run_id] = prog
            self._current_id = run_id
        prog.emit("queued", message="任务已进入执行队列", status="queued", phase="排队中")
        return prog

    def get(self, run_id: str) -> Optional[CrawlProgress]:
        return self._runs.get(run_id)

    def current(self) -> Optional[CrawlProgress]:
        with self._lock:
            if self._current_id:
                return self._runs.get(self._current_id)
            return None

    def is_busy(self) -> bool:
        cur = self.current()
        return bool(cur and cur.status in ("queued", "running", "analyzing", "emailing"))


progress_hub = ProgressHub()
