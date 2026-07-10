"""数据库ORM完整模型，无修改，原始结构保留"""
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import get_settings

settings = get_settings()


def _ensure_sqlite_dir(db_url: str) -> str:
    """Ensure sqlite parent dir exists; fall back to ./data if /var/data is not writable."""
    if not db_url.startswith("sqlite:///"):
        return db_url
    raw = db_url.replace("sqlite:///", "", 1)
    path = Path(raw)
    # Handle sqlite:////var/data/x.db (4 slashes -> absolute)
    if db_url.startswith("sqlite:////"):
        path = Path("/" + db_url.replace("sqlite:////", "", 1))
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        # probe write
        probe = path.parent / ".write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
        return db_url
    except Exception:
        fallback = Path("data") / "intel.db"
        fallback.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{fallback.resolve().as_posix()}"


db_url = _ensure_sqlite_dir(settings.database_url)
engine = create_engine(db_url, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

class Source(Base):
    __tablename__ = "sources"
    id = Column(Integer, primary_key=True, index=True)
    system_id = Column(Integer)
    system_name = Column(String)
    org_name = Column(String)
    org_name_mn = Column(String)
    base_url = Column(String)
    page_url = Column(String, unique=True)
    is_seed = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    lang = Column(String)
    discover_depth = Column(Integer, default=0)
    last_status = Column(String, default="pending")
    last_crawled_at = Column(DateTime, nullable=True)

class IntelItem(Base):
    __tablename__ = "intel_items"
    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(Integer, ForeignKey("sources.id"))
    system_id = Column(Integer)
    system_name = Column(String)
    org_name = Column(String)
    url = Column(String, unique=True)
    title = Column(Text)
    title_zh = Column(Text)
    summary = Column(Text)
    summary_zh = Column(Text)
    content = Column(Text)
    content_zh = Column(Text)
    lang = Column(String)
    published_at = Column(DateTime, nullable=True)
    crawled_at = Column(DateTime, default=datetime.utcnow)
    content_hash = Column(String)
    intel_level = Column(String, default="一般")
    category = Column(String)
    is_duplicate = Column(Boolean, default=False)
    is_alert = Column(Boolean, default=False)
    status = Column(String, default="new")
    raw_meta = Column(Text)

class Report(Base):
    __tablename__ = "reports"
    id = Column(Integer, primary_key=True)
    report_type = Column(String)
    title = Column(String)
    period_start = Column(DateTime)
    period_end = Column(DateTime)
    content_md = Column(Text)
    content_html = Column(Text)
    file_path = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    emailed = Column(Boolean, default=False)

class CrawlJob(Base):
    __tablename__ = "crawl_jobs"
    id = Column(Integer, primary_key=True)
    status = Column(String)
    started_at = Column(DateTime)
    finished_at = Column(DateTime, nullable=True)
    checkpoint = Column(Text)
    pages_fetched = Column(Integer, default=0)
    items_new = Column(Integer, default=0)
    items_updated = Column(Integer, default=0)
    items_filtered = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    message = Column(Text, nullable=True)

class StatRecord(Base):
    __tablename__ = "stat_records"
    id = Column(Integer, primary_key=True)
    metric_name = Column(String)
    metric_value = Column(String)
    unit = Column(String)
    period = Column(String)
    org_name = Column(String)
    title = Column(Text)
    source_url = Column(String)
    source_type = Column(String)
    raw_snippet = Column(Text)
    confidence = Column(String)
    crawled_at = Column(DateTime, default=datetime.utcnow)

class EmailLog(Base):
    __tablename__ = "email_logs"
    id = Column(Integer, primary_key=True)
    send_time = Column(DateTime, default=datetime.utcnow)
    report_id = Column(Integer, nullable=True)
    subject = Column(String)
    success = Column(Boolean)
    error_msg = Column(Text, nullable=True)

class SystemSetting(Base):
    __tablename__ = "system_settings"
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True)
    value = Column(Text)

class CrawlRecord(Base):
    __tablename__ = "crawl_records"
    id = Column(Integer, primary_key=True)
    host = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

Base.metadata.create_all(bind=engine)
