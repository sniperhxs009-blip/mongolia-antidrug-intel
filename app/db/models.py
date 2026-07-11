"""数据库模型与会话管理"""
from __future__ import annotations

import os
from datetime import datetime
from typing import Generator

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    UniqueConstraint,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import get_settings


class Base(DeclarativeBase):
    pass


class Source(Base):
    """数据源（七大体系机构及自动发现的下级页面）"""

    __tablename__ = "sources"
    __table_args__ = (
        UniqueConstraint("org_name", "page_url", name="uq_source_org_page"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    system_id = Column(Integer, nullable=False, index=True)
    system_name = Column(String(128), nullable=False)
    org_name = Column(String(256), nullable=False)
    org_name_mn = Column(String(256), default="")
    base_url = Column(String(512), nullable=False)
    page_url = Column(String(1024), nullable=False, index=True)
    is_seed = Column(Boolean, default=True)
    is_active = Column(Boolean, default=True)
    lang = Column(String(16), default="mn")
    last_crawled_at = Column(DateTime, nullable=True)
    last_status = Column(String(64), default="pending")
    discover_depth = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class IntelItem(Base):
    """结构化情报条目"""

    __tablename__ = "intel_items"
    __table_args__ = (
        # 修改原因：高频查询索引（口岸/毒品类型/告警/发布时间）
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    source_id = Column(Integer, index=True)
    system_id = Column(Integer, index=True)
    system_name = Column(String(128), default="")
    org_name = Column(String(256), default="", index=True)
    url = Column(String(1024), nullable=False, unique=True, index=True)
    title = Column(String(512), default="")
    title_zh = Column(String(512), default="")
    summary = Column(Text, default="")
    summary_zh = Column(Text, default="")
    content = Column(Text, default="")
    content_zh = Column(Text, default="")
    lang = Column(String(16), default="mn")
    published_at = Column(DateTime, nullable=True, index=True)
    crawled_at = Column(DateTime, default=datetime.utcnow, index=True)
    content_hash = Column(String(64), unique=True, index=True)
    intel_level = Column(String(32), default="一般", index=True)  # 一般 / 关注 / 重要 / 紧急
    category = Column(String(64), default="综合", index=True)
    is_alert = Column(Boolean, default=False, index=True)
    is_duplicate = Column(Boolean, default=False)
    status = Column(String(32), default="new")  # new / updated / revoked
    raw_meta = Column(Text, default="{}")
    # 定稿新增字段
    credibility = Column(String(16), default="中", index=True)  # 高/中/低
    alert_kind = Column(String(64), default="", index=True)
    port_tag = Column(String(64), default="", index=True)  # 扎门乌德/甘其毛都/其他
    drug_type = Column(String(64), default="", index=True)


class CrawlJob(Base):
    """爬取任务记录"""

    __tablename__ = "crawl_jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    started_at = Column(DateTime, default=datetime.utcnow, index=True)  # 修改原因：高频查询索引
    finished_at = Column(DateTime, nullable=True)
    status = Column(String(32), default="running", index=True)
    pages_fetched = Column(Integer, default=0)
    items_new = Column(Integer, default=0)
    items_updated = Column(Integer, default=0)
    items_filtered = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    message = Column(Text, default="")
    checkpoint = Column(Text, default="{}")


class Report(Base):
    """研判报告"""

    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    report_type = Column(String(32), default="daily")  # daily / weekly / monthly / alert
    title = Column(String(512), nullable=False)
    period_start = Column(DateTime, nullable=True)
    period_end = Column(DateTime, nullable=True)
    content_md = Column(Text, default="")
    content_html = Column(Text, default="")
    file_path = Column(String(512), default="")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    emailed = Column(Boolean, default=False)


class EmailLog(Base):
    """邮件发送日志"""

    __tablename__ = "email_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    to_addr = Column(String(256), default="")
    subject = Column(String(512), default="")
    kind = Column(String(32), default="daily")  # daily / alert
    success = Column(Boolean, default=False)
    error = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)


class StatRecord(Base):
    """从官方新闻/PDF 抽取的结构化毒情统计点"""

    __tablename__ = "stat_records"
    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_stat_fingerprint"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    intel_id = Column(Integer, nullable=True, index=True)
    system_id = Column(Integer, default=9, index=True)
    system_name = Column(String(128), default="官方统计与年报体系")
    org_name = Column(String(256), default="")
    source_url = Column(String(1024), default="")
    source_type = Column(String(32), default="news_stat")  # news_stat / pdf / manual
    title = Column(String(512), default="")
    metric_name = Column(String(128), default="", index=True)
    metric_value = Column(Float, default=0.0)
    unit = Column(String(32), default="")
    period = Column(String(64), default="", index=True)
    raw_snippet = Column(Text, default="")
    confidence = Column(Float, default=0.7)
    fingerprint = Column(String(64), nullable=False, unique=True, index=True)
    crawled_at = Column(DateTime, default=datetime.utcnow, index=True)


class SystemSetting(Base):
    """运行时配置（可在 Web 控制台修改）"""

    __tablename__ = "system_settings"

    key = Column(String(128), primary_key=True)
    value = Column(Text, default="")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


def _ensure_data_dir(db_url: str) -> None:
    if db_url.startswith("sqlite:///"):
        path = db_url.replace("sqlite:///", "", 1)
        if path.startswith("./"):
            path = path[2:]
        directory = os.path.dirname(path)
        if directory:
            os.makedirs(directory, exist_ok=True)


settings = get_settings()
_ensure_data_dir(settings.database_url)

connect_args = {"check_same_thread": False, "timeout": 60} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)

if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):  # noqa: ARG001
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    # SQLite 增量列（旧库兼容）
    if settings.database_url.startswith("sqlite"):
        with engine.begin() as conn:
            cols = {r[1] for r in conn.exec_driver_sql("PRAGMA table_info(intel_items)").fetchall()}
            for col, decl in (
                ("credibility", "VARCHAR(16) DEFAULT '中'"),
                ("alert_kind", "VARCHAR(64) DEFAULT ''"),
                ("port_tag", "VARCHAR(64) DEFAULT ''"),
                ("drug_type", "VARCHAR(64) DEFAULT ''"),
            ):
                if col not in cols:
                    conn.exec_driver_sql(f"ALTER TABLE intel_items ADD COLUMN {col} {decl}")
    data_dir = settings.resolved_data_dir
    os.makedirs(f"{data_dir}/reports", exist_ok=True)
    os.makedirs(f"{data_dir}/raw", exist_ok=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
