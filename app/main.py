"""应用入口"""
from __future__ import annotations

import logging
import os
import secrets
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import get_settings
from app.crawler.engine import CrawlEngine
from app.db.models import SessionLocal, SystemSetting, init_db
from app.scheduler.jobs import start_scheduler, stop_scheduler

# 修改原因：分模块日志级别 DEBUG/INFO/WARN/ERROR
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logging.getLogger("mn-antidrug.crawler").setLevel(logging.INFO)
logging.getLogger("mn-antidrug.email").setLevel(logging.INFO)
logging.getLogger("mn-antidrug.filter").setLevel(logging.WARNING)
logging.getLogger("audit").setLevel(logging.INFO)
logger = logging.getLogger("mn-antidrug")
settings = get_settings()


def _enforce_secret_key() -> None:
    """修改原因：部署强制高强度 SECRET_KEY，禁止默认值上线。"""
    weak = {"", "change-me-to-a-long-random-string", "secret", "changeme"}
    sk = (settings.secret_key or "").strip()
    if sk in weak or len(sk) < 24:
        if os.environ.get("RENDER") or os.environ.get("FORCE_SECURE_SECRET", "").lower() in ("1", "true"):
            raise RuntimeError("SECRET_KEY 过弱：请在环境变量设置 ≥24 位随机串后再启动")
        # 本地开发：自动生成临时密钥并告警
        new_sk = secrets.token_urlsafe(32)
        object.__setattr__(settings, "secret_key", new_sk)
        logger.warning("SECRET_KEY 为默认/过弱值，已生成本地临时密钥（勿用于生产）")


@asynccontextmanager
async def lifespan(app: FastAPI):
    _enforce_secret_key()
    os.makedirs(settings.reports_dir, exist_ok=True)
    os.makedirs(f"{settings.resolved_data_dir}/raw", exist_ok=True)
    os.makedirs(f"{settings.resolved_data_dir}/backups", exist_ok=True)
    init_db()
    db = SessionLocal()
    try:
        CrawlEngine(db).seed_sources()
        row = db.query(SystemSetting).filter(SystemSetting.key == "crawl_interval").first()
        if row and row.value:
            settings.crawl_interval = row.value
    finally:
        db.close()
    # 修改原因：人工部署开关不阻断业务定时任务；仅禁止外部自动部署钩子（见 .cursor/rules）
    start_scheduler()
    logger.info("%s 已启动（manual_deploy=%s）", settings.app_name, settings.require_manual_deploy)
    yield
    stop_scheduler()
    logger.info("应用已关闭")


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.include_router(router)

static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port, reload=False)
