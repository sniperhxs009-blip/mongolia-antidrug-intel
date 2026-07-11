"""全链路审计日志：爬虫/API/报告/邮件/删除，留存 ≥90 天。

修改原因：合规整改——操作可追溯。
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from app.config import get_settings

logger = logging.getLogger("audit")


def _log_path() -> Path:
    s = get_settings()
    base = Path(getattr(s, "resolved_data_dir", None) or getattr(s, "data_dir", "./data") or "./data")
    d = base / "audit"
    d.mkdir(parents=True, exist_ok=True)
    return d / "audit.jsonl"


def audit_log(
    action: str,
    *,
    ip: str = "",
    user: str = "",
    detail: Any = None,
) -> None:
    row = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "action": action,
        "ip": ip or "",
        "user": user or "",
        "detail": detail if isinstance(detail, (str, int, float, bool, dict, list)) else str(detail),
    }
    try:
        path = _log_path()
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as exc:  # noqa: BLE001
        logger.warning("audit write failed: %s", exc)


def purge_old_audit_logs(retention_days: Optional[int] = None) -> int:
    """清理超期审计行，默认 90 天。"""
    days = retention_days or int(getattr(get_settings(), "audit_log_retention_days", 90) or 90)
    cutoff = datetime.utcnow() - timedelta(days=days)
    path = _log_path()
    if not path.exists():
        return 0
    kept = []
    removed = 0
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        try:
            row = json.loads(line)
            ts = datetime.fromisoformat(row["ts"].replace("Z", ""))
            if ts >= cutoff:
                kept.append(line)
            else:
                removed += 1
        except Exception:
            kept.append(line)
    path.write_text("\n".join(kept) + ("\n" if kept else ""), encoding="utf-8")
    return removed
