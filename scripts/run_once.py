"""手动触发一轮采集+研判（本地调试）"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.db.models import SessionLocal, init_db
from app.pipeline import run_intel_cycle


def main():
    init_db()
    db = SessionLocal()
    try:
        result = run_intel_cycle(db, report_type="daily", send_email=False)
        print(result)
    finally:
        db.close()


if __name__ == "__main__":
    main()
