"""SQLite 自动归档脚本：清理超 30 天非关键情报。

用法: python -m scripts.archive_db
修改原因：控制数据库体积。
"""
from __future__ import annotations

from app.crawler.cleanup import archive_old_non_critical, purge_noise_geo_items
from app.db.models import SessionLocal, init_db
from app.audit import purge_old_audit_logs


def main() -> None:
    init_db()
    db = SessionLocal()
    try:
        a = archive_old_non_critical(db, days=30)
        b = purge_noise_geo_items(db)
        c = purge_old_audit_logs()
        print({"archive": a, "noise_geo": b, "audit_purged_lines": c})
    finally:
        db.close()


if __name__ == "__main__":
    main()
