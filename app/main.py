"""程序入口"""
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.api.routes import router as api_router
from app.scheduler.jobs import start_scheduler
from app.db.models import Base, engine
from app.config import get_settings

# 初始化数据表
Base.metadata.create_all(bind=engine)
app = FastAPI(title="蒙古国禁毒情报采集系统")
static_dir = Path(__file__).resolve().parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")
app.include_router(api_router)


@app.on_event("startup")
def startup():
    start_scheduler()


if __name__ == "__main__":
    import uvicorn
    settings = get_settings()
    uvicorn.run("app.main:app", host=settings.app_host, port=settings.app_port)
