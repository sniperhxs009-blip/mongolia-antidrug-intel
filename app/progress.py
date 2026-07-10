"""前端SSE进度内存管理"""
from dataclasses import dataclass, field
from typing import Dict, List, Optional
import uuid


@dataclass
class TaskProgress:
    run_id: str
    report_type: str = "daily"
    status: str = "queued"
    phase: str = ""
    message: str = ""
    percent: int = 0
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
    events: List[Dict] = field(default_factory=list)

    def emit(self, event_type: str, **kwargs):
        for k, v in kwargs.items():
            if hasattr(self, k):
                setattr(self, k, v)
        self.events.append({"type": event_type, "data": kwargs})

    def snapshot(self) -> dict:
        return {
            "run_id": self.run_id,
            "report_type": self.report_type,
            "status": self.status,
            "phase": self.phase,
            "message": self.message,
            "percent": self.percent,
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
            "events": self.events.copy(),
        }


class ProgressHub:
    def __init__(self):
        self.running: Dict[str, TaskProgress] = {}
        self.current_run: Optional[str] = None

    def create(self, report_type: str = "daily") -> TaskProgress:
        rid = str(uuid.uuid4())[:12]
        tp = TaskProgress(run_id=rid, report_type=report_type, status="queued")
        self.running[rid] = tp
        self.current_run = rid
        return tp

    def get(self, run_id: str) -> Optional[TaskProgress]:
        return self.running.get(run_id)

    def current(self) -> Optional[TaskProgress]:
        if not self.current_run:
            return None
        return self.running.get(self.current_run)

    def is_busy(self) -> bool:
        return any(tp.status in ("queued", "running", "analyzing", "emailing") for tp in self.running.values())


progress_hub = ProgressHub()
