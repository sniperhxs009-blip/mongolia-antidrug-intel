"""应用入口"""
from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.config import get_settings
from app.crawler.engine import CrawlEngine
from app.db.models import SessionLocal, SystemSetting, init_db
from app.scheduler.jobs import start_scheduler, stop_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("mn-antidrug")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    os.makedirs(settings.reports_dir, exist_ok=True)
    os.makedirs(f"{settings.resolved_data_dir}/raw", exist_ok=True)
    init_db()
    db = SessionLocal()
    try:
        CrawlEngine(db).seed_sources()
        row = db.query(SystemSetting).filter(SystemSetting.key == "crawl_interval").first()
        if row and row.value:
            settings.crawl_interval = row.value
    finally:
        db.close()
    start_scheduler()
    logger.info("%s 已启动", settings.app_name)
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
