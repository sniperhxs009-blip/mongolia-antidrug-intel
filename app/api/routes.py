"""FastAPI 路由：情报指挥台、实时进度 SSE、API"""
from __future__ import annotations

import json
import threading
import time
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db.models import CrawlJob, EmailLog, IntelItem, Report, Source, SystemSetting, get_db
from app.pipeline import run_intel_cycle
from app.progress import progress_hub
from app.scheduler.jobs import reschedule_crawl

router = APIRouter()
templates = Jinja2Templates(directory="app/templates")
settings = get_settings()


def _run_cycle_with_progress(run_id: str, report_type: str = "daily") -> None:
    from app.db.models import SessionLocal

    prog = progress_hub.get(run_id)
    if not prog:
        return

    def on_event(event_type: str, **payload):
        prog.emit(event_type, **payload)

    db = SessionLocal()
    try:
        run_intel_cycle(db, report_type=report_type, send_email=True, on_event=on_event)
    except Exception as exc:  # noqa: BLE001
        prog.emit("error", status="failed", phase="失败", message=str(exc))
    finally:
        db.close()


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    intel_count = db.query(IntelItem).count()
    source_count = db.query(Source).filter(Source.is_active.is_(True)).count()
    report_count = db.query(Report).count()
    alert_count = db.query(IntelItem).filter(IntelItem.is_alert.is_(True)).count()
    latest_items = (
        db.query(IntelItem).order_by(IntelItem.crawled_at.desc()).limit(30).all()
    )
    latest_reports = db.query(Report).order_by(Report.created_at.desc()).limit(6).all()
    latest_jobs = db.query(CrawlJob).order_by(CrawlJob.started_at.desc()).limit(5).all()
    systems = (
        db.query(Source.system_id, Source.system_name)
        .distinct()
        .order_by(Source.system_id)
        .all()
    )
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "app_name": settings.app_name,
            "intel_count": intel_count,
            "source_count": source_count,
            "report_count": report_count,
            "alert_count": alert_count,
            "latest_items": latest_items,
            "latest_reports": latest_reports,
            "latest_jobs": latest_jobs,
            "systems": systems,
            "crawl_interval": settings.crawl_interval,
            "email_configured": bool(settings.smtp_user and settings.smtp_password and settings.email_to),
            "now": datetime.utcnow(),
        },
    )


@router.get("/api/health")
def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat(), "app": settings.app_name}


@router.get("/api/stats")
def stats(db: Session = Depends(get_db)):
    return {
        "intel_items": db.query(IntelItem).count(),
        "sources": db.query(Source).count(),
        "reports": db.query(Report).count(),
        "alerts": db.query(IntelItem).filter(IntelItem.is_alert.is_(True)).count(),
        "jobs": db.query(CrawlJob).count(),
        "emails": db.query(EmailLog).count(),
    }


@router.get("/api/intel")
def list_intel(
    db: Session = Depends(get_db),
    limit: int = 50,
    system_id: Optional[int] = None,
    alert_only: bool = False,
):
    q = db.query(IntelItem).order_by(IntelItem.crawled_at.desc())
    if system_id:
        q = q.filter(IntelItem.system_id == system_id)
    if alert_only:
        q = q.filter(IntelItem.is_alert.is_(True))
    rows = q.limit(min(limit, 200)).all()
    return [
        {
            "id": r.id,
            "title": r.title_zh or r.title,
            "org": r.org_name,
            "system": r.system_name,
            "level": r.intel_level,
            "category": r.category,
            "url": r.url,
            "published_at": r.published_at.isoformat() if r.published_at else None,
            "crawled_at": r.crawled_at.isoformat() if r.crawled_at else None,
            "is_alert": r.is_alert,
        }
        for r in rows
    ]


@router.get("/api/sources")
def list_sources(db: Session = Depends(get_db)):
    rows = db.query(Source).order_by(Source.system_id, Source.id).all()
    return [
        {
            "id": s.id,
            "system_id": s.system_id,
            "system_name": s.system_name,
            "org_name": s.org_name,
            "page_url": s.page_url,
            "is_seed": s.is_seed,
            "is_active": s.is_active,
            "last_status": s.last_status,
            "last_crawled_at": s.last_crawled_at.isoformat() if s.last_crawled_at else None,
            "discover_depth": s.discover_depth,
        }
        for s in rows
    ]


@router.get("/api/reports")
def list_reports(db: Session = Depends(get_db), limit: int = 20):
    rows = db.query(Report).order_by(Report.created_at.desc()).limit(limit).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "type": r.report_type,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "emailed": r.emailed,
            "file_path": r.file_path,
        }
        for r in rows
    ]


@router.get("/api/reports/{report_id}")
def get_report(report_id: int, db: Session = Depends(get_db)):
    r = db.query(Report).filter(Report.id == report_id).first()
    if not r:
        return JSONResponse({"error": "not found"}, status_code=404)
    return {
        "id": r.id,
        "title": r.title,
        "type": r.report_type,
        "content_md": r.content_md,
        "content_html": r.content_html,
        "created_at": r.created_at.isoformat() if r.created_at else None,
    }


@router.get("/api/crawl/status")
def crawl_status(run_id: Optional[str] = None):
    prog = progress_hub.get(run_id) if run_id else progress_hub.current()
    if not prog:
        return {"status": "idle", "busy": False}
    snap = prog.snapshot()
    snap["busy"] = prog.status in ("queued", "running", "analyzing", "emailing")
    return snap


@router.post("/api/crawl/run")
def trigger_crawl(report_type: str = "daily"):
    if progress_hub.is_busy():
        cur = progress_hub.current()
        return JSONResponse(
            {
                "status": "busy",
                "message": "已有巡检任务正在执行",
                "run_id": cur.run_id if cur else None,
                "progress": cur.snapshot() if cur else None,
            },
            status_code=409,
        )
    prog = progress_hub.create(report_type=report_type)
    t = threading.Thread(
        target=_run_cycle_with_progress,
        args=(prog.run_id, report_type),
        daemon=True,
        name=f"crawl-{prog.run_id}",
    )
    t.start()
    return {"status": "started", "report_type": report_type, "run_id": prog.run_id}


@router.get("/api/crawl/stream")
def crawl_stream(run_id: Optional[str] = None):
    """SSE：实时推送巡检进度与逐条情报事件。"""

    def event_generator():
        last_len = 0
        idle_ticks = 0
        while True:
            prog = progress_hub.get(run_id) if run_id else progress_hub.current()
            if not prog:
                yield f"data: {json.dumps({'type': 'idle', 'message': '无活动任务'}, ensure_ascii=False)}\n\n"
                break

            snap = prog.snapshot()
            events = snap.get("events") or []
            if len(events) > last_len:
                for evt in events[last_len:]:
                    payload = {"type": "event", "event": evt, "progress": {
                        k: snap[k] for k in (
                            "run_id", "status", "phase", "message", "percent",
                            "total_sources", "current_index", "pages_fetched",
                            "items_new", "items_updated", "items_filtered",
                            "error_count", "current_org", "current_url", "report_id",
                        )
                    }}
                    yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
                last_len = len(events)
                idle_ticks = 0
            else:
                # 心跳，保持连接
                heartbeat = {
                    "type": "heartbeat",
                    "progress": {
                        "status": snap["status"],
                        "phase": snap["phase"],
                        "percent": snap["percent"],
                        "message": snap["message"],
                        "current_org": snap["current_org"],
                        "items_new": snap["items_new"],
                        "pages_fetched": snap["pages_fetched"],
                        "report_id": snap["report_id"],
                    },
                }
                yield f"data: {json.dumps(heartbeat, ensure_ascii=False)}\n\n"
                idle_ticks += 1

            if snap["status"] in ("success", "failed") and idle_ticks >= 2:
                yield f"data: {json.dumps({'type': 'closed', 'progress': snap}, ensure_ascii=False)}\n\n"
                break
            time.sleep(0.6)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/api/schedule")
def update_schedule(interval: str = Form(...)):
    if interval not in ("hourly", "every_6h", "every_12h", "daily"):
        return JSONResponse({"error": "invalid interval"}, status_code=400)
    reschedule_crawl(interval)
    from app.db.models import SessionLocal

    db = SessionLocal()
    try:
        row = db.query(SystemSetting).filter(SystemSetting.key == "crawl_interval").first()
        if row:
            row.value = interval
        else:
            db.add(SystemSetting(key="crawl_interval", value=interval))
        db.commit()
    finally:
        db.close()
    return RedirectResponse(url="/", status_code=303)


@router.get("/reports/{report_id}", response_class=HTMLResponse)
def report_page(report_id: int, request: Request, db: Session = Depends(get_db)):
    r = db.query(Report).filter(Report.id == report_id).first()
    if not r:
        return HTMLResponse("报告不存在", status_code=404)
    return templates.TemplateResponse(
        "report.html",
        {"request": request, "report": r, "app_name": settings.app_name},
    )


@router.get("/sources", response_class=HTMLResponse)
def sources_page(request: Request, db: Session = Depends(get_db)):
    rows = db.query(Source).order_by(Source.system_id, Source.id).all()
    return templates.TemplateResponse(
        "sources.html",
        {"request": request, "sources": rows, "app_name": settings.app_name},
    )
