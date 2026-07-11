"""数据库与报表自动备份 / 宕机恢复。

用法:
  python scripts/backup_db.py backup
  python scripts/backup_db.py restore <backup_zip_path>

修改原因：安全加固——定时备份与恢复逻辑。
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.config import get_settings  # noqa: E402


def _paths():
    s = get_settings()
    data = Path(s.resolved_data_dir)
    db_url = s.database_url
    db_path = None
    if db_url.startswith("sqlite:///"):
        raw = db_url.replace("sqlite:///", "", 1)
        db_path = Path(raw)
        if not db_path.is_absolute():
            db_path = ROOT / db_path
    return data, db_path, data / "backups"


def backup() -> Path:
    data, db_path, backup_dir = _paths()
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    out = backup_dir / f"intel_backup_{stamp}"
    out.mkdir(parents=True, exist_ok=True)
    if db_path and db_path.exists():
        shutil.copy2(db_path, out / db_path.name)
    reports = data / "reports"
    if reports.exists():
        shutil.copytree(reports, out / "reports", dirs_exist_ok=True)
    audit = data / "audit"
    if audit.exists():
        shutil.copytree(audit, out / "audit", dirs_exist_ok=True)
    zip_path = shutil.make_archive(str(out), "zip", root_dir=out)
    shutil.rmtree(out, ignore_errors=True)
    # 仅保留最近 14 份
    zips = sorted(backup_dir.glob("intel_backup_*.zip"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in zips[14:]:
        old.unlink(missing_ok=True)
    print(f"backup ok: {zip_path}")
    return Path(zip_path)


def restore(zip_path: str) -> None:
    data, db_path, backup_dir = _paths()
    src = Path(zip_path)
    if not src.exists():
        raise SystemExit(f"backup not found: {src}")
    tmp = backup_dir / "_restore_tmp"
    if tmp.exists():
        shutil.rmtree(tmp)
    shutil.unpack_archive(str(src), tmp)
    # 找 sqlite
    candidates = list(tmp.rglob("*.db"))
    if candidates and db_path:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(candidates[0], db_path)
        print(f"restored db -> {db_path}")
    rep = next((p for p in tmp.rglob("reports") if p.is_dir()), None)
    if rep:
        dest = data / "reports"
        dest.mkdir(parents=True, exist_ok=True)
        for f in rep.iterdir():
            if f.is_file():
                shutil.copy2(f, dest / f.name)
        print(f"restored reports -> {dest}")
    shutil.rmtree(tmp, ignore_errors=True)
    print("restore complete")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("action", choices=["backup", "restore"])
    p.add_argument("path", nargs="?", default="")
    args = p.parse_args()
    if args.action == "backup":
        backup()
    else:
        if not args.path:
            raise SystemExit("restore requires path")
        restore(args.path)


if __name__ == "__main__":
    main()
